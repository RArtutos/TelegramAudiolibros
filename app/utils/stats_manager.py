import json
import os
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

class StatsManager:
    def __init__(self, stats_file: str = '/data/stats.json'):
        self.stats_file = stats_file
        self.stats = self._load_stats()
        
    def _load_stats(self) -> Dict:
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading stats: {e}")
        
        return {
            "total_uploads": 0,
            "total_size_bytes": 0,
            "uploaded_books": set(),
            "current_status": "idle"
        }
    
    def _save_stats(self):
        try:
            # Convert set to list for JSON serialization
            stats_copy = self.stats.copy()
            stats_copy["uploaded_books"] = list(self.stats["uploaded_books"])
            
            with open(self.stats_file, 'w') as f:
                json.dump(stats_copy, f)
        except Exception as e:
            logger.error(f"Error saving stats: {e}")
    
    def update_status(self, status: str):
        self.stats["current_status"] = status
        self._save_stats()
    
    def add_upload(self, book_id: str, size_bytes: int):
        if book_id not in self.stats["uploaded_books"]:
            self.stats["uploaded_books"].add(book_id)
            self.stats["total_uploads"] += 1
            self.stats["total_size_bytes"] += size_bytes
            self._save_stats()
    
    def is_book_uploaded(self, book_id: str) -> bool:
        return book_id in self.stats["uploaded_books"]
    
    def get_stats(self) -> Dict:
        total_gb = self.stats["total_size_bytes"] / (1024 ** 3)
        return {
            "total_uploads": self.stats["total_uploads"],
            "total_size_gb": f"{total_gb:.2f}",
            "unique_books": len(self.stats["uploaded_books"])
        }
    
    def get_status(self) -> str:
        return self.stats["current_status"]