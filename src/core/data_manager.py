import json
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self):
        self.data_dir = Path("data")
        self.sessions_file = self.data_dir / "sessions.json"
        self.ensure_data_directory()
        
    def ensure_data_directory(self):
        """Đảm bảo thư mục data và các file cần thiết tồn tại"""
        self.data_dir.mkdir(exist_ok=True)
        if not self.sessions_file.exists():
            self.sessions_file.write_text('{"sessions": []}', encoding='utf-8')
            
    def load_sessions(self):
        """Load tất cả sessions"""
        try:
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading sessions: {str(e)}")
            return {"sessions": []}
            
    def save_session(self, session_data):
        """Lưu hoặc cập nhật session"""
        try:
            data = self.load_sessions()
            
            # Tìm và cập nhật session nếu đ tồn tại
            session_found = False
            for i, session in enumerate(data["sessions"]):
                if session["id"] == session_data["id"]:
                    data["sessions"][i] = session_data
                    session_found = True
                    break
            
            # Thêm mới nếu chưa tồn tại
            if not session_found:
                data["sessions"].append(session_data)
            
            # Lưu file
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")
            return False 

    def backup_sessions(self):
        """Tạo backup cho dữ liệu sessions"""
        try:
            backup_dir = self.data_dir / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            # Tạo tên file backup với timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"sessions_backup_{timestamp}.json"
            
            # Copy dữ liệu hiện tại sang file backup
            data = self.load_sessions()
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            # Giữ lại tối đa 5 file backup gần nhất
            backup_files = sorted(backup_dir.glob("sessions_backup_*.json"))
            if len(backup_files) > 5:
                for file in backup_files[:-5]:
                    file.unlink()
                
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return False

    def restore_from_backup(self, backup_file):
        """Khôi phục dữ liệu từ file backup"""
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
                
            # Verify dữ liệu backup
            if "sessions" not in backup_data:
                raise ValueError("Invalid backup file format")
                
            # Backup file hiện tại trước khi restore
            self.backup_sessions()
            
            # Restore dữ liệu
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=4, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {str(e)}")
            return False 