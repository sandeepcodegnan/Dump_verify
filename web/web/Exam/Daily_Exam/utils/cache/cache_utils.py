"""Cache utilities - DRY Implementation"""
import time
from hashlib import sha256
from typing import Dict, Tuple, Any
from web.Exam.Daily_Exam.config.settings import CacheConfig

class BaseCache:
    """Base cache implementation - DRY"""
    
    def __init__(self, ttl: int = None):
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self.ttl = ttl or CacheConfig.SUBMISSION_CACHE_TTL
    
    def get(self, key: str) -> Dict[str, Any]:
        """Get cached result"""
        rec = self._cache.get(key)
        if not rec:
            return None
        expires_at, val = rec
        if expires_at < time.time():
            self._cache.pop(key, None)
            return None
        return val
    
    def put(self, key: str, val: Dict[str, Any]) -> None:
        """Cache result"""
        self._cache[key] = (time.time() + self.ttl, val)
    
    def clear(self) -> None:
        """Clear cache"""
        self._cache.clear()

def hash_submission(qid: str, lang: str, code: str) -> str:
    """Hash submission for caching - secure SHA256"""
    h = sha256()
    h.update(qid.encode())
    h.update(lang.lower().encode())
    h.update(code.encode())
    return h.hexdigest()

# Specific cache types with custom TTL
SubmissionCache = BaseCache
LeaderboardCache = lambda: BaseCache(60)  # 2 minutes
ExamCache = lambda: BaseCache(60)  # 1 minutes

# Global cache instances
submission_cache = SubmissionCache()
leaderboard_cache = LeaderboardCache()
exam_cache = ExamCache()  # Global exam cache instance