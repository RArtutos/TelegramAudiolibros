from telethon import TelegramClient
import logging
import os
from typing import Optional
from telethon.tl.types import DocumentAttributeAudio

logger = logging.getLogger(__name__)

async def send_audio_file(
    client: TelegramClient,
    channel_id: int,
    file_path: str,
    reply_to_id: Optional[int] = None,
    caption: Optional[str] = None
) -> None:
    """Send audio file to Telegram channel."""
    try:
        # Get the filename without path and extension
        filename = os.path.splitext(os.path.basename(file_path))[0]
        
        # Create audio attribute with the filename as title
        audio_attr = DocumentAttributeAudio(
            duration=0,  # Duration will be auto-detected
            title=filename,  # Use the full filename as title
            performer=None  # Remove performer to avoid "- UnknownTrack"
        )
        
        await client.send_file(
            channel_id,
            file_path,
            reply_to=reply_to_id,
            caption=caption,
            attributes=[audio_attr],
            force_document=False
        )
    except Exception as e:
        logger.error(f"Error sending audio file: {e}")
        raise