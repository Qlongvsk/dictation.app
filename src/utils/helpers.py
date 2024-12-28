import logging

logger = logging.getLogger(__name__)

def time_to_milliseconds(time_str):
    """Chuyển đổi chuỗi thời gian sang milliseconds"""
    try:
        time_parts = time_str.split(':')
        hours = int(time_parts[0])
        minutes = int(time_parts[1])
        seconds = float(time_parts[2].replace(',', '.'))
        
        total_milliseconds = (hours * 3600 + minutes * 60 + seconds) * 1000
        return int(total_milliseconds)
    except Exception as e:
        logger.error(f"Error converting time to milliseconds: {str(e)}")
        return 0

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