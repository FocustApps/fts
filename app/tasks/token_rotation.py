"""
Background scheduler for auth token rotation.

Provides APScheduler integration with FastAPI lifecycle for automatic
token rotation at configured intervals with proper startup/shutdown handling.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Any

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    AsyncIOScheduler = None
    IntervalTrigger = None

from app.services.auth_service import (
    get_auth_service,
    initialize_auth_service,
    shutdown_auth_service,
)
from app.config import get_base_app_config
from common.app_logging import create_logging

logger = create_logging()

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


async def rotate_auth_token_job():
    """Background job to rotate auth tokens."""
    try:
        auth_service = get_auth_service()
        new_token = auth_service.rotate_token()
        logger.info(
            f"Scheduled token rotation completed: {new_token[:4]}...{new_token[-4:]}"
        )
    except Exception as e:
        logger.error(f"Scheduled token rotation failed: {e}")


def external_sync_placeholder(token: str, file_path: Path) -> None:
    """
    External sync functionality for token updates.

    This function will be called whenever a token is rotated.
    Includes email notification if configured.

    Args:
        token: The new token that was generated
        file_path: Path to the token file
    """
    config = get_base_app_config()

    if config.email_notification_enabled:
        try:
            from app.services.email_service import send_token_notification

            send_token_notification(token, file_path)
            logger.info(f"Email notification sent for token: {token[:4]}...{token[-4:]}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    if config.auth_external_sync_enabled:
        logger.info(
            f"External sync placeholder called for token: {token[:4]}...{token[-4:]}"
        )
        logger.info(f"External sync URL: {config.auth_external_sync_url}")
        logger.info(f"Token file path: {file_path}")

        # TODO: Implement actual external sync logic here
        # Examples:
        # - HTTP POST to external service
        # - File upload to cloud storage
        # - Database update
        # - Message queue publication

        logger.info("External sync placeholder completed (no implementation yet)")
    else:
        logger.debug("External sync disabled, skipping")


async def start_token_rotation_scheduler() -> None:
    """
    Start the background scheduler for token rotation.

    Initializes auth service and starts APScheduler with configured interval.
    """
    global _scheduler

    try:
        config = get_base_app_config()

        # Initialize auth service with conditional external sync callback
        # Only use callback if external sync is enabled, otherwise pass None
        external_callback = (
            external_sync_placeholder
            if config.auth_external_sync_enabled or config.email_notification_enabled
            else None
        )

        auth_service = initialize_auth_service(
            token_file_path=Path(config.auth_token_file_path),
            rotation_interval_minutes=config.auth_rotation_interval_minutes,
            external_sync_callback=external_callback,
        )

        # Generate initial token
        initial_token = auth_service.get_current_token()
        if config.environment == "production":
            logger.info(
                f"Auth service initialized with token: {initial_token[:4]}...{initial_token[-4:]}"
            )
        else:
            logger.info(
                f"Auth service initialized in {config.environment}"
                f" environment allowing full token visibility"
            )
            logger.info(f"AI CAN USE THIS TOKEN: {initial_token}")

        # Only start scheduler if APScheduler is available
        if not HAS_APSCHEDULER:
            logger.warning("APScheduler not available, token rotation scheduler disabled")
            logger.warning("Install with: pip install apscheduler")
            logger.info("Auth service initialized without automatic rotation")
            return

        if _scheduler is not None:
            logger.warning("Token rotation scheduler already started")
            return

        # Start scheduler
        _scheduler = AsyncIOScheduler()

        # Add token rotation job
        _scheduler.add_job(
            rotate_auth_token_job,
            trigger=IntervalTrigger(minutes=config.auth_rotation_interval_minutes),
            id="auth_token_rotation",
            name="Auth Token Rotation",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping executions
        )

        _scheduler.start()
        logger.info(
            f"Token rotation scheduler started (interval: {config.auth_rotation_interval_minutes} minutes)"
        )

    except Exception as e:
        logger.error(f"Failed to start token rotation scheduler: {e}")
        raise


async def stop_token_rotation_scheduler() -> None:
    """
    Stop the background scheduler for token rotation.

    Gracefully shuts down APScheduler and auth service.
    """
    global _scheduler

    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=True)
            logger.info("Token rotation scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping token rotation scheduler: {e}")
        finally:
            _scheduler = None

    # Shutdown auth service
    shutdown_auth_service()


def get_scheduler_status() -> dict[str, Any]:
    """
    Get current status of the token rotation scheduler.

    Returns:
        Dictionary with scheduler status information
    """
    global _scheduler

    if not HAS_APSCHEDULER:
        return {
            "available": False,
            "reason": "APScheduler not installed",
            "running": False,
            "jobs": [],
        }

    if _scheduler is None:
        return {"available": True, "running": False, "jobs": []}

    try:
        jobs_info = []
        for job in _scheduler.get_jobs():
            jobs_info.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": (
                        job.next_run_time.isoformat() if job.next_run_time else None
                    ),
                    "trigger": str(job.trigger),
                }
            )

        return {"available": True, "running": _scheduler.running, "jobs": jobs_info}
    except Exception as e:
        return {"available": True, "running": False, "error": str(e), "jobs": []}


@asynccontextmanager
async def auth_scheduler_lifespan(app):
    """
    FastAPI lifespan context manager for auth scheduler.

    Use this in your FastAPI app initialization:

    ```python
    app = FastAPI(lifespan=auth_scheduler_lifespan)
    ```
    """
    # Startup
    logger.info("Starting auth scheduler lifespan")
    await start_token_rotation_scheduler()

    try:
        yield
    finally:
        # Shutdown
        logger.info("Stopping auth scheduler lifespan")
        await stop_token_rotation_scheduler()


# Alternative manual management functions
async def manual_token_rotation() -> dict[str, Any]:
    """
    Manually trigger token rotation outside of scheduled interval.

    Returns:
        Dictionary with rotation result
    """
    try:
        auth_service = get_auth_service()
        old_info = auth_service.get_token_info()
        new_token = auth_service.rotate_token()
        new_info = auth_service.get_token_info()

        logger.info(
            f"Manual token rotation completed: {new_token[:4]}...{new_token[-4:]}"
        )

        return {
            "success": True,
            "old_token_info": old_info,
            "new_token_info": new_info,
            "message": "Token rotated successfully",
        }
    except Exception as e:
        logger.error(f"Manual token rotation failed: {e}")
        return {"success": False, "error": str(e), "message": "Token rotation failed"}
