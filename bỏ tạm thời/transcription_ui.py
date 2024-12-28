import difflib
import string
from PyQt5.QtGui import QFont
import vlc  # Thư viện VLC
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QTextEdit, QHBoxLayout, QSpinBox, QDialog, QFormLayout
)
import json
from PyQt5.QtWidgets import QCompleter
from textblob import TextBlob
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QKeyEvent
from video_processing import parse_srt_to_segments, time_to_milliseconds
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QPushButton, QFileDialog, QApplication
import sys  # Đảm bảo import sys để sửa đoạn main.py

class CustomTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent  # Tham chiếu đến ứng dụng chính nếu cần

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:  # Nếu bấm Enter
            if self.parent_app:  # Kiểm tra xem có tham chiếu đến ứng dụng chính không
                self.parent_app.next_segment()  # Gọi hàm chuyển câu
            return  # Dừng xử lý thêm
        else:
            super().keyPressEvent(event)  # Gọi xử lý mặc định cho các phím khác

class TranscriptionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.player = None  # Trình phát VLC
        self.video_file = None
        self.subtitle_file = None
        self.segments = []
        self.current_segment_index = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.stop_video)

        self.replay_count = 1  # Số lần phát lại tự động (mặc định 1)
        self.current_replay = 0  # Bộ đếm số lần phát lại hiện tại

        self.init_ui()

    def show_about(self):
        from PyQt5.QtWidgets import QMessageBox

        QMessageBox.information(
            self, "About", "Transcription Practice with VLC\nVersion 1.0"
        )

    def init_ui(self):
        self.setFocusPolicy(Qt.StrongFocus)  # Đảm bảo ứng dụng nhận các sự kiện phím
        self.setWindowTitle("Transcription Practice with VLC")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()
        from PyQt5.QtWidgets import QMenuBar, QMenu  # Import các thành phần menu

        # Tạo menu
        menu_bar = QMenuBar()
        file_menu = menu_bar.addMenu("File")
        help_menu = menu_bar.addMenu("Help")

        # Thêm hành động vào menu
        load_action = file_menu.addAction("Load Video & Subtitle")
        exit_action = file_menu.addAction("Exit")

        about_action = help_menu.addAction("About")

        # Kết nối các hành động
        load_action.triggered.connect(self.load_files)
        exit_action.triggered.connect(self.close)
        about_action.triggered.connect(self.show_about)

        layout.setMenuBar(menu_bar)  # Thêm menu vào bố cục

        # Nhãn trạng thái
        from PyQt5.QtWidgets import QStatusBar  # Import QStatusBar

        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Select a video and subtitle file to start.")
        layout.addWidget(self.status_bar)

        # Khu vực nhập liệu
        self.text_edit = CustomTextEdit(self)
        layout.addWidget(self.text_edit)
        layout.addSpacing(10)  # Thêm khoảng cách

        # Các nút điều khiển
        button_layout = QHBoxLayout()
        self.check_button = QPushButton("Check")
        self.check_button.clicked.connect(self.check_transcription)

        self.next_button = QPushButton("Next Segment")
        self.next_button.clicked.connect(self.next_segment)
        self.next_button.setEnabled(False)

        self.replay_button = QPushButton("Replay")
        self.replay_button.clicked.connect(self.replay_segment)
        self.replay_button.setEnabled(False)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings_dialog)

        button_layout.addWidget(self.check_button)
        button_layout.addWidget(self.next_button)
        button_layout.addWidget(self.replay_button)
        button_layout.addWidget(self.settings_button)
        layout.addLayout(button_layout)

        # Nút tải video và phụ đề
        load_files_button = QPushButton("Load Video and Subtitle")
        load_files_button.clicked.connect(self.load_files)
        layout.addWidget(load_files_button)

         # Tạo nút để tạo phụ đề
        self.generate_subtitle_button = QPushButton("Generate Subtitle")
        self.generate_subtitle_button.clicked.connect(self.generate_subtitle_for_video)
        layout.addWidget(self.generate_subtitle_button)

        # Thanh trạng thái hiển thị thông báo
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)

        self.setLayout(layout)

        # Kết nối sự kiện nhập liệu
        self.text_edit.textChanged.connect(self.check_word_live)
        self.previous_button = QPushButton("Previous Segment")
        self.previous_button.clicked.connect(self.previous_segment)
        self.previous_button.setEnabled(False)
        button_layout.addWidget(self.previous_button)  # Thêm nút vào bố cục

    def get_adjusted_end_time(self, index):
        """
        Trả về thời gian kết thúc mở rộng cho đoạn phụ đề hiện tại.
        Nếu không có đoạn phụ đề kế tiếp, trả về thời gian kết thúc gốc.
        """
        if index < len(self.segments) - 1:
            # Trả về thời gian bắt đầu của đoạn phụ đề kế tiếp
            return time_to_milliseconds(self.segments[index + 1]["start_time"])
        else:
            # Đoạn cuối cùng, giữ nguyên thời gian kết thúc
            return time_to_milliseconds(self.segments[index]["end_time"])

    def correct_spelling(self, text):
        blob = TextBlob(text)
        corrected_text = blob.correct()
        return str(corrected_text)

    def previous_segment(self):
        if self.current_segment_index > 1:  # Chỉ lùi lại nếu không ở đầu danh sách
            self.current_segment_index -= 1
            segment = self.segments[self.current_segment_index - 1]

            start_ms = time_to_milliseconds(segment["start_time"])
            # Sử dụng thời gian kết thúc đã được điều chỉnh
            adjusted_end_ms = self.get_adjusted_end_time(self.current_segment_index - 1)

            # Phát video từ start_ms đến adjusted_end_ms
            self.player.set_time(start_ms)
            self.player.play()

            # Đặt thời gian dừng video
            duration = adjusted_end_ms - start_ms
            self.timer.start(duration)

            # Cập nhật trạng thái
            self.current_replay = 0  # Đặt lại bộ đếm phát lại
            self.text_edit.clear()
            self.status_bar.showMessage(f"Segment {self.current_segment_index}/{len(self.segments)}: Type what you hear.")
            self.replay_button.setEnabled(True)

            # Lưu tiến trình
            self.progress["video_file"] = self.video_file
            self.progress["subtitle_file"] = self.subtitle_file
            self.progress["current_segment_index"] = self.current_segment_index
            self.save_progress()
        else:
            self.status_bar.showMessage("Already at the first segment!")
        self.previous_button.setEnabled(self.current_segment_index > 1)  # Kích hoạt hoặc vô hiệu hóa nút Previous

    def load_files(self):
        # Tải file video
        video_file, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi *.ts)")
        if not video_file:
            self.status_bar.showMessage("No video file selected!")
            return

        # Tải file phụ đề
        subtitle_file, _ = QFileDialog.getOpenFileName(self, "Select Subtitle File", "", "Subtitle Files (*.srt)")
        if not subtitle_file:
            self.status_bar.showMessage("No subtitle file selected!")
            return

        # Parse file SRT
        self.segments = parse_srt_to_segments(subtitle_file)
        if not self.segments:
            self.status_bar.showMessage("Failed to parse subtitle file.")
            return

        # Lưu thông tin video/phụ đề mới
        self.video_file = video_file
        self.subtitle_file = subtitle_file
        self.player = vlc.MediaPlayer(self.video_file)  # Khởi tạo trình phát VLC

        # Kiểm tra tiến trình đã lưu
        self.load_progress()
        if (
            self.progress.get("video_file") == self.video_file
            and self.progress.get("subtitle_file") == self.subtitle_file
        ):
            # Phục hồi tiến trình
            self.current_segment_index = self.progress.get("current_segment_index", 0)
            self.status_bar.showMessage(f"Progress restored! Continuing from segment {self.current_segment_index + 1}.")
        else:
            # Nếu không khớp, bắt đầu lại
            self.current_segment_index = 0
            self.status_bar.showMessage("Files loaded! Starting from the beginning.")

        # Cập nhật trạng thái nút
        self.next_button.setEnabled(True)
        self.replay_button.setEnabled(False)
        self.previous_button.setEnabled(False)  # Reset nút Previous khi tải file mới

    def next_segment(self):
        if self.current_segment_index < len(self.segments):
            segment = self.segments[self.current_segment_index]

            start_ms = time_to_milliseconds(segment["start_time"])
            # Sử dụng thời gian kết thúc đã được điều chỉnh
            adjusted_end_ms = self.get_adjusted_end_time(self.current_segment_index)

            # Phát video từ start_ms đến adjusted_end_ms
            self.player.set_time(start_ms)
            self.player.play()

            # Đặt thời gian dừng video
            duration = adjusted_end_ms - start_ms
            self.timer.start(duration)

            # Cập nhật trạng thái
            self.current_replay = 0  # Đặt lại bộ đếm phát lại
            self.text_edit.clear()
            self.status_bar.showMessage(f"Segment {self.current_segment_index + 1}/{len(self.segments)}: Type what you hear.")
            self.replay_button.setEnabled(True)

            # Lưu tiến trình
            self.progress["video_file"] = self.video_file
            self.progress["subtitle_file"] = self.subtitle_file
            self.progress["current_segment_index"] = self.current_segment_index

            # Chuyển sang đoạn kế tiếp
            self.current_segment_index += 1
        else:
            self.status_bar.showMessage("All segments completed!")
        self.previous_button.setEnabled(self.current_segment_index > 1)  # Kích hoạt nút Previous nếu không ở đầu danh sách
        self.save_progress()

    def stop_video(self):
        if self.player:
            self.player.pause()
        self.timer.stop()

        # Tự động phát lại nếu chưa đủ số lần cấu hình
        if self.current_replay < self.replay_count - 1:
            self.current_replay += 1
            self.replay_segment()

    def check_word_live(self):
        if not self.segments or self.current_segment_index == 0:
            return

        # Lấy câu phụ đề hiện tại và chuỗi người dùng nhập
        segment_text = self.segments[self.current_segment_index - 1]["text"]
        segment_words = segment_text.split()
        user_input = self.text_edit.toPlainText()
        user_words = user_input.split()

        # Ngắt kết nối tín hiệu tạm thời để tránh vòng lặp
        self.text_edit.textChanged.disconnect(self.check_word_live)

        # Tạo định dạng cho từ đúng, sai, và tương tự
        format_correct = QTextCharFormat()
        format_correct.setForeground(QColor("green"))
        format_correct.setFontWeight(QFont.Bold)

        format_similar = QTextCharFormat()
        format_similar.setForeground(QColor("orange"))  # Màu cam cho từ tương tự

        format_error = QTextCharFormat()
        format_error.setForeground(QColor("red"))

        format_default = QTextCharFormat()
        format_default.setForeground(QColor("black"))

        # Khởi tạo con trỏ
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.Start)

        # So sánh từng từ
        for i, word in enumerate(user_words):
            if i < len(segment_words):
                # So sánh mức độ tương đồng bằng SequenceMatcher
                similarity = difflib.SequenceMatcher(None, word.lower(), segment_words[i].lower()).ratio()

                if similarity > 0.8:  # Từ đúng (trên 80% giống nhau)
                    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(word))
                    cursor.setCharFormat(format_correct)
                elif similarity > 0.5:  # Từ tương tự (50%-80% giống nhau)
                    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(word))
                    cursor.setCharFormat(format_similar)
                else:  # Từ sai
                    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(word))
                    cursor.setCharFormat(format_error)

            # Di chuyển qua khoảng trắng (giữ định dạng mặc định)
            if i < len(user_words) - 1:
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 1)
                cursor.setCharFormat(format_default)

        # Kết nối lại tín hiệu
        self.text_edit.textChanged.connect(self.check_word_live)

    def generate_subtitle_for_video(self):
        # Mở hộp thoại chọn tệp video
        video_file, _ = QFileDialog.getOpenFileName(self, "Select Video File for Subtitle Generation", "", "Video Files (*.mp4 *.avi *.ts)")
        if not video_file:
            self.status_bar.showMessage("No video file selected for subtitle generation!")
            return

        try:
            from video_processing import generate_subtitles  # Đảm bảo import đúng
            self.status_bar.showMessage("Generating subtitles, please wait...")
            QApplication.processEvents()  # Cập nhật giao diện người dùng

            srt_path = generate_subtitles(video_file)  # Tạo phụ đề từ tệp video
            self.status_bar.showMessage(f"Subtitle generated at: {srt_path}")

            # Cập nhật đường dẫn video và phụ đề
            self.video_file = video_file
            self.subtitle_file = srt_path

            # Tải và khởi động quá trình học với video và phụ đề mới
            self.load_files_after_generation()
        except Exception as e:
            self.status_bar.showMessage(f"Error generating subtitle: {str(e)}")

    def check_transcription(self):
        if not self.segments or self.current_segment_index == 0:
            self.status_bar.showMessage("No segment loaded to check.")
            return

        # Lấy câu phụ đề hiện tại và chuỗi người dùng nhập
        segment_text = self.segments[self.current_segment_index - 1]["text"]
        segment_words = segment_text.split()
        user_input = self.text_edit.toPlainText()
        user_words = user_input.split()

        # Loại bỏ dấu câu khỏi câu phụ đề
        def remove_punctuation(word):
            return word.translate(str.maketrans("", "", string.punctuation))

        cleaned_segment_words = [remove_punctuation(word) for word in segment_words]
        
        # Ngắt kết nối tín hiệu tạm thời
        self.text_edit.textChanged.disconnect(self.check_word_live)

        # Tạo định dạng cho từ đúng
        format_correct = QTextCharFormat()
        format_correct.setForeground(QColor("green"))
        format_correct.setFontWeight(QFont.Bold)

        # Tạo định dạng mặc định
        format_default = QTextCharFormat()
        format_default.setForeground(QColor("black"))

        # Khởi tạo con trỏ
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.Start)

        # Xử lý từng từ
        corrected_text = []  # Lưu trữ kết quả cuối cùng
        for i, word in enumerate(user_words):
            if i < len(cleaned_segment_words):
                # So sánh không phân biệt hoa/thường và bỏ qua dấu câu
                if word.lower() == cleaned_segment_words[i].lower():
                    # Từ đúng: thêm vào kết quả và định dạng màu xanh
                    corrected_text.append(segment_words[i])  # Giữ định dạng gốc từ phụ đề
                else:
                    # Từ sai: thay bằng từ đúng và định dạng màu xanh
                    corrected_text.append(segment_words[i])
            else:
                # Nếu có thêm từ không tồn tại trong phụ đề, bỏ qua
                continue

        # Đảm bảo chèn dấu cách giữa các từ
        corrected_text = " ".join(corrected_text)

        # Cập nhật văn bản
        cursor.select(QTextCursor.Document)
        cursor.insertText(corrected_text, format_correct)

        # Di chuyển con trỏ về cuối để người dùng tiếp tục
        cursor.movePosition(QTextCursor.End)
        self.text_edit.setTextCursor(cursor)

        # Kết nối lại tín hiệu
        self.text_edit.textChanged.connect(self.check_word_live)

        self.status_bar.showMessage("Updated incorrect words!")

    def replay_segment(self):
        if self.current_segment_index == 0:
            self.status_bar.showMessage("No segment to replay!")
            return

        segment = self.segments[self.current_segment_index - 1]
        start_ms = time_to_milliseconds(segment["start_time"])
        # Sử dụng thời gian kết thúc đã được điều chỉnh
        adjusted_end_ms = self.get_adjusted_end_time(self.current_segment_index - 1)
        duration = adjusted_end_ms - start_ms

        self.player.set_time(start_ms)
        self.player.play()

        self.timer.start(duration)
        self.status_bar.showMessage(f"Replaying Segment {self.current_segment_index}/{len(self.segments)}.")

    def open_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        layout = QFormLayout()

        replay_spinbox = QSpinBox()
        replay_spinbox.setRange(1, 10)
        replay_spinbox.setValue(self.replay_count)
        layout.addRow("Replay Count:", replay_spinbox)

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save_settings(dialog, replay_spinbox))
        layout.addWidget(save_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def save_settings(self, dialog, replay_spinbox):
        self.replay_count = replay_spinbox.value()
        dialog.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:  # Kiểm tra nếu phím bấm là Tab
            self.previous_segment()  # Gọi hàm quay lại phân đoạn trước
        elif event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_O:  # Ctrl + O: Mở file video/phụ đề
                self.load_files()
            elif event.key() == Qt.Key_R:  # Ctrl + R: Phát lại đoạn hiện tại
                self.replay_segment()
            elif event.key() == Qt.Key_N:  # Ctrl + N: Chuyển sang đoạn tiếp theo
                self.next_segment()
            elif event.key() == Qt.Key_T:  # Ctrl + T: Kiểm tra đoạn văn bản hiện tại
                self.check_transcription()
        elif event.key() == Qt.Key_Return:  # Enter: Chuyển sang đoạn tiếp theo
            self.next_segment()

    def save_progress(self):
        """Lưu tiến trình học vào file JSON."""
        if self.video_file and self.subtitle_file:
            progress_data = {
                "video_file": self.video_file,
                "subtitle_file": self.subtitle_file,
                "current_segment_index": self.current_segment_index,
                "replay_count": self.replay_count
            }
            # Lưu vào file JSON
            with open("progress.json", "w", encoding="utf-8") as file:
                json.dump(progress_data, file)
            self.status_bar.showMessage("Progress saved successfully!")
        else:
            self.status_bar.showMessage("No progress to save!")

    def load_progress(self):
        """Tải tiến trình học từ file JSON."""
        try:
            with open("progress.json", "r", encoding="utf-8") as file:
                self.progress = json.load(file)
                self.status_bar.showMessage("Progress loaded!")
        except (FileNotFoundError, json.JSONDecodeError):
            self.progress = {}
            self.status_bar.showMessage("No saved progress found or file is corrupted.")

    def closeEvent(self, event):
        """Lưu tiến trình khi ứng dụng đóng."""
        self.save_progress()
        event.accept()

    def load_files_after_generation(self):
        # Parse file SRT
        self.segments = parse_srt_to_segments(self.subtitle_file)
        if not self.segments:
            self.status_bar.showMessage("Failed to parse the generated subtitle file.")
            return

        # Khởi tạo trình phát VLC
        self.player = vlc.MediaPlayer(self.video_file)

        # Đặt lại chỉ mục đoạn hiện tại
        self.current_segment_index = 0
        self.status_bar.showMessage(f"Subtitle generated and loaded! Starting from the beginning.")

        # Cập nhật trạng thái nút
        self.next_button.setEnabled(True)
        self.replay_button.setEnabled(False)
        self.previous_button.setEnabled(False)

        # Tải tiến trình mới
        self.save_progress()