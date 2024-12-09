import os
from dotenv import load_dotenv
from typing import Optional

# Ensure environment variables are loaded
load_dotenv()

class Config:
    def __init__(self):
        self.BOT_TOKEN = self._get_env('BOT_TOKEN')
        self.API_ID = int(self._get_env('API_ID'))
        self.API_HASH = self._get_env('API_HASH')
        self.CHANNEL_ID = int(self._get_env('CHANNEL_ID'))
        self.ADMIN_ID = int(self._get_env('ADMIN_ID'))
        self.JSON_PATH = '/data/audiobooks.json'
        self.TEMP_DIR = '/tmp/audiobooks'
        self.ensure_temp_dir()

    def _get_env(self, key: str, default: Optional[any] = None) -> str:
        value = os.getenv(key, default)
        if value is None:
            raise ValueError(f"Environment variable {key} is required")
        return value

    def ensure_temp_dir(self):
        os.makedirs(self.TEMP_DIR, exist_ok=True)