"""Error handling middleware and formatters."""

from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

try:
    from backend.utils.logger import logger, log_event
except ModuleNotFoundError:
    from utils.logger import logger, log_event


class ErrorFormatter:
    """Formats user-friendly error messages."""
    
    @staticmethod
    def format_error(error_type: str, detail: str) -> dict:
        messages = {
            "rate_limit": "You're doing that too fast. Please wait a moment and try again.",
            "database_error": "We're experiencing temporary database issues. Your action has been queued.",
            "api_timeout": "The upstream service took too long to respond. We are showing cached data.",
            "not_found": "The requested resource could not be found.",
            "validation_error": "Please check your input and try again.",
            "auth_error": "You need to log in to perform this action.",
            "unknown": "An unexpected error occurred. Our team has been notified."
        }
        
        user_msg = messages.get(error_type, messages["unknown"])
        
        return {
            "error": True,
            "type": error_type,
            "message": user_msg,
            "detail": detail
        }


async def global_error_handler(request: Request, exc: Exception):
    """Global exception handler for the FastAPI app."""
    
    # Check if it's a known HTTP exception
    if hasattr(exc, "status_code"):
        status_code = exc.status_code
        detail = getattr(exc, "detail", str(exc))
        
        if status_code == 429:
            error_type = "rate_limit"
        elif status_code == 404:
            error_type = "not_found"
        elif status_code == 401 or status_code == 403:
            error_type = "auth_error"
        elif status_code == 400:
            error_type = "validation_error"
        else:
            error_type = "unknown"
            
    else:
        # Unhandled exceptions
        status_code = 500
        error_type = "unknown"
        detail = str(exc)
        
        # Log the full traceback for 500s
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", 
            extra={"context": {"traceback": traceback.format_exc()}}
        )

    # Log the event
    log_event(
        action="api_request",
        result="error",
        path=request.url.path,
        method=request.method,
        status=status_code,
        error_type=error_type
    )

    response_content = ErrorFormatter.format_error(error_type, detail)
    return JSONResponse(status_code=status_code, content=response_content)
