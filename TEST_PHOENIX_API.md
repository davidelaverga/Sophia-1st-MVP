# PhoenixClient API Testing Guide

## Task #42841 - PhoenixClient Implementation

###  API Endpoints Created

#### 1. **POST `/api/phoenix/classify`** - Emotion Classification

Classifies emotion from text using OpenAI API.

**Request:**
```bash
curl -X POST http://localhost:8000/api/phoenix/classify \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I'\''m really worried about the exam tomorrow",
    "prosody_context": "pitch: high, pace: fast"
  }'
```

**Response:**
```json
{
  "label": "anxious",
  "confidence": 0.87,
  "safety_flag": false,
  "source": "phoenix"
}
```

#### 2. **GET `/api/phoenix/health`** - Health Check

Checks if Phoenix is configured and available.

**Request:**
```bash
curl http://localhost:8000/api/phoenix/health
```

**Response:**
```json
{
  "status": "healthy",
  "openai_configured": true,
  "model": "gpt-4o-mini",
  "timeout_seconds": 12.0,
  "valid_emotions": [
    "joy", "excited", "sad", "anxious", "grief", "panic",
    "anger", "fearful", "calm", "neutral", "hopeful", "lonely"
  ]
}
```

## Test Cases for Frontend

### 1. Anxious User
```json
{
  "text": "I can't stop thinking about the presentation tomorrow, I'm so nervous",
  "prosody_context": "pitch: high, pace: fast, energy: medium"
}
```
**Expected:** `label: "anxious", confidence: ~0.85`

### 2. Happy/Excited User
```json
{
  "text": "I just got my dream job! This is amazing!",
  "prosody_context": "pitch: very high, pace: fast, energy: very high"
}
```
**Expected:** `label: "excited", confidence: ~0.90`

### 3. Sad/Lonely User
```json
{
  "text": "I feel so alone lately, nobody understands what I'm going through",
  "prosody_context": "pitch: low, pace: slow, energy: low"
}
```
**Expected:** `label: "lonely", confidence: ~0.80`

### 4. **CRISIS CASE** - Safety Flag
```json
{
  "text": "I don't see any point in continuing anymore, nothing matters",
  "prosody_context": "pitch: very low, pace: very slow, energy: very low"
}
```
**Expected:** `label: "grief", confidence: ~0.85, safety_flag: true` ⚠️

### 5. Neutral User
```json
{
  "text": "Can you explain how proof of stake works?",
  "prosody_context": null
}
```
**Expected:** `label: "neutral", confidence: ~0.85`

### 6. Angry User
```json
{
  "text": "This is so frustrating! Nothing is working correctly!",
  "prosody_context": "pitch: high, pace: very fast, energy: high"
}
```
**Expected:** `label: "anger", confidence: ~0.85`

## Frontend Integration

### React/Next.js Example

```typescript
// Phoenix API client
async function classifyEmotion(text: string, prosody?: string) {
  const response = await fetch('/api/phoenix/classify', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text,
      prosody_context: prosody
    })
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return await response.json();
}

// Usage
const result = await classifyEmotion(
  "I'm really worried about this",
  "pitch: high, pace: fast"
);

console.log(`Emotion: ${result.label}`);
console.log(`Confidence: ${result.confidence * 100}%`);

if (result.safety_flag) {
  // Show crisis intervention UI
  showCrisisSupport();
}
```

### UI Component Example

```tsx
function EmotionDisplay({ text, prosody }) {
  const [emotion, setEmotion] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyze = async () => {
    setLoading(true);
    try {
      const result = await classifyEmotion(text, prosody);
      setEmotion(result);
    } catch (error) {
      console.error('Emotion classification failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <textarea
        value={text}
        placeholder="Enter message..."
      />
      <button onClick={analyze} disabled={loading}>
        {loading ? 'Analyzing...' : 'Analyze Emotion'}
      </button>

      {emotion && (
        <div className={`emotion-result ${emotion.safety_flag ? 'crisis' : ''}`}>
          <h3>Emotion: {emotion.label.toUpperCase()}</h3>
          <p>Confidence: {(emotion.confidence * 100).toFixed(0)}%</p>

          {emotion.safety_flag && (
            <div className="crisis-alert">
              ⚠️ CRISIS DETECTED - Intervention Needed
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

## How to Test

### 1. Start the Backend
```bash
# In backend directory
source .venv/bin/activate
python main.py
```

Server will start on `http://localhost:8000`

### 2. Check Health
```bash
curl http://localhost:8000/api/phoenix/health
```

### 3. Test Classification
```bash
curl -X POST http://localhost:8000/api/phoenix/classify \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text": "I am feeling anxious today"}'
```

### 4. View API Docs
Open: `http://localhost:8000/docs`

## Implementation Details

### Files Modified/Created

✅ `app/emotion/phoenix_client.py` - PhoenixClient implementation
✅ `app/emotion/__init__.py` - Module exports
✅ `prompts/sophia_phoenix_emotion_prompt.md` - Custom emotion prompt
✅ `app/routers/phoenix_test.py` - API endpoints
✅ `main.py` - Router registration
✅ `tests/test_phoenix_client.py` - Unit tests

### Environment Variables Required

```bash
OPENAI_API_KEY=sk-...your-key...   # Required for classification
API_KEYS=your-backend-api-key       # Required for authentication
```

### Models Used

- **OpenAI Model:** `gpt-4o-mini`
- **Temperature:** 0.1 (consistent classification)
- **Timeout:** 12 seconds
- **Response Format:** JSON structured output

## Expected Behavior

1. **Fast Response:** 200-500ms typical latency
2. **High Accuracy:** 80-95% confidence for clear emotions
3. **Crisis Detection:** safety_flag=true for suicidal/self-harm content
4. **Graceful Fallback:** Returns neutral (confidence=0.3) on errors
5. **Prosody Enhancement:** Higher confidence when voice context provided

## Troubleshooting

### "OPENAI_API_KEY not configured"
→ Set `OPENAI_API_KEY` in `.env` file

### "API key verification failed"
→ Include valid API key in `Authorization: Bearer TOKEN` header

### Timeout Errors
→ Check OpenAI API status, increase `timeout_seconds` in config

### Invalid Emotion Labels
→ Client validates and maps to neutral if OpenAI returns invalid label
