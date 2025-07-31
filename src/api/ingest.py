"""
Ingestion API endpoints for handling file uploads and knowledge base management.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List

from ..models.schemas import FileUploadResponse, ErrorResponse
from ..services.ingestion_service import IngestionService

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# Initialize ingestion service
ingestion_service = IngestionService()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> FileUploadResponse:
    """
    Upload and process a file to add to the knowledge base.
    
    Args:
        background_tasks: FastAPI background tasks for processing
        file: The uploaded file (PDF or TXT)
        
    Returns:
        FileUploadResponse with processing results
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Process the file
        result = await ingestion_service.process_file(file)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.post("/upload-multiple")
async def upload_multiple_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
) -> List[FileUploadResponse]:
    """
    Upload and process multiple files to add to the knowledge base.
    
    Args:
        background_tasks: FastAPI background tasks for processing
        files: List of uploaded files (PDF or TXT)
        
    Returns:
        List of FileUploadResponse with processing results for each file
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        results = []
        for file in files:
            try:
                if file.filename:
                    result = await ingestion_service.process_file(file)
                    results.append(result)
                else:
                    results.append(FileUploadResponse(
                        message="No filename provided",
                        filename="unknown",
                        chunks_processed=0,
                        success=False
                    ))
            except Exception as e:
                results.append(FileUploadResponse(
                    message=f"Error processing file: {str(e)}",
                    filename=file.filename or "unknown",
                    chunks_processed=0,
                    success=False
                ))
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading files: {str(e)}")


@router.delete("/clear")
async def clear_knowledge_base():
    """
    Clear all documents from the knowledge base.
    
    Returns:
        Success message
    """
    try:
        success = await ingestion_service.clear_knowledge_base()
        
        if success:
            return {"message": "Knowledge base cleared successfully", "success": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear knowledge base")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing knowledge base: {str(e)}")


@router.get("/stats")
async def get_ingestion_stats():
    """
    Get statistics about the knowledge base.
    
    Returns:
        Dictionary with knowledge base statistics
    """
    try:
        stats = ingestion_service.get_knowledge_base_stats()
        return {
            "status": "healthy",
            **stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving ingestion stats: {str(e)}") 