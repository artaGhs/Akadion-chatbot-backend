"""
RAG (Retrieval-Augmented Generation) service.
Orchestrates the retrieval-augmentation-generation process for question answering.
"""

import asyncio
from typing import List, AsyncGenerator, Tuple
import google.generativeai as genai
import chromadb
from langchain.prompts import ChatPromptTemplate

from ..core.config import settings
from ..models.schemas import ChatRequest, ChatResponse
from .conversation_manager import conversation_manager


class RAGService:
    """Service for handling Retrieval-Augmented Generation."""
    
    def __init__(self):
        """Initialize the RAG service with ChromaDB and Gemini models."""
        # Configure Google Generative AI
        genai.configure(api_key=settings.google_api_key)
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chromadb_persist_directory
        )
        
        # Get the collection
        try:
            self.collection = self.chroma_client.get_collection(
                name=settings.collection_name
            )
        except Exception:
            # Collection doesn't exist yet, create it
            self.collection = self.chroma_client.create_collection(
                name=settings.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        
        # Initialize the generative model
        self.model = genai.GenerativeModel(settings.gemini_model)
        
        # Create the prompt template using configurable system prompt
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", settings.system_prompt),
            ("human", "{question}")
        ])
    
    async def generate_response(self, request: ChatRequest) -> ChatResponse:
        """
        Generate a response using RAG pipeline.
        
        Args:
            request: Chat request containing the user's message
            
        Returns:
            ChatResponse with generated answer and sources
        """
        try:
            # Step 1: Add user message to conversation
            conversation_manager.add_message(request.session_id, "user", request.message)
            
            # Step 2: Generate query embedding
            query_embedding = await self._generate_query_embedding(request.message)
            
            # Step 3: Retrieve relevant context
            relevant_chunks, sources = await self._retrieve_context(
                query_embedding, request.message
            )
            
            # Step 4: Generate response using LLM
            if not relevant_chunks:
                response_text = "I don't have any relevant information in my knowledge base to answer your question. Please upload some documents first or ask about something that might be covered in the uploaded documents."
                sources = []
            else:
                response_text = await self._generate_llm_response(
                    request.message, relevant_chunks, request.session_id
                )
            
            # Step 5: Add assistant response to conversation
            conversation_manager.add_message(request.session_id, "assistant", response_text)
            
            return ChatResponse(
                response=response_text,
                sources=sources
            )
            
        except Exception as e:
            return ChatResponse(
                response=f"I apologize, but I encountered an error while processing your question: {str(e)}",
                sources=[]
            )
    
    async def generate_streaming_response(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using RAG pipeline.
        
        Args:
            request: Chat request containing the user's message
            
        Yields:
            String chunks of the response as they are generated
        """
        try:
            # Step 1: Add user message to conversation
            conversation_manager.add_message(request.session_id, "user", request.message)
            
            # Step 2: Generate query embedding
            query_embedding = await self._generate_query_embedding(request.message)
            
            # Step 3: Retrieve relevant context
            relevant_chunks, sources = await self._retrieve_context(
                query_embedding, request.message
            )
            
            # Step 4: Generate streaming response using LLM
            if not relevant_chunks:
                response_text = "I don't have any relevant information in my knowledge base to answer your question. Please upload some documents first or ask about something that might be covered in the uploaded documents."
                conversation_manager.add_message(request.session_id, "assistant", response_text)
                yield response_text
            else:
                # Collect streaming chunks to save complete response to conversation
                complete_response = ""
                async for chunk in self._generate_streaming_llm_response(
                    request.message, relevant_chunks, request.session_id
                ):
                    complete_response += chunk
                    yield chunk
                
                # Step 5: Add complete assistant response to conversation
                conversation_manager.add_message(request.session_id, "assistant", complete_response)
                    
        except Exception as e:
            yield f"I apologize, but I encountered an error while processing your question: {str(e)}"
    
    async def _generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for the user's query."""
        def generate_embedding_sync():
            result = genai.embed_content(
                model=settings.embedding_model,
                content=query,
                task_type="RETRIEVAL_QUERY"
            )
            return result["embedding"]
        
        # Run embedding generation in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, generate_embedding_sync)
    
    async def _retrieve_context(self, query_embedding: List[float], query: str) -> Tuple[List[str], List[str]]:
        """
        Retrieve relevant context chunks from the vector database.
        
        Args:
            query_embedding: Vector embedding of the user's query
            query: Original query text for fallback search
            
        Returns:
            Tuple of (relevant_chunks, sources)
        """
        def retrieve_sync():
            try:
                # Perform similarity search
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=settings.max_retrieval_chunks,
                    include=["documents", "metadatas"]
                )
                
                if not results["documents"] or not results["documents"][0]:
                    return [], []
                
                documents = results["documents"][0]
                metadatas = results["metadatas"][0] if results["metadatas"] else []
                
                # Extract sources
                sources = []
                for metadata in metadatas:
                    if metadata and "source" in metadata:
                        source = metadata["source"]
                        if source not in sources:
                            sources.append(source)
                
                return documents, sources
                
            except Exception as e:
                print(f"Error retrieving context: {e}")
                return [], []
        
        # Run retrieval in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, retrieve_sync)
    
    async def _generate_llm_response(self, question: str, context_chunks: List[str], session_id: str) -> str:
        """Generate response using the LLM with retrieved context and conversation history."""
        # Combine context chunks
        context = "\n\n".join(context_chunks)
        
        # Get conversation history (excluding the current message)
        conversation_history = conversation_manager.get_conversation_context(session_id, include_current=False)
        
        # Create the prompt with both context and conversation history
        prompt = self.prompt_template.format_messages(
            context=context,
            conversation_history=conversation_history if conversation_history else "No previous conversation.",
            question=question
        )
        
        # Convert to string format for Gemini
        prompt_text = ""
        for message in prompt:
            if message.type == "system":
                prompt_text += f"System: {message.content}\n\n"
            elif message.type == "human":
                prompt_text += f"Human: {message.content}\n\n"
        
        def generate_sync():
            response = self.model.generate_content(
                prompt_text,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.temperature,
                    max_output_tokens=2048,
                )
            )
            return response.text
        
        # Run generation in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, generate_sync)
    
    async def _generate_streaming_llm_response(self, question: str, context_chunks: List[str], session_id: str) -> AsyncGenerator[str, None]:
        """Generate streaming response using the LLM with retrieved context and conversation history."""
        # Combine context chunks
        context = "\n\n".join(context_chunks)
        
        # Get conversation history (excluding the current message)
        conversation_history = conversation_manager.get_conversation_context(session_id, include_current=False)
        
        # Create the prompt with both context and conversation history
        prompt = self.prompt_template.format_messages(
            context=context,
            conversation_history=conversation_history if conversation_history else "No previous conversation.",
            question=question
        )
        
        # Convert to string format for Gemini
        prompt_text = ""
        for message in prompt:
            if message.type == "system":
                prompt_text += f"System: {message.content}\n\n"
            elif message.type == "human":
                prompt_text += f"Human: {message.content}\n\n"
        
        def generate_streaming_sync():
            response = self.model.generate_content(
                prompt_text,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.temperature,
                    max_output_tokens=2048,
                ),
                stream=True
            )
            return response
        
        # Run generation in thread pool and yield chunks
        loop = asyncio.get_event_loop()
        response_stream = await loop.run_in_executor(None, generate_streaming_sync)
        
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
    
    def get_collection_stats(self) -> dict:
        """Get statistics about the vector database collection."""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": settings.collection_name,
                "max_retrieval_chunks": settings.max_retrieval_chunks
            }
        except Exception as e:
            return {"error": str(e)} 