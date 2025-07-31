#!/usr/bin/env python3
"""
Startup script for the RAG Chatbot Backend.
This script provides an easy way to run the application.
"""

import uvicorn
from src.core.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.app_name}...")
    print(f"Server will be available at: http://{settings.host}:{settings.port}")
    print(f"API Documentation: http://{settings.host}:{settings.port}/docs")
    print(f"Health Check: http://{settings.host}:{settings.port}/health")
    print("\nMake sure you have set your GOOGLE_API_KEY in the .env file!")
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        access_log=True
    ) 