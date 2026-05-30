"""
网络扫描模块
包含矿机扫描、连接管理和扫描线程功能
"""
import socket
import threading
import time
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import parse_miner_info, parse_elapsed_time, parse_ip_segments


class NetworkScanner:
    """网络扫描器"""
    
    def __init__(self, connection_manager=None):
        self.scanning = False
        self.scan_thread = None
        self.connection_manager = connection_manager
        
        # 扫描统计
        self.current_scan_success = 0
        self.current_scan_fail = 0
        self.success_count = 0
        self.fail_count = 0
        
    def start_scan(self, ip_segments_text, connect_timeout, read_timeout, max_workers, retry_count, 
                   callback=None, progress_callback=None):
        if self.scanning:
            return False, "扫描正在进行中"
        
        try:
            # 解析IP段
            ip_segments = parse_ip_segments(ip_segments_text)
            if not ip_segments:
                return False, "无法解析IP段，请检查格式"
            
            # 计算总IP数量
            total_ips = 0
            for segment in ip_segments:
                total_ips += segment['end'] - segment['start'] + 1
            
            if total_ips == 0:
                return False, "没有有效的IP范围"
            
            # 验证重试次数
            if retry_count < 0 or retry_count > 10:
                return False, "重试次数必须在0-10之间"
            
            self.scanning = True
            self.current_scan_success = 0
            self.current_scan_fail = 0
            
            # 在新线程中执行扫描
            self.scan_thread = threading.Thread(
                target=self._scan_thread_func,
                args=(ip_segments, connect_timeout, read_timeout, max_workers, retry_count, 
                      total_ips, callback, progress_callback),
                daemon=True
            )
            self.scan_thread.start()
            
            return True, f"开始扫描 {total_ips} 个IP"
            
        except ValueError as e:
            return False, f"参数错误: {str(e)}"
        except Exception as e:
            return False, f"启动扫描失败: {str(e)}"
    
    def stop_scan(self):
        """停止扫描"""
        self.scanning = False
        if self.scan_thread:
            self.scan_thread.join(timeout=2)
        return True, "扫描已停止"
    
    def _scan_thread_func(self, ip_segments, connect_timeout, read_timeout, max_workers, retry_count,
                         total_ips, callback, progress_callback):
        """扫描线程函数"""
        # 智能线程数调整
        if total_ips <= 50:
            actual_workers = min(max_workers, 20)
        elif total_ips <= 200:
            actual_workers = min(max_workers, 50)
        else:
            actual_workers = min(max_workers, 100)
        
        # 性能监控变量
        start_time = time.time()
        completed_count = 0
        success_count = 0
        timeout_count = 0
        connection_error_count = 0
        
        # 使用线程池扫描
        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            # 生成所有IP地址
            futures = {}
            for segment in ip_segments:
                segment1 = segment['segment1']
                segment2 = segment['segment2']
                segment3 = segment['segment3']
                start = segment['start']
                end = segment['end']
                
                for i in range(start, end + 1):
                    ip = f"{segment1}.{segment2}.{segment3}.{i}"
                    futures[executor.submit(self._check_miner, ip, connect_timeout, read_timeout, retry_count)] = ip
            
            completed = 0
            batch_size = max(10, total_ips // 20)
            batch_start_time = time.time()
            
            for future in as_completed(futures):
                if not self.scanning:
                    break
                
                completed += 1
                completed_count += 1
                
                # 更新进度
                if progress_callback:
                    progress_callback(completed, total_ips)
                
                # 性能监控：每完成一批任务更新一次状态
                if completed % batch_size == 0 or completed == total_ips:
                    batch_end_time = time.time()
                    batch_duration = batch_end_time - batch_start_time
                    ips_per_second = batch_size / batch_duration if batch_duration > 0 else 0
                    
                    # 计算预估剩余时间
                    remaining_ips = total_ips - completed
                    estimated_remaining_time = remaining_ips / ips_per_second if ips_per_second > 0 else 0
                    
                    # 调用进度回调
                    if progress_callback:
                        progress_callback(completed, total_ips, ips_per_second, estimated_remaining_time)
                    
                    batch_start_time = time.time()
                
                try:
                    result = future.result()
                    ip, response, status, model, version, dna, mac, scan_time, elapsed_time, hashrate, hash_sn_list, cpu_info = result
                    
                    if status == "成功":
                        success_count += 1
                        self.current_scan_success += 1
                        self.success_count += 1
                        
                        # 调用结果回调
                        if callback:
                            callback(ip, model, version, dna, mac, scan_time, elapsed_time, 
                                    hashrate, hash_sn_list, cpu_info, response)
                    else:
                        # 统计不同类型的错误
                        if "连接超时" in status:
                            timeout_count += 1
                        elif "连接错误" in status or "连接失败" in status:
                            connection_error_count += 1
                        self.current_scan_fail += 1
                        self.fail_count += 1
                        
                except Exception as e:
                    print(f"处理结果时出错: {e}")
        
        self.scanning = False
        
        # 计算最终性能统计
        end_time = time.time()
        total_duration = end_time - start_time
        overall_speed = completed_count / total_duration if total_duration > 0 else 0
        success_rate = (success_count / completed_count * 100) if completed_count > 0 else 0
        
        # 调用完成回调
        if callback:
            callback(None, None, None, None, None, None, None, None, None, None, None, 
                    completed_count, success_count, total_duration, overall_speed, success_rate)
    
    def _check_miner(self, ip, connect_timeout, read_timeout, retry_count):
        """检查单个矿机"""
        if not self.scanning:
            return ip, "", "已停止", "", "", "", "", "", "未知", "", ["", "", "", ""], ""
        
        task_start_time = time.time()
        
        # 尝试连接矿机
        sock, retry_used, attempt, error_type = self._connect_with_retry(ip, connect_timeout, retry_count)
        
        if sock is None:
            return ip, "", f"连接失败 ({error_type})", "", "", "", "", "", "未知", "", ["", "", "", ""], ""
        
        try:
            # 发送version命令
            sock.sendall(b'version')
            
            # 设置读取超时
            sock.settimeout(read_timeout)
            
            # 接收响应
            response = b''
            try:
                while True:
                    data = sock.recv(1024)
                    if not data:
                        break
                    response += data
                    if len(response) >= 2048:
                        break
            except socket.timeout:
                pass
            except (ConnectionResetError, OSError) as e:
                return ip, "", f"连接中断: {str(e)[:30]}", "", "", "", "", "", "未知", "", ["", "", "", ""], ""
            
            if response:
                decoded_response = response.decode('utf-8', errors='ignore').strip()
                # 解析响应信息
                model, version, dna, mac, scan_time = parse_miner_info(decoded_response)
                
                # 获取算力信息和运行时间
                hashrate, elapsed_time, estats_response, cpu_info = self._get_hashrate_and_elapsed(ip, read_timeout)
                
                # 获取HASH板SN号
                hash_sn_list, hash_responses = self._get_all_hash_sn(ip, read_timeout)
                
                # 构建完整的响应信息
                full_response = f"VERSION:\n{decoded_response}\n\n"
                full_response += "HASH:\n"
                for i, resp in enumerate(hash_responses):
                    full_response += f"HASH{i}: {resp}\n"
                full_response += f"\nLOG:\n{estats_response}\n"
                
                if retry_used > 0:
                    full_response = f"【注意：此连接使用了{retry_used}次重试】\n\n{full_response}"
                
                return ip, full_response, "成功", model, version, dna, mac, scan_time, elapsed_time, hashrate, hash_sn_list, cpu_info
            else:
                return ip, "", "无响应数据", "", "", "", "", "", "未知", "", ["", "", "", ""], ""
            
        except Exception as e:
            return ip, "", f"错误: {str(e)[:30]}", "", "", "", "", "", "未知", "", ["", "", "", ""], ""
        finally:
            try:
                sock.close()
            except:
                pass
    
    def _connect_with_retry(self, ip, timeout, retry_count):
        """尝试连接矿机，支持智能重试和指数退避"""
        max_attempts = retry_count + 1
        retry_used = 0
        error_type = "unknown"
        
        # 指数退避参数
        base_delay = 0.1
        max_delay = 2.0
        
        for attempt in range(max_attempts):
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((ip, 4028))
                
                if attempt > 0:
                    retry_used = attempt
                
                return sock, retry_used, attempt + 1, "success"
                
            except socket.timeout:
                error_type = "timeout"
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                    sock = None
                
                # 连接超时：使用指数退避重试
                if attempt < max_attempts - 1:
                    retry_used = attempt + 1
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    time.sleep(delay + jitter)
                else:
                    return None, retry_used, attempt + 1, error_type
                    
            except ConnectionRefusedError:
                error_type = "connection_refused"
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                    sock = None
                
                # 连接被拒绝：通常是端口未开放，减少重试次数
                if attempt < max_attempts - 1 and attempt < 2:
                    retry_used = attempt + 1
                    time.sleep(0.05)
                else:
                    return None, retry_used, attempt + 1, error_type
                    
            except ConnectionResetError:
                error_type = "connection_reset"
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                    sock = None
                
                # 连接被重置：可能是网络不稳定，使用中等延迟重试
                if attempt < max_attempts - 1:
                    retry_used = attempt + 1
                    delay = min(base_delay * (1.5 ** attempt), max_delay)
                    time.sleep(delay)
                else:
                    return None, retry_used, attempt + 1, error_type
                    
            except OSError as e:
                error_type = "os_error"
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                    sock = None
                
                # 系统错误：根据错误码决定是否重试
                if hasattr(e, 'errno'):
                    if e.errno == 10061:
                        error_type = "connection_refused"
                    elif e.errno == 10060:
                        error_type = "timeout"
                    elif e.errno == 10054:
                        error_type = "connection_reset"
                
                # 对于网络相关的系统错误，使用指数退避重试
                if attempt < max_attempts - 1:
                    retry_used = attempt + 1
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    time.sleep(delay)
                else:
                    return None, retry_used, attempt + 1, error_type
                    
            except Exception as e:
                error_type = "unknown_error"
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                    sock = None
                
                # 其他未知错误：谨慎重试
                if attempt < max_attempts - 1 and attempt < 1:
                    retry_used = attempt + 1
                    time.sleep(0.1)
                else:
                    return None, retry_used, attempt + 1, error_type

        return None, retry_count, max_attempts, error_type
    
    def _get_hashrate_and_elapsed(self, ip, read_timeout):
        """获取矿机算力信息和运行时间"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(read_timeout)
                sock.connect((ip, 4028))
                
                # 发送estats命令
                sock.sendall(b'estats')
                
                # 接收响应
                response = b''
                try:
                    while True:
                        data = sock.recv(1024)
                        if not data:
                            break
                        response += data
                        if len(response) >= 4096:
                            break
                except socket.timeout:
                    pass
                except (ConnectionResetError, OSError) as e:
                    return f"连接中断: {str(e)[:20]}", "未知", f"连接中断: {str(e)}", ""
                
                if response:
                    decoded_response = response.decode('utf-8', errors='ignore').strip()
                    
                    # 解析算力信息
                    hashrate = "未知"
                    
                    # 方法1: 尝试JSON格式解析
                    try:
                        import json
                        data = json.loads(decoded_response)
                        
                        # 查找算力信息，支持多种可能的键名
                        hashrate_keys = ['GHSspd', 'GHS 5s', 'GHS av', 'GHS', 'ghs', 'hashrate', 'Hashrate']
                        for key in hashrate_keys:
                            if key in data:
                                value = data[key]
                                if isinstance(value, (int, float)):
                                    hashrate = f"{value} GH/s"
                                elif isinstance(value, str):
                                    num_match = re.search(r'([\d.]+)', value)
                                    if num_match:
                                        hashrate = f"{num_match.group(1)} GH/s"
                                    else:
                                        hashrate = f"{value} GH/s"
                                break
                                
                    except (json.JSONDecodeError, TypeError):
                        pass
                    
                    # 方法2: 如果JSON格式没有找到算力信息，尝试文本格式
                    if hashrate == "未知":
                        import re
                        hashrate_patterns = [
                            r'GHSspd\[([\d.]+)\]',
                            r'GHSspd[=:]?\s*([\d.]+)',
                            r'GHS\s*5s\[([\d.]+)\]',
                            r'GHS\s*5s[=:]?\s*([\d.]+)',
                            r'GHS\s*av\[([\d.]+)\]',
                            r'GHS\s*av[=:]?\s*([\d.]+)',
                            r'hashrate[=:]?\s*([\d.]+)',
                            r'Hashrate[=:]?\s*([\d.]+)',
                            r'([\d.]+)\s*GH/s',
                            r'([\d.]+)\s*GHS'
                        ]
                        
                        for pattern in hashrate_patterns:
                            match = re.search(pattern, decoded_response, re.IGNORECASE)
                            if match:
                                hashrate = f"{match.group(1)} GH/s"
                                break
                    
                    # 解析运行时间
                    elapsed_time = parse_elapsed_time(decoded_response)
                    
                    # 检测CPU信息
                    cpu_info = ""
                    cpu_patterns = [
                        r'K230',
                        r'K210',
                        r'ARM',
                        r'CPU[=:]?\s*([^,\s]+)',
                        r'Processor[=:]?\s*([^,\s]+)'
                    ]
                    
                    for pattern in cpu_patterns:
                        match = re.search(pattern, decoded_response, re.IGNORECASE)
                        if match:
                            if pattern == r'K230':
                                cpu_info = "K230"
                            elif pattern == r'K210':
                                cpu_info = "K210"
                            elif pattern == r'ARM':
                                cpu_info = "ARM"
                            else:
                                cpu_info = match.group(1) if match.groups() else match.group(0)
                            break
                    
                    return hashrate, elapsed_time, decoded_response, cpu_info
                else:
                    return "无响应", "未知", "无响应数据", ""
        except socket.timeout:
            return "连接超时", "未知", "连接超时", ""
        except ConnectionRefusedError:
            return "连接拒绝", "未知", "连接拒绝", ""
        except ConnectionResetError:
            return "连接重置", "未知", "连接重置", ""
        except OSError as e:
            return f"系统错误: {str(e)[:20]}", "未知", f"系统错误: {str(e)}", ""
        except Exception as e:
            return f"错误: {str(e)[:20]}", "未知", f"错误: {str(e)}", ""
    
    def _get_all_hash_sn(self, ip, read_timeout):
        """获取所有HASH板的SN号和响应信息"""
        hash_sn_list = ["", "", "", ""]
        hash_responses = ["", "", "", ""]
        
        for board_num in range(4):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(read_timeout)
                    sock.connect((ip, 4028))
                    
                    # 发送ascset命令
                    command = f"ascset|0,hash-sn-read,{board_num}"
                    sock.sendall(command.encode())
                    
                    # 接收响应
                    response = b''
                    while True:
                        try:
                            data = sock.recv(1024)
                            if not data:
                                break
                            response += data
                        except socket.timeout:
                            break
                    
                    if response:
                        decoded_response = response.decode('utf-8', errors='ignore').strip()
                        hash_responses[board_num] = decoded_response
                        # 解析SN号，格式是SN:开始英文逗号结束
                        import re
                        sn_match = re.search(r'SN:([^,]+)', decoded_response)
                        if sn_match:
                            hash_sn_list[board_num] = sn_match.group(1)
                        else:
                            hash_sn_list[board_num] = ""
                    else:
                        hash_sn_list[board_num] = "无响应"
                        hash_responses[board_num] = "无响应数据"
                        
            except Exception as e:
                hash_sn_list[board_num] = "获取失败"
                hash_responses[board_num] = f"错误: {str(e)}"
        
        return hash_sn_list, hash_responses
