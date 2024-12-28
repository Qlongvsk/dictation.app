from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timeout = 300  # 5 phút
        
    def get(self, key: str) -> Optional[Any]:
        """Lấy dữ liệu từ cache"""
        try:
            if key in self.cache:
                cache_data = self.cache[key]
                # Kiểm tra timeout
                if datetime.now() - cache_data["timestamp"] < timedelta(seconds=self.cache_timeout):
                    return cache_data["value"]
                else:
                    del self.cache[key]
            return None
            
        except Exception as e:
            logger.error(f"Error getting from cache: {str(e)}")
            return None
            
    def set(self, key: str, value: Any) -> bool:
        """Lưu dữ liệu vào cache"""
        try:
            self.cache[key] = {
                "value": value,
                "timestamp": datetime.now()
            }
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            return False
            
    def clear(self, key: Optional[str] = None) -> bool:
        """Xóa cache"""
        try:
            if key:
                if key in self.cache:
                    del self.cache[key]
            else:
                self.cache.clear()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False 