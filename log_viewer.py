import socket
import re
import tkinter as tk
from tkinter import ttk
import threading
import os
import sys
import time 

ASIC_MODELS = {
    "Avalon_3200": {"chip_type": ["3200", "3201"], "total_chips": 120, "columns": 20, "layout": [[3, 4, 9, 10, 15, 16, 21, 22, 27, 28, 33, 34, 39, 40, 45, 46, 51, 52, 57, 58],[2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35, 38, 41, 44, 47, 50, 53, 56, 59],[1, 6, 7, 12, 13, 18, 19, 24, 25, 30, 31, 36, 37, 42, 43, 48, 49, 54, 55, 60],[120, 115, 114, 109, 108, 103, 102, 97, 96, 91, 90, 85, 84, 79, 78, 73, 72, 67, 66, 61],[119, 116, 113, 110, 107, 104, 101, 98, 95, 92, 89, 86, 83, 80, 77, 74, 71, 68, 65, 62],[118, 117, 112, 111, 106, 105, 100, 99, 94, 93, 88, 87, 82, 81, 76, 75, 70, 69, 64, 63]]},
    "Avalon_3200c_120": {"chip_type": ["3200C"], "total_chips": 120, "columns": 21, "layout": [[1, 6, 7, 12, 13, 18, 19, 0, 24, 25, 30, 31, 36, 0, 37, 42, 43, 48, 49, 54, 55],[2, 5, 8, 11, 14, 17, 20, 0, 23, 26, 29, 32, 35, 0, 38, 41, 44, 47, 50, 53, 56],[3, 4, 9, 10, 15, 16, 21, 0, 22, 27, 28, 33, 34, 0, 39, 40, 45, 46, 51, 52, 57],[118, 117, 112, 111, 106, 105, 100, 99, 94, 93, 88, 87, 82, 81, 76, 75, 70, 69, 64, 63, 58],[119, 116, 113, 110, 107, 104, 101, 98, 95, 92, 89, 86, 83, 80, 77, 74, 71, 68, 65, 62, 59],[120, 115, 114, 109, 108, 103, 102, 97, 96, 91, 90, 85, 84, 79, 78, 73, 72, 67, 66, 61, 60]]},
    "Avalon_3198s_126": {"chip_type": ["3198S"], "total_chips": 126, "columns": 23, "layout": [[1, 6, 7, 12, 13, 0, 18, 19, 24, 0, 25, 30, 31, 0, 36, 37, 42, 0, 43, 48, 49, 54, 55],[2, 5, 8, 11, 14, 0, 17, 20, 23, 0, 26, 29, 32, 0, 35, 38, 41, 0, 44, 47, 50, 53, 56],[3, 4, 9, 10, 15, 0, 16, 21, 22, 0, 27, 28, 33, 0, 34, 39, 40, 0, 45, 46, 51, 52, 57],[124, 123, 118, 117, 112, 111, 106, 105, 100, 99, 94, 93, 88, 87, 82, 81, 76, 75, 70, 69, 64, 63, 58],[125, 122, 119, 116, 113, 110, 107, 104, 101, 98, 95, 92, 89, 86, 83, 80, 77, 74, 71, 68, 65, 62, 59],[126, 121, 120, 115, 114, 109, 108, 103, 102, 97, 96, 91, 90, 85, 84, 79, 78, 73, 72, 67, 66, 61, 60]]},
    "Avalon_3200c_126": {"chip_type": ["3200C"], "total_chips": 126, "columns": 21, "layout": [[1, 6, 7, 12, 13, 18, 19, 24, 25, 30, 31, 36, 37, 42, 43, 48, 49, 54, 55, 60, 61],[2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35, 38, 41, 44, 47, 50, 53, 56, 59, 62],[3, 4, 9, 10, 15, 16, 21, 22, 27, 28, 33, 34, 39, 40, 45, 46, 51, 52, 57, 58, 63],[124, 123, 118, 117, 112, 111, 106, 105, 100, 99, 94, 93, 88, 87, 82, 81, 76, 75, 70, 69, 64],[125, 122, 119, 116, 113, 110, 107, 104, 101, 98, 95, 92, 89, 86, 83, 80, 77, 74, 71, 68, 65],[126, 121, 120, 115, 114, 109, 108, 103, 102, 97, 96, 91, 90, 85, 84, 79, 78, 73, 72, 67, 66]]},
    "Avalon_3200c_114": {"chip_type": ["3200C"], "total_chips": 114, "columns": 21, "layout": [[1, 6, 7, 12, 0, 13, 18, 19, 0, 24, 25, 30, 0, 31, 36, 37, 0, 42, 43, 48, 49],[2, 5, 8, 11, 0, 14, 17, 20, 0, 23, 26, 29, 0, 32, 35, 38, 0, 41, 44, 47, 50],[3, 4, 9, 10, 0, 15, 16, 21, 0, 22, 27, 28, 0, 33, 34, 39, 0, 40, 45, 46, 51],[112, 111, 106, 105, 100, 99, 94, 93, 88, 87, 82, 81, 76, 75, 70, 69, 64, 63, 58, 57, 52],[113, 110, 107, 104, 101, 98, 95, 92, 89, 86, 83, 80, 77, 74, 71, 68, 65, 62, 59, 56, 53],[114, 109, 108, 103, 102, 97, 96, 91, 90, 85, 84, 79, 78, 73, 72, 67, 66, 61, 60, 55, 54]]},
    "Avalon_3198S_176": {"chip_type": ["3198S", "3197S"], "total_chips": 176, "columns": 23, "layout": [[1, 8, 9, 16, 17, 24, 25, 32, 0, 33, 40, 41, 48, 49, 56, 0, 57, 64, 65, 72, 73, 80, 81],[2, 7, 10, 15, 18, 23, 26, 31, 0, 34, 39, 42, 47, 50, 55, 0, 58, 63, 66, 71, 74, 79, 82],[3, 6, 11, 14, 19, 22, 27, 30, 0, 35, 38, 43, 46, 51, 54, 0, 59, 62, 67, 70, 75, 78, 83],[4, 5, 12, 13, 20, 21, 28, 29, 0, 36, 37, 44, 45, 52, 53, 0, 60, 61, 68, 69, 76, 77, 84],[173, 172, 165, 164, 157, 156, 149, 148, 141, 140, 133, 132, 125, 124, 117, 116, 109, 108, 101, 100, 93, 92, 85],[174, 171, 166, 163, 158, 155, 150, 147, 142, 139, 134, 131, 126, 123, 118, 115, 110, 107, 102, 99, 94, 91, 86],[175, 170, 167, 162, 159, 154, 151, 146, 143, 138, 135, 130, 127, 122, 119, 114, 111, 106, 103, 98, 95, 90, 87],[176, 169, 168, 161, 160, 153, 152, 145, 144, 137, 136, 129, 128, 121, 120, 113, 112, 105, 104, 97, 96, 89, 88]]}
}

class AvalonMinerViewer:
    def __init__(self, root, miner_ip="10.100.106.6"):
        self.root = root
        self.root.title(f"Avalon Log Visualisation - {miner_ip}")
        self.root.geometry("1850x950")
        self.root.configure(bg="#222")


        self.ip = miner_ip
        self.board_count = 3  # 默认初始板卡数
        self.current_model_name = None
        self.current_layout = ASIC_MODELS["Avalon_3200"]["layout"]
        self.current_cols = 20
        self.last_valid_data = None
        self.chip_labels = {}
        self.chip_headers = {}
        self.stats_labels = {}

        self.setup_ui()
        self.update_loop()
    def setup_ui(self):
        # 1. Top Bar
        top_f = tk.Frame(self.root, bg="#333", height=60)
        top_f.pack(side="top", fill="x")
        try:
            self.root.iconbitmap("imag/avalon.ico")
        except:
            pass  
        tk.Label(top_f, text=" IP:", bg="#333", fg="white").pack(side="left", padx=5)
        self.ip_ent = tk.Entry(top_f, width=15, font=("Arial", 12))
        self.ip_ent.insert(0, self.ip)
        self.ip_ent.pack(side="left", padx=5)
        self.refresh_time_var = tk.StringVar(value="2000")
        tk.Label(top_f, text=" 刷新(ms):", bg="#333", fg="white").pack(side="left", padx=(10, 2))
        tk.Entry(top_f, textvariable=self.refresh_time_var, width=5, font=("Arial", 12)).pack(side="left")
        tk.Button(top_f, text="刷新连接", command=self.change_ip).pack(side="left", padx=10)
        self.min_temp_var, self.max_temp_var = tk.StringVar(value="60"), tk.StringVar(value="90")
        tk.Label(top_f, text=" 色温:", bg="#333", fg="white").pack(side="left")
        tk.Entry(top_f, textvariable=self.min_temp_var, width=3).pack(side="left")
        tk.Label(top_f, text="-", bg="#333", fg="white").pack(side="left")
        tk.Entry(top_f, textvariable=self.max_temp_var, width=3).pack(side="left")
        self.display_mode = tk.StringVar(value="Temperature")
        for txt, md in [("温度", "Temperature"), ("电压", "Voltage"), ("MW频率", "MW")]:
            tk.Radiobutton(top_f, text=txt, variable=self.display_mode, value=md, indicatoron=0, 
                           width=8, bg="#444", fg="white", selectcolor="#555").pack(side="left", padx=2)

        side_f = tk.Frame(self.root, width=280, bg="#252526", padx=10)
        side_f.pack(side="left", fill="y")
        self.create_info_group(side_f, "身份与状态", [("Status", "运行状态:"), ("Core", "芯片型号:"), ("DNA", "设备ID:"), ("Ver", "固件版本:"), ("Elapsed", "运行时间:"), ("Ping", "网络延迟:")])
        self.create_info_group(side_f, "算力详情", [("GHS", "实时算力:"), ("GHSavg", "平均算力:"), ("GHSmm", "理论算力:"), ("Freq", "平均频率:")])
        self.create_info_group(side_f, "功耗与温度", [("WallPower", "墙上功耗:"), ("Vo", "平均电压:"), ("TMax", "最高温度:"), ("TAvg", "平均温度:")])
        self.create_info_group(side_f, "通风系统", [("FanR", "风扇占空比:")])
        right_main_frame = tk.Frame(self.root, bg="#1E1E1E")
        right_main_frame.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(right_main_frame, bg="#1E1E1E", highlightthickness=0)
        v_scroll = ttk.Scrollbar(right_main_frame, orient="vertical", command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(right_main_frame, orient="horizontal", command=self.canvas.xview)
        self.chip_container = tk.Frame(self.canvas, bg="#1E1E1E")
        self.chip_container.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.chip_container, anchor="nw")
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.rebuild_ui()

    def create_info_group(self, parent, title, items):
        group = tk.LabelFrame(parent, text=title, bg="#252526", fg="#00CCFF", font=("Arial", 10, "bold"), padx=5, pady=5)
        group.pack(fill="x", pady=5)
        for key, label in items:
            row = tk.Frame(group, bg="#252526")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, bg="#252526", fg="#AAA", font=("Arial", 9)).pack(side="left")
            val_l = tk.Label(row, text="--", bg="#252526", fg="white", font=("Arial", 10, "bold"))
            val_l.pack(side="right")
            self.stats_labels[key] = val_l

    def change_ip(self):
        self.ip = self.ip_ent.get()
        print(f"Switching to IP: {self.ip}")

    def detect_model(self, ta, core_type):
        try:
            count = int(ta) // self.board_count
            for name, info in ASIC_MODELS.items():
                if count == info["total_chips"] and any(c in core_type.upper() for c in info["chip_type"]):
                    return name
        except: pass
        return "Avalon_3200"

    def parse_data(self, raw):
        try:
            m = {
                "TA": re.search(r'TA\[(\d+)\]', raw),
                "Core": re.search(r'Core\[(.*?)\]', raw),
                "Ver": re.search(r'Ver\[(.*?)\]', raw),
                "DNA": re.search(r'DNA\[(.*?)\]', raw),
                "Status": re.search(r'SYSTEMSTATU\[(.*?)\]', raw),
                "Elapsed": re.search(r'Elapsed\[(\d+)\]', raw),
                "GHS": re.search(r'GHSspd\[(\d+\.\d+)\]', raw),
                "GHSavg": re.search(r'GHSavg\[(\d+\.\d+)\]', raw),
                "GHSmm": re.search(r'GHSmm\[(\d+\.\d+)\]', raw),
                "WallPower": re.search(r'WALLPOWER\[(\d+)\]', raw),
                "TMax": re.search(r'TMax\[(\d+)\]', raw),
                "TAvg": re.search(r'TAvg\[(\d+)\]', raw),
                "FanR": re.search(r'FanR\[(\d+%)\]', raw),
                "Vo": re.search(r'Vo\[(\d+)\]', raw),
                "Freq": re.search(r'Freq\[(\d+\.\d+)\]', raw),
                "Ping": re.search(r'PING\[(\d+)\]', raw),
                "MGHS": re.search(r'MGHS\[(.*?)\]', raw),
                "CRC": re.search(r'CRC\[(.*?)\]', raw),
            }
            for k in m: m[k] = m[k].group(1) if m[k] else "--"

            board_match = re.search(r'Hash Board:\s*(\d+)', m["Status"])
            new_board_count = int(board_match.group(1)) if board_match else self.board_count

            model = self.detect_model(m["TA"], m["Core"])
            if model != self.current_model_name or new_board_count != self.board_count:
                self.board_count = new_board_count
                self.current_model_name = model
                self.current_layout = ASIC_MODELS[model]["layout"]
                self.current_cols = ASIC_MODELS[model]["columns"]
                self.root.after(0, self.rebuild_ui)

            mode = self.display_mode.get()
            m["BoardData"] = {}
            m["AvgV"] = {}
            key_prefix = {"Temperature": "PVT_T", "Voltage": "PVT_V", "MW": "MW"}.get(mode, "PVT_T")

            for i in range(self.board_count):
                b_name = f"Board {i}"
                chips = re.findall(fr"{key_prefix}{i}\[(.*?)\]", raw)
                if chips:
                    vals = [int(v) for v in chips[0].split() if v.strip().isdigit()]
                    m["BoardData"][b_name] = [[vals[cid - 1] if 0 < cid <= len(vals) else 0 for cid in row] for row in self.current_layout]
                    if mode == "Voltage":
                        vv = [v for v in vals if v > 0]
                        m["AvgV"][b_name] = sum(vv) / len(vv) if vv else 0
            self.last_valid_data = m
            return m
        except: return self.last_valid_data

    def rebuild_ui(self):
        for w in self.chip_container.winfo_children(): w.destroy()
        self.chip_labels.clear()
        self.chip_headers.clear()
        for i in range(self.board_count):
            b_name = f"Board {i}"
            f = tk.Frame(self.chip_container, bg="#1E1E1E")
            f.pack(fill="x", pady=10)
            h = tk.Label(f, text=f"{b_name} | 加载中...", font=("Arial", 12, "bold"), anchor="w", bg="#444", fg="white")
            h.pack(fill="x")
            self.chip_headers[b_name] = h
            gf = tk.Frame(f, bg="#1E1E1E")
            gf.pack(pady=5)
            rows = []
            for r in range(len(self.current_layout)):
                cols = []
                for c in range(self.current_cols):
                    l = tk.Label(gf, text="--", width=4, height=2, font=("Arial", 10, "bold"), bg="white", relief="flat")
                    l.grid(row=r, column=c, padx=2, pady=2)
                    cols.append(l)
                rows.append(cols)
            self.chip_labels[b_name] = rows
        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def update_ui(self, data):
        if not data: return
        for k, label in self.stats_labels.items():
            val = data.get(k, "--")
            if k == "WallPower": label.config(text=f"{val} W", foreground="#00FF00")
            elif k == "GHS": label.config(text=f"{val} GH/s")
            else: label.config(text=str(val))

        mode = self.display_mode.get()
        mghs = data["MGHS"].split()
        crcs = data["CRC"].split()
        
        for i in range(self.board_count):
            b_name = f"Board {i}"
            if b_name not in self.chip_labels: continue
            m_val = mghs[i] if i < len(mghs) else "0"
            c_val = crcs[i] if i < len(crcs) else "0"
            self.chip_headers[b_name].config(text=f" {b_name} | {mode} | 板算力: {m_val} GH/s | CRC: {c_val}")
            matrix, avg_v = data["BoardData"].get(b_name, []), data.get("AvgV", {}).get(b_name, 0)
            for r in range(len(self.chip_labels[b_name])):
                for c in range(self.current_cols):
                    try:
                        val = matrix[r][c]
                        if self.current_layout[r][c] == 0:
                            self.chip_labels[b_name][r][c].config(text="", bg="#333")
                            continue
                        bg = self.get_temp_color(val) if mode == "Temperature" else self.get_volt_color(val, avg_v) if mode == "Voltage" else ("#90EE90" if val > 0 else "white")
                        txt = str(val) if mode != "MW" else str(val)[-3:]
                        self.chip_labels[b_name][r][c].config(text=txt, bg=bg)
                    except: pass

    def get_temp_color(self, val):
        try:
            min_t, max_t = int(self.min_temp_var.get()), int(self.max_temp_var.get())
            val = max(min_t, min(val, max_t))
            t = (val - min_t) / (max_t - min_t)
            r, g, b = (int(2 * t * 255), 255, 0) if t < 0.5 else (255, int(255 - (t - 0.5) * 2 * 255), 0)
            return f"#{r:02X}{g:02X}{b:02X}"
        except: return "white"

    def get_volt_color(self, val, avg_v):
        if avg_v == 0: return "white"
        dev = max(-1, min(1, (val - avg_v) / avg_v * 10))
        r, b = int(255 * max(0, dev)), int(255 * max(0, -dev))
        g = int(255 * (1 - abs(dev)))
        return f"#{r:02X}{g:02X}{b:02X}"

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_loop(self):
        self.send_command()

    def send_command(self):
        def task():
            try:
                with socket.create_connection((self.ip, 4028), timeout=4) as s:
                    s.sendall(b'stats')
                    data = b""
                    while True:
                        chunk = s.recv(16384)
                        if not chunk: break
                        data += chunk
                    raw = data.decode('utf-8', errors='ignore')
                    if "STATUS=" in raw: 
                        self.root.after(0, lambda: self.process_and_update(raw))
            except: pass
            try: delay = int(self.refresh_time_var.get())
            except: delay = 2000
            self.root.after(max(500, delay), self.update_loop)
        threading.Thread(target=task, daemon=True).start()

    def process_and_update(self, raw):
        data = self.parse_data(raw)
        self.update_ui(data)

if __name__ == "__main__":
    root = tk.Tk()
    app = AvalonMinerViewer(root, miner_ip="10.100.106.6")
    root.mainloop()
