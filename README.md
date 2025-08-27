# Sophia-1st-MVP

Sophia AI Backend

Sophia is an AI-powered conversational backend built with FastAPI.
It integrates transcription, LLM response generation, text-to-speech synthesis, emotion analysis, and Supabase for storage & persistence.

🚀 Features

Speech-to-text transcription with Voxtral/Mistral.

LLM-powered replies via Mistral & Gemini APIs.

Text-to-speech synthesis (Inworld).

Emotion detection from text and audio.

Supabase storage & database integration for conversation history.

REST API built with FastAPI + rate limiting.

📦 Setup (Local Development)
1. Clone the repo
git clone https://github.com/yourusername/sophia-ai-backend.git
cd sophia-ai-backend

2. Create a virtual environment
python -m venv venv
venv\Scripts\activate    # On Windows
# OR
source venv/bin/activate # On Linux/Mac

3. Install dependencies
pip install -r requirements.txt

4. Environment variables

Create a .env file at the root (already referenced in code):

APP_NAME=Sophia AI Backend
API_RATE_LIMIT=5/minute

SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_KEY=<your-service-role-or-anon-key>
SUPABASE_BUCKET_AUDIO=audio
SUPABASE_AUDIO_PREFIX=uploads/

# Optional: direct DSN if using Postgres directly
SUPABASE_DB_DSN=postgresql://user:pass@host:5432/dbname


⚠️ Make sure SUPABASE_URL starts with https://.

5. Run the backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload


The API will be available at:
👉 http://localhost:8000

👉 Interactive docs: http://localhost:8000/docs

🐳 Running with Docker
1. Build the image
docker build -t sophia-backend .

2. Run the container
docker run -d \
  --name sophia-backend \
  -p 8000:8000 \
  --env-file .env \
  sophia-backend


Now visit:
👉 http://localhost:8000/docs

📝 Project Structure
Sophia-1st-MVP/
│
├── main.py                # FastAPI entrypoint
├── requirements.txt        # Python dependencies
├── app/
│   ├── services/
│   │   ├── supabase.py     # Supabase storage/db logic
│   │   ├── tts.py          # TTS synthesis
│   │   ├── mistral.py      # Transcription + LLM reply
│   │   └── emotion.py      # Emotion detection
│   └── config.py           # Settings loader
├── .env                    # Environment variables
└── Dockerfile              # Docker instructions

🧪 API Endpoints

POST /transcribe → Transcribes .wav audio, returns text + emotion.

POST /generate-response → Generates AI reply from text.

POST /synthesize → Synthesizes AI speech, uploads audio to Supabase.

POST /chat → Full pipeline (transcribe → LLM reply → synthesize → persist).


#to test the api:

python test_api.py