import os
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def download_file(url: str, destination: str) -> Optional[str]:
    try:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(destination, 'wb') as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                    return destination
                else:
                    logger.error(f"Failed to download file: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return None