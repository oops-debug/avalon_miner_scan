"""
Avalon矿机扫描工具主程序入口
"""
import tkinter as tk
from gui import MinerScannerGUI


def main():
    """主函数"""
    root = tk.Tk()
    app = MinerScannerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
