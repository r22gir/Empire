"""
Background Worker for Chat Backup Scheduler.
Runs periodic backups of chat sessions.
"""
import asyncio
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.services.chat_backup_service import ChatBackupService
from app.schemas.chat_backup import BackupRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatBackupScheduler:
    """
    Background scheduler for periodic chat backups.
    Can be run as a standalone worker or integrated into the main application.
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        backup_interval_hours: int = 6,
        backup_dir: Optional[str] = None
    ):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:pass@localhost:5432/empirebox"
        )
        self.backup_interval_hours = backup_interval_hours
        self.backup_dir = backup_dir or os.getenv("CHAT_BACKUP_DIR", "/tmp/chat_backups")
        self._running = False
        self._engine = None
        self._session_maker = None

    async def _init_db(self):
        """Initialize database connection."""
        if not self._engine:
            self._engine = create_async_engine(
                self.database_url,
                echo=False,
                future=True
            )
            self._session_maker = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

    async def _get_db_session(self) -> AsyncSession:
        """Get a database session."""
        await self._init_db()
        return self._session_maker()

    async def run_backup(self) -> dict:
        """
        Execute a single backup operation.
        Returns backup result summary.
        """
        logger.info("Starting scheduled backup...")
        
        async with await self._get_db_session() as db:
            try:
                service = ChatBackupService(db)
                
                # Get backup status first
                status = await service.get_backup_status()
                logger.info(
                    f"Backup status: {status.pending_sessions} pending, "
                    f"{status.backed_up_sessions} already backed up"
                )
                
                if status.pending_sessions == 0:
                    logger.info("No sessions pending backup")
                    return {
                        "status": "skipped",
                        "message": "No sessions pending backup",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                
                # Execute backup
                request = BackupRequest(
                    backup_location=self.backup_dir,
                    include_archived=False
                )
                result = await service.backup_sessions(request)
                
                logger.info(
                    f"Backup completed: {result.sessions_backed_up} sessions backed up to {result.backup_location}"
                )
                
                return {
                    "status": "success",
                    "backup_id": result.backup_id,
                    "sessions_backed_up": result.sessions_backed_up,
                    "backup_location": result.backup_location,
                    "backup_size_bytes": result.backup_size_bytes,
                    "timestamp": result.backed_up_at.isoformat()
                }
                
            except Exception as e:
                logger.error(f"Backup failed: {str(e)}")
                return {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

    async def start_scheduler(self):
        """
        Start the backup scheduler loop.
        Runs continuously until stopped.
        """
        self._running = True
        logger.info(
            f"Starting backup scheduler with {self.backup_interval_hours} hour interval"
        )
        
        while self._running:
            try:
                # Run backup
                result = await self.run_backup()
                logger.info(f"Backup result: {result['status']}")
                
                # Wait for next interval
                if self._running:
                    await asyncio.sleep(self.backup_interval_hours * 3600)
                    
            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}")
                # Wait a bit before retrying
                await asyncio.sleep(60)

    def stop_scheduler(self):
        """Stop the backup scheduler."""
        self._running = False
        logger.info("Stopping backup scheduler")

    async def cleanup(self):
        """Cleanup resources."""
        if self._engine:
            await self._engine.dispose()


# Standalone runner
async def run_scheduler():
    """Run the backup scheduler as a standalone process."""
    scheduler = ChatBackupScheduler(
        backup_interval_hours=int(os.getenv("CHAT_BACKUP_INTERVAL_HOURS", "6"))
    )
    
    try:
        await scheduler.start_scheduler()
    finally:
        await scheduler.cleanup()


def start_backup_worker():
    """Entry point for starting the backup worker."""
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    start_backup_worker()
