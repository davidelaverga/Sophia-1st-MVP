"""
Enhanced Reflection Card Service with Multi-turn Support

Generates reflection cards using ALL messages from conversation_messages table,
providing richer context and better summaries.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from app.services.supabase import get_supabase
from app.services.mistral import _client as get_mistral_client

logger = logging.getLogger(__name__)


class ReflectionService:
    """Service for generating reflection cards from conversations"""
    
    @staticmethod
    def get_conversation_messages(session_id: str) -> List[Dict]:
        """
        Get ALL messages from a conversation in chronological order.
        
        Returns list of messages with role, content, emotion, timestamp.
        """
        try:
            supabase = get_supabase()
            
            result = supabase.table("conversation_messages").select(
                "id, role, content, emotion, audio_url, created_at"
            ).eq("session_id", session_id).order(
                "created_at", desc=False  # Chronological order
            ).execute()
            
            if not result.data:
                logger.warning(f"No messages found for session {session_id}")
                return []
            
            logger.info(f"Retrieved {len(result.data)} messages for session {session_id}")
            return result.data
            
        except Exception as e:
            logger.error(f"Failed to get conversation messages: {e}")
            return []
    
    @staticmethod
    def format_conversation_for_llm(messages: List[Dict]) -> str:
        """
        Format conversation messages into a readable string for LLM.
        
        Returns formatted conversation like:
        User: Hello
        Sophia: Hi there!
        User: Tell me about DeFi
        Sophia: DeFi stands for...
        """
        formatted_lines = []
        
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Sophia"
            content = msg["content"]
            
            # Add emotion if available
            emotion = ""
            if msg.get("emotion"):
                emotion_label = msg["emotion"].get("label", "")
                if emotion_label and emotion_label != "neutral":
                    emotion = f" [{emotion_label}]"
            
            formatted_lines.append(f"{role}{emotion}: {content}")
        
        return "\n".join(formatted_lines)
    
    @staticmethod
    def extract_conversation_metadata(messages: List[Dict]) -> Dict:
        """
        Extract metadata from conversation messages.
        
        Returns:
        - message_count
        - user_emotions (list of unique emotions)
        - sophia_emotions (list of unique emotions)
        - conversation_length (in characters)
        """
        user_emotions = set()
        sophia_emotions = set()
        total_length = 0
        
        for msg in messages:
            total_length += len(msg["content"])
            
            if msg.get("emotion") and msg["emotion"].get("label"):
                emotion = msg["emotion"]["label"]
                if msg["role"] == "user":
                    user_emotions.add(emotion)
                else:
                    sophia_emotions.add(emotion)
        
        return {
            "message_count": len(messages),
            "user_emotions": list(user_emotions),
            "sophia_emotions": list(sophia_emotions),
            "conversation_length": total_length,
            "has_multi_turn": len(messages) > 2,  # More than just 1 exchange
        }
    
    @staticmethod
    def generate_reflection_with_mistral(
        conversation_text: str,
        metadata: Dict
    ) -> Dict:
        """
        Generate reflection card using Mistral with full conversation context.
        
        Returns:
        - title: Short title for the reflection
        - summary: 2-3 sentence summary
        - insight_tags: List of key topics/concepts discussed
        - key_moments: Important exchanges or insights
        """
        
        # Build enhanced prompt with conversation context
        prompt = f"""You are creating a reflection card for a conversation between a user and Sophia AI.

CONVERSATION CONTEXT:
- Total messages: {metadata['message_count']}
- User emotions: {', '.join(metadata['user_emotions'])}
- Sophia emotions: {', '.join(metadata['sophia_emotions'])}
- Multi-turn conversation: {'Yes' if metadata['has_multi_turn'] else 'No'}

FULL CONVERSATION:
{conversation_text}

TASK: Create a thoughtful reflection card that captures:
1. The main topics discussed
2. Key insights or learning moments
3. The emotional journey of the conversation
4. Any significant shifts or breakthroughs

Generate a JSON response with:
{{
  "title": "A concise, engaging title (max 60 chars)",
  "summary": "A 2-3 sentence summary capturing the essence of the conversation",
  "insight_tags": ["tag1", "tag2", "tag3"],
  "key_moments": ["Important exchange or insight 1", "Important exchange or insight 2"],
  "emotional_arc": "Brief description of emotional journey"
}}

IMPORTANT: 
- Focus on what was actually discussed, not generic statements
- Highlight specific topics mentioned (e.g., "nutrition", "protein", "calories")
- If it's a multi-turn conversation, note how the discussion evolved
- Keep it personal and meaningful
- YOUR ENTIRE RESPONSE MUST BE VALID JSON ONLY - NO MARKDOWN, NO EXPLANATIONS, JUST THE JSON OBJECT"""

        try:
            client = get_mistral_client()
            
            logger.info(f"[Reflection] Calling Mistral with {len(conversation_text)} chars of conversation")
            
            response = client.chat.complete(
                model="mistral-large-latest",  # Use large model for better quality
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800,
            )
            
            # Extract response content
            response_content = response.choices[0].message.content
            
            # Log the raw response for debugging
            logger.info(f"[Reflection] Raw Mistral response type: {type(response_content)}")
            logger.info(f"[Reflection] Raw Mistral response: {response_content[:500]}")
            
            # Handle case where response_content might be None or not a string
            if not response_content:
                logger.error("[Reflection] Mistral returned empty response")
                raise ValueError("Empty response from Mistral")
            
            # Convert to string if needed
            response_text = str(response_content)
            
            # Parse JSON response
            import json
            
            # Clean response - remove markdown code blocks if present
            clean_content = response_text.strip()
            
            # Remove various markdown wrappers
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:]
            
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            
            clean_content = clean_content.strip()
            
            logger.info(f"[Reflection] Cleaned content: {clean_content[:200]}")
            
            # Try to parse JSON
            reflection_data = json.loads(clean_content)
            
            # Validate required fields
            required_fields = ["title", "summary", "insight_tags"]
            for field in required_fields:
                if field not in reflection_data:
                    logger.warning(f"[Reflection] Missing field: {field}, adding default")
                    if field == "title":
                        reflection_data[field] = "Conversation Reflection"
                    elif field == "summary":
                        reflection_data[field] = "A meaningful conversation."
                    else:
                        reflection_data[field] = []
            
            # Ensure arrays
            if not isinstance(reflection_data.get("insight_tags"), list):
                reflection_data["insight_tags"] = ["conversation"]
            if not isinstance(reflection_data.get("key_moments"), list):
                reflection_data["key_moments"] = []
            if "emotional_arc" not in reflection_data:
                reflection_data["emotional_arc"] = "neutral"
            
            logger.info(f"[Reflection] Successfully generated: {reflection_data.get('title', 'Unknown')}")
            return reflection_data
            
        except json.JSONDecodeError as e:
            logger.error(f"[Reflection] JSON parsing failed: {e}")
            logger.error(f"[Reflection] Failed content was: {response_text if 'response_text' in locals() else 'N/A'}")
            
            # Try to extract at least something useful from the text
            try:
                # Sometimes Mistral returns the JSON within text
                if 'response_text' in locals() and '{' in response_text and '}' in response_text:
                    start = response_text.index('{')
                    end = response_text.rindex('}') + 1
                    json_str = response_text[start:end]
                    logger.info(f"[Reflection] Attempting to extract JSON from position {start} to {end}")
                    reflection_data = json.loads(json_str)
                    logger.info(f"[Reflection] Successfully extracted JSON: {reflection_data.get('title')}")
                    return reflection_data
            except Exception as extract_error:
                logger.error(f"[Reflection] JSON extraction also failed: {extract_error}")
            
            # Final fallback with conversation context
            return {
                "title": "Conversation Reflection",
                "summary": f"A conversation with {metadata['message_count']} messages exploring various topics.",
                "insight_tags": list(set(metadata['user_emotions'] + metadata['sophia_emotions']))[:3] if metadata['user_emotions'] or metadata['sophia_emotions'] else ["conversation", "learning"],
                "key_moments": [],
                "emotional_arc": metadata.get('user_emotions', ['neutral'])[0] if metadata.get('user_emotions') else "neutral"
            }
            
        except Exception as e:
            logger.error(f"[Reflection] Failed to generate reflection with Mistral: {e}", exc_info=True)
            
            # Fallback response
            return {
                "title": "Conversation Reflection",
                "summary": "A meaningful conversation exploring various topics.",
                "insight_tags": ["conversation", "learning"],
                "key_moments": [],
                "emotional_arc": "neutral"
            }
    
    @staticmethod
    def create_reflection_card(
        session_id: str,
        user_id: str
    ) -> Dict:
        """
        Create a complete reflection card using multi-turn conversation.
        
        Main function that orchestrates the whole process:
        1. Get all messages from conversation
        2. Format for LLM
        3. Generate reflection with Mistral
        4. Save to database
        
        Returns the created reflection card data.
        """
        
        logger.info(f"Creating reflection for session {session_id}, user {user_id}")
        
        # Step 1: Get all messages
        messages = ReflectionService.get_conversation_messages(session_id)
        
        if not messages:
            raise ValueError(f"No messages found for session {session_id}")
        
        # Step 2: Format and extract metadata
        conversation_text = ReflectionService.format_conversation_for_llm(messages)
        metadata = ReflectionService.extract_conversation_metadata(messages)
        
        logger.info(f"Conversation metadata: {metadata}")
        
        # Step 3: Generate reflection
        reflection_data = ReflectionService.generate_reflection_with_mistral(
            conversation_text,
            metadata
        )
        
        # Step 4: Get user and sophia emotions from last messages
        user_emotion = {"label": "neutral", "confidence": 0.7}
        sophia_emotion = {"label": "neutral", "confidence": 0.7}
        
        # Get last user message emotion
        user_messages = [m for m in messages if m["role"] == "user"]
        if user_messages and user_messages[-1].get("emotion"):
            user_emotion = user_messages[-1]["emotion"]
        
        # Get last sophia message emotion
        sophia_messages = [m for m in messages if m["role"] == "sophia"]
        if sophia_messages and sophia_messages[-1].get("emotion"):
            sophia_emotion = sophia_messages[-1]["emotion"]
        
        # Step 5: Save to database
        try:
            supabase = get_supabase()
            
            reflection_card = {
                "user_id": user_id,
                "conversation_id": session_id,
                "title": reflection_data["title"],
                "summary": reflection_data["summary"],
                "insight_tags": reflection_data["insight_tags"],
                "key_moments": reflection_data.get("key_moments", []),
                "emotional_arc": reflection_data.get("emotional_arc", ""),
                "user_emotion": user_emotion,
                "sophia_emotion": sophia_emotion,
                "message_count": metadata["message_count"],
                "shared": False,
                "discord_message_id": None,
            }
            
            result = supabase.table("reflection_cards").insert(reflection_card).execute()
            
            if result.data:
                created_card = result.data[0]
                logger.info(f"Reflection card created: {created_card['id']}")
                return created_card
            else:
                raise Exception("No data returned from insert")
                
        except Exception as e:
            logger.error(f"Failed to save reflection card: {e}")
            raise
    
    @staticmethod
    def get_user_reflections(
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get user's reflection cards, newest first.
        """
        try:
            supabase = get_supabase()
            
            result = supabase.table("reflection_cards").select(
                "*"
            ).eq("user_id", user_id).order(
                "created_at", desc=True
            ).limit(limit).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get user reflections: {e}")
            return []


# Singleton instance
reflection_service = ReflectionService()