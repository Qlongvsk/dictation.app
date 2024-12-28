from PyQt5.QtWidgets import QFrame, QSizePolicy
from PyQt5.QtCore import Qt
import sys

class VideoPlayer(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.player = None
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