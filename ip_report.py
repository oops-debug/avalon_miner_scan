import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import re
from tkinter import TclError
import sys
import time
import os


# 需要在同一个IP段下修改
class IPReportManager:
    def __init__(self, root):

        self.root = root
        self.ip_report_window = None
        self.ip_reporting = False
        self.reported_ips = set()
        self.ip_report_data = []
        self.ip_report_status_var = tk.StringVar(value="请在下方设置目标IP段，然后点击'开始IP监听'")
        self.ip_report_button = None
        self.ip_report_tree = None

        # 新增静态IP配置相关属性
        self.target_ip_pool = []  # 目标IP池
        self.subnet_mask = ""  # 默认子网掩码
        self.gateway = ""  # 默认网关
        self.target_ip_seg = ""  # 默认目标IP段
        self.custom_ip_var = tk.BooleanVar(value=False)  # 自定义IP标识

    def toggle_ip_report_state(self):
        # 只显示IP上报页面，不自动开始监听
        # 监听由用户点击窗口中的"开始IP监听"按钮手动启动
        self.show_ip_report_page()

    def start_ip_report(self):
        """开始IP上报"""
        if self.ip_reporting:
            return

        ip_range = self.ip_range_var.get() if hasattr(self, 'ip_range_var') else self.target_ip_seg

        if not ip_range or ip_range.strip() == "":
            response = messagebox.askyesno("IP段为空", "目的IP段为空或未设置。是否继续只做监听（不分配目的IP）？")
            if not response:
                return  # 用户点击"否"，直接返回，不更新按钮

            self.target_ip_pool = []
            self.target_ip_seg = ""
        else:
            ip_pattern = r'^(\d+\.\d+\.\d+)\.(\d+)-(\d+)$'
            match = re.match(ip_pattern, ip_range)
            if not match:
                response = messagebox.askyesno("IP段格式错误",
                                               f"IP段格式应为: 192.168.1.1-255\n当前输入: {ip_range}\n\n是否继续只做监听（不分配目的IP）？")
                if not response:
                    return  # 用户点击"否"，直接返回，不更新按钮

                self.target_ip_pool = []
                self.target_ip_seg = ""
            else:
                prefix = match.group(1)
                start = int(match.group(2))
                end = int(match.group(3))

                if start < 0 or end > 255 or start > end:
                    response = messagebox.askyesno("IP范围错误",
                                                   f"IP范围应在0-255之间且起始<=结束\n当前范围: {start}-{end}\n\n是否继续只做监听（不分配目的IP）？")
                    if not response:
                        return  # 用户点击"否"，直接返回，不更新按钮

                    self.target_ip_pool = []
                    self.target_ip_seg = ""
                else:

                    self.target_ip_pool = [f"{prefix}.{i}" for i in range(start, end + 1)]
                    self.target_ip_seg = ip_range

        if hasattr(self, 'custom_ip_var') and self.custom_ip_var.get():

            if hasattr(self, 'subnet_var'):
                subnet_mask = self.subnet_var.get()
                if not self._is_valid_ipv4(subnet_mask):
                    messagebox.showerror("格式错误",
                                         f"子网掩码格式无效: {subnet_mask}\n应为IPv4地址格式，如: 255.255.255.0")
                    return  # 验证失败，直接返回，不更新按钮

            if hasattr(self, 'gateway_var'):
                gateway = self.gateway_var.get()
                if not self._is_valid_ipv4(gateway):
                    messagebox.showerror("格式错误", f"网关格式无效: {gateway}\n应为IPv4地址格式，如: 192.168.1.1")
                    return  # 验证失败，直接返回，不更新按钮

        # 所有验证通过后，才更新按钮文本和命令
        if self.ip_report_button and self.ip_report_button.winfo_exists():
            self.ip_report_button.config(text="停止IP监听", command=self.stop_ip_report)

        self.ip_reporting = True

        if self.target_ip_pool:
            self.ip_report_status_var.set(f"正在监听，等待IP上报... IP池: {len(self.target_ip_pool)}个IP")
        else:
            self.ip_report_status_var.set("正在监听（仅监听模式，不分配目的IP），等待IP上报...")

        self.ip_report_thread = threading.Thread(
            target=self._listen_udp_thread,
            daemon=True
        )
        self.ip_report_thread.start()

    def stop_ip_report(self):
        """停止IP上报"""
        if not self.ip_reporting:
            return
        
        self.ip_reporting = False
        # 更新按钮文本和命令
        if self.ip_report_button and self.ip_report_button.winfo_exists():
            self.ip_report_button.config(text="开始IP监听", command=self.start_ip_report)
        self.ip_report_status_var.set("IP上报已停止，UDP监听关闭")

    def copy_to_clipboard(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except TclError:
            messagebox.showwarning("复制失败", "无法访问剪贴板，请重试")

    def copy_ip_report_item(self, item, column_name):

        if not self.ip_report_tree or not self.ip_report_tree.winfo_exists():
            return
        values = self.ip_report_tree.item(item, 'values')
        if not values:
            return

        columns = ("序号", "IP地址", "设备类型", "MAC地址", "上报时间", "目的IP")
        try:
            col_index = columns.index(column_name)
            text = values[col_index]
            if text:
                self.copy_to_clipboard(text)
                self.ip_report_status_var.set(f"已复制{column_name}: {text}")
        except ValueError:
            self.ip_report_status_var.set("复制失败：列名不存在")

    def delete_ip_report_item(self, item):

        if not self.ip_report_tree or not self.ip_report_tree.winfo_exists():
            return
        values = self.ip_report_tree.item(item, 'values')
        if not values:
            return

        ip = values[1]
        if messagebox.askyesno("确认删除", f"确定要删除IP地址 {ip} 的上报记录吗？"):
            self.ip_report_tree.delete(item)
            for i, data in enumerate(self.ip_report_data):
                if data.get('ip') == ip:
                    self.ip_report_data.pop(i)
                    break
            self.ip_report_status_var.set(f"已删除IP地址 {ip} 的上报记录")

    def clear_ip_report(self):

        # 检查表格组件有效性
        if not self.ip_report_tree or not self.ip_report_tree.winfo_exists():
            self.ip_report_status_var.set("暂无记录可清空")
            return

        if not self.ip_report_tree.get_children():
            self.ip_report_status_var.set("暂无记录可清空")
            return

        if messagebox.askyesno("确认清空", "确定要清空所有IP上报记录吗？"):
            for item in self.ip_report_tree.get_children():
                self.ip_report_tree.delete(item)
            self.ip_report_data.clear()
            self.ip_report_status_var.set("已清空所有上报记录")

    def export_ip_report(self):

        if not self.ip_report_tree or not self.ip_report_tree.winfo_exists():
            messagebox.showwarning("导出失败", "没有可导出的IP上报记录")
            return

        if not self.ip_report_tree.get_children():
            messagebox.showwarning("导出失败", "没有可导出的IP上报记录")
            return

        try:
            filename = f"ip_report_{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.csv"

            with open(filename, 'w', newline='', encoding='utf-8') as f:
                headers = self.ip_report_tree["columns"]  # 自动同步移除后的列
                f.write(','.join(headers) + '\n')

                for item in self.ip_report_tree.get_children():
                    values = self.ip_report_tree.item(item, 'values')
                    escaped_values = ['"' + str(v).replace('"', '""') + '"' for v in values]
                    f.write(','.join(escaped_values) + '\n')

            messagebox.showinfo("导出成功", f"IP上报记录已导出到: {filename}")
            self.ip_report_status_var.set(f"已导出 {len(self.ip_report_tree.get_children())} 条记录到 {filename}")

        except Exception as e:
            messagebox.showerror("导出失败", f"导出文件时出错: {e}")

    def _listen_udp_thread(self):

        udp_socket = None
        try:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_socket.settimeout(1.0)
            udp_socket.bind(('0.0.0.0', 10002))

            self.ip_report_status_var.set("UDP监听已启动，请依次点击矿机的FUNC按钮")

            while self.ip_reporting:
                try:
                    data, addr = udp_socket.recvfrom(1024)

                    try:
                        decoded_data = data.decode('utf-8', errors='ignore')
                        print(f"decode={decoded_data}")
                    except:
                        decoded_data = str(data)

                    extracted_data = self._extract_ip_from_data(decoded_data)

                    if (extracted_data and extracted_data.get('ip') and
                            self.ip_reporting and
                            self.ip_report_window and self.ip_report_window.winfo_exists() and
                            self.ip_report_tree and self.ip_report_tree.winfo_exists()):
                        self.root.after(0, self._process_reported_ip, extracted_data, addr[0])

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.ip_reporting:
                        error_msg = f"UDP接收错误: {str(e)[:50]}"
                        self.root.after(0, lambda: self.ip_report_status_var.set(error_msg))

        except Exception as e:
            error_msg = f"UDP监听失败: {str(e)[:50]}"
            self.root.after(0, lambda: self.ip_report_status_var.set(error_msg))
            self.ip_reporting = False
            self.root.after(0, lambda: self.ip_report_button.config(
                text="开始IP监听") if self.ip_report_button and self.ip_report_button.winfo_exists() else None)
        finally:
            # 确保socket关闭
            if udp_socket:
                try:
                    udp_socket.close()
                except:
                    pass
            if self.ip_reporting is False:
                self.root.after(0, lambda: self.ip_report_status_var.set("UDP监听已停止"))

    def _is_valid_ipv4(self, ip_address):
        """验证IPv4地址格式"""
        if not ip_address:
            return False

        # IPv4地址正则表达式
        ip_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
        match = re.match(ip_pattern, ip_address)
        if not match:
            return False

        # 检查每个部分是否在0-255范围内
        for part in match.groups():
            try:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            except ValueError:
                return False

        return True

    def _extract_ip_from_data(self, data):
        """从数据中提取IP、device和mac信息"""
        result = {'ip': None, 'device': None, 'mac': None}

        # 提取IP地址
        ip_pattern = r'"ip"\s*:\s*"([^"]+)"'
        ip_match = re.search(ip_pattern, data)
        if ip_match:
            result['ip'] = ip_match.group(1)
        else:
            ip_pattern2 = r'ip[=:]\s*([\d.]+)'
            ip_match2 = re.search(ip_pattern2, data)
            if ip_match2:
                result['ip'] = ip_match2.group(1)

        # 提取device信息
        device_pattern = r'"device"\s*:\s*"([^"]+)"'
        device_match = re.search(device_pattern, data)
        if device_match:
            result['device'] = device_match.group(1)
        else:
            device_pattern2 = r'device[=:]\s*([^,\s]+)'
            device_match2 = re.search(device_pattern2, data)
            if device_match2:
                result['device'] = device_match2.group(1)

        # 提取mac信息
        mac_pattern = r'"mac"\s*:\s*"([^"]+)"'
        mac_match = re.search(mac_pattern, data)
        if mac_match:
            result['mac'] = mac_match.group(1)
        else:
            mac_pattern2 = r'mac[=:]\s*([^,\s]+)'
            mac_match2 = re.search(mac_pattern2, data)
            if mac_match2:
                result['mac'] = mac_match2.group(1)

        return result

    def _process_reported_ip(self, extracted_data, source_ip):
        """处理上报的IP地址（主线程执行）"""
        # 先检查表格和窗口有效性
        if (not self.ip_report_tree or not self.ip_report_tree.winfo_exists() or
                not self.ip_report_window or not self.ip_report_window.winfo_exists()):
            return

        ip_address = extracted_data.get('ip')
        if not ip_address:
            return

        if ip_address in self.reported_ips:
            return

        self.reported_ips.add(ip_address)
        # 仍传入source_ip，但表格中不再显示
        target_ip = self._add_to_ip_report_table(extracted_data, source_ip)

        self.ip_report_status_var.set(f"收的：源IP={ip_address},自动分配目的IP={target_ip}")

    def _add_to_ip_report_table(self, extracted_data, source_ip):
        """将上报数据添加到IP上报页面表格（移除来源IP列）"""
        # 核心检查：表格组件是否有效
        if not self.ip_report_tree or not self.ip_report_tree.winfo_exists():
            return ""

        ip_address = extracted_data.get('ip')
        device = extracted_data.get('device', '未知')
        mac = extracted_data.get('mac', '未知')

        # 分配目的IP
        target_ip = self.target_ip_pool.pop(0) if self.target_ip_pool else ""

        # 检查是否已存在相同IP（索引同步调整）
        for item in self.ip_report_tree.get_children():
            values = self.ip_report_tree.item(item, 'values')
            if values and len(values) > 1 and values[1] == ip_address:
                new_values = list(values)
                new_values[2] = device
                new_values[3] = mac
                new_values[4] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # 更新目的IP（索引调整为5）
                if len(new_values) > 5 and not new_values[5] and target_ip:
                    new_values[5] = target_ip
                self.ip_report_tree.item(item, values=tuple(new_values))
                return target_ip

        # 添加新行（移除source_ip，列索引同步调整）
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        item_id = self.ip_report_tree.insert("", "end", values=(
            str(len(self.ip_report_data) + 1),
            ip_address,
            device,
            mac,
            timestamp,
            target_ip  # 目的IP（索引5）
        ))

        # 数据存储中移除source_ip字段
        self.ip_report_data.append({
            'ip': ip_address,
            'device': device,
            'mac': mac,
            'timestamp': timestamp,
            'target_ip': target_ip
        })

        self.ip_report_tree.see(item_id)

        if self.ip_report_window and self.ip_report_window.winfo_exists():
            self.ip_report_status_var.set(f"已接收 {len(self.ip_report_data)} 条上报数据")
        return target_ip

    def overleap_target_ip(self):
        # 先检查表格有效性
        # if not self.ip_report_tree or not self.ip_report_tree.winfo_exists():
        #     messagebox.showwarning("组件无效", "表格组件已销毁，无法执行操作")
        #     return
        # # 不要超过IP池
        if self.target_ip_pool:
            overleap_ip = self.target_ip_pool.pop(0)
            # children = self.ip_report_tree.get_children()
            # if not children:
            #     messagebox.showwarning("无数据", "表格中暂无记录，无法修改")
            #     return
            # last_item = children[-1]
            # current_values = list(self.ip_report_tree.item(last_item, 'values'))
            # if len(current_values) >= 6:  # 确保列数足够
            #     current_values[5] = new_target_ip  # 目的IP列索引5
            #     # 3. 更新表格显示
            #     self.ip_report_tree.item(last_item, values=tuple(current_values))
            #     # 4. 同步ip_report_data数据列表
            #     if self.ip_report_data:
            #         last_data = self.ip_report_data[-1]
            #         last_data['target_ip'] = new_target_ip
            if self.target_ip_pool:
                new_target_ip = self.target_ip_pool[0]
                self.ip_report_status_var.set(f"已跳过{overleap_ip}，下一个目的IP为: {new_target_ip}")
            else:
                messagebox.showwarning("IP池空", "目标IP池已空，无法修改目的IP")

        else:
            messagebox.showwarning("IP池空", "目标IP池已空，无法修改目的IP")

    def center_window(self, window, width, height):
        """窗口居中显示"""
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")

    def toggle_custom_ip(self, subnet_entry, gateway_entry):
        if self.custom_ip_var.get():
            # 勾选：启用输入框
            subnet_entry.config(state='normal')
            gateway_entry.config(state='normal')
        else:
            # 不勾选：禁用输入框，还原默认值
            subnet_entry.config(state='disabled')
            gateway_entry.config(state='disabled')

    def get_mask_and_gateway(self, original_ip):
        """获取本机的子网掩码和网关"""
        # print("正在获取子网掩码和网关...")
        message = f"ascset|0,ip"

        def tcp_getip_thread():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(10)
                    s.connect((original_ip, 4028))
                    s.sendall(message.encode('utf-8'))
                    response = s.recv(1024).decode('utf-8').strip()
                    '''修复正则表达式，IP[S/D ]'''
                    pattern1 = r'IP\[(?:[SD]\s)?([\d.]+)\s+([\d.]+)\s+([\d.]+)\]'
                    match1 = re.search(pattern1, response)
                    if match1:
                        self.subnet_mask = match1.group(2)
                        self.gateway = match1.group(3)
                        # print(f"subnet_mask={self.subnet_mask}")
                        # print(f"gateway={self.gateway}")
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("发送失败", f"连接或发送错误: {str(e)}"))

        threading.Thread(target=tcp_getip_thread).start()
        # print(self.subnet_mask)
        # print(self.gateway)

    def send_static_ip_config(self, item):
        """发送静态IP配置到设备（调整列索引）"""
        # 检查表格有效性
        if not self.ip_report_tree or not self.ip_report_tree.winfo_exists():
            messagebox.showwarning("组件无效", "表格组件已销毁，无法执行操作")
            return
        values = self.ip_report_tree.item(item, 'values')
        if not values or len(values) < 6:  # 列数减少，索引调整
            messagebox.showwarning("数据错误", "选中行数据不完整")
            return

        original_ip = values[1]  # IP地址索引不变
        target_ip = values[5]  # 目的IP索引从6调整为5

        if not target_ip:
            messagebox.showwarning("缺少数据", "目的IP未分配，请先设置IP段")
            return
        if not self.custom_ip_var.get():
            if (not self.subnet_mask) | (not self.gateway):
                self.get_mask_and_gateway(original_ip)
        # 构建发送格式
        message = f"ascset|0,ip,s,{target_ip},{self.subnet_mask},{self.gateway}"

        # print(message)
        # 在新线程中发送TCP数据
        def tcp_send_thread():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(10)
                    s.connect((original_ip, 4028))
                    s.sendall(message.encode('utf-8'))
                    response = s.recv(1024).decode('utf-8').strip()

                    if "OK" in response:
                        self.root.after(0, lambda: self.mark_success(item))
                        self.root.after(0, lambda: messagebox.showinfo("发送成功", f"IP {original_ip} 配置已生效"))
                    else:
                        self.root.after(0, lambda: messagebox.showwarning("响应异常", f"收到非预期响应: {response}"))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("发送失败", f"连接或发送错误: {str(e)}"))

        threading.Thread(target=tcp_send_thread, daemon=True).start()

    def mark_success(self, item):
        """标记成功的行为绿色"""
        if self.ip_report_tree and self.ip_report_tree.winfo_exists():
            self.ip_report_tree.item(item, tags=("success",))
            self.ip_report_tree.tag_configure("success", background="#c4ecc4")

    def resource_path(self, relative_path):
        """
        获取资源的绝对路径，兼容开发环境和打包后的EXE环境
        :param relative_path: 相对路径，如 "imag/avalon.ico"
        :return: 资源的绝对路径
        """
        # 判断是否是打包后的EXE环境
        if hasattr(sys, '_MEIPASS'):
            # _MEIPASS 是pyinstaller创建的临时目录
            base_path = sys._MEIPASS
        else:
            # 开发环境，使用当前脚本所在目录
            base_path = os.path.abspath(".")

        # 拼接绝对路径
        return os.path.join(base_path, relative_path)

    def show_ip_report_page(self):
        """显示IP上报页面"""
        # 如果窗口已经存在且有效，直接返回
        if self.ip_report_window and self.ip_report_window.winfo_exists():
            self.ip_report_window.deiconify()  # 显示窗口
            self.ip_report_window.focus_set()   # 获取焦点
            return

        # 创建新的Toplevel窗口
        self.ip_report_window = tk.Toplevel(self.root)
        self.ip_report_window.title("Avalon批量设置静态IP工具 - by Avalon Support")
        self.center_window(self.ip_report_window, 900, 650)
        try:
            self.ip_report_window.iconbitmap("imag/avalon.ico")
        except:
            pass

        # 设置窗口属性
        self.ip_report_window.transient(self.root)  # 设置为父窗口的临时窗口
        self.ip_report_window.grab_set()  # 模态窗口

        main_frame = ttk.Frame(self.ip_report_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="静态IP设置", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))

        status_label = ttk.Label(main_frame, textvariable=self.ip_report_status_var)
        status_label.pack(pady=(0, 10))

        # 静态IP设置框架（放在状态标签下方）
        ip_settings_frame = ttk.LabelFrame(main_frame, text="静态IP设置", padding=10)
        ip_settings_frame.pack(fill=tk.X, pady=(0, 10))

        # 目标IP段输入
        ttk.Label(ip_settings_frame, text="目标IP段 (格式: 192.168.1.1-255)").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ip_range_var = tk.StringVar(value=self.target_ip_seg)
        ip_range_entry = ttk.Entry(ip_settings_frame, textvariable=self.ip_range_var, width=30)
        ip_range_entry.grid(row=0, column=1, pady=5, padx=(10, 0))

        # 自定义IP复选框
        custom_check = ttk.Checkbutton(ip_settings_frame, text="自定义子网掩码和网关", variable=self.custom_ip_var,
                                       command=lambda: self.toggle_custom_ip(subnet_entry, gateway_entry))
        custom_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        # 子网掩码输入
        ttk.Label(ip_settings_frame, text="子网掩码").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.subnet_var = tk.StringVar(value=self.subnet_mask)
        subnet_entry = ttk.Entry(ip_settings_frame, textvariable=self.subnet_var, width=30, state='disabled')
        subnet_entry.grid(row=2, column=1, pady=5, padx=(10, 0))

        # 网关输入
        ttk.Label(ip_settings_frame, text="网关").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.gateway_var = tk.StringVar(value=self.gateway)
        gateway_entry = ttk.Entry(ip_settings_frame, textvariable=self.gateway_var, width=30, state='disabled')
        gateway_entry.grid(row=3, column=1, pady=5, padx=(10, 0))

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.ip_report_button = ttk.Button(button_frame, text="开始IP监听", command=self.start_ip_report)
        self.ip_report_button.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="批量发送静态IP", command=self.batch_send_static_ip).pack(side=tk.LEFT,
                                                                                                padx=(0, 10))
        ttk.Button(button_frame, text="跳过IP", command=self.overleap_target_ip).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="清空记录", command=self.clear_ip_report).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="导出记录", command=self.export_ip_report).pack(side=tk.LEFT, padx=(0, 10))

        # 表格框架
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # 移除"来源IP"列，调整列顺序
        columns = ("序号", "IP地址", "设备类型", "MAC地址", "上报时间", "目的IP")
        self.ip_report_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        for col in columns:
            self.ip_report_tree.heading(col, text=col)

        # 调整列宽（移除来源IP后，其他列宽保持不变）
        column_widths = {
            "序号": 50,
            "IP地址": 120,
            "设备类型": 120,
            "MAC地址": 150,
            "上报时间": 150,
            "目的IP": 120
        }

        for col, width in column_widths.items():
            self.ip_report_tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.ip_report_tree.yview)
        self.ip_report_tree.configure(yscrollcommand=scrollbar.set)

        self.ip_report_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定关闭事件
        def on_closing():
            # 1. 停止IP上报线程
            if self.ip_reporting:
                self.stop_ip_report()
                # 短暂等待线程退出（避免阻塞主线程）
                self.root.update_idletasks()
                self.root.after(100, lambda: None)

            # 2. 清空所有待执行的after任务
            try:
                self.root.after_cancel(self.root.after(0, lambda: None))
            except:
                pass

            # 3. 销毁表格组件并重置引用
            if self.ip_report_tree and self.ip_report_tree.winfo_exists():
                try:
                    for item in self.ip_report_tree.get_children():
                        self.ip_report_tree.delete(item)
                except TclError:
                    pass
            self.ip_report_tree = None

            # 4. 清空数据
            self.reported_ips.clear()
            self.ip_report_data.clear()
            self.target_ip_pool.clear()
            self.ip_reporting = False

            # 5. 只关闭IP上报窗口，而不是整个程序
            self.ip_report_window.destroy()
            self.ip_report_window = None

        self.ip_report_window.protocol("WM_DELETE_WINDOW", on_closing)

        # 右键菜单
        def on_right_click(event):
            if not self.ip_report_tree or not self.ip_report_tree.winfo_exists():
                return
            item = self.ip_report_tree.identify_row(event.y)
            if item:
                menu = tk.Menu(self.ip_report_window, tearoff=0)
                menu.add_command(label="复制IP地址",
                                 command=lambda: self.copy_ip_report_item(item, "IP地址"))
                menu.add_command(label="复制MAC地址",
                                 command=lambda: self.copy_ip_report_item(item, "MAC地址"))
                menu.add_command(label="复制目的IP",
                                 command=lambda: self.copy_ip_report_item(item, "目的IP"))
                menu.add_separator()
                menu.add_command(label="删除记录",
                                 command=lambda: self.delete_ip_report_item(item))
                menu.add_command(label="发送静态IP配置",
                                 command=lambda: self.send_static_ip_config(item))
                menu.tk_popup(event.x_root, event.y_root)

        self.ip_report_tree.bind("<Button-3>", on_right_click)

        # 双击事件
        def on_double_click(event):
            if not self.ip_report_tree or not self.ip_report_tree.winfo_exists():
                return
            item = self.ip_report_tree.identify_row(event.y)
            if item:
                values = self.ip_report_tree.item(item, 'values')
                if values and len(values) > 1:
                    ip = values[1]
                    self.open_miner_page(ip)

        self.ip_report_tree.bind("<Double-1>", on_double_click)

    def open_miner_page(self, ip):
        """双击IP打开矿机页面（占位方法）"""
        messagebox.showinfo("提示", f"暂未实现打开矿机页面功能，IP：{ip}")

    def batch_send_static_ip(self):
        """批量发送静态IP配置到所有已分配目的IP的设备（调整列索引）"""
        # 检查表格有效性
        if not self.ip_report_tree or not self.ip_report_tree.winfo_exists():
            messagebox.showwarning("批量发送", "表格组件无效，无法执行批量发送")
            return
        items = self.ip_report_tree.get_children()
        if not items:
            messagebox.showwarning("批量发送", "没有可发送的记录")
            return

        total = 0
        success_count = 0
        fail_count = 0
        self.ip_report_status_var.set("开始批量发送静态IP配置...")

        def send_task():
            nonlocal total, success_count, fail_count
            for item in items:
                # 中途检查表格是否有效
                if not self.ip_report_tree or not self.ip_report_tree.winfo_exists():
                    break
                values = self.ip_report_tree.item(item, 'values')
                if not values or len(values) < 6:
                    continue  # 跳过数据不完整的行

                original_ip = values[1]
                target_ip = values[5]  # 目的IP索引调整为5
                if not target_ip:
                    continue  # 跳过未分配目的IP的行
                if not self.custom_ip_var.get():
                    # print("正在获取子网掩码和网关...")
                    if (not self.subnet_mask) | (not self.gateway):
                        self.get_mask_and_gateway(original_ip)
                        print(f"首次获取子网掩码{self.subnet_mask},{self.gateway}")
                time.sleep(0.1)  # 短暂延时，避免过快发送
                total += 1
                try:
                    # 复用发送逻辑
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(5)
                        s.connect((original_ip, 4028))
                        message = f"ascset|0,ip,s,{target_ip},{self.subnet_mask},{self.gateway}"
                        print(f"message:{message}")
                        s.sendall(message.encode('utf-8'))
                        response = s.recv(1024).decode('utf-8').strip()
                        print(f"response:{response}")
                        if "OK" in response:
                            success_count += 1
                            self.root.after(0, lambda i=item: self.mark_success(i))

                        else:
                            fail_count += 1
                except:
                    fail_count += 1

            # 发送完成后更新状态
            result_msg = f"批量发送完成: 总{total} 成功{success_count} 失败{fail_count}"
            self.root.after(0, lambda: self.ip_report_status_var.set(result_msg))
            self.root.after(0, lambda: messagebox.showinfo("批量发送结果", result_msg))

        threading.Thread(target=send_task, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = IPReportManager(root)
    app.show_ip_report_page()
    root.mainloop()
