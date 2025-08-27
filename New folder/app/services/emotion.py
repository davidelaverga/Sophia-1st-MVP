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
        from mistralai import Mistral

        settings = get_settings()
        if not settings.MISTRAL_API_KEY:
            return None
        client = Mistral(api_key=settings.MISTRAL_API_KEY)

        result = llm_classify(
            llm=client,
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
        from mistralai import Mistral
        settings = get_settings()
        if not settings.MISTRAL_API_KEY:
            return Emotion(label="neutral", confidence=0.5)
        client = Mistral(api_key=settings.MISTRAL_API_KEY)
        prompt = (
            "Classify sentiment of the following text as one of: positive, neutral, negative. "
            "Respond with JSON: {\"label\": \"...\", \"confidence\": 0.0-1.0}. Text: "
            f"{text}"
        )
        resp = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
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
    phoenix = _classify_with_phoenix(text)
    if phoenix:
        return phoenix
    return _classify_with_llm(text)
