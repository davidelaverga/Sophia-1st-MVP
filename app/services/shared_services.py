"""Singleton helpers that share expensive LangGraph and session services across nodes."""
import logging
from typing import Optional

from app.services.session_manager import SessionTurnManager
from app.services.voxtral_large import HybridVoxtralService

logger = logging.getLogger(__name__)

class SharedServiceManager:
    """Singleton manager for shared service instances"""
    _hybrid_voxtral_service: Optional[HybridVoxtralService] = None
    _session_turn_manager: Optional[SessionTurnManager] = None

    @classmethod
    def get_hybrid_voxtral_service(cls) -> Optional[HybridVoxtralService]:
        """Get shared HybridVoxtralService instance with lazy initialization"""
        if cls._hybrid_voxtral_service is None:
            try:
                cls._hybrid_voxtral_service = HybridVoxtralService()
                logger.info("SharedServiceManager: HybridVoxtralService initialized successfully")
            except Exception as e:
                logger.warning(f"SharedServiceManager: Failed to initialize HybridVoxtralService: {e}")
                cls._hybrid_voxtral_service = None
        return cls._hybrid_voxtral_service

    @classmethod
    def is_voxtral_large_available(cls) -> bool:
        """Check if Voxtral Large service is available"""
        return cls.get_hybrid_voxtral_service() is not None

    @classmethod
    def reset_services(cls):
        """Reset all services - useful for testing"""
        cls._hybrid_voxtral_service = None
        cls._session_turn_manager = None
        logger.info("SharedServiceManager: All services reset")
    
    @classmethod
    def get_session_turn_manager(cls) -> SessionTurnManager:
        """Return shared SessionTurnManager instance."""
        if cls._session_turn_manager is None:
            cls._session_turn_manager = SessionTurnManager()
            logger.info("SharedServiceManager: SessionTurnManager initialized successfully")
        return cls._session_turn_manager

# Global instance
shared_services = SharedServiceManager()
