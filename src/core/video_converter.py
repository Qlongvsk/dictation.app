import subprocess
import logging
from pathlib import Path
import os
import re
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class VideoConverter(QObject):
    # Signal để cập nhật tiến trình
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self):
        super().__init__()
        # Kiểm tra ffmpeg đã được cài đặt chưa
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True)
            self.ffmpeg_available = True
        except FileNotFoundError:
            logger.error("FFmpeg not found. Please install FFmpeg first.")
            self.ffmpeg_available = False

    def convert_ts_to_mp4(self, ts_file_path):
        """Chuyển đổi file .ts sang .mp4"""
        if not self.ffmpeg_available:
            raise Exception("FFmpeg is not available")

        try:
            ts_path = Path(ts_file_path)
            if not ts_path.exists():
                raise FileNotFoundError(f"TS file not found: {ts_file_path}")

            # Lấy duration của video
            duration = self.get_video_duration(ts_path)
            
            # Tạo tên file mp4 mới
            mp4_path = ts_path.with_suffix('.mp4')
            
            # Lệnh chuyển đổi với output progress
            command = [
                'ffmpeg',
                '-i', str(ts_path),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-y',
                '-progress', 'pipe:1',  # Output progress to pipe
                str(mp4_path)
            ]

            # Thực hiện chuyển đổi và theo dõi tiến trình
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Đọc output và cập nhật tiến trình
            time_processed = 0
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # Tìm thời gian đã xử lý
                    time_match = re.search(r'out_time_ms=(\d+)', output)
                    if time_match:
                        time_processed = int(time_match.group(1)) // 1000000  # Convert to seconds
                        progress = min(int((time_processed / duration) * 100), 100)
                        self.progress_updated.emit(
                            progress,
                            f"Converting: {time_processed}s / {duration}s"
                        )

            if process.returncode != 0:
                raise Exception(f"Conversion failed: {process.stderr.read()}")

            # Xóa file .ts gốc
            ts_path.unlink()
            
            logger.info(f"Successfully converted {ts_path} to {mp4_path}")
            return str(mp4_path)

        except Exception as e:
            logger.error(f"Error converting video: {str(e)}")
            raise

    def get_video_duration(self, video_path):
        """Lấy độ dài của video (seconds)"""
        try:
            command = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(video_path)
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            return int(float(result.stdout))
        except:
            return 0 