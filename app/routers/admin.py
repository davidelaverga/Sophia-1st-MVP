"""Administrative and diagnostic endpoints."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.deps import verify_api_key
from app.services.memory import memory_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api")
def api_root():
    """API status endpoint"""
    return {"message": "Sophia AI Backend with DeFi Agent is running."}


@router.get("/status")
def status_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": int(time.time())}


@router.get("/memory/{session_id}")
async def get_memory(
    session_id: str,
    supabase_token: str = Depends(verify_api_key),
):
    """Get conversation memory for a session"""
    try:
        context = memory_manager.get_context_for_llm(
            session_id, access_token=supabase_token
        )

        return {"session_id": session_id, "context": context, "timestamp": time.time()}

    except Exception as e:
        logger.error(f"Failed to get memory for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve memory")


@router.post("/admin/reload-prompts")
async def reload_prompts(
    supabase_token: str = Depends(verify_api_key),
):
    """Hot reload system prompts from disk (Task #42597)"""
    try:
        from app.services.prompt_composer import prompt_composer

        success = prompt_composer.reload_prompts()
        status = prompt_composer.get_reload_status()

        if success:
            return {
                "message": "Prompts reloaded successfully",
                "status": status,
                "timestamp": time.time(),
            }
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "message": "Prompts reload failed or incomplete",
                    "status": status,
                    "timestamp": time.time(),
                },
            )

    except Exception as e:
        logger.error(f"Failed to reload prompts: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to reload prompts: {str(e)}"
        )


@router.get("/admin/memo-metrics")
async def get_memo_metrics(
    supabase_token: str = Depends(verify_api_key),
):
    """Get MemO performance metrics (Task #42597)"""
    try:
        from app.services.memo import memo_client

        metrics = memo_client.get_metrics()

        return {
            "memo_enabled": memo_client.enabled,
            "metrics": metrics,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Failed to get MemO metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")
