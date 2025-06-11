# Project Sam - Admin Links Retrieval System

An intelligent system that understands natural language queries, retrieves relevant admin links from a local JSON dataset, and uses a Large Language Model (LLM) to generate helpful, natural language responses.

## Features

- Natural language query processing
- Semantic search for admin links
- LLM-powered response generation
- REST API endpoints
- JSON-based data storage

## Getting Started

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run the application:
   ```bash
   python api/app.py
   ```

## Project Structure

- `backend/` - Backend API and core logic
- `backend/core/` - Core business logic
- `backend/api/` - REST API endpoints
- `backend/config/` - Configuration files
- `backend/data/` - JSON datasets
