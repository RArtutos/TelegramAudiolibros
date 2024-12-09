import aiohttp
import asyncio
import os
import logging
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB chunks
        self.chunk_size = chunk_size
        self.current_progress = 0
        self.total_size = 0
        self.status = "idle"
        self.current_file = ""
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def download_file(self, url: str, destination: str, num_connections: int = 4) -> Optional[str]:
        self.current_file = os.path.basename(destination)
        self.status = "starting"
        self.current_progress = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as response:
                    self.total_size = int(response.headers.get('content-length', 0))
                    
                if self.total_size == 0:
                    return await self._simple_download(session, url, destination)
                    
                return await self._parallel_download(session, url, destination, num_connections)
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            self.status = "error"
            return None

    async def _simple_download(self, session: aiohttp.ClientSession, url: str, destination: str) -> Optional[str]:
        self.status = "downloading"
        try:
            async with session.get(url) as response:
                with open(destination, 'wb') as f:
                    while True:
                        chunk = await response.content.read(self.chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        self.current_progress += len(chunk)
            self.status = "completed"
            return destination
        except Exception as e:
            logger.error(f"Error in simple download: {e}")
            self.status = "error"
            return None

    async def _parallel_download(self, session: aiohttp.ClientSession, url: str, destination: str, num_connections: int) -> Optional[str]:
        self.status = "downloading"
        chunk_size = self.total_size // num_connections
        chunks = []
        
        async def download_chunk(start: int, end: int) -> Optional[bytes]:
            headers = {'Range': f'bytes={start}-{end}'}
            try:
                async with session.get(url, headers=headers) as response:
                    chunk = await response.read()
                    self.current_progress += len(chunk)
                    return chunk
            except Exception as e:
                logger.error(f"Error downloading chunk: {e}")
                return None

        tasks = []
        for i in range(num_connections):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < num_connections - 1 else self.total_size - 1
            task = asyncio.create_task(download_chunk(start, end))
            tasks.append(task)

        chunks = await asyncio.gather(*tasks)
        
        if None in chunks:
            self.status = "error"
            return None

        try:
            with open(destination, 'wb') as f:
                for chunk in chunks:
                    f.write(chunk)
            self.status = "completed"
            return destination
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            self.status = "error"
            return None

    def get_progress(self) -> dict:
        return {
            "status": self.status,
            "progress": self.current_progress,
            "total": self.total_size,
            "percentage": (self.current_progress / self.total_size * 100) if self.total_size > 0 else 0,
            "current_file": self.current_file
        }