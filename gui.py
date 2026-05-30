"""
主GUI模块
包含MinerScannerGUI类和用户界面
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import sys
import webbrowser
import re
from datetime import datetime

# 导入自定义模块
import ConnectionManager
from ip_report import IPReportManager
from log_viewer import AvalonMinerViewer
from ip_manager import IPManager
from network_scanner import NetworkScanner
from miner_operations import MinerOperations
from utils import parse_ip_segments, validate_ip_segment_format


class MinerScannerGUI:
    """矿机扫描工具主GUI类"""
    
    def __init__(self, root):
        self.root = root
        self.ip_report_manager = IPReportManager(self.root)
        self.root.title("Avalon矿机扫描工具 V1.0.5 2026/2/9")
        self.root.geometry("1500x700")
        
        # 设置图标
        try:
            self.root.iconbitmap("imag/avalon.ico")
        except:
            pass
        
        # 初始化管理器
        self.ip_manager = IPManager()
        self.network_scanner = NetworkScanner(ConnectionManager.ConnectionManager())
        self.miner_operations = MinerOperations()
        
        # 扫描状态变量
        self.scanning = False
        
        # 存储完整响应数据
        self.full_responses = {}
        
        # 存储选中状态 {item_id: (ip, selected)}
        self.selection_states = {}
        
        # ALL标题栏状态：False=全不选，True=全选
        self.all_selected = False
        
        # 存储IP到item_id的映射，用于避免重复添加
        self.ip_to_item = {}
        
        # 存储当前表格中的IP集合，用于快速查找
        self.existing_ips = set()
        
        # 排序方向存储，True为升序，False为降序
        self.sort_directions = {}
        
        # 存储序号计数器
        self.row_counter = 1
        
        # 扫描统计
        self.success_count = 0
        self.fail_count = 0
        
        # 设置UI
        self.setup_ui()
        
        # 绑定右键菜单
        self.tree.bind("<Button-3>", self.on_right_click)
        
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.resizable(True, True)
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="Avalon矿机扫描工具", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))
        
        # 网络设置框架
        network_frame = ttk.LabelFrame(main_frame, text="网络设置", padding="10")
        network_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        network_frame.columnconfigure(1, weight=1)
        
        # IP段显示框
        ip_segments_frame = ttk.LabelFrame(network_frame, text="IP段列表", padding="5")
        ip_segments_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.N, tk.S, tk.E), padx=(0, 550), pady=(0, 5))
        ip_segments_frame.columnconfigure(0, weight=1)
        ip_segments_frame.rowconfigure(0, weight=1)
        
        # 添加全选复选框
        self.select_all_ipseg_var = tk.BooleanVar(value=False)
        select_all_checkbox = ttk.Checkbutton(
            ip_segments_frame, 
            text="全选", 
            variable=self.select_all_ipseg_var,
            command=self.toggle_select_all_ipsegments
        )
        select_all_checkbox.grid(row=0, column=5, sticky=(tk.W, tk.N), padx=5, pady=2)
        
        # 创建Canvas和Scrollbar
        canvas = tk.Canvas(ip_segments_frame, height=80)
        scrollbar = ttk.Scrollbar(ip_segments_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.ip_segments_canvas = canvas
        
        # 创建内部框架来容纳复选框
        self.ip_segments_inner_frame = ttk.Frame(canvas)
        self.ip_segments_inner_frame_id = canvas.create_window((0, 0), window=self.ip_segments_inner_frame, anchor=tk.NW)
        
        # 配置Canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 配置网格权重
        ip_segments_frame.columnconfigure(0, weight=1)
        ip_segments_frame.rowconfigure(0, weight=1)
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 存储IP段复选框状态
        self.ip_segment_vars = []
        self.ip_segment_checkbuttons = []
        
        # 更新IP段显示
        self.update_ip_segments_display()
        
        # 在右侧添加按钮
        self.add_ip_segment_button = ttk.Button(
            ip_segments_frame,
            text="IP段管理", 
            command=self.open_add_ip_segment_dialog
        )
        self.add_ip_segment_button.grid(row=0, column=5, sticky=(tk.E, tk.N), padx=(10, 2), pady=(30, 0))
        
        self.ip_report_button = ttk.Button(network_frame, text="批量修改IP", command=self.ip_report_manager.toggle_ip_report_state)
        self.ip_report_button.grid(row=0, column=5, sticky=(tk.E, tk.N), padx=(10, 2), pady=(1, 1))
        
        self.settings_button = ttk.Button(network_frame, text="设置", command=self.open_settings)
        self.settings_button.grid(row=0, column=5, sticky=(tk.E), padx=(10, 2), pady=(1, 1))
        
        # 设置变量
        self.connect_timeout = tk.StringVar(value="2")
        self.read_timeout = tk.StringVar(value="3")
        self.threads = tk.StringVar(value="50")
        self.retry_count = tk.StringVar(value="1")
        
        # 控制按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.scan_button = ttk.Button(button_frame, text="开始扫描", command=self.toggle_scan)
        self.scan_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="导出表格", command=self.export_results).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="导出日志", command=self.download_all_details).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="删除选中", command=self.delete_selected).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(button_frame, text="点灯", command=self.control_selected_leds).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(button_frame, text="关灯", command=self.control_selected_leds_off).pack(side=tk.LEFT, padx=(10, 0))
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N), pady=(0, 0))
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=4, column=0, columnspan=3, sticky=tk.W)
        
        # 结果表格框架
        results_frame = ttk.LabelFrame(main_frame,
                                       text="扫描结果 - 只显示成功连接的矿机 (左键点击序号更新信息，左键点击IP自动打开管理界面，右键点击IP查看更多选项)",
                                       padding="5")
        results_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(25, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # 创建表格
        columns = ("ALL", "NO", "IP", "MODEL", "VERSION", "DNA", "MAC", "TIME", "Elapsed", "GHSspd", "HASH0", "HASH1",
                   "HASH2", "HASH3", "CPU")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题
        self.tree.heading("ALL", text="ALL", command=self.on_all_header_click)
        self.tree.heading("NO", text="NO", command=lambda: self.sort_by_column("NO", True))
        
        # 设置其他列标题
        for col in columns[2:]:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c, True))
        
        # 设置列宽
        column_widths = {
            "ALL": 30,
            "NO": 30,
            "IP": 100,
            "MODEL": 50,
            "VERSION": 70,
            "DNA": 120,
            "MAC": 100,
            "TIME": 120,
            "Elapsed": 100,
            "GHSspd": 100,
            "HASH0": 100,
            "HASH1": 100,
            "HASH2": 100,
            "HASH3": 100,
            "CPU": 50,
        }
        
        for col, width in column_widths.items():
            self.tree.column(col, width=width)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 绑定单击事件
        self.tree.bind("<Button-1>", self.on_cell_click)
        
        # 统计信息
        stats_frame = ttk.Frame(main_frame)
        stats_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        self.stats_var = tk.StringVar(value="总计: 0 | 成功: 0 | 失败: 0")
        ttk.Label(stats_frame, textvariable=self.stats_var).pack(side=tk.LEFT)
        
        # 选中统计
        self.selection_stats_var = tk.StringVar(value="已选中: 0")
        ttk.Label(stats_frame, textvariable=self.selection_stats_var).pack(side=tk.LEFT, padx=(20, 0))
        
        self.stats_ver = tk.StringVar(value="by Avalon Support")
        ttk.Label(stats_frame, textvariable=self.stats_ver).pack(side=tk.RIGHT)
        
        # 存储扫描结果
        self.results = []
        
    def toggle_select_all_ipsegments(self):
        """全选或取消全选所有IP段"""
        select_all = self.select_all_ipseg_var.get()
        for var in self.ip_segment_vars:
            var.set(select_all)
    
    def on_all_header_click(self):
        """点击ALL标题栏时切换全选/全不选状态"""
        if self.all_selected:
            self.deselect_all()
            self.all_selected = False
        else:
            self.select_all()
            self.all_selected = True
    
    def sort_by_column(self, column, initial_ascending=False):
        """按列排序表格数据"""
        if column not in self.sort_directions:
            self.sort_directions[column] = initial_ascending
        else:
            self.sort_directions[column] = not self.sort_directions[column]
        
        ascending = self.sort_directions[column]
        
        items = list(self.tree.get_children())
        if not items:
            return
        
        columns = self.tree["columns"]
        try:
            col_index = columns.index(column)
        except ValueError:
            return
        
        rows = []
        for item in items:
            values = self.tree.item(item, 'values')
            if len(values) > col_index:
                cell_value = values[col_index]
                rows.append((item, cell_value, values))
        
        # 特殊处理IP列
        if column == "IP":
            def ip_key_func(item_data):
                item, cell_value, values = item_data
                try:
                    parts = cell_value.split('.')
                    if len(parts) == 4:
                        return tuple(int(part) for part in parts)
                except (ValueError, AttributeError):
                    pass
                return (999, 999, 999, 999)
            
            rows.sort(key=ip_key_func, reverse=not ascending)
        
        # 特殊处理NO列
        elif column == "NO":
            def no_key_func(item_data):
                item, cell_value, values = item_data
                try:
                    return int(cell_value)
                except (ValueError, TypeError):
                    return float('inf')
            
            rows.sort(key=no_key_func, reverse=not ascending)
        
        # 其他列
        else:
            def default_key_func(item_data):
                item, cell_value, values = item_data
                return str(cell_value).lower() if cell_value else ""
            
            rows.sort(key=default_key_func, reverse=not ascending)
        
        # 重新插入行
        for i, (item, cell_value, values) in enumerate(rows):
            self.tree.move(item, "", i)
            new_values = list(values)
            new_values[1] = values[1]
            self.tree.item(item, values=new_values)
        
        direction_text = "升序" if ascending else "降序"
        self.status_var.set(f"已按 {column} 列 {direction_text} 排序")
    
    def on_cell_click(self, event):
        """处理单元格点击事件"""
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        if not item:
            return
        
        columns = self.tree["columns"]
        col_index = int(column[1:]) - 1
        col_name = columns[col_index] if col_index < len(columns) else ""
        
        values = self.tree.item(item, 'values')
        cell_value = values[col_index] if col_index < len(values) else ""
        
        # 第一列（ALL列）特殊处理
        if col_name == "ALL":
            self.toggle_selection(item)
            return "break"
        elif col_name == "NO":
            if event.num == 1:
                # 从values[2]获取IP地址，而不是使用cell_value（序号）
                ip_address = values[2] if len(values) > 2 else ""
                if ip_address:
                    self.update_miner_info(ip_address, item)
                else:
                    self.status_var.set("无法获取IP地址")
            return "break"
        elif col_name == "IP":
            if event.num == 1:
                self.open_miner_page(cell_value)
            return "break"
        else:
            if cell_value and cell_value != "获取失败":
                self.copy_to_clipboard(cell_value)
                self.status_var.set(f"已复制: {cell_value}")
            return "break"
    
    def on_right_click(self, event):
        """右键点击事件处理"""
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        if not item:
            return
        
        columns = self.tree["columns"]
        col_index = int(column[1:]) - 1
        col_name = columns[col_index] if col_index < len(columns) else ""
        
        values = self.tree.item(item, 'values')
        cell_value = values[col_index] if col_index < len(values) else ""
        
        # 如果是IP列，打开右键菜单
        if col_name == "IP" and cell_value:
            ip = cell_value
            
            model = values[3] if len(values) > 3 else "Unknown"
            version = values[4] if len(values) > 4 else "Unknown"
            dna = values[5] if len(values) > 5 else "Unknown"
            scan_time = values[7] if len(values) > 7 else "Unknown"
            hash0_sn = values[10] if len(values) > 10 else "Unknown"
            hash1_sn = values[11] if len(values) > 11 else "Unknown"
            hash2_sn = values[12] if len(values) > 12 else "Unknown"
            hash3_sn = values[13] if len(values) > 13 else "Unknown"
            cpu_info = values[14] if len(values) > 14 else ""
            
            # 创建右键菜单
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_separator()
            menu.add_command(label="日志可视化",
                             command=lambda: self.open_log_viewer(ip))
            menu.add_command(label="显示完整日志",
                             command=lambda: self.show_response_details(
                                 ip, model, version, dna, scan_time,
                                 hash0_sn, hash1_sn, hash2_sn, hash3_sn, cpu_info))
            menu.add_separator()
            # 添加关灯和查询灯状态选项
            menu.add_command(label="关灯",
                             command=lambda: self.control_led(ip, "off", item))
            menu.add_command(label="查询灯状态",
                             command=lambda: self.query_led_status(ip))
            menu.add_separator()
            
            # 显示菜单
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
            return "break"
    
    def toggle_selection(self, item):
        """切换项的选中状态"""
        values = self.tree.item(item, 'values')
        ip = values[2]  # 第三列是IP
        
        # 获取当前选中状态
        current_state = values[0] if len(values) > 0 else "□"
        
        # 切换状态
        if current_state == "□":
            new_state = "✓"
        else:
            new_state = "□"
        
        # 更新存储的状态
        self.selection_states[item] = (ip, new_state == "✓")
        
        # 更新表格显示
        new_values = list(values)
        new_values[0] = new_state
        self.tree.item(item, values=new_values)
        
        # 更新选中统计
        self.update_selection_stats()
        
        # 更新全选状态
        self.update_all_selected_state()
    
    def select_all(self):
        """全选所有机器"""
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values:
                ip = values[2]
                new_values = list(values)
                new_values[0] = "✓"
                self.tree.item(item, values=new_values)
                self.selection_states[item] = (ip, True)
        
        self.update_selection_stats()
        self.all_selected = True
    
    def deselect_all(self):
        """取消所有选择"""
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values:
                ip = values[2]
                new_values = list(values)
                new_values[0] = "□"
                self.tree.item(item, values=new_values)
                self.selection_states[item] = (ip, False)
        
        self.update_selection_stats()
        self.all_selected = False
    
    def update_all_selected_state(self):
        """更新全选状态"""
        all_selected = True
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values and len(values) > 0 and values[0] != "✓":
                all_selected = False
                break
        
        self.all_selected = all_selected
    
    def update_selection_stats(self):
        """更新选中统计"""
        selected_count = 0
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values and len(values) > 0 and values[0] == "✓":
                selected_count += 1
        
        self.selection_stats_var.set(f"已选中: {selected_count}")
    
    def update_miner_info(self, ip, item):
        """更新指定矿机的信息"""
        try:
            connect_timeout = float(self.connect_timeout.get())
            read_timeout = float(self.read_timeout.get())
            retry_count = int(self.retry_count.get())
        except ValueError:
            messagebox.showerror("输入错误", "超时或重试次数设置无效")
            return
        
        self.status_var.set(f"正在更新 {ip} 的信息...")
        
        # 设置矿机操作的超时时间
        self.miner_operations.connect_timeout = connect_timeout
        self.miner_operations.read_timeout = read_timeout
        
        # 调用矿机操作模块
        self.miner_operations.update_miner_info(ip, 
            callback=lambda ip, model, version, dna, mac, scan_time, elapsed_time, 
                           hashrate, hash_sn_list, cpu_info, response, success, error_msg: 
                self._update_miner_info_callback(ip, model, version, dna, mac, scan_time, 
                                                elapsed_time, hashrate, hash_sn_list, cpu_info, 
                                                response, success, error_msg, item))
    
    def _update_miner_info_callback(self, ip, model, version, dna, mac, scan_time, elapsed_time,
                                   hashrate, hash_sn_list, cpu_info, response, success, error_msg, item):
        """更新矿机信息的回调函数"""
        if success:
            # 获取当前选中状态和序号
            current_values = self.tree.item(item, 'values')
            current_selection = "□"
            current_no = "1"
            if current_values and len(current_values) > 0:
                current_selection = current_values[0]
                current_no = current_values[1]
            
            # 更新表格中的值
            self.tree.item(item, values=(
                current_selection,
                current_no,
                ip, model, version, dna, mac, scan_time, elapsed_time,
                hashrate,
                hash_sn_list[0], hash_sn_list[1], hash_sn_list[2], hash_sn_list[3],
                cpu_info
            ))
            
            # 更新存储的完整响应
            self.full_responses[ip] = response
            
            self.status_var.set(f"已更新 {ip} 的信息")
        else:
            self.status_var.set(f"更新 {ip} 失败: {error_msg}")
    
    def toggle_scan(self):
        """切换扫描状态"""
        if self.scanning:
            self.stop_scan()
        else:
            self.start_scan()
    
    def start_scan(self):
        """开始扫描"""
        try:
            connect_timeout = float(self.connect_timeout.get())
            read_timeout = float(self.read_timeout.get())
            max_workers = int(self.threads.get())
            retry_count = int(self.retry_count.get())
            
            # 获取启用的IP段内容
            ip_segments_text = self.get_enabled_ip_segments()
            if not ip_segments_text:
                messagebox.showerror("输入错误", "请至少启用一个IP段")
                return
            
            # 验证重试次数
            if retry_count < 0 or retry_count > 10:
                messagebox.showerror("输入错误", "重试次数必须在0-10之间")
                return
            
            self.scanning = True
            self.scan_button.config(text="停止扫描")
            self.progress['value'] = 0
            
            # 设置网络扫描器的超时时间
            self.network_scanner.connect_timeout = connect_timeout
            self.network_scanner.read_timeout = read_timeout
            
            # 开始扫描
            success, message = self.network_scanner.start_scan(
                ip_segments_text, connect_timeout, read_timeout, max_workers, retry_count,
                callback=self._scan_callback,
                progress_callback=self._scan_progress_callback
            )
            
            if not success:
                messagebox.showerror("扫描错误", message)
                self.scanning = False
                self.scan_button.config(text="开始扫描")
            else:
                self.status_var.set(message)
                
        except ValueError:
            messagebox.showerror("输入错误", "请检查所有设置，确保它们是有效的数字")
            self.scanning = False
            self.scan_button.config(text="开始扫描")
    
    def _scan_callback(self, ip, model, version, dna, mac, scan_time, elapsed_time, 
                      hashrate, hash_sn_list, cpu_info, response, 
                      completed_count=None, success_count=None, total_duration=None, 
                      overall_speed=None, success_rate=None):
        """扫描回调函数"""
        if ip is not None:
            # 单个矿机扫描结果
            self.add_to_tree(ip, model, version, dna, mac, scan_time, elapsed_time,
                            hashrate, hash_sn_list, cpu_info, response)
        else:
            # 扫描完成
            self.scanning = False
            self.scan_button.config(text="开始扫描")
            
            if completed_count is not None:
                current_ip_count = len(self.existing_ips)
                self.status_var.set(
                    f"扫描完成! 总计: {completed_count} IP | 成功: {success_count} | 失败: {completed_count - success_count} | "
                    f"成功率: {success_rate:.1f}% | 平均速度: {overall_speed:.1f} IP/秒 | "
                    f"总耗时: {total_duration:.1f}秒")
    
    def _scan_progress_callback(self, completed, total_ips, ips_per_second=None, estimated_remaining_time=None):
        """扫描进度回调函数"""
        self.progress['value'] = completed
        self.progress['maximum'] = total_ips
        
        if ips_per_second is not None and estimated_remaining_time is not None:
            self.status_var.set(f"扫描中... 速度: {ips_per_second:.1f} IP/秒, 预计剩余: {estimated_remaining_time:.0f}秒")
        else:
            self.status_var.set(f"扫描中... 已完成: {completed}/{total_ips}")
    
    def stop_scan(self):
        """停止扫描"""
        success, message = self.network_scanner.stop_scan()
        self.scanning = False
        self.scan_button.config(text="开始扫描")
        self.status_var.set(message)
    
    def add_to_tree(self, ip, model, version, dna, mac, scan_time, elapsed_time, hashrate, hash_sn_list, cpu_info, response):
        """向表格添加一行数据"""
        # 检查IP是否已经存在
        if ip in self.existing_ips:
            item_id = self.ip_to_item.get(ip)
            if item_id:
                current_values = self.tree.item(item_id, 'values')
                current_selection = "□"
                current_no = "1"
                if current_values and len(current_values) > 0:
                    current_selection = current_values[0]
                    current_no = current_values[1]
                
                self.tree.item(item_id, values=(
                    current_selection,
                    current_no,
                    ip, model, version, dna, mac, scan_time, elapsed_time,
                    hashrate,
                    hash_sn_list[0], hash_sn_list[1], hash_sn_list[2], hash_sn_list[3],
                    cpu_info
                ))
                
                self.full_responses[ip] = response
                self.status_var.set(f"已更新IP: {ip}")
                self.tree.see(item_id)
            return
        
        # IP不存在，添加新行
        item_id = self.tree.insert("", "end", values=(
            "□",
            str(self.row_counter),
            ip, model, version, dna, mac, scan_time, elapsed_time,
            hashrate,
            hash_sn_list[0], hash_sn_list[1], hash_sn_list[2], hash_sn_list[3],
            cpu_info
        ))
        
        self.ip_to_item[ip] = item_id
        self.existing_ips.add(ip)
        self.row_counter += 1
        self.full_responses[ip] = response
        self.tree.see(item_id)
        self.status_var.set(f"已添加新IP: {ip}")
        
        # 更新统计
        self.update_stats()
    
    def update_stats(self):
        """更新统计信息"""
        current_ip_count = len(self.existing_ips)
        self.stats_var.set(f"总计: {current_ip_count} | 成功: {self.success_count} | 失败: {self.fail_count}")
    
    def open_miner_page(self, ip):
        """打开矿机管理页面"""
        # 获取该IP的CPU信息和型号
        cpu_info = ""
        model = ""
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values and len(values) > 2 and values[2] == ip:
                if len(values) > 3:
                    model = values[3]
                if len(values) > 14:
                    cpu_info = values[14]
                break
        
        # 调用矿机操作模块
        self.miner_operations.open_miner_page(ip, model, cpu_info,
            callback=lambda ip, action, success, message: 
                self._open_miner_page_callback(ip, action, success, message))
    
    def _open_miner_page_callback(self, ip, action, success, message):
        """打开矿机页面的回调函数"""
        if success:
            self.status_var.set(f"已打开 {ip} 的矿机页面")
        else:
            self.status_var.set(f"打开 {ip} 页面失败: {message}")
    
    def control_led(self, ip, action, item=None):
        """控制矿机LED灯开关"""
        # 调用矿机操作模块
        self.miner_operations.control_led(ip, action,
            callback=lambda ip, action_name, result, response: 
                self._control_led_callback(ip, action_name, result, response, item))
    
    def _control_led_callback(self, ip, action_name, result, response, item=None):
        """控制LED灯的回调函数"""
        status_text = f"{ip} {action_name} {result}"
        self.status_var.set(status_text)
        
        if action_name == "点灯" and result == "成功" and item:
            self.tree.tag_configure('success', background='#90EE90')
            self.tree.item(item, tags=('success',))
            self.status_var.set(f"{ip} 点灯成功，IP行已标记为绿色")
            self.root.after(60000, lambda i=item: self._restore_row_color(i))
        elif action_name == "关灯" and result == "成功" and item:
            current_tags = self.tree.item(item, 'tags')
            if 'success' in current_tags:
                self._restore_row_color(item)
                self.status_var.set(f"{ip} 关灯成功，绿色行已恢复颜色")
            else:
                self.status_var.set(f"{ip} 关灯成功")
    
    def _restore_row_color(self, item):
        """恢复行的原始颜色"""
        try:
            self.tree.item(item, tags=())
            values = self.tree.item(item, 'values')
            if values and len(values) > 2:
                ip = values[2]
                self.status_var.set(f"{ip} 行颜色已恢复")
        except:
            pass
    
    def query_led_status(self, ip):
        """查询矿机LED灯状态"""
        # 调用矿机操作模块
        self.miner_operations.query_led_status(ip,
            callback=lambda ip, status, response: 
                self._query_led_status_callback(ip, status, response))
    
    def _query_led_status_callback(self, ip, status, response):
        """查询LED灯状态的回调函数"""
        self.status_var.set(f"{ip} 灯状态: {status}")
        
        # 创建自动关闭的提示窗口
        popup = tk.Toplevel(self.root)
        popup.title("灯状态查询")
        popup.geometry("500x200")
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (500 // 2)
        y = (popup.winfo_screenheight() // 2) - (200 // 2)
        popup.geometry(f"500x200+{x}+{y}")
        popup.overrideredirect(True)
        popup.configure(bg="#2196F3")
        popup.attributes("-topmost", True)
        
        label = tk.Label(popup, text=f"矿机IP: {ip}\n灯状态: {status}",
                         bg="#2196F3", fg="white",
                         font=("Microsoft YaHei", 12))
        label.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        response_text = response[:100] + "..." if len(response) > 100 else response
        response_label = tk.Label(popup, text=f"响应: {response_text}",
                                  bg="#2196F3", fg="white",
                                  font=("Microsoft YaHei", 10))
        response_label.pack(pady=(0, 10))
        
        popup.after(3000, popup.destroy)
    
    def open_log_viewer(self, ip):
        """打开日志查看器并填充指定IP"""
        try:
            log_window = tk.Toplevel(self.root)
            AvalonMinerViewer(log_window, miner_ip=ip)
        except Exception as e:
            messagebox.showerror("错误", f"打开日志查看器失败: {str(e)}")
    
    def show_response_details(self, ip, model, version, dna, scan_time, hash0_sn, hash1_sn, hash2_sn, hash3_sn, cpu_info):
        """显示详细的响应信息窗口"""
        if ip not in self.full_responses:
            messagebox.showinfo("日志信息", f"没有找到 {ip} 的完整日志信息")
            return
        
        response = self.full_responses[ip]
        
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"矿机完整日志 - {ip}")
        detail_window.geometry("800x600")
        
        try:
            detail_window.iconbitmap("imag/avalon.ico")
        except:
            pass
        
        detail_window.transient(self.root)
        detail_window.grab_set()
        
        # 创建文本区域
        text_area = scrolledtext.ScrolledText(detail_window, wrap=tk.WORD, width=80, height=30)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 插入信息
        info_text = f"""矿机IP: {ip}
型号: {model}
版本: {version}
DNA: {dna}
扫描时间: {scan_time}
HASH0 SN: {hash0_sn}
HASH1 SN: {hash1_sn}
HASH2 SN: {hash2_sn}
HASH3 SN: {hash3_sn}
CPU: {cpu_info}

{'='*50}
完整响应信息:
{'='*50}

{response}
"""
        text_area.insert(tk.END, info_text)
        text_area.config(state=tk.DISABLED)
        
        # 添加关闭按钮
        close_button = ttk.Button(detail_window, text="关闭", command=detail_window.destroy)
        close_button.pack(pady=(0, 10))
    
    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
    
    def control_selected_leds(self):
        """控制选中矿机的LED灯"""
        selected_ips = []
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values and len(values) > 0 and values[0] == "✓":
                ip = values[2]
                selected_ips.append((ip, item))
        
        if not selected_ips:
            messagebox.showinfo("提示", "请先选择要操作的矿机")
            return
        
        # 批量点灯
        for ip, item in selected_ips:
            self.control_led(ip, "on", item)
        
        self.status_var.set(f"已为 {len(selected_ips)} 台矿机发送点灯指令")

    def control_selected_leds_off(self):
        """控制选中矿机的LED灯关闭"""
        selected_ips = []
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values and len(values) > 0 and values[0] == "✓":
                ip = values[2]
                selected_ips.append((ip, item))
        
        if not selected_ips:
            messagebox.showinfo("提示", "请先选择要操作的矿机")
            return
        
        # 批量关灯
        for ip, item in selected_ips:
            self.control_led(ip, "off", item)
        
        self.status_var.set(f"已为 {len(selected_ips)} 台矿机发送关灯指令")

    def delete_selected(self):
        """删除选中的矿机"""
        selected_items = []
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values and len(values) > 0 and values[0] == "✓":
                selected_items.append(item)
        
        if not selected_items:
            messagebox.showinfo("提示", "请先选择要删除的矿机")
            return
        
        # 确认删除
        if not messagebox.askyesno("确认删除", f"确定要删除 {len(selected_items)} 台矿机吗？"):
            return
        
        # 删除选中的项
        for item in selected_items:
            values = self.tree.item(item, 'values')
            if values and len(values) > 2:
                ip = values[2]
                if ip in self.existing_ips:
                    self.existing_ips.remove(ip)
                if ip in self.ip_to_item:
                    del self.ip_to_item[ip]
                if ip in self.full_responses:
                    del self.full_responses[ip]
                if item in self.selection_states:
                    del self.selection_states[item]
            
            self.tree.delete(item)
        
        # 重新编号
        self.reorder_rows()
        
        self.status_var.set(f"已删除 {len(selected_items)} 台矿机")
        self.update_stats()
        self.update_selection_stats()
    
    def reorder_rows(self):
        """重新为表格行编号"""
        items = self.tree.get_children()
        self.row_counter = 1
        
        for i, item in enumerate(items):
            values = self.tree.item(item, 'values')
            if values:
                new_values = list(values)
                new_values[1] = str(self.row_counter)
                self.tree.item(item, values=new_values)
                self.row_counter += 1
    
    def clear_results(self):
        """清空所有结果"""
        if not messagebox.askyesno("确认清空", "确定要清空所有扫描结果吗？"):
            return
        
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 重置状态
        self.existing_ips.clear()
        self.ip_to_item.clear()
        self.full_responses.clear()
        self.selection_states.clear()
        self.row_counter = 1
        self.success_count = 0
        self.fail_count = 0
        
        self.status_var.set("已清空所有结果")
        self.update_stats()
        self.update_selection_stats()
    
    def export_results(self):
        """导出结果到CSV文件"""
        if not self.existing_ips:
            messagebox.showinfo("提示", "没有可导出的数据")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scan_results_{timestamp}.csv"
            
            with open(filename, 'w', encoding='utf-8-sig') as f:
                # 写入标题行
                headers = ["序号", "IP", "型号", "版本", "DNA", "MAC", "扫描时间", "运行时间", "算力", 
                          "HASH0 SN", "HASH1 SN", "HASH2 SN", "HASH3 SN", "CPU"]
                f.write(",".join(headers) + "\n")
                
                # 写入数据行
                for item in self.tree.get_children():
                    values = self.tree.item(item, 'values')
                    if values and len(values) >= 15:
                        row_data = [
                            values[1],  # NO
                            values[2],  # IP
                            values[3],  # MODEL
                            values[4],  # VERSION
                            values[5],  # DNA
                            values[6],  # MAC
                            values[7],  # TIME
                            values[8],  # Elapsed
                            values[9],  # GHSspd
                            values[10], # HASH0
                            values[11], # HASH1
                            values[12], # HASH2
                            values[13], # HASH3
                            values[14]  # CPU
                        ]
                        # 处理可能包含逗号的值
                        row_data = [f'"{value}"' if ',' in str(value) else str(value) for value in row_data]
                        f.write(",".join(row_data) + "\n")
            
            self.status_var.set(f"结果已导出到 {filename}")
            messagebox.showinfo("导出成功", f"结果已成功导出到 {filename}")
            
        except Exception as e:
            messagebox.showerror("导出失败", f"导出结果时出错: {str(e)}")
    
    def download_all_details(self):
        """下载所有矿机的详细日志"""
        if not self.full_responses:
            messagebox.showinfo("提示", "没有可导出的日志数据")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"miner_details_{timestamp}"
            os.makedirs(folder_name, exist_ok=True)
            
            saved_count = 0
            for ip, response in self.full_responses.items():
                # 获取矿机型号
                model = "Unknown"
                for item in self.tree.get_children():
                    values = self.tree.item(item, 'values')
                    if values and len(values) > 2 and values[2] == ip:
                        if len(values) > 3:
                            model = values[3]
                        break
                
                # 创建安全的文件名
                safe_model = re.sub(r'[<>:"/\\|?*]', '_', model)
                if not safe_model or safe_model == "Unknown":
                    safe_model = "unknown_model"
                
                filename = f"{folder_name}/{safe_model}_{ip.replace('.', '_')}_{timestamp}.txt"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(response)
                
                saved_count += 1
            
            self.status_var.set(f"已保存 {saved_count} 个矿机日志到 {folder_name} 文件夹")
            messagebox.showinfo("保存成功", f"已保存 {saved_count} 个矿机日志到 {folder_name} 文件夹")
            
        except Exception as e:
            messagebox.showerror("保存失败", f"保存日志时出错: {str(e)}")
    
    def update_ip_segments_display(self):
        """更新IP段显示"""
        # 清除现有复选框
        for widget in self.ip_segments_inner_frame.winfo_children():
            widget.destroy()
        
        self.ip_segment_vars.clear()
        self.ip_segment_checkbuttons.clear()
        
        # 获取IP段列表
        ip_segments = self.ip_manager.get_ip_segments()
        
        # 创建复选框，每个IP段显示在单独的行上
        for i, segment_text in enumerate(ip_segments):
            var = tk.BooleanVar(value=True)  # 默认启用
            self.ip_segment_vars.append(var)
            
            # 创建框架来容纳复选框和标签
            segment_frame = ttk.Frame(self.ip_segments_inner_frame)
            segment_frame.grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            
            checkbox = ttk.Checkbutton(
                segment_frame,
                text="",
                variable=var,
                command=lambda idx=i: self._on_ip_segment_toggle(idx)
            )
            checkbox.pack(side=tk.LEFT)
            
            # 解析IP段文本，提取标签和IP段
            display_text = segment_text
            if '#' in segment_text:
                parts = segment_text.split('#', 1)
                if len(parts) == 2:
                    ip_part = parts[0].strip()
                    tag_part = parts[1].strip()
                    # 格式：标签加粗，空两格，IP段
                    display_text = f"{tag_part}  {ip_part}"
            
            # 添加IP段文本标签
            label = ttk.Label(segment_frame, text=display_text, font=("Arial", 9, "bold") if '#' in segment_text else ("Arial", 9))
            label.pack(side=tk.LEFT, padx=(5, 0))
            
            self.ip_segment_checkbuttons.append(checkbox)
        
        # 更新Canvas滚动区域
        self.ip_segments_inner_frame.update_idletasks()
        self.ip_segments_canvas.configure(scrollregion=self.ip_segments_canvas.bbox("all"))
        
        # 调整Canvas高度以适应内容
        inner_height = self.ip_segments_inner_frame.winfo_reqheight()
        canvas_height = min(80, max(40, inner_height))
        self.ip_segments_canvas.configure(height=canvas_height)
    
    def _on_ip_segment_toggle(self, index):
        """IP段复选框状态变化处理"""
        if index < len(self.ip_segment_vars):
            enabled = self.ip_segment_vars[index].get()
            self.ip_manager.toggle_ip_segment(index, enabled)
    
    def get_enabled_ip_segments(self):
        """获取启用的IP段文本"""
        ip_segments = self.ip_manager.get_ip_segments()
        enabled_segments = []
        
        for i, segment_text in enumerate(ip_segments):
            if i < len(self.ip_segment_vars) and self.ip_segment_vars[i].get():
                enabled_segments.append(segment_text)
        
        return "\n".join(enabled_segments)
    
    def open_add_ip_segment_dialog(self):
        """打开IP段管理对话框（直接在现有IP段输入，确认即覆盖）"""
        dialog = tk.Toplevel(self.root)
        dialog.title("IP段管理")
        dialog.geometry("550x550")  # 稍微增加宽度以更好地显示左对齐内容
        dialog.transient(self.root)
        dialog.grab_set()
        
        try:
            dialog.iconbitmap("imag/avalon.ico")
        except:
            pass
        
        # 创建主框架
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重，使内容左对齐
        main_frame.columnconfigure(0, weight=1)
        
        # 格式提示和示例 - 显示在输入框上方，明确左对齐
        instructions_frame = ttk.LabelFrame(main_frame, text="格式说明", padding="8")
        instructions_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        instructions_frame.columnconfigure(0, weight=1)
        
        instructions = """直接在下方编辑IP段列表，每行一个IP段
注意事项：
1. 每行一个IP段
2. 支持IP段范围，如192.168.1.1-255
3. 支持添加标签，格式为IP段#标签名
4. 标签名不能包含逗号、分号等特殊字符
格式示例：
    192.168.1.1-100
    10.0.0.1-50#机房A
    172.16.0.0-255
"""
        
        # 使用Text组件以便更好地控制对齐和换行
        instructions_text = tk.Text(instructions_frame, wrap=tk.WORD, height=10, width=60,
                                   relief=tk.FLAT, font=("Arial", 9))
        # 设置背景色与LabelFrame背景色保持一致
        try:
            # 获取LabelFrame的背景色
            bg_color = instructions_frame.cget('background')
            instructions_text.config(bg=bg_color)
        except:
            # 如果无法获取背景色，使用系统默认对话框背景色
            try:
                bg_color = dialog.cget('background')
                instructions_text.config(bg=bg_color)
            except:
                # 使用默认浅灰色背景
                instructions_text.config(bg='#f0f0f0')
        instructions_text.insert(tk.END, instructions)
        instructions_text.config(state=tk.DISABLED)  # 设置为只读
        instructions_text.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # IP段编辑区域
        edit_frame = ttk.LabelFrame(main_frame, text="IP段列表编辑", padding="8")
        edit_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        edit_frame.columnconfigure(0, weight=1)
        edit_frame.rowconfigure(1, weight=1)
        
        # IP段编辑标签 - 明确左对齐
        edit_label = ttk.Label(edit_frame, text="编辑IP段列表（每行一个）：", anchor=tk.W)
        edit_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # IP段编辑文本框
        text_area = scrolledtext.ScrolledText(edit_frame, wrap=tk.WORD, height=12, width=60)
        text_area.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        
        # 获取并显示所有现有IP段
        ip_segments = self.ip_manager.get_ip_segments()
        for segment in ip_segments:
            text_area.insert(tk.END, segment + "\n")
        
        # 错误提示标签 - 左对齐
        error_label = ttk.Label(main_frame, text="", foreground="red", wraplength=500, anchor=tk.W, justify=tk.LEFT)
        error_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        
        def validate_and_save():
            # 获取编辑后的内容
            content = text_area.get("1.0", tk.END).strip()
            if not content:
                error_label.config(text="❌ IP段列表不能为空")
                return
            
            # 分割文本为多行
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            valid_segments = []
            invalid_lines = []
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # 验证IP段格式
                if not validate_ip_segment_format(line):
                    # 检查是否是带标签的格式
                    if '#' in line:
                        parts = line.split('#', 1)
                        ip_part = parts[0].strip()
                        if validate_ip_segment_format(ip_part):
                            valid_segments.append(line)
                        else:
                            invalid_lines.append(f"第{line_num}行: {line}")
                    else:
                        invalid_lines.append(f"第{line_num}行: {line}")
                else:
                    valid_segments.append(line)
            
            if invalid_lines:
                error_label.config(text=f"❌ 以下行格式无效:\n" + "\n".join(invalid_lines[:3]))
                if len(invalid_lines) > 3:
                    error_label.config(text=error_label.cget("text") + f"\n...还有{len(invalid_lines)-3}个错误")
                return
            
            if not valid_segments:
                error_label.config(text="❌ 没有有效的IP段")
                return
            
            # 直接覆盖现有IP段列表
            self.ip_manager.set_ip_segments(valid_segments)
            self.ip_manager.save_ip_segments()
            
            # 更新显示
            self.update_ip_segments_display()
            
            error_label.config(text=f"✅ 成功保存 {len(valid_segments)} 个IP段", foreground="green")
            # 更新主界面状态
            self.status_var.set(f"✅ 成功保存 {len(valid_segments)} 个IP段")
            
            # 1秒后自动关闭对话框
            dialog.after(1000, dialog.destroy)
        
        # 按钮框架 - 左对齐
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        # 使用更明确的按钮文本
        confirm_button = ttk.Button(button_frame, text="确认保存", command=validate_and_save)
        confirm_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)
        
        # 绑定回车键（直接按Enter也可以提交）
        def on_enter(event):
            validate_and_save()
            return "break"
        
        # 绑定Ctrl+Enter提交，Enter键正常换行
        text_area.bind('<Control-Return>', on_enter)
        # 移除对Enter键的绑定，允许正常换行
        
        # 对话框级别的Enter键绑定改为Ctrl+Enter
        dialog.bind('<Control-Return>', on_enter)
        # 添加一个专门的提交按钮快捷键
        dialog.bind('<Alt-s>', on_enter)
        
        # 确保输入框获得焦点并显示光标
        def set_focus():
            text_area.focus_set()
            # 将光标定位在文本末尾，不选中任何文本
            text_area.mark_set(tk.INSERT, tk.END)
            text_area.see(tk.INSERT)
        
        # 延迟设置焦点，确保窗口已经显示
        dialog.after(100, set_focus)
        
        # 添加窗口关闭事件处理
        def on_closing():
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_closing)
        
        # 配置对话框的网格权重
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
    
    def open_settings(self):
        """打开设置对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("设置")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        try:
            dialog.iconbitmap("imag/avalon.ico")
        except:
            pass
        
        # 设置框架
        settings_frame = ttk.Frame(dialog, padding="20")
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # 连接超时设置
        ttk.Label(settings_frame, text="连接超时 (秒):").grid(row=0, column=0, sticky=tk.W, pady=5)
        connect_timeout_entry = ttk.Entry(settings_frame, textvariable=self.connect_timeout, width=10)
        connect_timeout_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 读取超时设置
        ttk.Label(settings_frame, text="读取超时 (秒):").grid(row=1, column=0, sticky=tk.W, pady=5)
        read_timeout_entry = ttk.Entry(settings_frame, textvariable=self.read_timeout, width=10)
        read_timeout_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 线程数设置
        ttk.Label(settings_frame, text="最大线程数:").grid(row=2, column=0, sticky=tk.W, pady=5)
        threads_entry = ttk.Entry(settings_frame, textvariable=self.threads, width=10)
        threads_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 重试次数设置
        ttk.Label(settings_frame, text="重试次数 (0-10):").grid(row=3, column=0, sticky=tk.W, pady=5)
        retry_entry = ttk.Entry(settings_frame, textvariable=self.retry_count, width=10)
        retry_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        def save_settings():
            try:
                # 验证输入
                connect_timeout = float(self.connect_timeout.get())
                read_timeout = float(self.read_timeout.get())
                threads = int(self.threads.get())
                retry_count = int(self.retry_count.get())
                
                if connect_timeout <= 0 or read_timeout <= 0:
                    messagebox.showerror("输入错误", "超时时间必须大于0")
                    return
                
                if threads <= 0 or threads > 500:
                    messagebox.showerror("输入错误", "线程数必须在1-500之间")
                    return
                
                if retry_count < 0 or retry_count > 10:
                    messagebox.showerror("输入错误", "重试次数必须在0-10之间")
                    return
                
                dialog.destroy()
                self.status_var.set("设置已保存")
                
            except ValueError:
                messagebox.showerror("输入错误", "请确保所有设置都是有效的数字")
        
        ttk.Button(button_frame, text="保存", command=save_settings).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
        
        # 绑定回车键
        dialog.bind('<Return>', lambda e: save_settings())
        connect_timeout_entry.focus_set()
    
    def resource_path(self, relative_path):
        """获取资源文件的绝对路径"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relative_path)


def main():
    """主函数"""
    root = tk.Tk()
    app = MinerScannerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
