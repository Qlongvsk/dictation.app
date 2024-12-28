from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

class NoteManager:
    def __init__(self):
        try:
            self.notes_dir = Path("data/notes")
            # Tạo thư mục nếu chưa tồn tại
            self.notes_dir.mkdir(parents=True, exist_ok=True)
            
            # Kiểm tra quyền ghi
            test_file = self.notes_dir / "test.txt"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            logger.error(f"Error initializing NoteManager: {str(e)}")
            raise
        
    def get_note_file(self, video_file):
        """Lấy file note tương ứng với video"""
        video_hash = str(hash(video_file))
        logger.info(f"Video file: {video_file}")  # Log video file path
        logger.info(f"Video hash: {video_hash}")  # Log hash value
        return self.notes_dir / f"{video_hash}.json"
        
    def load_notes(self, video_file):
        """Load notes cho video"""
        try:
            note_file = self.get_note_file(video_file)
            logger.info(f"Loading notes from file: {note_file}")  # Log file path
            if note_file.exists():
                with open(note_file, 'r', encoding='utf-8') as f:
                    notes = json.load(f)
                    logger.info(f"Loaded notes content: {notes}")  # Log content
                    return notes
            logger.info("No existing notes file found, returning empty notes")
            return {"words": [], "segments": []}
        except Exception as e:
            logger.error(f"Error loading notes: {str(e)}")
            return {"words": [], "segments": []}
            
    def save_notes(self, video_file, notes):
        """Lưu notes cho video"""
        try:
            note_file = self.get_note_file(video_file)
            with open(note_file, 'w', encoding='utf-8') as f:
                json.dump(notes, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving notes: {str(e)}")
            return False
            
    def add_word(self, video_file, word):
        """Thêm từ vào notes"""
        notes = self.load_notes(video_file)
        if word not in notes["words"]:
            notes["words"].append(word)
            self.save_notes(video_file, notes)
            
    def add_segment(self, video_file, segment_text):
        """Thêm segment vào notes"""
        notes = self.load_notes(video_file)
        if segment_text not in notes["segments"]:
            notes["segments"].append(segment_text)
            self.save_notes(video_file, notes)
            
    def export_notes(self, video_file, export_path):
        """Export notes ra file markdown"""
        try:
            notes = self.load_notes(video_file)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                # Write words section
                f.write("# Saved Words\n\n")
                for word in notes["words"]:
                    f.write(f"- {word}\n")
                    
                # Write segments section
                f.write("\n# Saved Segments\n\n")
                for segment in notes["segments"]:
                    f.write(f"> {segment}\n\n")
                    
            # Clear notes after export
            self.save_notes(video_file, {"words": [], "segments": []})
            return True
            
        except Exception as e:
            logger.error(f"Error exporting notes: {str(e)}")
            return False 