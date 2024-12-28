import logging
import json
import shutil
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    INVALID_DATA = "INVALID_DATA"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BACKUP_ERROR = "BACKUP_ERROR"
    SESSION_ERROR = "SESSION_ERROR"
    STATISTICS_ERROR = "STATISTICS_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class AppError(Exception):
    def __init__(
        self, 
        error_type: ErrorType,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)

class ErrorHandler:
    def __init__(self):
        self.error_log_file = Path("logs/errors.log")
        self.error_log_file.parent.mkdir(exist_ok=True)
        
    def handle_error(self, error: AppError) -> bool:
        """Xử lý lỗi và trả về True nếu có thể recover"""
        try:
            # Log lỗi
            logger.error(
                f"Error: {error.error_type.value} - {error.message}",
                extra={"details": error.details}
            )
            
            # Xử lý theo loại lỗi
            if error.error_type == ErrorType.FILE_NOT_FOUND:
                return self.handle_file_not_found(error)
                
            elif error.error_type == ErrorType.INVALID_DATA:
                return self.handle_invalid_data(error)
                
            elif error.error_type == ErrorType.BACKUP_ERROR:
                return self.handle_backup_error(error)
                
            elif error.error_type == ErrorType.SESSION_ERROR:
                return self.handle_session_error(error)
                
            else:
                return self.handle_unknown_error(error)
                
        except Exception as e:
            logger.critical(f"Error handler failed: {str(e)}")
            return False
            
    def handle_file_not_found(self, error: AppError) -> bool:
        """Xử lý lỗi file không tồn tại"""
        try:
            file_path = Path(error.details.get("file_path", ""))
            
            # Kiểm tra và tạo file mặc định
            if file_path.suffix == ".json":
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    if "sessions" in file_path.name:
                        json.dump({"sessions": []}, f, indent=4)
                    elif "statistics" in file_path.name:
                        json.dump({"daily_stats": {}}, f, indent=4)
                    elif "progress" in file_path.name:
                        json.dump({
                            "practice_streak": 0,
                            "total_practice_time": 0,
                            "completed_videos": []
                        }, f, indent=4)
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error handling file not found: {str(e)}")
            return False
            
    def handle_invalid_data(self, error: AppError) -> bool:
        """Xử lý lỗi dữ liệu không hợp lệ"""
        try:
            # Backup dữ liệu lỗi
            self.backup_corrupted_data(error.details.get("file_path"))
            
            # Tạo dữ liệu mới
            return self.handle_file_not_found(error)
            
        except Exception as e:
            logger.error(f"Error handling invalid data: {str(e)}")
            return False

    def handle_backup_error(self, error: AppError) -> bool:
        """Xử lý lỗi backup"""
        try:
            # Log chi tiết lỗi backup
            logger.error(
                "Backup error occurred",
                extra={
                    "error_details": error.details,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Thử backup lại với tên file khác
            if "file_path" in error.details:
                new_path = Path(error.details["file_path"]).with_suffix(".bak")
                shutil.copy2(error.details["file_path"], new_path)
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error handling backup error: {str(e)}")
            return False

    def handle_session_error(self, error: AppError) -> bool:
        """Xử lý lỗi session"""
        try:
            # Log chi tiết lỗi session
            logger.error(
                "Session error occurred",
                extra={
                    "session_id": error.details.get("session_id"),
                    "action": error.details.get("action"),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Thử khôi phục session từ backup
            if "session_id" in error.details:
                backup_path = Path("backups/sessions")
                if backup_path.exists():
                    latest_backup = max(backup_path.glob("*.json"), key=lambda x: x.stat().st_mtime)
                    shutil.copy2(latest_backup, "data/sessions.json")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error handling session error: {str(e)}")
            return False

    def handle_unknown_error(self, error: AppError) -> bool:
        """Xử lý lỗi không xác định"""
        try:
            # Log chi tiết lỗi
            logger.error(
                "Unknown error occurred",
                extra={
                    "error_type": error.error_type.value,
                    "details": error.details,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Backup dữ liệu hiện tại
            self.backup_all_data()
            return True
            
        except Exception as e:
            logger.error(f"Error handling unknown error: {str(e)}")
            return False
            
    def backup_corrupted_data(self, file_path: Optional[str]) -> bool:
        """Backup dữ liệu bị lỗi"""
        try:
            if not file_path:
                return False
                
            src = Path(file_path)
            if not src.exists():
                return False
                
            # Tạo backup với timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst = src.parent / f"{src.stem}_corrupted_{timestamp}{src.suffix}"
            shutil.copy2(src, dst)
            
            return True
            
        except Exception as e:
            logger.error(f"Error backing up corrupted data: {str(e)}")
            return False

    def backup_all_data(self) -> bool:
        """Backup tất cả dữ liệu"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path(f"backups/error_backup_{timestamp}")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup các file quan trọng
            for file in Path("data").glob("*.json"):
                shutil.copy2(file, backup_dir / file.name)
                
            return True
            
        except Exception as e:
            logger.error(f"Error backing up all data: {str(e)}")
            return False 