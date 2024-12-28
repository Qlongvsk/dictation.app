from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLabel, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt

class NoteDialog(QDialog):
    def __init__(self, note_manager, video_file, parent=None):
        super().__init__(parent)
        self.note_manager = note_manager
        self.video_file = video_file
        self.setup_ui()
        self.load_notes()
        
    def setup_ui(self):
        """Thiết lập giao diện"""
        self.setWindowTitle("Notes")
        self.setMinimumSize(400, 500)
        
        layout = QVBoxLayout()
        
        # Words section
        words_label = QLabel("Saved Words:")
        layout.addWidget(words_label)
        
        self.words_list = QListWidget()
        layout.addWidget(self.words_list)
        
        # Segments section
        segments_label = QLabel("Saved Segments:")
        layout.addWidget(segments_label)
        
        self.segments_list = QListWidget()
        layout.addWidget(self.segments_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        export_button = QPushButton("Export Notes")
        export_button.clicked.connect(self.export_notes)
        button_layout.addWidget(export_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def load_notes(self):
        """Load và hiển thị notes"""
        notes = self.note_manager.load_notes(self.video_file)
        
        self.words_list.clear()
        self.words_list.addItems(notes["words"])
        
        self.segments_list.clear()
        self.segments_list.addItems(notes["segments"])
        
    def export_notes(self):
        """Export notes ra file markdown"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Notes", "", "Markdown Files (*.md)"
        )
        
        if file_path:
            if self.note_manager.export_notes(self.video_file, file_path):
                QMessageBox.information(self, "Success", "Notes exported successfully!")
                self.load_notes()  # Refresh list after export
            else:
                QMessageBox.critical(self, "Error", "Failed to export notes") 