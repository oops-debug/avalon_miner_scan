"""
工具函数模块
包含解析矿机信息、格式化等通用功能
"""
import re
import json
from datetime import datetime


def validate_ip_segment_format(ip_segment):
    pattern = r'^\d+\.\d+\.\d+\.\d+-\d+$'
    if not re.match(pattern, ip_segment):
        return False
    
    try:
        ip_part, range_part = ip_segment.split('-')
        ip_parts = ip_part.split('.')
        
        for part in ip_parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        
        start = int(ip_parts[3])
        end = int(range_part)
        if start < 0 or start > 255 or end < 0 or end > 255:
            return False
        if start > end:
            return False
            
        return True
    except (ValueError, IndexError):
        return False


def parse_miner_info(response):
    model = ""
    version = ""
    dna = ""
    mac = ""
    scan_time = ""
    
    model_match = re.search(r'MODEL[=:]\s*([^,\|\n]+)', response, re.IGNORECASE)
    if model_match:
        model = model_match.group(1).strip()

    version_match = re.search(r'VERSION[=:]\s*([^,\|\n]+)', response, re.IGNORECASE)
    if version_match:
        version = version_match.group(1).strip()
    dna_match = re.search(r'DNA[=:]\s*([^,\|\n]+)', response, re.IGNORECASE)
    if dna_match:
        dna = dna_match.group(1).strip()

    mac_match = re.search(r'MAC[=:]\s*([^,\|\n]+)', response, re.IGNORECASE)
    if mac_match:
        mac_raw = mac_match.group(1).strip()
        mac = _normalize_mac_address(mac_raw)
    when_match = re.search(r'When[=:]\s*([^,\|\n]+)', response, re.IGNORECASE)
    if when_match:
        when_value = when_match.group(1).strip()
        try:
            timestamp = int(when_value)
            scan_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            scan_time = when_value
    if not all([model, version, dna, mac, scan_time]):
        try:
            data = json.loads(response)
            if not model:
                for key in ['Model', 'MODEL', 'Type', 'type', 'model']:
                    if key in data:
                        model = str(data[key]).strip()
                        break
            if not version:
                for key in ['Version', 'VERSION', 'version']:
                    if key in data:
                        version = str(data[key]).strip()
                        break
            if not dna:
                for key in ['DNA', 'Dna', 'dna', 'Serial', 'serial', 'SN', 'sn']:
                    if key in data:
                        dna = str(data[key]).strip()
                        break
            
            if not mac:
                for key in ['MAC', 'Mac', 'mac']:
                    if key in data:
                        mac_raw = str(data[key]).strip()
                        if mac_raw.endswith('|'):
                            mac_raw = mac_raw[:-1]
                        mac = _normalize_mac_address(mac_raw)
                        break
            if not scan_time:
                for key in ['When', 'when', 'Time', 'time', 'Timestamp', 'timestamp']:
                    if key in data:
                        when_value = data[key]
                        try:
                            if isinstance(when_value, (int, float)):
                                timestamp = int(when_value)
                                scan_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                scan_time = str(when_value)
                        except (ValueError, OSError):
                            scan_time = str(when_value)
                        break

        except (json.JSONDecodeError, TypeError):
            pass
    if not all([model, version, dna, mac, scan_time]):
        if not model:
            model_patterns = [
                r'(Avalon[-\s]?\d+[A-Z]*)',
                r'(A\d+[A-Z]*)',
                r'(1566[I\-]?HF?)',
                r'(15xHY)',
                r'(16x)',
                r'(A15)'
            ]
            for pattern in model_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    model = match.group(1)
                    break
        if not version:
            version_match = re.search(r'v?(\d+\.\d+\.\d+)', response)
            if version_match:
                version = version_match.group(1)
        

        if not dna:

            dna_patterns = [
                r'([A-Z0-9]{8,20})',
                r'(SN[:=]\s*([A-Z0-9]+))',
                r'(Serial[:=]\s*([A-Z0-9]+))'
            ]
            for pattern in dna_patterns:
                match = re.search(pattern, response)
                if match:
                    dna = match.group(1) if match.groups() else match.group(0)
                    break
        
        if not mac:
            mac_patterns = [
                r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', 
                r'([0-9A-Fa-f]{12})' 
            ]
            for pattern in mac_patterns:
                match = re.search(pattern, response)
                if match:
                    mac_raw = match.group(0)
                    mac = _normalize_mac_address(mac_raw)
                    break

    if model:
        model = re.sub(r'[\|\n\r\t]', '', model).strip()
    if version:
        version = re.sub(r'[\|\n\r\t]', '', version).strip()
    if dna:
        dna = re.sub(r'[\|\n\r\t]', '', dna).strip()
    if not scan_time:
        scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return model, version, dna, mac, scan_time


def _normalize_mac_address(mac):
    """标准化MAC地址格式"""
    if not mac:
        return ""
    mac_clean = re.sub(r'[^0-9A-Fa-f]', '', mac)
    
    if len(mac_clean) != 12:
        return mac
    normalized = ':'.join(mac_clean[i:i+2] for i in range(0, 12, 2))
    return normalized.upper()


def parse_elapsed_time(estats_response):
    """从estats响应中解析Elapsed时间并格式化为可读格式"""
    if not estats_response:
        return "未知"
    elapsed_match = re.search(r'Elapsed\[(\d+)\]', estats_response)
    if elapsed_match:
        try:
            seconds = int(elapsed_match.group(1))
            return format_elapsed_time(seconds)
        except ValueError:
            pass
    elapsed_match = re.search(r'Elapsed[=:]?\s*(\d+)', estats_response)
    if elapsed_match:
        try:
            seconds = int(elapsed_match.group(1))
            return format_elapsed_time(seconds)
        except ValueError:
            pass
    elapsed_match = re.search(r'Elapsed.*?(\d+)', estats_response, re.IGNORECASE)
    if elapsed_match:
        try:
            seconds = int(elapsed_match.group(1))
            return format_elapsed_time(seconds)
        except ValueError:
            pass

    return "未知"


def format_elapsed_time(total_seconds):
    """将秒数格式化为可读的时间格式"""
    if total_seconds <= 0:
        return "0秒"
    days = total_seconds // (24 * 3600)
    hours = (total_seconds % (24 * 3600)) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return "".join(parts)


def parse_ip_segments(ip_segments_text):

    segments = []
    lines = ip_segments_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = re.split(r'[,;\s]+', line)
        for part in parts:
            part = part.strip()
            if not part:
                continue

            ip_part = part
            if '#' in part:

                ip_part = part.split('#')[0].strip()
            
            match = re.match(r'^(\d+)\.(\d+)\.(\d+)\.(\d+)-(\d+)$', ip_part)
            if match:
                segment1, segment2, segment3, start_str, end_str = match.groups()
                
                # 验证IP段
                if not (validate_ip_segment(segment1) and
                        validate_ip_segment(segment2) and
                        validate_ip_segment(segment3)):
                    continue
                    
                try:
                    start = int(start_str)
                    end = int(end_str)
                    
                    if start < 0 or start > 255 or end < 0 or end > 255:
                        continue
                        
                    if start > end:
                        continue
                        
                    segments.append({
                        'segment1': segment1,
                        'segment2': segment2,
                        'segment3': segment3,
                        'start': start,
                        'end': end
                    })
                except ValueError:
                    continue
    
    return segments


def validate_ip_segment(segment):
    """验证IP段是否为有效的0-255之间的数字"""
    try:
        num = int(segment)
        return 0 <= num <= 255
    except ValueError:
        return False
