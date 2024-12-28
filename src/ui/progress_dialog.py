from PyQt5.QtWidgets import QDialog, QProgressBar, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class ConversionProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Converting Video")
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Label hiển thị trạng thái
        self.status_label = QLabel("Converting TS to MP4...")
        layout.addWidget(self.status_label)
        
        # Thanh tiến trình
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
        
        # Label hiển thị phần trăm
        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.percent_label)
        
        self.setLayout(layout)
        
    def update_progress(self, percent, status=None):
        self.progress_bar.setValue(percent)
        self.percent_label.setText(f"{percent}%")
        if status:
            self.status_label.setText(status) 