import unittest
from pathlib import Path
import json
import shutil
from datetime import datetime

from src.core.session_manager import SessionManager
from src.core.statistics_manager import StatisticsManager
from src.core.backup_manager import BackupManager
from src.core.validation_manager import ValidationManager

class TestSessionManager(unittest.TestCase):
    def setUp(self):
        """Khởi tạo môi trường test"""
        self.test_data_dir = Path("tests/test_data")
        self.test_data_dir.mkdir(exist_ok=True)
        
        # Tạo dữ liệu test
        self.test_session = {
            "id": "test_session",
            "name": "Test Session",
            "video_path": "test.mp4",
            "subtitle_path": "test.srt",
            "created_date": datetime.now().isoformat(),
            "progress": {
                "total_segments": 10,
                "completed_segments": 0,
                "current_segment": 1
            },
            "segments_data": {}
        }
        
    def tearDown(self):
        """Dọn dẹp sau khi test"""
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)
            
    def test_add_segment_attempt(self):
        """Test thêm attempt mới"""
        session_manager = SessionManager()
        session_manager.current_session = self.test_session
        
        attempt_data = {
            "timestamp": datetime.now().isoformat(),
            "text": "test input",
            "accuracy": 90.5,
            "typing_speed": 45,
            "time_taken": 10.5,
            "correct_words": 9,
            "total_words": 10
        }
        
        # Test thêm attempt
        result = session_manager.add_segment_attempt(1, attempt_data)
        self.assertTrue(result)
        
        # Kiểm tra dữ liệu đã được thêm
        segment_data = session_manager.current_session["segments_data"]["1"]
        self.assertEqual(len(segment_data["attempts"]), 1)
        self.assertEqual(segment_data["best_accuracy"], 90.5)
        
    def test_update_session_progress(self):
        """Test cập nhật tiến độ"""
        session_manager = SessionManager()
        session_manager.current_session = self.test_session
        
        # Test cập nhật progress
        result = session_manager.update_session_progress(1, 95, 50, 15)
        self.assertTrue(result)
        
        # Kiểm tra progress đã được cập nhật
        progress = session_manager.current_session["progress"]
        self.assertEqual(progress["completed_segments"], 1)
        self.assertEqual(progress["current_segment"], 1)

class TestStatisticsManager(unittest.TestCase):
    def setUp(self):
        self.stats_manager = StatisticsManager(None)
        
    def test_update_daily_stats(self):
        """Test cập nhật thống kê hàng ngày"""
        stats = {
            "accuracy": 90,
            "typing_speed": 45,
            "time_taken": 15,
            "correct_words": 9,
            "total_words": 10
        }
        
        result = self.stats_manager.update_daily_stats("test_session", stats)
        self.assertTrue(result)
        
        # Kiểm tra thống kê đã được cập nhật
        today = datetime.now().strftime("%Y-%m-%d")
        daily_stats = self.stats_manager.daily_stats[today]
        self.assertEqual(daily_stats["average_accuracy"], 90)
        
class TestBackupManager(unittest.TestCase):
    def setUp(self):
        self.backup_manager = BackupManager(None)
        
    def test_create_backup(self):
        """Test tạo backup"""
        result = self.backup_manager.create_backup()
        self.assertTrue(result)
        
        # Kiểm tra file backup đã được tạo
        backup_files = list(Path("backups").glob("*"))
        self.assertTrue(len(backup_files) > 0)

def run_tests():
    unittest.main()

if __name__ == '__main__':
    run_tests() 