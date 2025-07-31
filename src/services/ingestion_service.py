"""
Ingestion service for processing uploaded knowledge base files.
Handles file processing, text extraction, chunking, vectorization, and storage.
"""

import os
import uuid
import asyncio
from typing import List, Tuple
from pathlib import Path

import fitz  # PyMuPDF
import google.generativeai as genai
import chromadb
from fastapi import UploadFile, HTTPException
from langchain.text_splitter import RecursiveCharacterTextSplitter

from ..core.config import settings
from ..models.schemas import TextChunk, FileUploadResponse


class IngestionService:
    """Service for handling file ingestion and knowledge base population."""
    
    def __init__(self):
        """Initialize the ingestion service with ChromaDB and text splitter."""
        # Configure Google Generative AI
        genai.configure(api_key=settings.google_api_key)
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chromadb_persist_directory
        )
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    async def process_file(self, file: UploadFile) -> FileUploadResponse:
        """
        Process an uploaded file and add it to the knowledge base.
        
        Args:
            file: The uploaded file object
            
        Returns:
            FileUploadResponse with processing results
        """
        try:
            # Validate file
            self._validate_file(file)
            
            # Save file temporarily
            temp_file_path = await self._save_temp_file(file)
            
            try:
                # Extract text from file
                text_content = await self._extract_text(temp_file_path, file.filename)
                
                # Chunk the text
                text_chunks = self._chunk_text(text_content, file.filename)
                
                # Generate embeddings and store in ChromaDB
                chunks_processed = await self._store_chunks(text_chunks)
                
                return FileUploadResponse(
                    message="File processed successfully",
                    filename=file.filename,
                    chunks_processed=chunks_processed,
                    success=True
                )
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file size and type."""
        if file.size > settings.max_file_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {settings.max_file_size} bytes"
            )
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.allowed_file_types:
            raise HTTPException(
                status_code=415,
                detail=f"File type not supported. Allowed types: {settings.allowed_file_types}"
            )
    
    async def _save_temp_file(self, file: UploadFile) -> str:
        """Save uploaded file to temporary location."""
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
        
        with open(temp_file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        return temp_file_path
    
    async def _extract_text(self, file_path: str, filename: str) -> str:
        """Extract text from PDF or text files."""
        file_extension = Path(filename).suffix.lower()
        
        if file_extension == ".pdf":
            return await self._extract_pdf_text(file_path)
        elif file_extension == ".txt":
            return await self._extract_txt_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    async def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF using PyMuPDF."""
        def extract_text_sync():
            text_content = ""
            with fitz.open(file_path) as doc:
                for page in doc:
                    text_content += page.get_text()
            return text_content
        
        # Run PDF extraction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_text_sync)
    
    async def _extract_txt_text(self, file_path: str) -> str:
        """Extract text from plain text files."""
        def read_text_sync():
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, read_text_sync)
    
    def _chunk_text(self, text: str, source_filename: str) -> List[TextChunk]:
        """Split text into chunks using RecursiveCharacterTextSplitter."""
        chunks = self.text_splitter.split_text(text)
        
        text_chunks = []
        for i, chunk_text in enumerate(chunks):
            chunk = TextChunk(
                id=f"{source_filename}_{i}_{uuid.uuid4().hex[:8]}",
                text=chunk_text.strip(),
                source=source_filename,
                page_number=None  # Could be enhanced to track page numbers for PDFs
            )
            text_chunks.append(chunk)
        
        return text_chunks
    
    async def _store_chunks(self, text_chunks: List[TextChunk]) -> int:
        """Generate embeddings and store chunks in ChromaDB."""
        if not text_chunks:
            return 0
        
        # Generate embeddings for all chunks
        texts = [chunk.text for chunk in text_chunks]
        embeddings = await self._generate_embeddings(texts)
        
        # Prepare data for ChromaDB
        ids = [chunk.id for chunk in text_chunks]
        metadatas = []
        for chunk in text_chunks:
            metadata = {
                "source": str(chunk.source),  # Ensure source is always a string
                "text_length": len(chunk.text)
            }
            # Only add page_number if it's not None
            if chunk.page_number is not None:
                metadata["page_number"] = int(chunk.page_number)  # Ensure page_number is an integer
            metadatas.append(metadata)
        
        documents = texts
        
        # Store in ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        
        return len(text_chunks)
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Google Generative AI."""
        def generate_embeddings_sync():
            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model=settings.embedding_model,
                    content=text,
                    task_type="RETRIEVAL_DOCUMENT"
                )
                embeddings.append(result["embedding"])
            return embeddings
        
        # Run embedding generation in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, generate_embeddings_sync)
    
    async def clear_knowledge_base(self) -> bool:
        """Clear all documents from the knowledge base."""
        try:
            # Delete the collection and recreate it
            self.chroma_client.delete_collection(name=settings.collection_name)
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            return True
        except Exception as e:
            print(f"Error clearing knowledge base: {e}")
            return False
    
    def get_knowledge_base_stats(self) -> dict:
        """Get statistics about the current knowledge base."""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": settings.collection_name
            }
        except Exception as e:
            return {"error": str(e)} 