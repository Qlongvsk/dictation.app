import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        self.config_file = Path("data/config.json")
        self.load_config()
        
    def load_config(self):
        """Load cấu hình từ file"""
        try:
            if not self.config_file.exists():
                self.create_default_config()
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            self.create_default_config()
            
    def create_default_config(self):
        """Tạo cấu hình mặc định"""
        self.config = {
            "app_settings": {
                "auto_save_interval": 300,
                "max_backup_files": 5,
                "min_accuracy_threshold": 95,
                "typing_speed_goal": 60,
                "practice_reminder_interval": 24
            },
            "practice_settings": {
                "auto_pause_after_segment": True,
                "show_typing_speed": True,
                "show_accuracy": True,
                "highlight_errors": True,
                "auto_replay_count": 1
            },
            "ui_settings": {
                "theme": "dark",
                "font_size": 14,
                "subtitle_position": "bottom",
                "show_progress_bar": True,
                "show_statistics": True
            }
        }
        self.save_config()
        
    def save_config(self):
        """Lưu cấu hình"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
            return False
            
    def get_setting(self, section, key, default=None):
        """Lấy giá trị cấu hình"""
        try:
            return self.config[section][key]
        except:
            return default
            
    def update_setting(self, section, key, value):
        """Cập nhật giá trị cấu hình"""
        try:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
            return self.save_config()
        except Exception as e:
            logger.error(f"Error updating setting: {str(e)}")
            return False 