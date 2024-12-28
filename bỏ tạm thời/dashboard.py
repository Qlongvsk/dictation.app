import sys
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QProgressBar, QMessageBox, QInputDialog,
    QComboBox
)
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class Dashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard Quản Lý Tiến Trình Học")
        self.setGeometry(150, 150, 1000, 600)
        self.parent_app = parent  # Tham chiếu đến ứng dụng chính
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()

        # Tiêu đề
        title = QLabel("Dashboard Quản Lý Tiến Trình Học")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # Các nút chức năng
        button_layout = QHBoxLayout()
        self.add_folder_btn = QPushButton("Tạo Thư Mục")
        self.edit_folder_btn = QPushButton("Sửa Thư Mục")
        self.delete_folder_btn = QPushButton("Xóa Thư Mục")
        self.refresh_btn = QPushButton("Làm Mới")
        self.open_transcription_btn = QPushButton("Mở Luyện Chép Chính Tả")

        button_layout.addWidget(self.add_folder_btn)
        button_layout.addWidget(self.edit_folder_btn)
        button_layout.addWidget(self.delete_folder_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.open_transcription_btn)

        layout.addLayout(button_layout)

        # Kết nối các nút
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.edit_folder_btn.clicked.connect(self.edit_folder)
        self.delete_folder_btn.clicked.connect(self.delete_folder)
        self.refresh_btn.clicked.connect(self.load_data)
        self.open_transcription_btn.clicked.connect(self.open_transcription)

        # Bảng danh sách video
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Tên Video", "Thư Mục", "Tiến Trình (%)", "Ngày Bắt Đầu",
            "Ngày Hoàn Thành", "Tổng Số Ngày"
        ])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Biểu đồ thống kê
        self.figure = plt.figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def load_data(self):
        self.table.setRowCount(0)
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Lấy danh sách video
        cursor.execute('''
            SELECT videos.id, videos.name, topics.name, videos.progress,
                   videos.start_date, videos.end_date, videos.total_days
            FROM videos
            LEFT JOIN topics ON videos.topic_id = topics.id
        ''')
        videos = cursor.fetchall()

        for row_number, row_data in enumerate(videos):
            self.table.insertRow(row_number)
            self.table.setItem(row_number, 0, QTableWidgetItem(row_data[1]))
            self.table.setItem(row_number, 1, QTableWidgetItem(row_data[2] if row_data[2] else "Chưa xác định"))

            # Thanh tiến trình
            progress_bar = QProgressBar()
            progress_bar.setValue(row_data[3])
            self.table.setCellWidget(row_number, 2, progress_bar)

            self.table.setItem(row_number, 3, QTableWidgetItem(row_data[4] if row_data[4] else "Chưa bắt đầu"))
            self.table.setItem(row_number, 4, QTableWidgetItem(row_data[5] if row_data[5] else "Chưa hoàn thành"))
            self.table.setItem(row_number, 5, QTableWidgetItem(str(row_data[6]) if row_data[6] else "0"))

        conn.close()
        self.plot_statistics()

    def add_folder(self):
        text, ok = QInputDialog.getText(self, "Tạo Thư Mục Mới", "Nhập tên thư mục:")
        if ok and text:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO topics (name) VALUES (?)", (text,))
                conn.commit()
                QMessageBox.information(self, "Thành Công", f"Thư mục '{text}' đã được tạo.")
                self.load_data()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Lỗi", f"Thư mục '{text}' đã tồn tại.")
            conn.close()

    def edit_folder(self):
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM topics")
        topics = cursor.fetchall()
        conn.close()

        if not topics:
            QMessageBox.warning(self, "Lỗi", "Không có thư mục nào để sửa.")
            return

        items = [topic[1] for topic in topics]
        item, ok = QInputDialog.getItem(self, "Sửa Thư Mục", "Chọn thư mục cần sửa:", items, 0, False)
        if ok and item:
            new_name, ok = QInputDialog.getText(self, "Sửa Thư Mục", f"Nhập tên mới cho thư mục '{item}':")
            if ok and new_name:
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                try:
                    cursor.execute("UPDATE topics SET name = ? WHERE name = ?", (new_name, item))
                    conn.commit()
                    QMessageBox.information(self, "Thành Công", f"Thư mục '{item}' đã được đổi tên thành '{new_name}'.")
                    self.load_data()
                except sqlite3.IntegrityError:
                    QMessageBox.warning(self, "Lỗi", f"Thư mục '{new_name}' đã tồn tại.")
                conn.close()

    def delete_folder(self):
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM topics")
        topics = cursor.fetchall()
        conn.close()

        if not topics:
            QMessageBox.warning(self, "Lỗi", "Không có thư mục nào để xóa.")
            return

        items = [topic[1] for topic in topics]
        item, ok = QInputDialog.getItem(self, "Xóa Thư Mục", "Chọn thư mục cần xóa:", items, 0, False)
        if ok and item:
            reply = QMessageBox.question(
                self, 'Xác Nhận', 
                f"Bạn có chắc chắn muốn xóa thư mục '{item}'? Toàn bộ video trong thư mục này cũng sẽ bị xóa.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM topics WHERE name = ?", (item,))
                topic_id = cursor.fetchone()[0]
                # Xóa các video trong thư mục
                cursor.execute("DELETE FROM videos WHERE topic_id = ?", (topic_id,))
                # Xóa thư mục
                cursor.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Thành Công", f"Thư mục '{item}' và toàn bộ video trong thư mục đã được xóa.")
                self.load_data()

    def open_transcription(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một video từ danh sách.")
            return

        row = selected_items[0].row()
        video_name = self.table.item(row, 0).text()

        # Lấy đường dẫn file video từ cơ sở dữ liệu
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM videos WHERE name = ?", (video_name,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy đường dẫn của video.")
            return

        video_path = result[0]

        # Mở giao diện luyện nghe chép chính tả
        self.parent_app.open_transcription_app(video_path)

    def plot_statistics(self):
        # Ví dụ: Thống kê số lượng phụ đề hoàn thành theo video
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, progress FROM videos
        ''')
        data = cursor.fetchall()
        conn.close()

        if not data:
            return  # Không có dữ liệu để vẽ

        names = [row[0] for row in data]
        progresses = [row[1] for row in data]

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.barh(names, progresses, color='skyblue')
        ax.set_xlabel('Tiến Trình (%)')
        ax.set_title('Tiến Trình Học của Các Video')
        self.canvas.draw()