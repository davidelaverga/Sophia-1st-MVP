# Sophia Backend API

## Setup Instructions

1. Clone the repository
2. Create a `.env` file in the root directory with the following variables:
```
MISTRAL_API_KEY=your_mistral_key
INWORLD_API_KEY=your_inworld_key
GOOGLE_API_KEY=your_google_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
SUPABASE_KEY=your_key
SUPABASE_DB_DSN=your_db_dsn
SUPABASE_BUCKET_AUDIO=audio
SUPABASE_AUDIO_PREFIX=uploads/
API_KEYS=your_api_key
API_RATE_LIMIT=30/minute
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
python main.py
```
Or with uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on http://localhost:8000

## API Endpoints

- POST `/transcribe` - Transcribe audio file
- POST `/chat` - Complete conversation flow with audio

## Docker Deployment

Build and run with Docker:
```bash
docker build -t sophia-backend .
docker run -p 8000:8000 sophia-backend
```
