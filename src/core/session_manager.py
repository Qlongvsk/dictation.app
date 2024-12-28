from datetime import datetime
import uuid
import logging
from .data_manager import DataManager
from .error_handler import ErrorType, AppError
from .cache_manager import CacheManager
from pathlib import Path

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.data_manager = DataManager()
        self.current_session = None
        self.cache_manager = CacheManager()
        self.error_handler = None
        
    def create_session(self, video_path, subtitle_path, name=None):
        """Tạo phiên học mới"""
        try:
            session = {
                "id": str(uuid.uuid4()),
                "name": name or f"Practice Session {datetime.now().strftime('%Y%m%d_%H%M')}",
                "video_path": str(video_path),
                "subtitle_path": str(subtitle_path),
                "created_date": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "progress": {
                    "total_segments": 0,
                    "completed_segments": 0,
                    "current_segment": 1,
                    "accuracy": 0
                },
                "segments_data": {}
            }
            
            if self.data_manager.save_session(session):
                self.current_session = session
                return session
            return None
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return None
            
    def load_session(self, session_id):
        """Load một phiên học cụ thể"""
        try:
            data = self.data_manager.load_sessions()
            for session in data["sessions"]:
                if session["id"] == session_id:
                    self.current_session = session
                    return session
            return None
            
        except Exception as e:
            logger.error(f"Error loading session: {str(e)}")
            return None
            
    def update_progress(self, segment_index, accuracy):
        """Cập nhật tiến độ của phiên hiện tại"""
        if not self.current_session:
            return False
            
        try:
            # Cập nhật thông tin segment
            self.current_session["segments_data"][str(segment_index)] = {
                "attempts": self.current_session["segments_data"].get(str(segment_index), {}).get("attempts", 0) + 1,
                "accuracy": accuracy,
                "completed": True
            }
            
            # Cập nhật tiến độ tổng thể
            completed = len([s for s in self.current_session["segments_data"].values() if s["completed"]])
            total_accuracy = sum(s["accuracy"] for s in self.current_session["segments_data"].values()) / len(self.current_session["segments_data"]) if self.current_session["segments_data"] else 0
            
            self.current_session["progress"].update({
                "completed_segments": completed,
                "current_segment": segment_index,
                "accuracy": total_accuracy
            })
            
            # Lưu thay đổi
            return self.data_manager.save_session(self.current_session)
            
        except Exception as e:
            logger.error(f"Error updating progress: {str(e)}")
            return False 

    def add_segment_attempt(self, segment_index, attempt_data):
        """Thêm một lần thử mới cho segment"""
        try:
            if not self.current_session:
                raise AppError(
                    ErrorType.SESSION_ERROR,
                    "No active session",
                    {"action": "add_attempt"}
                )
            
            # Validate attempt data
            if not self.validation_manager.validate_attempt_data(attempt_data):
                raise AppError(
                    ErrorType.VALIDATION_ERROR,
                    "Invalid attempt data",
                    {"attempt_data": attempt_data}
                )
            
            segment_id = str(segment_index)
            if segment_id not in self.current_session["segments_data"]:
                self.current_session["segments_data"][segment_id] = {
                    "attempts": [],
                    "best_accuracy": 0,
                    "average_time": 0,
                    "completed": False,
                    "typing_speeds": []
                }
            
            # Thêm attempt và cập nhật thống kê
            segment = self.current_session["segments_data"][segment_id]
            segment["attempts"].append(attempt_data)
            segment["best_accuracy"] = max(
                segment["best_accuracy"],
                attempt_data["accuracy"]
            )
            segment["typing_speeds"].append(attempt_data["typing_speed"])
            
            # Tính thời gian trung bình
            total_time = sum(a["time_taken"] for a in segment["attempts"])
            segment["average_time"] = total_time / len(segment["attempts"])
            
            if not self.save_sessions():
                raise AppError(
                    ErrorType.SESSION_ERROR,
                    "Failed to save session data",
                    {"session_id": self.current_session["id"]}
                )
            
            return True
            
        except AppError as e:
            self.error_handler.handle_error(e)
            return False
        except Exception as e:
            logger.error(f"Error adding segment attempt: {str(e)}")
            return False

    def get_session_statistics(self):
        """Lấy thống kê chi tiết của session hiện tại"""
        try:
            if not self.current_session:
                return None
            
            # Kiểm tra cache
            cache_key = f"stats_{self.current_session['id']}"
            cached_stats = self.cache_manager.get(cache_key)
            if cached_stats:
                return cached_stats
            
            # Tính toán thống kê mới
            stats = {
                "total_segments": len(self.segments),
                "completed_segments": len([
                    s for s in self.current_session["segments_data"].values()
                    if s["completed"]
                ]),
                "total_attempts": sum(
                    len(s["attempts"])
                    for s in self.current_session["segments_data"].values()
                ),
                "average_accuracy": sum(
                    s["best_accuracy"]
                    for s in self.current_session["segments_data"].values()
                ) / len(self.current_session["segments_data"])
                if self.current_session["segments_data"] else 0,
                "average_speed": sum(
                    sum(s["typing_speeds"]) / len(s["typing_speeds"])
                    for s in self.current_session["segments_data"].values()
                    if s["typing_speeds"]
                ) / len(self.current_session["segments_data"])
                if self.current_session["segments_data"] else 0,
                "total_time": sum(
                    s["average_time"] * len(s["attempts"])
                    for s in self.current_session["segments_data"].values()
                ),
                "difficult_segments": [
                    segment_id for segment_id, data
                    in self.current_session["segments_data"].items()
                    if len(data["attempts"]) > 3 or data["best_accuracy"] < 80
                ]
            }
            
            # Lưu vào cache
            self.cache_manager.set(cache_key, stats)
            return stats
            
        except Exception as e:
            logger.error(f"Error getting session statistics: {str(e)}")
            return None 

    def get_difficult_segments(self):
        """Lấy danh sách các segment khó"""
        if not self.current_session:
            return []
        
        try:
            difficult = []
            for segment_id, data in self.current_session["segments_data"].items():
                if (len(data["attempts"]) > 3 or 
                    data.get("best_accuracy", 0) < 80 or
                    data.get("average_time", 0) > 60):
                    difficult.append({
                        "segment_id": int(segment_id),
                        "attempts": len(data["attempts"]),
                        "best_accuracy": data.get("best_accuracy", 0),
                        "average_time": data.get("average_time", 0)
                    })
            return sorted(difficult, key=lambda x: x["best_accuracy"])
            
        except Exception as e:
            logger.error(f"Error getting difficult segments: {str(e)}")
            return []

    def get_practice_recommendations(self):
        """Đưa ra các đề xuất luyện tập"""
        if not self.current_session:
            return []
        
        try:
            recommendations = []
            stats = self.get_session_statistics()
            
            # Kiểm tra segments khó
            difficult = self.get_difficult_segments()
            if difficult:
                recommendations.append({
                    "type": "review",
                    "message": f"Review {len(difficult)} difficult segments",
                    "segments": [d["segment_id"] for d in difficult]
                })
            
            # Kiểm tra độ chính xác
            if stats["average_accuracy"] < 90:
                recommendations.append({
                    "type": "accuracy",
                    "message": "Focus on accuracy improvement",
                    "target": 90
                })
            
            # Đề xuất dựa trên thời gian
            slow_segments = [
                s for s in self.current_session["segments_data"].values()
                if s.get("average_time", 0) > 45
            ]
            if slow_segments:
                recommendations.append({
                    "type": "speed",
                    "message": "Practice typing speed",
                    "target_segments": len(slow_segments)
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            return [] 

    def update_session_progress(self, segment_index, accuracy, typing_speed, time_taken):
        """Cập nhật tiến độ session"""
        try:
            session = self.current_session
            if not session:
                return False

            # Cập nhật thông tin segment
            segment_id = str(segment_index)
            if segment_id not in session["segments_data"]:
                session["segments_data"][segment_id] = {
                    "attempts": [],
                    "best_accuracy": 0,
                    "average_time": 0,
                    "completed": False,
                    "typing_speeds": []
                }

            segment_data = session["segments_data"][segment_id]
            
            # Cập nhật thống kê segment
            segment_data["best_accuracy"] = max(segment_data["best_accuracy"], accuracy)
            segment_data["typing_speeds"].append(typing_speed)
            segment_data["average_time"] = (
                segment_data["average_time"] * len(segment_data["attempts"]) + time_taken
            ) / (len(segment_data["attempts"]) + 1) if segment_data["attempts"] else time_taken
            
            # Đánh dấu hoàn thành nếu đạt yêu cầu
            if accuracy >= 95:
                segment_data["completed"] = True

            # Cập nhật tiến độ tổng thể
            completed_segments = sum(
                1 for data in session["segments_data"].values()
                if data["completed"]
            )
            
            total_attempts = sum(
                len(data["attempts"]) 
                for data in session["segments_data"].values()
            )
            
            # Tính các chỉ số trung bình
            if total_attempts > 0:
                avg_accuracy = sum(
                    data["best_accuracy"] 
                    for data in session["segments_data"].values()
                ) / len(session["segments_data"])
                
                avg_speed = sum(
                    sum(data["typing_speeds"]) / len(data["typing_speeds"])
                    for data in session["segments_data"].values()
                    if data["typing_speeds"]
                ) / len(session["segments_data"])
            else:
                avg_accuracy = 0
                avg_speed = 0

            # Cập nhật progress
            session["progress"].update({
                "total_segments": len(self.segments),
                "completed_segments": completed_segments,
                "current_segment": segment_index,
                "accuracy": avg_accuracy,
                "typing_speed": avg_speed,
                "total_time": sum(
                    data["average_time"] * len(data["attempts"])
                    for data in session["segments_data"].values()
                )
            })

            # Lưu session
            return self.save_sessions()

        except Exception as e:
            logger.error(f"Error updating session progress: {str(e)}")
            return False 

    def set_error_handler(self, error_handler):
        """Thiết lập error handler"""
        self.error_handler = error_handler

    def handle_error(self, error_type, message):
        """Xử lý lỗi thông qua error handler"""
        if self.error_handler:
            self.error_handler.handle_error(error_type, message)
        else:
            logger.error(f"Error ({error_type}): {message}") 