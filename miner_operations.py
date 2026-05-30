"""
矿机操作模块
包含LED控制、信息更新、矿机页面打开等功能
"""
import socket
import threading
import time
import random
import re
import urllib.request
import urllib.error
import webbrowser
import os
from utils import parse_miner_info, parse_elapsed_time


class MinerOperations:
    """矿机操作管理器"""
    
    def __init__(self, connect_timeout=2, read_timeout=3):
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        
    def control_led(self, ip, action, callback=None):
        if action == "on":
            command = "ascset|0,led,1-1"
            action_name = "点灯"
        elif action == "off":
            command = "ascset|0,led,1-0"
            action_name = "关灯"
        else:
            if callback:
                callback(ip, action_name, "失败", "无效的操作类型")
            return
        
        # 在新线程中执行控制操作
        control_thread = threading.Thread(
            target=self._control_led_thread,
            args=(ip, command, action_name, callback),
            daemon=True
        )
        control_thread.start()
    
    def _control_led_thread(self, ip, command, action_name, callback):
        """控制LED灯的线程函数"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.connect_timeout)
                sock.connect((ip, 4028))
                sock.sendall(command.encode())
                
                # 接收响应
                response = b''
                try:
                    while True:
                        data = sock.recv(1024)
                        if not data:
                            break
                        response += data
                except socket.timeout:
                    pass
                
                decoded_response = response.decode('utf-8', errors='ignore').strip()
                
                # 根据返回信息判断操作结果
                if "set OK" in decoded_response:
                    result = "成功"
                else:
                    result = "失败"
                
                # 调用回调函数
                if callback:
                    callback(ip, action_name, result, decoded_response)
                    
        except Exception as e:
            error_msg = f"控制失败: {str(e)[:50]}"
            if callback:
                callback(ip, action_name, "失败", error_msg)
    
    def query_led_status(self, ip, callback=None):
        # 在新线程中执行查询操作
        query_thread = threading.Thread(
            target=self._query_led_status_thread,
            args=(ip, callback),
            daemon=True
        )
        query_thread.start()
    
    def _query_led_status_thread(self, ip, callback):
        """查询LED灯状态的线程函数"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.connect_timeout)
                sock.connect((ip, 4028))
                sock.sendall(b'ascset|0,led,1-255')
                
                # 接收响应
                response = b''
                try:
                    while True:
                        data = sock.recv(1024)
                        if not data:
                            break
                        response += data
                except socket.timeout:
                    pass
                
                decoded_response = response.decode('utf-8', errors='ignore').strip()
                
                # 解析灯状态
                if "LED[1]" in decoded_response:
                    status = "灯已点亮"
                elif "LED[0]" in decoded_response:
                    status = "灯已关闭"
                else:
                    status = "状态未知"
                
                # 调用回调函数
                if callback:
                    callback(ip, status, decoded_response)
                    
        except Exception as e:
            error_msg = f"查询失败: {str(e)[:50]}"
            if callback:
                callback(ip, "查询失败", error_msg)
    
    def update_miner_info(self, ip, callback=None):
        # 在新线程中执行更新
        update_thread = threading.Thread(
            target=self._update_miner_info_thread,
            args=(ip, callback),
            daemon=True
        )
        update_thread.start()
    
    def _update_miner_info_thread(self, ip, callback):
        """更新矿机信息的线程函数"""
        start_time = time.time()
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.connect_timeout)
                sock.connect((ip, 4028))
                
                # 发送version命令
                sock.sendall(b'version')
                response = b''
                while True:
                    try:
                        data = sock.recv(1024)
                        if not data:
                            break
                        response += data
                        if len(response) >= 2048:
                            break
                    except socket.timeout:
                        break
                
                if response:
                    decoded_response = response.decode('utf-8', errors='ignore').strip()
                    # 解析响应信息
                    model, version, dna, mac, scan_time = parse_miner_info(decoded_response)
                    
                    # 获取算力信息和运行时间
                    hashrate, elapsed_time, estats_response, cpu_info = self._get_hashrate_and_elapsed(ip)
                    
                    # 获取HASH板SN号
                    hash_sn_list, hash_responses = self._get_all_hash_sn(ip)
                    
                    response_time = round((time.time() - start_time) * 1000, 2)
                    
                    # 构建完整的响应信息
                    full_response = f"VERSION:\n{decoded_response}\n\n"
                    full_response += "HASH:\n"
                    for i, resp in enumerate(hash_responses):
                        full_response += f"HASH{i}: {resp}\n"
                    full_response += f"\nLOG:\n{estats_response}\n"
                    
                    # 调用回调函数
                    if callback:
                        callback(ip, model, version, dna, mac, scan_time, elapsed_time, 
                                hashrate, hash_sn_list, cpu_info, full_response, True, "")
                else:
                    if callback:
                        callback(ip, "", "", "", "", "", "", "", ["", "", "", ""], "", "", False, "无响应数据")
                        
        except Exception as e:
            error_msg = f"更新失败: {str(e)}"
            if callback:
                callback(ip, "", "", "", "", "", "", "", ["", "", "", ""], "", "", False, error_msg)
    
    def _get_hashrate_and_elapsed(self, ip):
        """获取矿机算力信息和运行时间"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.read_timeout)
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
    
    def _get_all_hash_sn(self, ip):
        """获取所有HASH板的SN号和响应信息"""
        hash_sn_list = ["", "", "", ""]
        hash_responses = ["", "", "", ""]
        
        for board_num in range(4):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(self.read_timeout)
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
    
    def open_miner_page(self, ip, model="", cpu_info="", callback=None):

        # 在新线程中处理
        open_thread = threading.Thread(
            target=self._open_miner_page_thread,
            args=(ip, model, cpu_info, callback),
            daemon=True
        )
        open_thread.start()
    
    def _open_miner_page_thread(self, ip, model, cpu_info, callback):
        """打开矿机页面的线程函数"""
        try:
            # 检查是否是K230设备
            if cpu_info == "K230":
                # K230设备需要特殊处理：获取HTTP响应中的auth值
                random_num = random.random()
                url = f"http://{ip}/get_auth.cgi?num={random_num}"
                req = urllib.request.Request(url)
                
                try:
                    response = urllib.request.urlopen(req, timeout=self.connect_timeout)
                    http_response = response.read().decode('utf-8', errors='ignore')
                    
                    # 从HTTP响应中提取auth值
                    auth_match = re.search(r'"auth"\s*:\s*"([^"]+)"', http_response)
                    if auth_match:
                        auth_value = auth_match.group(1)
                        full_auth = auth_value + "4813494d137e1631bba301d5"
                        special_url = f"http://{ip}/?auth={full_auth}"
                        webbrowser.open(special_url)
                        if callback:
                            callback(ip, "K230认证", True, "")
                    else:
                        webbrowser.open(f"http://{ip}")
                        if callback:
                            callback(ip, "普通页面（未找到auth）", True, "")
                            
                except urllib.error.URLError as e:
                    webbrowser.open(f"http://{ip}")
                    if callback:
                        callback(ip, f"HTTP错误: {str(e)[:30]}", True, "")
                except socket.timeout:
                    webbrowser.open(f"http://{ip}")
                    if callback:
                        callback(ip, "HTTP超时", True, "")
                except Exception as e:
                    webbrowser.open(f"http://{ip}")
                    if callback:
                        callback(ip, f"错误: {str(e)[:30]}", True, "")
                        
            else:
                # 非K230设备，创建自动登录HTML文件
                safe_model = re.sub(r'[<>:"/\\|?*]', '_', model)
                if not safe_model or safe_model == "Unknown":
                    safe_model = "unknown_model"
                
                html_filename = f"canaan_avalon_miner_{safe_model}.html"
                
                html_content = f"""<html>
    <body>
      <form id="autoLoginForm" action="http://{ip}/dashboard.cgi" method="post">
        <input type="hidden" name="username" value="root">
        <input type="hidden" name="password" value="root">
      </form>
      <script>
        setTimeout(() => {{
          document.getElementById("autoLoginForm").submit();
        }}, 50);
      </script>
    </body>
    </html>"""
                
                # 写入HTML文件
                with open(html_filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                filepath = os.path.abspath(html_filename)
                webbrowser.open(f"file://{filepath}")
                if callback:
                    callback(ip, "自动登录页面", True, html_filename)
                    
        except Exception as e:
            error_msg = f"自动登录时出错: {str(e)}"
            if callback:
                callback(ip, "打开失败", False, error_msg)
