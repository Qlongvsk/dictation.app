from PyQt5.QtWidgets import QFrame, QSizePolicy
from PyQt5.QtCore import Qt
import sys
import vlc

class VideoPlayer(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.player = None
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.setup_ui()
        
    def setup_ui(self):
        """Thiết lập giao diện video player"""
        # Đặt kích thước tối thiểu
        self.setMinimumSize(640, 360)
        
        # Đặt màu nền đen
        self.setStyleSheet("QFrame { background-color: black; }")
        
        # Đặt policy để widget có thể phóng to
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_player(self, player):
        """Thiết lập player và kết nối với widget"""
        self.player = player
        if sys.platform == "win32":
            self.player.set_hwnd(self.get_handle())
        elif sys.platform == "darwin":  # macOS
            self.player.set_nsobject(self.get_handle())
        else:  # Linux
            self.player.set_xwindow(self.get_handle())

    def get_handle(self):
        """Lấy handle của widget để VLC có thể render video"""
        if sys.platform == "win32":
            return int(self.winId())
        else:
            return self.winId()

    def resizeEvent(self, event):
        """Xử lý sự kiện thay đổi kích thước"""
        if self.player:
            if sys.platform == "win32":
                self.player.set_hwnd(self.get_handle())
            elif sys.platform == "darwin":  # macOS
                self.player.set_nsobject(self.get_handle())
            else:  # Linux
                self.player.set_xwindow(self.get_handle())
        super().resizeEvent(event) 

    def load_video(self, video_file):
        """Load video file vào player"""
        try:
            # Load video
            media = self.instance.media_new(video_file)
            self.player.set_media(media)
            
            # Gán player vào video frame
            if sys.platform.startswith('linux'):
                self.player.set_xwindow(self.winId())
            elif sys.platform == "win32":
                self.player.set_hwnd(self.winId())
            elif sys.platform == "darwin":
                self.player.set_nsobject(int(self.winId()))
                
            return True
            
        except Exception as e:
            logger.error(f"Error loading video in VideoPlayer: {str(e)}")
            return False
            
    def play(self):
        """Phát video"""
        self.player.play()
        
    def pause(self):
        """Tạm dừng video"""
        self.player.pause()
        
    def stop(self):
        """Dừng video"""
        self.player.stop()
        
    def set_time(self, time_ms):
        """Đặt vị trí phát"""
        self.player.set_time(time_ms) 