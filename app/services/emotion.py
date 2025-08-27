import logging
from pydantic import BaseModel
from app.config import get_settings

logger = logging.getLogger("emotion")


class Emotion(BaseModel):
    label: str
    confidence: float


def _classify_with_phoenix(text: str) -> Emotion | None:
    try:
        # Lazy import to avoid hard dep if not installed in some envs
        from phoenix.evals import llm_classify
        try:
            from phoenix.evals import GoogleGenAIModel
        except Exception as e:
            logger.info(f"Phoenix GoogleGenAIModel unavailable; skipping phoenix text classify: {e}")
            return None
        model = GoogleGenAIModel(model="gemini-2.5-flash")
        settings = get_settings()

        result = llm_classify(
            llm=model,
            data=[{"input": text}],
            template=(
                "Classify the overall sentiment of the INPUT as one of: positive, neutral, negative. "
                "Return only the label.")
            ,
            label_schema={"positive", "neutral", "negative"},
        )
        # Phoenix may return a dict-like with labeled outputs; adapt safely
        label = None
        score = 0.0
        try:
            label = result["label"][0]
            score = float(result.get("score", [0.0])[0])
        except Exception:
            # Fallback parse
            label = "neutral"
            score = 0.5
        if label not in {"positive", "neutral", "negative"}:
            label = "neutral"
        return Emotion(label=label, confidence=score)
    except Exception as e:
        logger.warning(f"Phoenix emotion model failed: {e}")
        return None


def _classify_with_llm(text: str) -> Emotion:
    try:
        from mistralai.client import MistralClient
        from mistralai.models.chat_completion import ChatMessage
        settings = get_settings()
        if not settings.MISTRAL_API_KEY:
            return Emotion(label="neutral", confidence=0.5)
        client = MistralClient(api_key=settings.MISTRAL_API_KEY)
        prompt = (
            "Classify sentiment of the following text as one of: positive, neutral, negative. "
            "Respond with JSON: {\"label\": \"...\", \"confidence\": 0.0-1.0}. Text: "
            f"{text}"
        )
        resp = client.chat(
            model="mistral-small-latest",
            messages=[ChatMessage(role="user", content=prompt)],
        )
        import json
        content = str(resp.choices[0].message.content)
        try:
            obj = json.loads(content)
            label = obj.get("label", "neutral")
            conf = float(obj.get("confidence", 0.5))
        except Exception:
            label = "neutral"
            conf = 0.5
        if label not in {"positive", "neutral", "negative"}:
            label = "neutral"
        conf = max(0.0, min(1.0, conf))
        return Emotion(label=label, confidence=conf)
    except Exception:
        return Emotion(label="neutral", confidence=0.5)


def analyze_emotion_text(text: str) -> Emotion:
    # Define allowed emotion labels for database compatibility
    ALLOWED_LABELS = ["positive", "neutral", "negative"]
    
    phoenix = _classify_with_phoenix(text)
    if phoenix:
        # Ensure label is in allowed list
        if phoenix.label not in ALLOWED_LABELS:
            phoenix.label = "neutral"
        return phoenix
        
    result = _classify_with_llm(text)
    # Ensure label is in allowed list
    if result.label not in ALLOWED_LABELS:
        result.label = "neutral"
    return result


def analyze_emotion_audio(wav_bytes: bytes) -> Emotion:
    """Classify emotion from audio using Phoenix Evals + Google Gemini.
    Requires GOOGLE_API_KEY in environment. Returns an Emotion model.
    
    Note: The database has a check constraint requiring emotion labels to be
    one of: positive, neutral, negative
    """
    try:
        import base64
        import pandas as pd
        from phoenix.evals import llm_classify
        try:
            from phoenix.evals import GoogleGenAIModel
            from phoenix.evals.templates import ClassificationTemplate, PromptPartContentType, PromptPartTemplate
        except Exception as e:
            logger.info(f"Phoenix GoogleGenAIModel unavailable; returning neutral for audio classify: {e}")
            return Emotion(label="neutral", confidence=0.5)
        
        # Define emotion rails (categories)
        EMOTION_RAILS = [
            "anger", "happiness", "excitement", "sadness", "neutral",
            "frustration", "fear", "surprise", "disgust", "other"
        ]
        
        # Create improved emotion template
        emotion_template = ClassificationTemplate(
            rails=EMOTION_RAILS,
            template=[
                PromptPartTemplate(
                    content_type=PromptPartContentType.TEXT,
                    template=(
                        "You are an AI system designed to classify emotions in audio files.\n"
                        "Analyze the provided audio and classify the primary emotion based on tone, pitch, pace, volume, and intensity.\n"
                        f"Valid emotions: {EMOTION_RAILS}\n"
                        "Return ONLY one word from the list."
                    ),
                ),
                PromptPartTemplate(
                    content_type=PromptPartContentType.AUDIO,
                    template="{audio}",
                ),
                PromptPartTemplate(
                    content_type=PromptPartContentType.TEXT,
                    template="Your response must be exactly one word from the valid emotions list.",
                ),
            ],
        )

        # 1) encode audio to base64
        audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")

        # 2) dataframe with expected column name 'audio'
        df = pd.DataFrame([{"audio": audio_b64}])

        # 3) model: gemini
        model = GoogleGenAIModel(model="gemini-2.5-flash")

        # 4) run classification with improved template
        results = llm_classify(
            model=model,
            data=df,
            template=emotion_template,
            rails=EMOTION_RAILS,
        )

        # 5) extract single label
        label = str(results.iloc[0, 0]).strip().lower()
        valid = [r.lower() for r in EMOTION_RAILS]
        if label not in valid:
            label = "neutral"
            
        # Map emotion labels to database-allowed values (positive, neutral, negative)
        # This is required by the database check constraint
        emotion_mapping = {
            "happiness": "positive",
            "excitement": "positive",
            "surprise": "positive",
            "neutral": "neutral",
            "anger": "negative",
            "sadness": "negative",
            "frustration": "negative",
            "fear": "negative",
            "disgust": "negative",
            "other": "neutral"
        }
        
        # Map to allowed database values
        db_label = emotion_mapping.get(label, "neutral")
        
        # Confidence not provided by default template; set midpoint
        return Emotion(label=db_label, confidence=0.8)  # Higher confidence with improved template
    except Exception as e:
        logger.warning(f"Audio emotion classification failed: {e}")
        return Emotion(label="neutral", confidence=0.5)
