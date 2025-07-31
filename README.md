# RAG Chatbot Backend

A sophisticated Retrieval-Augmented Generation (RAG) chatbot backend built with FastAPI and Google Gemini. This system allows you to upload documents to create a knowledge base and then ask questions that will be answered using the uploaded content.

## Features

- 🚀 **High-Performance**: Built with FastAPI for excellent async performance
- 🤖 **Google Gemini Integration**: Powered by Google's latest language models
- 📚 **Knowledge Base**: Upload PDFs and text files to create a searchable knowledge base
- 🔍 **Vector Search**: ChromaDB for efficient similarity search
- 💨 **Streaming Responses**: Real-time response streaming for better UX
- 🏗️ **Production Ready**: Layered architecture with proper error handling
- 📖 **Auto Documentation**: Interactive API docs with Swagger UI

## Architecture

The application follows a layered architecture pattern:

```
src/
├── api/           # API endpoints and routing
├── services/      # Business logic and core services
├── models/        # Pydantic models for data validation
├── core/          # Configuration and core components
└── main.py        # FastAPI application entry point
```

## Prerequisites

- Python 3.8 or higher
- Google API key for Gemini
- Virtual environment (recommended)

## Quick Start

### 1. Clone and Setup

```bash
# Navigate to your project directory
cd /path/to/your/chatbot/project

# Activate your virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root with your configuration:

```env
# REQUIRED: Google Gemini API Key
GOOGLE_API_KEY=your_google_api_key_here

# Optional configurations (defaults shown)
APP_NAME=RAG Chatbot Backend
DEBUG=false
HOST=0.0.0.0
PORT=8000
GEMINI_MODEL=gemini-pro
EMBEDDING_MODEL=models/embedding-001
CHROMADB_PERSIST_DIRECTORY=./chroma_db
COLLECTION_NAME=knowledge_base
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_RETRIEVAL_CHUNKS=5
TEMPERATURE=0.1
MAX_FILE_SIZE=10485760
```

### 3. Get Your Google API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file

### 4. Run the Application

```bash
# Option 1: Using the startup script
python run.py

# Option 2: Using uvicorn directly
uvicorn src.main:app --reload

# Option 3: Using the main module
python -m src.main
```

The application will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Core Endpoints

#### Health Check
```http
GET /health
```

#### Upload Documents
```http
POST /ingest/upload
Content-Type: multipart/form-data

{
  "file": "document.pdf"
}
```

#### Chat (Non-streaming)
```http
POST /chat/
Content-Type: application/json

{
  "message": "What is the main topic of the uploaded document?",
  "stream": false
}
```

#### Chat (Streaming)
```http
POST /chat/stream
Content-Type: application/json

{
  "message": "Explain the key concepts in detail",
  "stream": true
}
```

### Management Endpoints

#### Clear Knowledge Base
```http
DELETE /ingest/clear
```

#### Get Statistics
```http
GET /chat/stats
GET /ingest/stats
```

## Usage Examples

### 1. Upload a Document

```bash
curl -X POST "http://localhost:8000/ingest/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### 2. Ask a Question

```bash
curl -X POST "http://localhost:8000/chat/" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the main points discussed in the document?",
    "stream": false
  }'
```

### 3. Streaming Chat

```bash
curl -X POST "http://localhost:8000/chat/stream" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Provide a detailed summary",
    "stream": true
  }'
```

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key (required) | - |
| `APP_NAME` | Application name | "RAG Chatbot Backend" |
| `DEBUG` | Enable debug mode | false |
| `HOST` | Server host | "0.0.0.0" |
| `PORT` | Server port | 8000 |
| `GEMINI_MODEL` | Gemini model to use | "gemini-pro" |
| `EMBEDDING_MODEL` | Embedding model | "models/embedding-001" |
| `CHROMADB_PERSIST_DIRECTORY` | ChromaDB storage path | "./chroma_db" |
| `COLLECTION_NAME` | Vector collection name | "knowledge_base" |
| `CHUNK_SIZE` | Text chunk size | 1000 |
| `CHUNK_OVERLAP` | Overlap between chunks | 200 |
| `MAX_RETRIEVAL_CHUNKS` | Max chunks to retrieve | 5 |
| `TEMPERATURE` | LLM temperature | 0.1 |
| `MAX_FILE_SIZE` | Max upload size (bytes) | 10485760 (10MB) |

## File Support

- **PDF Files**: Extracted using PyMuPDF for robust text extraction
- **Text Files**: Plain text files (.txt)
- **Size Limit**: 10MB by default (configurable)

## Development

### Project Structure

- `src/api/`: API layer with routers and endpoints
- `src/services/`: Business logic and service classes
- `src/models/`: Pydantic models for data validation
- `src/core/`: Configuration and shared components
- `tests/`: Test suite (ready for pytest)

### Adding New Features

1. **New API Endpoint**: Add to appropriate router in `src/api/`
2. **Business Logic**: Implement in `src/services/`
3. **Data Models**: Define in `src/models/schemas.py`
4. **Configuration**: Add to `src/core/config.py`

## Troubleshooting

### Common Issues

1. **Missing API Key**: Ensure `GOOGLE_API_KEY` is set in `.env`
2. **Import Errors**: Make sure you're in the project root and virtual environment is activated
3. **Port Already in Use**: Change the `PORT` in `.env` or kill the process using the port
4. **File Upload Errors**: Check file size limits and supported formats

### Logging

Enable debug mode for detailed logging:
```env
DEBUG=true
```

## License

This project is open source and available under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

Built with ❤️ using FastAPI, Google Gemini, and ChromaDB. 