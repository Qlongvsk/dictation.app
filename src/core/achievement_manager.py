from datetime import datetime
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AchievementManager:
    def __init__(self, statistics_manager):
        self.statistics_manager = statistics_manager
        self.achievements = {
            "speed_demon": {
                "name": "Speed Demon 🚀",
                "description": "Type faster than 60 WPM",
                "condition": lambda stats: stats.get("typing_speed", 0) > 60
            },
            "accuracy_master": {
                "name": "Accuracy Master 🎯",
                "description": "Achieve 95% accuracy",
                "condition": lambda stats: stats.get("accuracy", 0) >= 95
            },
            "practice_streak": {
                "name": "Practice Streak 🔥",
                "description": "Practice for 5 days in a row",
                "condition": lambda stats: stats.get("practice_streak", 0) >= 5
            }
        }
        
    def check_achievements(self):
        """Kiểm tra thành tích mới"""
        new_achievements = []
        stats = self.statistics_manager.get_current_stats()
        
        for achievement_id, achievement in self.achievements.items():
            if achievement["condition"](stats):
                new_achievements.append(achievement)
                
        return new_achievements 