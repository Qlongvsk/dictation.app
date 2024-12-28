from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTabWidget,
    QWidget, QGridLayout, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPalette
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class StatisticsDialog(QDialog):
    def __init__(self, statistics_manager, parent=None):
        super().__init__(parent)
        self.statistics_manager = statistics_manager
        self.init_ui()
        self.load_statistics()
        
    def init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("Learning Statistics")
        self.setMinimumSize(600, 400)
        
        # Thêm style cho title bar và toàn bộ dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QDialog::title {
                background-color: #2b2b2b;
                color: white;
            }
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 8px 16px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            QLabel {
                color: #ffffff;
            }
            QScrollArea {
                border: none;
                background-color: #2b2b2b;
            }
            /* Style cho title bar */
            QTitleBar {
                background-color: #2b2b2b;
                color: white;
            }
            /* Style cho nút đóng, thu nhỏ, phóng to */
            QTitleBar QToolButton {
                background-color: #2b2b2b;
                color: white;
            }
            QTitleBar QToolButton:hover {
                background-color: #4d4d4d;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Tab widget để phân chia thống kê
        self.tab_widget = QTabWidget()
        
        # Tab tổng quan
        self.overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "Overview")
        
        # Tab chi tiết theo ngày
        self.daily_tab = self.create_daily_tab()
        self.tab_widget.addTab(self.daily_tab, "Daily Stats")
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        
    def create_overview_tab(self):
        """Tạo tab tổng quan"""
        tab = QWidget()
        layout = QGridLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Tạo các label cho thống kê
        self.total_time_label = self.create_stat_label("Total Practice Time")
        self.accuracy_label = self.create_stat_label("Average Accuracy")
        self.speed_label = self.create_stat_label("Average Typing Speed")
        self.segments_label = self.create_stat_label("Segments Completed")
        self.streak_label = self.create_stat_label("Practice Streak")
        
        # Thêm vào layout với style
        stats = [
            ("📊 Total Practice Time:", self.total_time_label),
            ("🎯 Average Accuracy:", self.accuracy_label),
            ("⚡ Average Typing Speed:", self.speed_label),
            ("📝 Segments Completed:", self.segments_label),
            ("🔥 Practice Streak:", self.streak_label)
        ]
        
        for i, (title, label) in enumerate(stats):
            title_label = QLabel(title)
            title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
            layout.addWidget(title_label, i, 0)
            layout.addWidget(label, i, 1)
            
            # Thêm line separator
            if i < len(stats) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setStyleSheet("background-color: #3d3d3d;")
                layout.addWidget(line, i+1, 0, 1, 2)
        
        tab.setLayout(layout)
        return tab
        
    def create_daily_tab(self):
        """Tạo tab thống kê theo ngày"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(20)
        
        # Lấy và hiển thị thống kê theo ngày
        daily_stats = self.statistics_manager.daily_stats
        for date, stats in sorted(daily_stats.items(), reverse=True):
            # Tạo frame cho mỗi ngày
            day_frame = QFrame()
            day_frame.setStyleSheet("""
                QFrame {
                    background-color: #3d3d3d;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            
            frame_layout = QVBoxLayout()
            
            # Tiêu đề ngày
            date_label = QLabel(f"📅 {date}")
            date_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
            frame_layout.addWidget(date_label)
            
            # Thống kê của ngày
            stats_text = f"""
                ⏱️ Time spent: {stats['total_time']:.1f}s
                🎯 Accuracy: {stats['average_accuracy']:.1f}%
                ⚡ Typing speed: {stats['average_speed']:.1f} WPM
                📝 Segments completed: {stats['segments_completed']}
            """
            stats_label = QLabel(stats_text)
            stats_label.setStyleSheet("font-size: 14px; margin-left: 20px;")
            frame_layout.addWidget(stats_label)
            
            day_frame.setLayout(frame_layout)
            content_layout.addWidget(day_frame)
        
        content.setLayout(content_layout)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        tab.setLayout(layout)
        return tab
        
    def create_stat_label(self, text):
        """Tạo label cho thống kê với style"""
        label = QLabel()
        label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                padding: 8px;
                background-color: #3d3d3d;
                border-radius: 4px;
            }
        """)
        return label
        
    def load_statistics(self):
        """Load và hiển thị thống kê"""
        try:
            # Lấy thống kê từ manager
            current_stats = self.statistics_manager.get_current_stats()
            
            # Cập nhật UI với thống kê mới nhất
            self.update_statistics_display(current_stats)
            
        except Exception as e:
            logger.error(f"Error loading statistics: {str(e)}")
            
    def update_statistics_display(self, stats):
        """Cập nhật hiển thị thống kê"""
        try:
            # Cập nhật các label với thông tin mới
            self.total_time_label.setText(f"Total Practice Time: {stats['total_time']:.1f} seconds")
            self.accuracy_label.setText(f"Average Accuracy: {stats['accuracy']:.1f}%")
            self.speed_label.setText(f"Average Speed: {stats['typing_speed']:.1f} WPM")
            self.segments_label.setText(f"Segments Completed: {stats['segments_completed']}")
            self.streak_label.setText(f"Practice Streak: {stats['practice_streak']} days")
            
        except Exception as e:
            logger.error(f"Error updating statistics display: {str(e)}") 