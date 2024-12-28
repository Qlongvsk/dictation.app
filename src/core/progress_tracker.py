from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ProgressTracker:
    def __init__(self, session_manager):
        self.session_manager = session_manager
        
    def track_segment_attempt(self, segment_index, user_text, correct_text, time_taken):
        """Theo dõi một lần thử của segment"""
        try:
            # Tính toán độ chính xác
            accuracy = self.calculate_accuracy(user_text, correct_text)
            
            # Tính toán tốc độ gõ
            typing_speed = self.calculate_typing_speed(user_text, time_taken)
            
            # Phân tích lỗi
            errors = self.analyze_errors(user_text, correct_text)
            
            # Tạo dữ liệu attempt
            attempt_data = {
                "timestamp": datetime.now().isoformat(),
                "accuracy": accuracy,
                "typing_speed": typing_speed,
                "time_taken": time_taken,
                "errors": errors
            }
            
            # Cập nhật vào session
            return self.session_manager.add_segment_attempt(segment_index, attempt_data)
            
        except Exception as e:
            logger.error(f"Error tracking segment attempt: {str(e)}")
            return False
            
    def calculate_accuracy(self, user_text, correct_text):
        """Tính toán độ chính xác"""
        try:
            # Chuẩn hóa text
            user_words = user_text.lower().split()
            correct_words = correct_text.lower().split()
            
            # Đếm từ đúng
            correct_count = sum(1 for u, c in zip(user_words, correct_words) if u == c)
            total_words = len(correct_words)
            
            return (correct_count / total_words * 100) if total_words > 0 else 0
            
        except Exception as e:
            logger.error(f"Error calculating accuracy: {str(e)}")
            return 0
            
    def calculate_typing_speed(self, text, time_taken):
        """Tính toán tốc độ gõ (WPM)"""
        try:
            words = len(text.split())
            minutes = time_taken / 60  # Chuyển seconds thành minutes
            return round(words / minutes) if minutes > 0 else 0
            
        except Exception as e:
            logger.error(f"Error calculating typing speed: {str(e)}")
            return 0
            
    def analyze_errors(self, user_text, correct_text):
        """Phân tích các lỗi gõ"""
        try:
            user_words = user_text.lower().split()
            correct_words = correct_text.lower().split()
            
            errors = []
            for i, (user, correct) in enumerate(zip(user_words, correct_words)):
                if user != correct:
                    errors.append({
                        "position": i,
                        "expected": correct,
                        "actual": user,
                        "type": self.categorize_error(user, correct)
                    })
                    
            return errors
            
        except Exception as e:
            logger.error(f"Error analyzing errors: {str(e)}")
            return []
            
    def categorize_error(self, user_word, correct_word):
        """Phân loại loại lỗi"""
        if len(user_word) == 0:
            return "missing"
        if user_word in correct_word:
            return "partial"
        if len(user_word) != len(correct_word):
            return "length_mismatch"
        return "wrong_word" 