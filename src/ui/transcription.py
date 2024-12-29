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
from core.note_manager import NoteManager
from src.ui.note_dialog import NoteDialog

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

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        
        # Add save to notes action if text is selected
        cursor = self.textCursor()
        if cursor.hasSelection():
            save_action = menu.addAction("Save to Notes")
            save_action.triggered.connect(
                lambda: self.parent_app.save_selected_text()
            )
        
        # Add save segment action
        save_segment_action = menu.addAction("Save Current Segment")
        save_segment_action.triggered.connect(
            lambda: self.parent_app.save_current_segment()
        )
            
        menu.exec_(event.globalPos())

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

class SegmentCountWidget(QLabel):
    """Widget hiển thị số segment đã hoàn thành"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLabel {
                background-color: #3d3d3d;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
            }
        """)
        self.update_count(0, 0, 0)
        
    def update_count(self, current, total, progress):
        """Cập nhật số segment đã hoàn thành"""
        self.setText(f"Segments: {current}/{total} [{current}/{total}] {progress:.1f}%")

class FloatingTextEdit(CustomTextEdit):
    """Widget nhập liệu nổi trên video"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
        # Thêm timer để theo dõi và cập nhật vị trí
        self.position_timer = QTimer(self)
        self.position_timer.setInterval(1)  # Cập nhật mỗi 100ms
        self.position_timer.timeout.connect(self.update_position)
        self.position_timer.start()
        
    def setup_ui(self):
        """Setup cho FloatingTextEdit"""
        # Cho phép trong suốt
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Style với text được căn giữa hoàn toàn
        self.setStyleSheet("""
            FloatingTextEdit {
                background-color: rgba(43, 43, 43, 0.8);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 15px 20px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 18px;
                line-height: 1.2;
            }
            QScrollBar {
                width: 0px;
                height: 0px;
            }
        """)
        
        # Thiết lập căn giữa text
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setAlignment(Qt.AlignCenter)
        
        # Kích thước cố định
        self.setFixedHeight(60)
        self.setMinimumWidth(400)
        self.setMaximumWidth(1200)

    def update_position(self):
        """Cập nhật vị trí liên tục"""
        if self.parent():
            try:
                # Lấy kích thước parent
                parent_width = self.parent().width()
                parent_height = self.parent().height()
                
                # Tính toán chiều rộng (60% chiều rộng parent)
                desired_width = parent_width * 0.6
                width = max(400, min(desired_width, 1200))
                
                # Tính toán vị trí để căn giữa theo chiều ngang
                x = (parent_width - width) / 2
                
                # Khoảng cách cố định với bottom là 50px
                y = parent_height - self.height() - 50
                
                # Cập nhật kích thước và vị trí
                self.setFixedWidth(int(width))
                self.move(int(x), int(y))
                
            except Exception as e:
                logger.error(f"Error updating position: {str(e)}")

    def resizeEvent(self, event):
        """Xử lý resize event"""
        super().resizeEvent(event)
        self.update_position()

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
    def __init__(self, video_file=None, subtitle_file=None):
        super().__init__()
        # Khởi tạo các thuộc tính
        self.video_file = video_file
        self.subtitle_file = subtitle_file
        self.video_file = video_file
        self.subtitle_file = subtitle_file
        self.segments = None
        self.current_segment_index = 1
        self.current_segment_index = 1
        self.timer = QTimer()
        self.segment_timer = QTimer()
        
        # Khởi tạo managers và UI
        self.init_managers()
        self.init_ui()
        
        # Nếu có file video và subtitle, load ngay
        if self.video_file and self.subtitle_file:
            try:
                if not self.load_video():
                    raise Exception("Failed to load video")
                if not self.load_subtitles():
                    raise Exception("Failed to load subtitles")
                # Load tiến trình học cũ
                self.load_progress()
                # Load notes cũ nếu có
                self.load_notes()
            except Exception as e:
                logger.error(f"Error loading files: {str(e)}")
                raise

    def init_managers(self):
        """Khởi tạo các manager"""
        try:
            # Khởi tạo theo thứ tự phụ thuộc
            self.config_manager = ConfigManager()  # Khởi tạo config_manager trước
            self.session_manager = SessionManager()
            self.data_manager = DataManager()
            self.statistics_manager = StatisticsManager(self.data_manager)
            self.achievement_manager = AchievementManager(self.statistics_manager)
            self.progress_manager = ProgressManager()
            self.backup_manager = BackupManager(self.config_manager)  # Truyền config_manager vào
            self.validation_manager = ValidationManager()
            self.video_converter = VideoConverter()
            self.note_manager = NoteManager()
            
            # Thiết lập error handler cho session manager
            self.session_manager.error_handler = self.show_error_message
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
        
        # Thêm segment count widget
        self.segment_count_widget = SegmentCountWidget()
        status_layout.addWidget(self.segment_count_widget)
        
        # Thêm word count widget
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
        
        # Add Notes menu
        notes_menu = menu_bar.addMenu("Notes")
        
        show_notes_action = notes_menu.addAction("Show Notes")
        show_notes_action.triggered.connect(self.show_notes)
        show_notes_action.setShortcut("Ctrl+N")
        
        # Thêm action Save Current Segment
        save_segment_action = notes_menu.addAction("Save Current Segment")
        save_segment_action.triggered.connect(self.save_current_segment)
        save_segment_action.setShortcut("Ctrl+S")  # Phím tắt Ctrl+S

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
        
        # Thêm spacer để để các nút lên trên
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
                return False

            # Chọn file phụ đề
            subtitle_file, _ = QFileDialog.getOpenFileName(
                self, "Open Subtitle File", "", 
                "Subtitle Files (*.srt)"
            )
            if not subtitle_file:
                return False

            # Cập nhật đường dẫn file
            self.video_file = video_file
            self.subtitle_file = subtitle_file

            # Load video và phụ đề
            if not self.load_video():
                raise Exception("Failed to load video")
            if not self.load_subtitles():
                raise Exception("Failed to load subtitles")
            
            # Load tiến trình học cũ nếu có
            self.load_progress()

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
            if not self.video_file:
                return False
            
            if not self.video_file:
                return False
            
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
        """Load và xử lý file phụ đề"""
        try:
            if not self.subtitle_file:
                return False
                
            if not self.subtitle_file:
                return False
                
            # Tải phụ đề
            self.video_processor = VideoProcessor()
            self.segments = self.video_processor.load_subtitles(self.subtitle_file)
            if not self.segments:
                raise Exception("No segments found in subtitle file")
            
            # Đặt vị trí video tại segment đầu tiên
            if self.segments:
                self.current_segment_index = 1
                self.play_current_segment()
                
                self.current_segment_index = 1
                self.play_current_segment()
                
            # Cập nhật segment count
            total_segments = len(self.segments)
            self.segment_count_widget.update_count(
                self.current_segment_index,
                total_segments,
                (self.current_segment_index / total_segments * 100)
            )
            
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
        """Highlight text khi g"""
        """Highlight text khi g"""
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
            
            # Cập nhật segment count
            total_segments = len(self.segments)
            self.segment_count_widget.update_count(
                self.current_segment_index,
                total_segments,
                (self.current_segment_index / total_segments * 100)
            )
            
            # Reset word count với số từ của câu mới
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
            
            # Cập nhật segment count
            total_segments = len(self.segments)
            self.segment_count_widget.update_count(
                self.current_segment_index,
                total_segments,
                (self.current_segment_index / total_segments * 100)
            )
            
            # Reset word count với số từ của câu mới
            total_words = len(self.segments[self.current_segment_index - 1]["text"].split())
            self.word_count_widget.update_count(0, total_words, 0)
            
            self.update_button_states()

    def replay_segment(self):
        """Phát lại segment hiện tại"""
        if self.player:
            self.play_current_segment()

    def play_current_segment(self):
        """Phát segment hiện tại"""
        try:
            if not self.segments or not self.player:
                return
            
            # Lấy thông tin segment hiện tại
            current_segment = self.segments[self.current_segment_index - 1]
            start_time = current_segment["start_time"]
            end_time = current_segment["end_time"]
            
            # Chuyển đổi thời gian sang milliseconds
            start_ms = self.video_processor.time_to_milliseconds(start_time)
            end_ms = self.video_processor.time_to_milliseconds(end_time)
            
            # Thêm 500ms vào thời gian kết thúc
            end_ms += 400 # Thêm 0.5 giây
            duration = end_ms - start_ms
            
            # Đặt vị trí video chính xác đến millisecond
            self.player.set_time(int(start_ms))
            self.player.play()
            
            # Dừng video khi hết segment (đã bao gồm 500ms phụ trội)
            self.segment_timer.stop()  # Dừng timer cũ nếu có
            self.segment_timer.singleShot(duration, self.player.pause)
            
            # Cập nhật word count
            total_words = len(current_segment["text"].split())
            self.word_count_widget.update_count(0, total_words, 0)
            
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
                progress_data = {
                    "video_file": self.video_file,
                    "subtitle_file": self.subtitle_file,
                    "current_segment_index": self.current_segment_index
                }
                self.progress_manager.save_progress(progress_data)
                logger.info(f"Progress saved: segment {self.current_segment_index}")
            except Exception as e:
                logger.error(f"Error saving progress: {str(e)}")
                self.show_error_message("Error", "Could not save progress")

    def load_progress(self):
        """Load tiến trình học cũ"""
        try:
            if self.video_file and self.subtitle_file:
                progress = self.progress_manager.get_progress(self.video_file)
                if progress and progress["subtitle_file"] == self.subtitle_file:
                    self.current_segment_index = progress["current_segment_index"]
                    self.play_current_segment()
                    
                    # Cập nhật segment count
                    total_segments = len(self.segments)
                    self.segment_count_widget.update_count(
                        self.current_segment_index,
                        total_segments,
                        (self.current_segment_index / total_segments * 100)
                    )
                    logger.info(f"Progress loaded: segment {self.current_segment_index}")
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

    def show_notes(self):
        """Hiển thị dialog notes"""
        if self.video_file:
            dialog = NoteDialog(self.note_manager, self.video_file, self)
            dialog.exec_()

    def save_selected_text(self):
        """Lưu text đã chọn vào notes"""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            self.note_manager.add_word(self.video_file, selected_text)
            # Hiển thị thông báo nhỏ khi lưu thành công
            QMessageBox.information(self, "Success", f"Saved word: {selected_text}")

    def save_current_segment(self):
        """Lưu segment hiện tại vào notes"""
        if self.segments:
            segment_text = self.segments[self.current_segment_index - 1]["text"]
            self.note_manager.add_segment(self.video_file, segment_text)
            # Hiển thị thông báo nhỏ khi lưu thành công
            QMessageBox.information(self, "Success", "Current segment saved to notes")

    def load_notes(self):
        """Load notes từ file"""
        try:
            if self.video_file:
                # Notes sẽ tự động được load khi mở NoteDialog
                # Chỉ cần đảm bảo NoteManager đã được khởi tạo
                if not hasattr(self, 'note_manager'):
                    self.note_manager = NoteManager()
                return True
        except Exception as e:
            logger.error(f"Error loading notes: {str(e)}")
            return False 