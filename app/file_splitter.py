import os
from typing import List

class FileSplitter:
    def split_file(self, file_path: str, chunk_size: int = 1.92 * 1024 * 1024 * 1024) -> List[str]:
        file_size = os.path.getsize(file_path)
        if file_size <= chunk_size:
            return [file_path]
            
        chunks = []
        with open(file_path, 'rb') as f:
            chunk_number = 1
            while True:
                chunk = f.read(int(chunk_size))
                if not chunk:
                    break
                    
                chunk_path = f"{file_path}.part{chunk_number}"
                with open(chunk_path, 'wb') as chunk_file:
                    chunk_file.write(chunk)
                chunks.append(chunk_path)
                chunk_number += 1
                
        return chunks