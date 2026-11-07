"""Cache historique indexé uniquement par pixels, non utilisé par Pipeline.

Ne pas réactiver sur un traitement OCR sans qualifier son contexte complet.
Conservé pour compatibilité et lecture des données existantes ; pas de purge.
"""
import hashlib
import json
import sqlite3
from typing import Optional

from .config import get_config
from .models import PageResult


class PageCache:
    def __init__(self):
        cfg = get_config()
        self.db_path = cfg.data_dir / "ocr_cache.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS page_cache (
                    hash TEXT PRIMARY KEY,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _hash_image(self, image_data: bytes) -> str:
        return hashlib.sha256(image_data).hexdigest()

    def get(self, image_data: bytes) -> Optional[PageResult]:
        h = self._hash_image(image_data)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT data FROM page_cache WHERE hash = ?", (h,)).fetchone()
            if row:
                data = json.loads(row[0])
                return PageResult(**data)
        return None

    def set(self, image_data: bytes, result: PageResult):
        h = self._hash_image(image_data)
        data = json.dumps(result.model_dump(mode='json'))
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO page_cache (hash, data) VALUES (?, ?)", (h, data))
