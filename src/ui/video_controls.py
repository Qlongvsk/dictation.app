from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSlider, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, QTime
import logging

logger = logging.getLogger(__name__)

class VideoControls(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)  # Giảm margin
        
        # Thanh timeline
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setEnabled(True)
        self.time_slider.setMinimumWidth(600)  # Tăng chiều dài tối thiểu
        self.time_slider.sliderMoved.connect(self.set_video_position)
        self.time_slider.sliderPressed.connect(self.on_slider_pressed)
        self.time_slider.sliderReleased.connect(self.on_slider_released)
        
        # Label thời gian
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFixedWidth(100)  # Cố định chiều rộng
        
        # Thanh âm lượng nhỏ gọn
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(2)
        
        volume_icon = QLabel("🔊")  # Icon âm lượng
        volume_icon.setFixedWidth(15)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(60)  # Thu gọn chiều rộng
        self.volume_slider.valueChanged.connect(self.set_volume)
        
        volume_layout.addWidget(volume_icon)
        volume_layout.addWidget(self.volume_slider)
        
        # Thêm các widget vào layout chính
        layout.addWidget(self.time_slider, stretch=1)  # Cho phép timeline mở rộng
        layout.addWidget(self.time_label)
        layout.addLayout(volume_layout)
        
        # Style cho widget
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #4a4a4a;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                width: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #2196F3;
            }
            QLabel {
                color: #CCCCCC;
            }
        """)
        
        self.setLayout(layout)

    def setup_timer(self):
        """Thiết lập timer cập nhật thời gian"""
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)  # Cập nhật mỗi 100ms
        self.update_timer.timeout.connect(self.update_video_time)

    def update_video_time(self):
        """Cập nhật thời gian video"""
        if not self.parent or not hasattr(self.parent, 'player') or not self.parent.player:
            return
            
        try:
            # Lấy thời gian hiện tại và tổng thời gian của segment
            if self.parent.segments and self.parent.current_segment_index > 0:
                segment = self.parent.segments[self.parent.current_segment_index - 1]
                
                # Chuyển đổi thời gian từ string sang milliseconds
                start_time_parts = segment["start_time"].split(':')
                end_time_parts = segment["end_time"].split(':')
                
                # Thay thế dấu phẩy bằng dấu chấm trước khi chuyển đổi
                start_ms = ((int(start_time_parts[0]) * 3600 + 
                            int(start_time_parts[1]) * 60 + 
                            float(start_time_parts[2].replace(',', '.'))) * 1000)
                end_ms = ((int(end_time_parts[0]) * 3600 + 
                          int(end_time_parts[1]) * 60 + 
                          float(end_time_parts[2].replace(',', '.'))) * 1000)
                
                current_ms = self.parent.player.get_time() - int(start_ms)
                duration_ms = int(end_ms - start_ms)
                
                # Đảm bảo current_ms không âm
                current_ms = max(0, current_ms)
                
                # Cập nhật timeline
                if not self.time_slider.isSliderDown():
                    self.time_slider.setMaximum(duration_ms)
                    self.time_slider.setValue(current_ms)
                
                # Cập nhật label thời gian
                current_time = QTime(0, 0).addMSecs(current_ms)
                total_time = QTime(0, 0).addMSecs(duration_ms)
                time_format = 'mm:ss'
                time_text = f"{current_time.toString(time_format)} / {total_time.toString(time_format)}"
                self.time_label.setText(time_text)
                
        except Exception as e:
            logger.error(f"Error updating video time: {str(e)}")

    def on_slider_pressed(self):
        """Xử lý khi người dùng bắt đầu kéo timeline"""
        if self.parent and hasattr(self.parent, 'player') and self.parent.player:
            self.update_timer.stop()
            if self.parent.player.is_playing():
                self.parent.player.pause()

    def on_slider_released(self):
        """Xử lý khi người dùng thả timeline"""
        if self.parent and hasattr(self.parent, 'player') and self.parent.player:
            segment = self.parent.segments[self.parent.current_segment_index - 1]
            start_time_parts = segment["start_time"].split(':')
            start_ms = ((int(start_time_parts[0]) * 3600 + 
                        int(start_time_parts[1]) * 60 + 
                        float(start_time_parts[2].replace(',', '.'))) * 1000)
            position = int(start_ms + self.time_slider.value())
            self.parent.player.set_time(position)
            self.parent.player.play()
            self.update_timer.start()

    def set_video_position(self, position):
        """Đặt vị trí video trong segment"""
        if self.parent and hasattr(self.parent, 'player') and self.parent.player:
            segment = self.parent.segments[self.parent.current_segment_index - 1]
            start_time_parts = segment["start_time"].split(':')
            start_ms = ((int(start_time_parts[0]) * 3600 + 
                        int(start_time_parts[1]) * 60 + 
                        float(start_time_parts[2].replace(',', '.'))) * 1000)
            self.parent.player.set_time(int(start_ms + position))

    def set_volume(self, volume):
        """Điều chỉnh âm lượng"""
        if self.parent and hasattr(self.parent, 'player') and self.parent.player:
            self.parent.player.audio_set_volume(volume)

    def keyPressEvent(self, event):
        """Xử lý phím Space cho video controls"""
        if event.key() == Qt.Key_Space:
            if self.parent and hasattr(self.parent, 'toggle_play_pause'):
                self.parent.toggle_play_pause()
            event.accept()
        else:
            super().keyPressEvent(event)