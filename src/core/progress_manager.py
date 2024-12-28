from pathlib import Path
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

class ProgressManager:
    def __init__(self):
        self.progress_file = Path("data/progress.json")
        self.load_progress()
        
    def load_progress(self):
        """Load dữ liệu tiến độ"""
        try:
            if not self.progress_file.exists():
                self.create_default_progress()
            
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                self.progress = json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading progress: {str(e)}")
            self.create_default_progress()
            
    def create_default_progress(self):
        """Tạo dữ liệu tiến độ mặc định"""
        try:
            self.progress = {
                "last_session": None,
                "practice_streak": 0,
                "last_practice_date": None,
                "total_practice_time": 0,
                "completed_videos": []
            }
            return self.save_progress()
        except Exception as e:
            logger.error(f"Error creating default progress: {str(e)}")
            return False
        
    def save_progress(self, progress_data=None):
        """Lưu dữ liệu tiến độ"""
        try:
            if progress_data:
                # Cập nhật các trường từ progress_data
                self.progress.update({
                    "video_file": progress_data["video_file"],
                    "subtitle_file": progress_data["subtitle_file"],
                    "current_segment_index": progress_data["current_segment_index"]
                })
            
            # Lưu xuống file
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, indent=4, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving progress: {str(e)}")
            return False
            
    def update_practice_streak(self):
        """Cập nhật chuỗi ngày luyện tập"""
        try:
            today = datetime.now().date()
            
            # Đảm bảo progress có đủ các trường cần thiết
            if "last_practice_date" not in self.progress:
                self.progress["last_practice_date"] = None
            if "practice_streak" not in self.progress:
                self.progress["practice_streak"] = 0
            
            # Xử lý trường hợp last_practice_date là None
            if self.progress["last_practice_date"] is None:
                self.progress["practice_streak"] = 1
                self.progress["last_practice_date"] = today.strftime("%Y-%m-%d")
                return self.save_progress()
            
            # Chuyển đổi last_practice_date từ string sang date
            try:
                last_practice = datetime.strptime(
                    self.progress["last_practice_date"], 
                    "%Y-%m-%d"
                ).date()
            except (ValueError, TypeError):
                # Nếu có lỗi khi chuyển đổi, reset về giá trị mặc định
                self.progress["practice_streak"] = 1
                self.progress["last_practice_date"] = today.strftime("%Y-%m-%d")
                return self.save_progress()
            
            # Cập nhật streak dựa trên khoảng cách giữa các ngày
            if (today - last_practice) > timedelta(days=1):
                self.progress["practice_streak"] = 1
            elif today > last_practice:
                self.progress["practice_streak"] += 1
            
            self.progress["last_practice_date"] = today.strftime("%Y-%m-%d")
            return self.save_progress()
            
        except Exception as e:
            logger.error(f"Error updating practice streak: {str(e)}")
            # Nếu có lỗi, reset về giá trị mặc định
            self.create_default_progress()
            return False
            
    def save_completed_video(self, video_id, accuracy):
        """Lưu thông tin video đã hoàn thành"""
        try:
            completed_video = {
                "id": video_id,
                "completed_date": datetime.now().strftime("%Y-%m-%d"),
                "accuracy": accuracy
            }
            
            # Kiểm tra xem video đã tồn tại chưa
            for i, video in enumerate(self.progress["completed_videos"]):
                if video["id"] == video_id:
                    # Cập nhật thông tin nếu độ chính xác cao hơn
                    if accuracy > video["accuracy"]:
                        self.progress["completed_videos"][i] = completed_video
                    return self.save_progress()
                    
            # Thêm video mới
            self.progress["completed_videos"].append(completed_video)
            return self.save_progress()
            
        except Exception as e:
            logger.error(f"Error saving completed video: {str(e)}")
            return False
            
    def get_practice_summary(self):
        """Lấy tổng quan tiến độ luyện tập"""
        try:
            return {
                "current_streak": self.progress["practice_streak"],
                "total_videos": len(self.progress["completed_videos"]),
                "total_time": self.progress["total_practice_time"],
                "average_accuracy": sum(v["accuracy"] for v in self.progress["completed_videos"]) / 
                                 len(self.progress["completed_videos"]) if self.progress["completed_videos"] else 0
            }
        except Exception as e:
            logger.error(f"Error getting practice summary: {str(e)}")
            return None
            
    def update_practice_time(self, seconds):
        """Cập nhật tổng thời gian luyện tập"""
        try:
            self.progress["total_practice_time"] += seconds
            return self.save_progress()
        except Exception as e:
            logger.error(f"Error updating practice time: {str(e)}")
            return False 