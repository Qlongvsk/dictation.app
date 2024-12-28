from pathlib import Path
import difflib
import string
import json
import logging
import vlc
from textblob import TextBlob
from datetime import datetime

from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTextEdit, QSpinBox, QDialog, QFormLayout,
    QMenuBar, QMessageBox, QSlider, QShortcut, QSizePolicy,
    QSplitter, QMenu, QGraphicsOpacityEffect
)
from PyQt5.QtCore import QTimer, Qt, QTime, QSize
from PyQt5.QtGui import QKeySequence

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.video import VideoProcessor
from core.session_manager import SessionManager
from core.config_manager import ConfigManager
from core.statistics_manager import StatisticsManager
from core.achievement_manager import AchievementManager
from core.progress_manager import ProgressManager
from core.backup_manager import BackupManager
from core.validation_manager import ValidationManager
from core.video_converter import VideoConverter
from src.ui.progress_dialog import ConversionProgressDialog
from core.data_manager import DataManager
from src.ui.video_player import VideoPlayer
from src.ui.video_controls import VideoControls

logger = logging.getLogger(__name__)

class CustomTextEdit(QTextEdit):
    """Widget tùy chỉnh cho việc nhập văn bản"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setAcceptRichText(False)
        self.ctrl_pressed = False
        self.is_updating = False
        self.current_word_index = 0
        self.textChanged.connect(self.on_text_changed)
        
    def normalize_text(self, text):
        """Chuẩn hóa text: bỏ dấu câu, chuyển về chữ thường"""
        punctuation = '!()-[]{};:\'",<>./?@#$%^&*_~'
        for char in punctuation:
            text = text.replace(char, '')
        return ' '.join(text.lower().split())

    def keyPressEvent(self, event):
        # Xử lý phím Ctrl để replay
        if event.key() == Qt.Key_Control:
            if self.parent_app:
                self.parent_app.replay_segment()
            return

        # Xử lý phím Tab để previous segment
        if event.key() == Qt.Key_Tab:
            if self.parent_app:
                self.parent_app.previous_segment()
            return

        # Xử lý phím Enter như cũ
        if event.key() == Qt.Key_Return:
            current_text = self.toPlainText().strip()
            target_text = self.parent_app.segments[self.parent_app.current_segment_index - 1]["text"]
            
            if current_text == target_text:
                self.parent_app.next_segment()
                return
                
            self.setText(target_text)
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.setTextCursor(cursor)
            return

        # Xử lý phím Space như cũ
        if event.key() == Qt.Key_Space:
            if self.parent_app and self.parent_app.segments:
                current_text = self.toPlainText().strip()
                target_text = self.parent_app.segments[self.parent_app.current_segment_index - 1]["text"]
                if len(current_text.split()) == len(target_text.split()):
                    return

        super().keyPressEvent(event)

    def on_text_changed(self):
        if self.is_updating:
            return

        try:
            if not self.parent_app or not self.parent_app.segments:
                return

            self.is_updating = True
            current_text = self.toPlainText()
            target_text = self.parent_app.segments[self.parent_app.current_segment_index - 1]["text"]

            # Tách thành từng từ
            current_words = current_text.split()
            target_words = target_text.split()

            # Reset format
            cursor = self.textCursor()
            cursor.select(QTextCursor.Document)
            cursor.setCharFormat(QTextCharFormat())

            # Highlight từng từ
            cursor.setPosition(0)
            pos = 0
            correct_count = 0
            
            for i, current_word in enumerate(current_words):
                if i >= len(target_words):
                    break

                word_format = QTextCharFormat()
                if self.normalize_text(current_word) == self.normalize_text(target_words[i]):
                    word_format.setForeground(QColor("green"))
                    correct_count += 1
                else:
                    word_format.setForeground(QColor("red"))

                cursor.setPosition(pos)
                cursor.setPosition(pos + len(current_word), QTextCursor.KeepAnchor)
                cursor.setCharFormat(word_format)

                pos += len(current_word) + 1

            # Cập nhật word count trong 2 trường hợp:
            # 1. Khi gõ xong từ (có space hoặc enter) cho các từ không phải từ cuối
            # 2. Khi từ cuối cùng đc gõ đúng
            if (current_text.endswith(' ') or current_text.endswith('\n')) or \
               (len(current_words) == len(target_words) and \
                len(current_words) > 0 and \
                self.normalize_text(current_words[-1]) == self.normalize_text(target_words[-1])):
                
                total_words = len(target_words)
                accuracy = (correct_count / total_words * 100) if total_words > 0 else 0
                self.parent_app.word_count_widget.update_count(
                    correct_count,
                    total_words,
                    accuracy
                )

        except Exception as e:
            logger.error(f"Error handling text changed: {str(e)}")

        finally:
            self.is_updating = False

    def keyReleaseEvent(self, event):
        """Xử lý sự kiện th phím"""
        if event.key() == Qt.Key_Control:
            self.ctrl_pressed = False
        super().keyReleaseEvent(event)

class WordCountWidget(QLabel):
    """Widget hiển thị số từ và độ chính xác"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignRight)
        self.setStyleSheet("""
            QLabel {
                color: white;
                padding: 5px;
                background-color: #3d3d3d;
                border-radius: 4px;
            }
        """)
        self.update_count(0, 0, 0)
        
    def update_count(self, correct: int, total: int, accuracy: float):
        """Cập nhật số từ và độ chính xác"""
        progress = "░" * 20  # Thanh progress mặc định
        if total > 0:
            filled = int((correct / total) * 20)
            progress = "█" * filled + "░" * (20 - filled)
        
        self.setText(f"Words: {correct}/{total} [{progress}] {accuracy:.1f}%")

class FloatingTextEdit(CustomTextEdit):
    """Widget nhập liệu nổi trên video"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup cho FloatingTextEdit"""
        # Cho phép trong suốt hoàn toàn
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Style cơ bản - chỉ có background màu đen trong suốt, không có viền
        self.setStyleSheet("""
            FloatingTextEdit {
                background-color: rgba(43, 43, 43, 0.8);
                color: white;
                border: none;
                padding: 0px 8px;
            }
            QScrollBar {
                background: transparent;
                width: 0px;
                height: 0px;
            }
        """)
        
        # Thiết lập căn giữa text theo chiều dọc
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setAlignment(Qt.AlignVCenter)
        
        # Font mặc định
        self.current_font_size = 14
        self.current_opacity = 0.8
        font = QFont()
        font.setPointSize(self.current_font_size)
        self.setFont(font)
        
        # Kích thước mặc định
        self.default_height = 40
        self.setMinimumWidth(400)
        self.setMaximumWidth(1200)
        self.setFixedHeight(self.default_height)
        
        # Context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Kết nối signal textChanged để điều chỉnh chiều cao
        self.textChanged.connect(self.adjust_height)

    def adjust_height(self):
        """Tự động điều chỉnh chiều cao theo nội dung"""
        # Tính toán chiều cao cần thiết dựa trên nội dung
        doc = self.document()
        doc_height = doc.size().height()
        
        # Thêm padding để text không bị sát cạnh
        needed_height = int(doc_height + 24)
        
        # Giới hạn chiều cao từ default đến max
        new_height = max(needed_height, self.default_height)
        new_height = min(new_height, 200)
        
        # Chỉ thay đổi nếu chiều cao mới khác chiều cao hiện tại
        if new_height != self.height():
            self.setFixedHeight(new_height)
            
            # Cập nhật vị trí để giữ nguyên bottom edge
            if hasattr(self, 'parent') and self.parent():
                parent_height = self.parent().height()
                parent_width = self.parent().width()
                
                # Tính toán chiều rộng cần thiết
                doc_width = doc.idealWidth() + 50  # Thêm margin
                new_width = min(max(doc_width, self.minimumWidth()), self.maximumWidth())
                
                # Căn giữa theo chiều ngang và đặt ở dưới
                new_x = int((parent_width - new_width) // 2)
                new_y = int(parent_height - new_height - 40)
                
                self.setGeometry(new_x, new_y, new_width, new_height)

    def change_font_size(self, size):
        """Thay đổi cỡ chữ"""
        self.current_font_size = size
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)
        self.adjust_height()

    def change_opacity(self, opacity):
        """Thay đổi độ trong suốt"""
        self.current_opacity = opacity
        self.setStyleSheet(f"""
            FloatingTextEdit {{
                background-color: rgba(43, 43, 43, {opacity});
                color: white;
                border: none;
                padding: 0px 8px;
            }}
            QScrollBar {{
                background: transparent;
                width: 0px;
                height: 0px;
            }}
        """)

    def resizeEvent(self, event):
        """Xử lý resize event"""
        super().resizeEvent(event)
        if hasattr(self, 'parent') and self.parent():
            # Cập nhật vị trí để giữ nguyên bottom edge
            parent_height = self.parent().height()
            new_y = parent_height - self.height() - 40  # Cách bottom 40px
            self.setGeometry(self.x(), new_y, self.width(), self.height())

    def next_segment(self):
        """Reset kích thước khi chuyển segment"""
        self.setFixedHeight(self.default_height)
        super().next_segment()

    def show_context_menu(self, pos):
        """Hiển thị menu tùy chỉnh khi right-click"""
        menu = QMenu(self)
        
        # Menu điều chỉnh font size
        font_menu = menu.addMenu("Font Size")
        for size in [12, 14, 16, 18, 20]:
            action = font_menu.addAction(f"{size}pt")
            action.triggered.connect(lambda checked, s=size: self.change_font_size(s))
        
        # Menu điều chỉnh độ trong suốt
        opacity_menu = menu.addMenu("Opacity")
        for opacity in [0.6, 0.7, 0.8, 0.9, 1.0]:
            action = opacity_menu.addAction(f"{int(opacity * 100)}%")
            action.triggered.connect(lambda checked, o=opacity: self.change_opacity(o))
        
        menu.exec_(self.mapToGlobal(pos))

class TranscriptionApp(QWidget):
    def __init__(self):
        super().__init__()
        # Khởi tạo các thuộc tính
        self.video_file = None
        self.subtitle_file = None
        self.segments = None
        self.current_segment_index = 0
        self.timer = QTimer()
        self.segment_timer = QTimer()
        self.replay_count = 1  # Thêm replay_count với giá trị mặc định
        
        # Khởi tạo managers và UI
        self.init_managers()
        self.init_ui()

    def init_managers(self):
        """Khởi tạo các manager"""
        try:
            # Khởi tạo theo thứ tự phụ thuộc
            self.config_manager = ConfigManager()
            self.data_manager = DataManager()
            self.statistics_manager = StatisticsManager(self.data_manager)
            self.achievement_manager = AchievementManager(self.statistics_manager)
            self.session_manager = SessionManager()
            self.progress_manager = ProgressManager()
            self.video_converter = VideoConverter()
            self.validation_manager = ValidationManager()
            
            # Thiết lập error handler cho session manager
            self.session_manager.set_error_handler(self.validation_manager)
            
        except Exception as e:
            logger.error(f"Error initializing managers: {str(e)}")
            raise
        
    def init_ui(self):
        """Khởi tạo giao diện người dùng"""
        self.setWindowTitle("Transcription Practice")
        self.setGeometry(100, 100, 1280, 720)
        
        main_layout = QHBoxLayout()  # Đổi thành HBox để chia 2 cột
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Container bên trái chứa video và text
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setSpacing(0)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Thêm menu
        self.setup_menu(left_layout)
        
        # Container cho video
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        # Thêm video player
        self.video_frame = VideoPlayer(self)
        video_layout.addWidget(self.video_frame)
        
        # Thêm video controls
        self.video_controls = VideoControls(self)
        video_layout.addWidget(self.video_controls)
        
        left_layout.addWidget(video_container)
        
        # Status bar và word count ở dưới
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        self.word_count_widget = WordCountWidget()
        status_layout.addWidget(self.word_count_widget)
        left_layout.addWidget(status_container)
        
        # Text edit nổi trên video - Sửa lại parent
        self.text_edit = FloatingTextEdit(self)  # Truyền self thay vì video_container
        self.text_edit.setParent(video_container)  # Đặt parent widget là video_container
        self.text_edit.parent_app = self  # Thêm reference đến TranscriptionApp
        self.text_edit.show()
        
        # Đặt vị trí ban đầu cho text edit
        video_container.resizeEvent = lambda e: self.on_container_resize(e)
        
        main_layout.addWidget(left_container)
        
        # Container bên phải cho các nút điều khiển
        right_container = QWidget()
        right_container.setFixedWidth(60)
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Thêm các nút điều khiển theo chiều dọc
        self.setup_control_buttons(right_layout)
        
        main_layout.addWidget(right_container)
        
        self.setLayout(main_layout)

    def on_container_resize(self, event):
        """Xử lý khi container thay đổi kích thước"""
        if hasattr(self, 'text_edit'):
            container_width = event.size().width()
            container_height = event.size().height()
            
            # Tính toán kích thước cho text edit
            text_width = min(600, container_width - 40)  # Max 600px hoặc nhỏ hơn video
            text_height = 40  # Chiều cao mặc định
            
            # Đặt vị trí: căn giữa theo chiều ngang, phía dưới video
            x = (container_width - text_width) // 2
            y = container_height - text_height - 40  # Cách bottom 40px
            
            self.text_edit.setGeometry(x, y, text_width, text_height)

    def setup_menu(self, layout):
        """Thiết lập menu"""
        menu_bar = QMenuBar()
        layout.addWidget(menu_bar)
        
        # Menu File
        file_menu = menu_bar.addMenu("File")
        
        open_action = file_menu.addAction("Open Files")
        open_action.triggered.connect(self.load_files)
        
        save_action = file_menu.addAction("Save Progress")
        save_action.triggered.connect(self.save_progress)
        
        # Menu View
        view_menu = menu_bar.addMenu("View")
        
        stats_action = view_menu.addAction("Statistics")
        stats_action.triggered.connect(self.show_statistics)
        
        # Menu Help
        help_menu = menu_bar.addMenu("Help")
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        
    def setup_control_buttons(self, layout):
        """Thiết lập các nút điều khiển theo chiều dọc"""
        button_style = """
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 6px;
                min-width: 32px;
                min-height: 32px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
            }
        """
        
        # Các nút theo thứ tự từ trên xuống (bỏ nút check)
        buttons = [
            ("⏮", "Previous segment", self.previous_segment),
            ("⟳", "Replay current segment", self.replay_segment),
            ("⏭", "Next segment", self.next_segment),
            ("⚙", "Settings", self.show_settings)
        ]
        
        for icon, tooltip, callback in buttons:
            btn = QPushButton(icon)
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            btn.setStyleSheet(button_style)
            layout.addWidget(btn)
        
        # Thêm spacer để đẩy các nút lên trên
        layout.addStretch()

    def load_files(self):
        """Tải file video và phụ đề"""
        try:
            # Chọn file video
            video_file, _ = QFileDialog.getOpenFileName(
                self, "Open Video File", "", 
                "Video Files (*.mp4 *.avi *.mkv *.ts)"
            )
            if not video_file:
                return

            # Nếu là file .ts, tự động chuyển đi
            if video_file.lower().endswith('.ts'):
                try:
                    # Tạo và hiển thị dialog tiền trình
                    progress_dialog = ConversionProgressDialog(self)
                    
                    # Kết nối signal từ converter với dialog
                    self.video_converter.progress_updated.connect(
                        progress_dialog.update_progress
                    )
                    
                    # Hiển thị dialog
                    progress_dialog.show()
                    
                    # Chuyển đổi video
                    video_file = self.video_converter.convert_ts_to_mp4(video_file)
                    
                    # Đóng dialog
                    progress_dialog.close()
                    
                    # Ngắt kết nối signal
                    self.video_converter.progress_updated.disconnect()
                    
                    self.show_message("Success", "Conversion completed successfully!")
                except Exception as e:
                    self.show_error_message("Conversion Error", str(e))
                    return

            # Chọn file phụ đề
            subtitle_file, _ = QFileDialog.getOpenFileName(
                self, "Open Subtitle File", "", "Subtitle Files (*.srt)"
            )
            if not subtitle_file:
                return

            # Cập nhật đường dẫn file
            self.video_file = video_file
            self.subtitle_file = subtitle_file

            # Load video và phụ đề
            if not self.load_video():
                raise Exception("Failed to load video")
            if not self.load_subtitles():
                raise Exception("Failed to load subtitles")

            return True

        except Exception as e:
            logger.error(f"Error loading files: {str(e)}")
            self.show_error_message("Error", f"Could not load files: {str(e)}")
            return False

    def show_message(self, title: str, message: str):
        """Hiển thị thông báo"""
        QMessageBox.information(self, title, message)

    def show_error_message(self, title: str, message: str):
        """Hiển thị thông báo lỗi"""
        QMessageBox.critical(self, title, message)

    def load_video(self):
        """Load file video"""
        try:
            # Khởi tạo VLC player
            self.instance = vlc.Instance()
            self.player = self.instance.media_player_new()
            
            # Load video
            media = self.instance.media_new(self.video_file)
            self.player.set_media(media)
            
            # Gán player vào video frame
            if sys.platform.startswith('linux'):
                self.player.set_xwindow(self.video_frame.winId())
            elif sys.platform == "win32":
                self.player.set_hwnd(self.video_frame.winId())
            elif sys.platform == "darwin":
                self.player.set_nsobject(int(self.video_frame.winId()))
                
            return True
            
        except Exception as e:
            logger.error(f"Error loading video: {str(e)}")
            return False

    def load_subtitles(self):
        """Load và x lý file phụ đề"""
        try:
            # Tải phụ đề
            self.video_processor = VideoProcessor()
            self.segments = self.video_processor.load_subtitles(self.subtitle_file)
            if not self.segments:
                raise Exception("No segments found in subtitle file")
            
            # Đặt vị trí video tại segment đầu tiên
            self.current_segment_index = 1
            if self.segments:
                first_segment = self.segments[0]
                start_time = first_segment["start_time"]
                end_time = first_segment["end_time"]
                
                # Chuyển đổi thời gian
                start_ms = self.video_processor.time_to_milliseconds(start_time)
                end_ms = self.video_processor.time_to_milliseconds(end_time)
                
                # Set vị trí và timer
                self.player.set_time(int(start_ms))
                duration = end_ms - start_ms
                self.timer.start(int(duration))
                
            # Cập nhật giao diện
            self.text_edit.clear()
            self.update_button_states()
            self.word_count_widget.update_count(0, 0, 0)  # Reset word count
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading subtitles: {str(e)}")
            return False

    def check_transcription(self):
        """Kiểm tra kết quả gõ phụ đề"""
        try:
            if not self.text_edit or not self.segments:
                return None
            
            current_text = self.text_edit.toPlainText().strip()
            correct_text = self.segments[self.current_segment_index - 1]["text"]
            
            # Tính số từ đúng và accuracy
            current_words = current_text.split()
            correct_words = correct_text.split()
            
            correct_count = sum(1 for c, t in zip(current_words, correct_words) 
                              if self.normalize_text(c) == self.normalize_text(t))
                              
            total_words = len(correct_words)
            accuracy = (correct_count / total_words * 100) if total_words > 0 else 0
            
            # Cập nhật word count widget
            self.word_count_widget.update_count(
                correct_count,
                total_words,
                accuracy
            )
            
            # Lưu kết quả kiểm tra
            self.last_check_result = {
                "accuracy": accuracy,
                "typing_speed": 0,  # Tính sau
                "time_taken": 0,    # Tính sau
                "correct_words": correct_count,
                "total_words": total_words
            }
            
            # Tự động chuyển câu nếu đạt yêu cầu
            if accuracy >= 95:
                QTimer.singleShot(1000, self.next_segment)
            
            return self.last_check_result
            
        except Exception as e:
            logger.error(f"Error checking transcription: {str(e)}")
            if self.validation_manager:
                self.validation_manager.handle_error("validation_error", str(e))
            return None

    def normalize_text(self, text):
        """Chuẩn hóa text: bỏ dấu câu, chuyển về chữ thường"""
        if not text:
            return ""
        punctuation = '!()-[]{};:\'",<>./?@#$%^&*_~'
        for char in punctuation:
            text = text.replace(char, '')
        return ' '.join(text.lower().split())

    def highlight_text(self, current_text, correct_text, current_word_index=0):
        """Highlight text khi gõ"""
        try:
            if not self.text_edit:
                return
            
            # Tách thành từng từ
            current_words = current_text.split()
            correct_words = correct_text.split()
            
            # Reset format
            cursor = self.text_edit.textCursor()
            cursor.select(QTextCursor.Document)
            cursor.setCharFormat(QTextCharFormat())
            
            # Highlight từng từ
            cursor.setPosition(0)
            pos = 0
            correct_count = 0
            
            for i, current_word in enumerate(current_words):
                if i >= len(correct_words):
                    break
                    
                word_format = QTextCharFormat()
                if self.normalize_text(current_word) == self.normalize_text(correct_words[i]):
                    word_format.setForeground(QColor("green"))
                    correct_count += 1
                else:
                    word_format.setForeground(QColor("red"))
                    
                cursor.setPosition(pos)
                cursor.setPosition(pos + len(current_word), QTextCursor.KeepAnchor)
                cursor.setCharFormat(word_format)
                
                pos += len(current_word) + 1
                
            # Cập nhật word count
            total_words = len(correct_words)
            accuracy = (correct_count / total_words * 100) if total_words > 0 else 0
            self.word_count_widget.update_count(
                correct_count,
                total_words,
                accuracy
            )
            
        except Exception as e:
            logger.error(f"Error highlighting text: {str(e)}")

    def show_result_message(self, accuracy, typing_speed):
        """Hiển thị kết quả kiểm tra"""
        if accuracy >= 95:
            emoji = "🌟"
            message = "Perfect!"
        elif accuracy >= 80:
            emoji = "👍"
            message = "Good job!"
        elif accuracy >= 60:
            emoji = "💪"
            message = "Keep practicing!"
        else:
            emoji = "📝"
            message = "Try again!"
            
        # Cập nhật word count widget
        total_words = len(self.segments[self.current_segment_index - 1]["text"].split())
        self.word_count_widget.update_count(
            int(accuracy * total_words / 100),
            total_words,
            accuracy
        )

    def previous_segment(self):
        """Chuyển đến segment trước"""
        if self.current_segment_index > 1:
            self.current_segment_index -= 1
            self.save_progress()
            self.play_current_segment()
            self.text_edit.clear()
            
            # Reset status bar với số từ của câu mới
            total_words = len(self.segments[self.current_segment_index - 1]["text"].split())
            self.word_count_widget.update_count(0, total_words, 0)
            
            self.update_button_states()

    def next_segment(self):
        """Chuyển đến segment tiếp theo"""
        if self.current_segment_index < len(self.segments):
            self.current_segment_index += 1
            self.save_progress()
            self.play_current_segment()
            self.text_edit.clear()
            
            # Reset status bar với số từ của câu mới
            total_words = len(self.segments[self.current_segment_index - 1]["text"].split())
            self.word_count_widget.update_count(0, total_words, 0)
            
            self.update_button_states()

    def replay_segment(self):
        """Phát lại segment hiện tại"""
        if self.player:
            self.play_current_segment()

    def play_current_segment(self):
        """Phát segment hiện tại"""
        if not self.segments or not self.player:
            return

        try:
            segment = self.segments[self.current_segment_index - 1]
            start_time = self.video_processor.time_to_milliseconds(segment["start_time"])
            end_time = self.video_processor.time_to_milliseconds(segment["end_time"])
            
            # Thêm 2ms (không phải 2s) vào end_time
            end_time += 0.002  # 2 milliseconds = 0.002 seconds

            # Đặt thời gian bắt đầu
            self.player.set_time(start_time)
            
            # Cập nhật end time cho timer
            self.segment_end_time = end_time
            
            # Bắt đầu phát
            self.player.play()
            
            # Khởi động timer để kiểm tra thời điểm kết thúc
            self.segment_timer.stop()  # Dừng timer cũ
            
            # Ngắt kết nối signal cũ nếu có
            try:
                self.segment_timer.timeout.disconnect()
            except:
                pass
            
            # Kết nối signal mới và start timer
            self.segment_timer.setInterval(1)  # Kiểm tra mỗi 1ms
            self.segment_timer.timeout.connect(self.check_segment_end)
            self.segment_timer.start()
            
        except Exception as e:
            logger.error(f"Error playing segment: {str(e)}")

    def check_segment_end(self):
        """Kiểm tra và dừng video khi đến cuối segment"""
        try:
            if not self.player:
                return
            
            current_time = self.player.get_time()
            if current_time >= self.segment_end_time:
                self.player.pause()
                self.segment_timer.stop()
            
        except Exception as e:
            logger.error(f"Error checking segment end: {str(e)}")

    def show_statistics(self):
        """Hiển thị cửa sổ thống kê"""
        try:
            from src.ui.statistics_dialog import StatisticsDialog
            dialog = StatisticsDialog(self.statistics_manager)
            dialog.exec_()
        except Exception as e:
            logger.error(f"Error showing statistics: {str(e)}")
            self.show_error_message("Error", "Could not show statistics")

    def show_settings(self):
        """Hiển thị cửa sổ cài đặt"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Settings")
            layout = QFormLayout()
            
            # Replay count
            replay_count = QSpinBox()
            replay_count.setValue(self.config_manager.get_setting("practice_settings", "auto_replay_count", 1))
            replay_count.valueChanged.connect(lambda v: self.config_manager.update_setting(
                "practice_settings", "auto_replay_count", v
            ))
            layout.addRow("Auto replay count:", replay_count)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error showing settings: {str(e)}")
            self.show_error_message("Error", "Could not show settings")

    def show_about(self):
        """Hiển thị thông tin về ứng dụng"""
        about_text = """
        Transcription Practice App
        Version 1.0
        
        A tool for practicing subtitle transcription
        with video playback and accuracy checking.
        """
        QMessageBox.about(self, "About", about_text)

    def save_progress(self):
        """Lưu tiến trình học"""
        if self.video_file and self.subtitle_file:
            try:
                self.progress_manager.save_progress({
                    "video_file": self.video_file,
                    "subtitle_file": self.subtitle_file,
                    "current_segment_index": self.current_segment_index
                    # Bỏ replay_count vì không cần thiết
                })
                
            except Exception as e:
                logger.error(f"Error saving progress: {str(e)}")
                self.show_error_message("Error", "Could not save progress")

    def load_progress(self):
        """Load tiến trình học cũ"""
        try:
            progress = self.progress_manager.load_progress()
            if progress:
                self.video_file = progress["video_file"]
                self.subtitle_file = progress["subtitle_file"]
                if self.load_video() and self.load_subtitles():
                    self.current_segment_index = progress["current_segment_index"]
                    self.play_current_segment()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error loading progress: {str(e)}")
            return False

    def closeEvent(self, event):
        """Xử lý khi đóng ứng dụng"""
        try:
            # Lưu tiến trình
            self.save_progress()
            
            # Dừng video
            if hasattr(self, 'player'):
                self.player.stop()
                
            event.accept()
            
        except Exception as e:
            logger.error(f"Error handling close event: {str(e)}")
            event.accept() 

    def update_button_states(self):
        """Cập nhật trạng thái các nút điều khiển"""
        try:
            has_segments = bool(self.segments)
            is_first = self.current_segment_index <= 1
            is_last = self.current_segment_index >= len(self.segments) if has_segments else True
            
            # Tìm các nút trong layout
            for button in self.findChildren(QPushButton):
                if "Previous" in button.text():
                    button.setEnabled(has_segments and not is_first)
                elif "Next" in button.text():
                    button.setEnabled(has_segments and not is_last)
                elif "Check" in button.text() or "Replay" in button.text():
                    button.setEnabled(has_segments)
                    
        except Exception as e:
            logger.error(f"Error updating button states: {str(e)}") 