from datetime import datetime, timedelta
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class StatisticsManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.stats_file = Path("data/statistics.json")
        self.daily_stats = {}
        self.load_statistics()  # Load sẵn thống kê khi khởi tạo
        
    def load_statistics(self):
        """Load dữ liệu thống kê"""
        try:
            if not self.stats_file.exists():
                self.create_default_stats()
            else:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    self.daily_stats = stats.get("daily_stats", {})
                    
        except Exception as e:
            logger.error(f"Error loading statistics: {str(e)}")
            self.create_default_stats()
            
    def create_default_stats(self):
        """Tạo dữ liệu thống kê mặc định"""
        default_stats = {
            "daily_stats": {},
            "total_practice_time": 0,
            "total_segments_completed": 0,
            "achievements": []
        }
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(default_stats, f, indent=4)
        self.daily_stats = {}

    def save_statistics(self):
        """Lưu dữ liệu thống kê"""
        try:
            stats = {
                "daily_stats": self.daily_stats,
                "total_practice_time": sum(
                    day["total_time"] 
                    for day in self.daily_stats.values()
                ),
                "total_segments_completed": sum(
                    day["segments_completed"] 
                    for day in self.daily_stats.values()
                ),
                "achievements": []  # Sẽ cập nhật sau
            }
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=4, ensure_ascii=False)
            return True
            
        except Exception as e:
            logger.error(f"Error saving statistics: {str(e)}")
            return False

    def update_daily_stats(self, session_id, stats):
        """Cập nhật thống kê hàng ngày"""
        try:
            # Validate attempt data trước khi cập nhật
            if not self.validation_manager.validate_attempt_data(stats):
                raise ValueError("Invalid attempt data")
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            if today not in self.daily_stats:
                self.daily_stats[today] = {
                    "sessions": {},
                    "total_time": 0,
                    "average_accuracy": 0,
                    "average_speed": 0,
                    "segments_completed": 0
                }
                
            # Cập nhật thống kê cho session
            if session_id not in self.daily_stats[today]["sessions"]:
                self.daily_stats[today]["sessions"][session_id] = []
                
            self.daily_stats[today]["sessions"][session_id].append(stats)
            
            # Tính toán thống kê tổng hợp
            all_attempts = [
                attempt
                for session_stats in self.daily_stats[today]["sessions"].values()
                for attempt in session_stats
            ]
            
            total_attempts = len(all_attempts)
            if total_attempts > 0:
                self.daily_stats[today].update({
                    "total_time": sum(a["time_taken"] for a in all_attempts),
                    "average_accuracy": sum(a["accuracy"] for a in all_attempts) / total_attempts,
                    "average_speed": sum(a["typing_speed"] for a in all_attempts) / total_attempts,
                    "segments_completed": len(set(
                        session_id + "_" + str(i)
                        for session_id, attempts in self.daily_stats[today]["sessions"].items()
                        for i, attempt in enumerate(attempts)
                        if attempt["accuracy"] >= 95
                    ))
                })
            
            return self.save_statistics()
            
        except Exception as e:
            logger.error(f"Error updating daily stats: {str(e)}")
            return False

    def get_current_stats(self):
        """Lấy thống kê hiện tại"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            if today not in self.daily_stats:
                return {
                    "accuracy": 0,
                    "typing_speed": 0,
                    "total_time": 0,
                    "segments_completed": 0,
                    "practice_streak": 1  # Mặc định là 1 khi bắt đầu
                }
            
            daily = self.daily_stats[today]
            return {
                "accuracy": daily["average_accuracy"],
                "typing_speed": daily["average_speed"],
                "total_time": daily["total_time"],
                "segments_completed": daily["segments_completed"],
                "practice_streak": 1  # Sẽ cập nhật từ ProgressManager sau
            }
            
        except Exception as e:
            logger.error(f"Error getting current stats: {str(e)}")
            return {
                "accuracy": 0,
                "typing_speed": 0,
                "total_time": 0,
                "segments_completed": 0,
                "practice_streak": 1
            } 