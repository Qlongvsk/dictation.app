import re
import logging
from datetime import datetime
from pathlib import Path
import speech_recognition as sr
from pydub import AudioSegment
import subprocess
import pysrt

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.subtitles = None
        
    def load_subtitles(self, subtitle_file):
        """Load và parse file phụ đề với thời gian chính xác"""
        try:
            segments = []
            current_segment = {}
            
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if line.isdigit():  # Segment number
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = {"index": int(line)}
                    
                elif '-->' in line:  # Timestamp
                    start, end = line.split(' --> ')
                    current_segment["start_time"] = start.strip()
                    current_segment["end_time"] = end.strip()
                    current_segment["duration_ms"] = (
                        self.time_to_milliseconds(end.strip()) - 
                        self.time_to_milliseconds(start.strip())
                    )
                    
                elif line:  # Text content
                    if "text" not in current_segment:
                        current_segment["text"] = line
                    else:
                        current_segment["text"] += "\n" + line
                        
                i += 1
                
            if current_segment:
                segments.append(current_segment)
                
            return segments
            
        except Exception as e:
            logger.error(f"Error loading subtitles: {str(e)}")
            return None
            
    def time_to_milliseconds(self, time_str):
        """Chuyển đổi thời gian từ string sang milliseconds chính xác"""
        try:
            h, m, s = time_str.split(':')
            s, ms = s.split(',')
            total_ms = (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)
            return total_ms
        except Exception as e:
            logger.error(f"Error converting time to milliseconds: {str(e)}")
            return 0

    @staticmethod
    def make_chunks(audio, chunk_length):
        """Chia audio thành các đoạn nhỏ"""
        chunks = []
        for i in range(0, len(audio), chunk_length):
            chunks.append(audio[i:i + chunk_length])
        return chunks

    @staticmethod
    def parse_srt_to_segments(srt_file):
        """Đọc file SRT và chuyển thành danh sách các đoạn phụ đề"""
        try:
            segments = []
            current_segment = {}
            
            with open(srt_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if not line:
                    i += 1
                    continue
                    
                if line.isdigit():
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = {'index': int(line)}
                    i += 1
                    continue
                    
                if '-->' in line:
                    times = line.split(' --> ')
                    current_segment['start_time'] = times[0].strip()
                    current_segment['end_time'] = times[1].strip()
                    i += 1
                    continue
                    
                text = []
                while i < len(lines) and lines[i].strip():
                    text.append(lines[i].strip())
                    i += 1
                current_segment['text'] = ' '.join(text)
                
            if current_segment:
                segments.append(current_segment)
                
            return segments
            
        except Exception as e:
            logger.error(f"Error parsing SRT file: {str(e)}")
            return []

    @staticmethod
    def generate_subtitles(video_file):
        """Tạo phụ đề từ file video"""
        try:
            video_path = Path(video_file)
            output_srt = video_path.with_suffix('.srt')
            
            audio_file = VideoProcessor.extract_audio(video_file)
            if not audio_file:
                return None
                
            segments = VideoProcessor.speech_to_text(audio_file)
            if not segments:
                return None
                
            VideoProcessor.write_srt_file(segments, output_srt)
            
            return str(output_srt)
            
        except Exception as e:
            logger.error(f"Error generating subtitles: {str(e)}")
            return None

    @staticmethod
    def extract_audio(video_file):
        """Trích xuất audio từ video"""
        try:
            output_file = Path(video_file).with_suffix('.wav')
            
            command = [
                'ffmpeg', '-i', str(video_file),
                '-ab', '160k', '-ac', '2', '-ar', '44100', '-vn',
                str(output_file)
            ]
            
            subprocess.run(command, check=True)
            return output_file
            
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            return None

    @staticmethod
    def speech_to_text(audio_file):
        """Chuyển đổi speech thành text"""
        try:
            recognizer = sr.Recognizer()
            segments = []
            
            audio = AudioSegment.from_wav(str(audio_file))
            chunk_length = 10000  # 10 seconds
            chunks = VideoProcessor.make_chunks(audio, chunk_length)
            
            for i, chunk in enumerate(chunks):
                chunk_file = f"temp_chunk_{i}.wav"
                chunk.export(chunk_file, format="wav")
                
                with sr.AudioFile(chunk_file) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data, language='vi-VN')
                    
                    segments.append({
                        'index': i + 1,
                        'start_time': VideoProcessor.format_time(i * chunk_length),
                        'end_time': VideoProcessor.format_time((i + 1) * chunk_length),
                        'text': text
                    })
                    
                Path(chunk_file).unlink()
                
            return segments
            
        except Exception as e:
            logger.error(f"Error converting speech to text: {str(e)}")
            return None

    @staticmethod
    def format_time(milliseconds):
        """Format thời gian theo định dạng SRT"""
        seconds = milliseconds / 1000
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace('.', ',')

    @staticmethod
    def write_srt_file(segments, output_file):
        """Ghi segments ra file SRT"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for segment in segments:
                    f.write(f"{segment['index']}\n")
                    f.write(f"{segment['start_time']} --> {segment['end_time']}\n")
                    f.write(f"{segment['text']}\n\n")
            return True
        except Exception as e:
            logger.error(f"Error writing SRT file: {str(e)}")
            return False 