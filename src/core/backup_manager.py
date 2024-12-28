from datetime import datetime
import shutil
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.last_backup_time = datetime.now()
        
        # Khởi tạo timer cho backup tự động
        self.backup_interval = self.config_manager.get_setting(
            "backup_settings", 
            "auto_backup_interval",
            300  # 5 phút
        )
        self.start_auto_backup()
        
    def start_auto_backup(self):
        """Bắt đầu backup tự động"""
        try:
            from PyQt5.QtCore import QTimer
            self.backup_timer = QTimer()
            self.backup_timer.timeout.connect(self.auto_backup)
            self.backup_timer.start(self.backup_interval * 1000)  # Convert to milliseconds
        except Exception as e:
            logger.error(f"Error starting auto backup: {str(e)}")
            
    def auto_backup(self):
        """Thực hiện backup tự động"""
        try:
            # Kiểm tra thời gian từ lần backup cuối
            time_since_last = (datetime.now() - self.last_backup_time).total_seconds()
            if time_since_last >= self.backup_interval:
                self.create_backup()
                self.last_backup_time = datetime.now()
                self.cleanup_old_backups()
                logger.info("Auto backup completed successfully")
        except Exception as e:
            logger.error(f"Auto backup failed: {str(e)}")
            
    def create_backup(self):
        """Tạo backup cho các file dữ liệu"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.backup_dir / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup các file quan trọng
            files_to_backup = [
                "data/sessions.json",
                "data/statistics.json",
                "data/progress.json"
            ]
            
            # Tạo backup cho từng file
            for file_path in files_to_backup:
                src = Path(file_path)
                if src.exists():
                    # Validate file trước khi backup
                    if self.validate_file(src):
                        dst = backup_dir / src.name
                        shutil.copy2(src, dst)
                    else:
                        logger.warning(f"Skipped backup of invalid file: {src}")
                        
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return False
            
    def validate_file(self, file_path):
        """Kiểm tra tính hợp lệ của file trước khi backup"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Kiểm tra cấu trúc cơ bản
            if file_path.name == "sessions.json":
                return isinstance(data.get("sessions"), list)
            elif file_path.name == "statistics.json":
                return isinstance(data.get("daily_stats"), dict)
            elif file_path.name == "progress.json":
                return isinstance(data, dict) and "practice_streak" in data
                
            return True
            
        except Exception as e:
            logger.error(f"File validation failed: {str(e)}")
            return False
            
    def cleanup_old_backups(self):
        """Xóa các backup cũ"""
        try:
            max_backups = self.config_manager.get_setting(
                "backup_settings",
                "max_backups",
                10
            )
            
            # Lấy danh sách backup theo thời gian
            backups = sorted(
                self.backup_dir.glob("*"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            # Xóa các backup cũ
            if len(backups) > max_backups:
                for backup in backups[max_backups:]:
                    if backup.is_dir():
                        shutil.rmtree(backup)
                    else:
                        backup.unlink()
                        
            logger.info(f"Cleaned up old backups, keeping {max_backups} most recent")
            
        except Exception as e:
            logger.error(f"Error cleaning up backups: {str(e)}")
            
    def restore_from_backup(self, backup_path):
        """Khôi phục từ backup"""
        try:
            # Tạo backup hiện tại trước khi restore
            self.create_backup()
            
            # Copy từ backup vào thư mục data
            data_dir = Path("data")
            for file in backup_path.glob("*.json"):
                shutil.copy2(file, data_dir / file.name)
                
            return True
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {str(e)}")
            return False 