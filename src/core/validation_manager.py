import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ValidationManager:
    def __init__(self):
        self.schemas = {
            "session": {
                "required": ["id", "name", "video_path", "subtitle_path", "created_date"],
                "types": {
                    "id": str,
                    "name": str,
                    "video_path": str,
                    "subtitle_path": str,
                    "progress": dict,
                    "segments_data": dict
                }
            },
            "progress": {
                "required": ["practice_streak", "total_practice_time", "completed_videos"],
                "types": {
                    "practice_streak": int,
                    "total_practice_time": int,
                    "completed_videos": list
                }
            }
        }
        
        self.error_types = {
            "file_not_found": "File not found",
            "invalid_format": "Invalid file format",
            "parse_error": "Error parsing file",
            "validation_error": "Validation failed"
        }

    def handle_error(self, error_type, message):
        """Xử lý lỗi"""
        try:
            error_message = f"{self.error_types.get(error_type, 'Unknown error')}: {message}"
            logger.error(error_message)
            return error_message
            
        except Exception as e:
            logger.error(f"Error handling error: {str(e)}")
            return str(e)

    def validate_session(self, session_data):
        """Kiểm tra tính hợp lệ của session"""
        try:
            # Kiểm tra các trường bắt buộc
            for field in self.schemas["session"]["required"]:
                if field not in session_data:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Kiểm tra kiểu dữ liệu
            for field, expected_type in self.schemas["session"]["types"].items():
                if field in session_data and not isinstance(session_data[field], expected_type):
                    raise TypeError(f"Invalid type for {field}: expected {expected_type}")
                    
            # Kiểm tra tồn tại của file
            video_path = Path(session_data["video_path"])
            subtitle_path = Path(session_data["subtitle_path"])
            
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            if not subtitle_path.exists():
                raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")
                
            return True
            
        except Exception as e:
            self.handle_error("validation_error", str(e))
            return False
            
    def validate_progress(self, progress_data):
        """Kiểm tra tính hợp lệ của progress"""
        try:
            # Kiểm tra các trường bắt buộc
            for field in self.schemas["progress"]["required"]:
                if field not in progress_data:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Kiểm tra kiểu dữ liệu
            for field, expected_type in self.schemas["progress"]["types"].items():
                if field in progress_data and not isinstance(progress_data[field], expected_type):
                    raise TypeError(f"Invalid type for {field}: expected {expected_type}")
                    
            # Kiểm tra giá trị hợp lệ
            if progress_data["practice_streak"] < 0:
                raise ValueError("Practice streak cannot be negative")
            if progress_data["total_practice_time"] < 0:
                raise ValueError("Total practice time cannot be negative")
                
            return True
            
        except Exception as e:
            self.handle_error("validation_error", str(e))
            return False
            
    def validate_json_file(self, file_path):
        """Kiểm tra tính hợp lệ của file JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Kiểm tra cấu trúc file dựa trên tên
            if "sessions" in file_path.name:
                if not isinstance(data.get("sessions"), list):
                    raise ValueError("Invalid sessions file structure")
                    
            elif "progress" in file_path.name:
                self.validate_progress(data)
                
            return True
            
        except json.JSONDecodeError as e:
            self.handle_error("invalid_format", str(e))
            return False
        except Exception as e:
            self.handle_error("parse_error", str(e))
            return False 

    def validate_session_data(self, session_data):
        """Validate dữ liệu session trước khi lưu"""
        required_fields = [
            "id", "name", "video_path", "subtitle_path",
            "created_date", "last_accessed", "progress", 
            "segments_data"
        ]
        
        try:
            # Kiểm tra các trường bắt buộc
            for field in required_fields:
                if field not in session_data:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Validate progress
            progress = session_data["progress"]
            if not isinstance(progress["total_segments"], int):
                raise ValueError("total_segments must be integer")
            if not isinstance(progress["completed_segments"], int):
                raise ValueError("completed_segments must be integer")
            
            # Validate segments_data
            for segment_id, data in session_data["segments_data"].items():
                if "attempts" not in data:
                    raise ValueError(f"Missing attempts in segment {segment_id}")
                if "accuracy" not in data:
                    raise ValueError(f"Missing accuracy in segment {segment_id}")
                
            return True
            
        except Exception as e:
            self.handle_error("validation_error", str(e))
            return False 

    def validate_statistics_data(self, stats_data):
        """Validate dữ liệu thống kê"""
        try:
            # Kiểm tra cấu trúc cơ bản
            if not isinstance(stats_data, dict):
                raise ValueError("Statistics data must be a dictionary")
            
            required_fields = ["daily_stats", "total_practice_time", "total_segments_completed"]
            for field in required_fields:
                if field not in stats_data:
                    raise ValueError(f"Missing required field: {field}")
                
            # Validate daily_stats
            daily_stats = stats_data["daily_stats"]
            if not isinstance(daily_stats, dict):
                raise ValueError("daily_stats must be a dictionary")
            
            for date, day_data in daily_stats.items():
                # Validate date format
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    raise ValueError(f"Invalid date format: {date}")
                    
                # Validate day data structure
                required_day_fields = [
                    "sessions", "total_time", "average_accuracy",
                    "average_speed", "segments_completed"
                ]
                for field in required_day_fields:
                    if field not in day_data:
                        raise ValueError(f"Missing field {field} in day data for {date}")
                    
                # Validate numeric values
                if not isinstance(day_data["total_time"], (int, float)):
                    raise ValueError(f"Invalid total_time for {date}")
                if not isinstance(day_data["average_accuracy"], (int, float)):
                    raise ValueError(f"Invalid average_accuracy for {date}")
                if not isinstance(day_data["average_speed"], (int, float)):
                    raise ValueError(f"Invalid average_speed for {date}")
                
            return True
            
        except Exception as e:
            self.handle_error("validation_error", str(e))
            return False 

    def validate_progress_data(self, progress_data):
        """Validate dữ liệu tiến độ"""
        try:
            required_fields = [
                "last_practice_date", "practice_streak",
                "total_practice_time", "completed_videos"
            ]
            
            # Kiểm tra các trường bắt buộc
            for field in required_fields:
                if field not in progress_data:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Validate date format
            if progress_data["last_practice_date"]:
                try:
                    datetime.strptime(progress_data["last_practice_date"], "%Y-%m-%d")
                except ValueError:
                    raise ValueError("Invalid last_practice_date format")
                    
            # Validate numeric values
            if not isinstance(progress_data["practice_streak"], int):
                raise ValueError("practice_streak must be integer")
            if not isinstance(progress_data["total_practice_time"], (int, float)):
                raise ValueError("total_practice_time must be numeric")
            
            # Validate completed_videos
            if not isinstance(progress_data["completed_videos"], list):
                raise ValueError("completed_videos must be a list")
            
            for video in progress_data["completed_videos"]:
                if not isinstance(video, dict):
                    raise ValueError("Each completed video must be a dictionary")
                if "id" not in video or "accuracy" not in video:
                    raise ValueError("Video entries must have id and accuracy")
                    
            return True
            
        except Exception as e:
            self.handle_error("validation_error", str(e))
            return False 

    def validate_attempt_data(self, attempt_data):
        """Validate dữ liệu attempt"""
        try:
            required_fields = [
                "timestamp", "text", "accuracy", "typing_speed",
                "time_taken", "correct_words", "total_words"
            ]
            
            # Kiểm tra các trường bắt buộc
            for field in required_fields:
                if field not in attempt_data:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Validate timestamp format
            try:
                datetime.fromisoformat(attempt_data["timestamp"])
            except ValueError:
                raise ValueError("Invalid timestamp format")
                
            # Validate numeric values
            numeric_fields = ["accuracy", "typing_speed", "time_taken", "correct_words", "total_words"]
            for field in numeric_fields:
                if not isinstance(attempt_data[field], (int, float)):
                    raise ValueError(f"{field} must be numeric")
                    
            # Validate ranges
            if not (0 <= attempt_data["accuracy"] <= 100):
                raise ValueError("Accuracy must be between 0 and 100")
            if attempt_data["typing_speed"] < 0:
                raise ValueError("Typing speed cannot be negative")
            if attempt_data["time_taken"] < 0:
                raise ValueError("Time taken cannot be negative")
            if attempt_data["correct_words"] > attempt_data["total_words"]:
                raise ValueError("Correct words cannot exceed total words")
                
            return True
            
        except Exception as e:
            self.handle_error("validation_error", str(e))
            return False 

    def validate_all_data(self):
        """Validate toàn bộ dữ liệu"""
        try:
            # Validate sessions
            with open("data/sessions.json", 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
                for session in sessions_data["sessions"]:
                    if not self.validate_session_data(session):
                        raise ValueError(f"Invalid session data: {session['id']}")
                    
            # Validate statistics
            with open("data/statistics.json", 'r', encoding='utf-8') as f:
                stats_data = json.load(f)
                if not self.validate_statistics_data(stats_data):
                    raise ValueError("Invalid statistics data")
                    
            # Validate progress
            with open("data/progress.json", 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
                if not self.validate_progress_data(progress_data):
                    raise ValueError("Invalid progress data")
                    
            return True
            
        except Exception as e:
            self.handle_error("validation_error", str(e))
            return False 

    def validate_video_file(self, file_path):
        """Kiểm tra file video"""
        try:
            # Giữ nguyên code cũ...
            pass
            
        except Exception as e:
            self.handle_error("validation_error", str(e))
            return False

    def validate_subtitle_file(self, file_path):
        """Kiểm tra file phụ đề"""
        try:
            # Giữ nguyên code cũ...
            pass
            
        except Exception as e:
            self.handle_error("validation_error", str(e))
            return False 