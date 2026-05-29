"""Resilience utilities for handling outages."""

import asyncio
from typing import Callable, Any, List, Dict
from datetime import datetime, timezone

try:
    from backend.utils.logger import logger
except ModuleNotFoundError:
    from utils.logger import logger


class OperationQueue:
    """Queues operations when database is down, to be retried later."""
    
    def __init__(self, max_size: int = 1000):
        self.queue: List[Dict[str, Any]] = []
        self.max_size = max_size
        self.is_processing = False
        
    async def add(self, operation_name: str, func: Callable, *args, **kwargs):
        """Add an operation to the queue if DB is down."""
        if len(self.queue) >= self.max_size:
            logger.warning(f"Operation queue full. Dropping operation {operation_name}")
            return False
            
        self.queue.append({
            "name": operation_name,
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "timestamp": datetime.now(timezone.utc)
        })
        logger.info(f"Queued operation {operation_name} due to outage")
        return True
        
    async def process_queue(self):
        """Process the queue when DB is back online."""
        if self.is_processing or not self.queue:
            return
            
        self.is_processing = True
        logger.info(f"Processing {len(self.queue)} queued operations")
        
        failed = []
        
        while self.queue:
            op = self.queue.pop(0)
            try:
                # We need to await if it's an async function
                if asyncio.iscoroutinefunction(op["func"]):
                    await op["func"](*op["args"], **op["kwargs"])
                else:
                    op["func"](*op["args"], **op["kwargs"])
                logger.info(f"Successfully processed queued operation: {op['name']}")
            except Exception as e:
                logger.error(f"Failed to process queued operation {op['name']}: {str(e)}")
                failed.append(op)
                
        # Put failed ones back (maybe with a retry limit in a real app)
        self.queue.extend(failed)
        self.is_processing = False

# Global instance
operation_queue = OperationQueue()
