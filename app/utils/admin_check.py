from typing import Callable
from functools import wraps
from telethon import events
from config import Config

def admin_only():
    config = Config()
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(event: events.NewMessage.Event):
            if event.sender_id != config.ADMIN_ID:
                await event.respond("❌ Lo siento, solo el administrador puede usar este comando.")
                return
            return await func(event)
        return wrapper
    return decorator