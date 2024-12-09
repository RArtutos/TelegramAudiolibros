import json
import random
import os
from typing import List, Dict
from config import Config
from utils.file_utils import download_file

class AudiobookHandler:
    def __init__(self):
        self.config = Config()
        self.config.ensure_temp_dir()
        self._load_audiobooks()

    def _load_audiobooks(self):
        try:
            with open(self.config.JSON_PATH, 'r', encoding='utf-8') as f:
                self.audiobooks = json.load(f)
        except FileNotFoundError:
            self.audiobooks = {}
            
    def get_random_audiobook(self) -> Dict:
        if not self.audiobooks:
            raise ValueError("No audiobooks available")
        return random.choice(list(self.audiobooks.values()))

    def search_audiobooks(self, query: str) -> List[Dict]:
        query = query.lower()
        results = []
        
        for book in self.audiobooks.values():
            if query in book['title'].lower():
                results.append(book)
                
        return sorted(
            results,
            key=lambda x: x['title'].lower().find(query),
            reverse=True
        )[:10]

    async def download_audiobook(self, audiobook: Dict) -> str:
        filename = f"{self.config.TEMP_DIR}/{audiobook['idDownload']}.mp3"
        download_url = (
            f"https://pelis.gbstream.us.kg/api/v1/redirectdownload/"
            f"{audiobook['title']}.mp3?a=0&id={audiobook['idDownload']}"
        )
        
        result = await download_file(download_url, filename)
        if not result:
            raise Exception("Failed to download audiobook")
        return filename

    async def download_cover(self, url: str) -> str:
        """Descarga la portada del audiolibro y retorna la ruta temporal."""
        filename = f"{self.config.TEMP_DIR}/cover_{random.randint(1000, 9999)}.jpg"
        result = await download_file(url, filename)
        if not result:
            raise Exception("Failed to download cover image")
        return filename