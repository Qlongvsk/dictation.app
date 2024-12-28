import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QMessageBox
)
from PyQt5.QtCore import Qt
from .transcription import TranscriptionApp
from .statistics_dialog import StatisticsDialog
from src.core.statistics_manager import StatisticsManager
from src.core.data_manager import DataManager

logger = logging.getLogger(__name__)

class Dashboard(QMainWindow):
    """Màn hình chính của ứng dụng"""
    
    def __init__(self):
        super().__init__()
        self.init_managers()
        self.init_ui()
        
    def init_managers(self):
        """Khởi tạo các manager"""
        self.data_manager = DataManager()
        self.statistics_manager = StatisticsManager(self.data_manager)
        
    def init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("Transcription Practice")
        self.setGeometry(100, 100, 1280, 720)
        
        # Thêm style cho title bar và toàn bộ window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QMainWindow::title {
                background-color: #2b2b2b;
                color: white;
            }
            /* Style cho title bar */
            QTitleBar {
                background-color: #2b2b2b;
                color: white;
            }
            /* Style cho nút điều khiển cửa sổ */
            QTitleBar QToolButton {
                background-color: #2b2b2b;
                color: white;
            }
            QTitleBar QToolButton:hover {
                background-color: #4d4d4d;
            }
            /* Style cho các widget khác */
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4CAF50;
            }
        """)
        
        # Widget chính
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Stack widget để chuyển đổi giữa welcome screen và practice screen
        self.stack = QStackedWidget()
        
        # Welcome screen
        self.welcome_screen = self.create_welcome_screen()
        self.stack.addWidget(self.welcome_screen)
        
        # Layout chính chứa stack
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.addWidget(self.stack)
        
    def create_welcome_screen(self):
        """Tạo màn hình chào mừng"""
        welcome_widget = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Welcome to Transcription Practice")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 24px; margin: 20px;")
        layout.addWidget(header)
        
        # Thêm spacer để đẩy các nút xuống giữa màn hình
        layout.addStretch()
        
        # Container cho các nút
        button_container = QWidget()
        button_layout = QVBoxLayout()
        button_container.setLayout(button_layout)
        
        # Nút bắt đầu practice
        start_button = QPushButton("Start New Practice")
        start_button.clicked.connect(self.start_new_practice)
        start_button.setFixedWidth(200)
        start_button.setMinimumHeight(40)
        button_layout.addWidget(start_button, alignment=Qt.AlignCenter)
        
        # Nút xem thống kê
        stats_button = QPushButton("View Statistics")
        stats_button.clicked.connect(self.show_statistics)
        stats_button.setFixedWidth(200)
        stats_button.setMinimumHeight(40)
        button_layout.addWidget(stats_button, alignment=Qt.AlignCenter)
        
        layout.addWidget(button_container)
        
        # Thêm spacer để đẩy các nút lên giữa màn hình
        layout.addStretch()
        
        welcome_widget.setLayout(layout)
        return welcome_widget
        
    def start_new_practice(self):
        """Bắt đầu phiên luyện tập mới"""
        try:
            self.transcription_app = TranscriptionApp()
            # Thêm transcription app vào stack và chuyển sang nó
            self.stack.addWidget(self.transcription_app)
            self.stack.setCurrentWidget(self.transcription_app)
            
            # Ẩn welcome screen
            self.welcome_screen.hide()
            
        except Exception as e:
            logger.error(f"Error starting new practice: {str(e)}")
            self.show_error_message("Error", f"Could not start practice: {str(e)}")
            
    def show_statistics(self):
        """Hiển thị thống kê"""
        try:
            dialog = StatisticsDialog(self.statistics_manager)
            dialog.exec_()
        except Exception as e:
            logger.error(f"Error showing statistics: {str(e)}")
            self.show_error_message("Error", f"Could not show statistics: {str(e)}")
            
    def show_error_message(self, title: str, message: str):
        """Hiển thị thông báo lỗi"""
        QMessageBox.critical(self, title, message) 