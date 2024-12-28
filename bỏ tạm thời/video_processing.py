import re
import whisper
import os
import srt
import subprocess
import shutil
import math
# Trường hợp không có SRT
def format_timedelta(td):
    """Chuyển đổi timedelta thành định dạng thời gian SRT: HH:MM:SS,mmm"""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"
def format_srt_timestamp(seconds):
    """Chuyển đổi giây thành định dạng thời gian SRT: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(math.floor((seconds - math.floor(seconds)) * 1000))
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def extract_audio_from_video(video_path, output_audio_path):
    """Trích xuất audio từ video."""
    command = f"ffmpeg -i \"{video_path}\" -vn -acodec pcm_s16le -ar 16000 -ac 1 \"{output_audio_path}\""
    subprocess.run(command, shell=True, check=True)

def generate_subtitles(video_path, model_name="medium"):
    """Tạo phụ đề từ video bằng Whisper."""
    # Kiểm tra nếu đã có ffmpeg
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg không được cài đặt. Hãy cài đặt ffmpeg trước.")

    # Trích xuất audio từ video
    audio_path = "temp_audio.wav"
    extract_audio_from_video(video_path, audio_path)

    # Tải model Whisper
    model = whisper.load_model(model_name)

    # Nhận diện và tạo phụ đề
    result = model.transcribe(audio_path)

    # Kiểm tra kết quả
    if not result.get("segments"):
        raise ValueError("Không có đoạn phụ đề nào được tạo ra.")

    # Lưu phụ đề vào file SRT với định dạng thời gian đúng
    srt_path = os.path.splitext(video_path)[0] + ".srt"
    with open(srt_path, "w", encoding="utf-8") as srt_file:
        for i, segment in enumerate(result["segments"]):
            start = format_srt_timestamp(segment["start"])
            end = format_srt_timestamp(segment["end"])
            text = segment["text"].strip()
            srt_file.write(f"{i + 1}\n{start} --> {end}\n{text}\n\n")

    # Xóa file âm thanh tạm
    os.remove(audio_path)

    # Kiểm tra tệp SRT đã được tạo và có nội dung
    if not os.path.exists(srt_path) or os.path.getsize(srt_path) == 0:
        raise FileNotFoundError("Tệp SRT không được tạo ra hoặc trống.")

    return srt_path

#####
def parse_srt_to_segments(srt_file_path):
    """Parse tệp SRT và trích xuất các đoạn thời gian và văn bản tương ứng sử dụng thư viện python-srt."""
    segments = []
    try:
        with open(srt_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            subs = list(srt.parse(content))
            for sub in subs:
                segments.append({
                    "start_time": format_timedelta(sub.start),
                    "end_time": format_timedelta(sub.end),
                    "text": sub.content.replace('\n', ' ')
                })
    except Exception as e:
        print(f"Lỗi khi phân tích tệp SRT: {e}")

    print(f"Tổng số đoạn phụ đề được phân tích: {len(segments)}")
    return segments

def time_to_milliseconds(time_str):
    """Convert time string (HH:MM:SS,ms) to milliseconds."""
    hours, minutes, seconds_ms = time_str.split(':')
    seconds, milliseconds = map(int, seconds_ms.split(','))
    return (int(hours) * 3600 + int(minutes) * 60 + seconds) * 1000 + milliseconds
