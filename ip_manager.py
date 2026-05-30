"""
IP段管理模块
包含IP段的加载、保存、验证和显示功能
"""
import os
import json
import re
from utils import validate_ip_segment_format


class IPManager:
    """IP段管理器"""
    
    def __init__(self, ip_segments_file="ip_segments.json"):
        self.ip_segments_file = ip_segments_file
        self.ip_segments_list = self.load_ip_segments()
        
    def load_ip_segments(self):
        """加载IP段，支持IP段#标签格式，保持向后兼容"""
        default_ip_segments = ["10.100.106.0-255", "10.100.107.0-255", "10.100.108.0-255", 
                              "192.168.0.1-255", "192.168.1.1-255"]
        
        try:
            if os.path.exists(self.ip_segments_file) and os.path.getsize(self.ip_segments_file) > 0:
                with open(self.ip_segments_file, "r", encoding="utf-8") as f:
                    loaded_segments = json.load(f)
                    if isinstance(loaded_segments, list) and len(loaded_segments) > 0:
                        # 验证并处理每个IP段，确保格式正确
                        processed_segments = []
                        for segment in loaded_segments:
                            if isinstance(segment, str):
                                # 检查是否是IP段#标签格式
                                if '#' in segment:
                                    # 验证格式：IP段#标签
                                    parts = segment.split('#', 1)
                                    if len(parts) == 2:
                                        ip_part = parts[0].strip()
                                        tag_part = parts[1].strip()
                                        # 验证IP段格式
                                        if validate_ip_segment_format(ip_part):
                                            processed_segments.append(f"{ip_part}#{tag_part}")
                                        else:
                                            # 如果IP段格式无效，只保留IP段部分（如果有）
                                            if validate_ip_segment_format(ip_part):
                                                processed_segments.append(ip_part)
                                    else:
                                        # 格式不正确，只保留IP段部分
                                        if validate_ip_segment_format(parts[0].strip()):
                                            processed_segments.append(parts[0].strip())
                                else:
                                    # 没有标签，验证IP段格式
                                    if validate_ip_segment_format(segment):
                                        processed_segments.append(segment)
                        return processed_segments if processed_segments else default_ip_segments
        except Exception as e:
            print(f"加载文件出错: {e}")
        
        return default_ip_segments
    
    def save_ip_segments(self):
        """保存当前IP段列表到本地文件，支持IP段#标签格式"""
        try:
            with open(self.ip_segments_file, "w", encoding="utf-8") as f:
                # 将IP段列表写入JSON文件，保持IP段#标签格式
                json.dump(self.ip_segments_list, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存IP段失败：{e}")
            return False
    
    def add_ip_segment(self, ip_segment):
        """添加IP段到列表"""
        if ip_segment not in self.ip_segments_list:
            self.ip_segments_list.append(ip_segment)
            self.save_ip_segments()
            return True, f"IP段 '{ip_segment}' 添加成功"
        return False, f"IP段 '{ip_segment}' 已存在"
    
    def remove_ip_segment(self, ip_segment):
        """从列表中移除IP段"""
        if ip_segment in self.ip_segments_list:
            self.ip_segments_list.remove(ip_segment)
            return True
        return False
    
    def get_ip_segments(self):
        """获取IP段列表"""
        return self.ip_segments_list
    
    def set_ip_segments(self, ip_segments):
        """设置IP段列表"""
        self.ip_segments_list = ip_segments
    
    def toggle_ip_segment(self, index, enabled):
        """切换IP段的启用状态（为了兼容性，实际上不存储状态，只是返回成功）"""
        # 注意：当前实现不存储启用状态，只是返回成功
        # 如果需要存储启用状态，需要修改数据结构
        return True
    
    def validate_ip_segment_input(self, text):
        """验证IP段输入文本"""
        if not text:
            return False, "请输入IP段"
        
        # 解析IP段，支持逗号分隔和换行分隔
        ip_segments = []
        comma_parts = text.split(',')
        for part in comma_parts:
            part = part.strip()
            if not part:
                continue
            # 再按换行分割（处理多行输入）
            lines = part.split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    ip_segments.append(line)
        
        # 验证IP段格式，支持IP段#标签格式
        valid_segments = []
        for segment in ip_segments:
            # 检查是否是IP段#标签格式
            if '#' in segment:
                # 分割IP段和标签
                parts = segment.split('#', 1)
                ip_part = parts[0].strip()
                tag_part = parts[1].strip()
                
                # 验证IP段部分格式
                if validate_ip_segment_format(ip_part):
                    # 验证标签部分（不能为空，不能包含逗号、分号等特殊字符）
                    if tag_part and not re.search(r'[,;\n\r]', tag_part):
                        valid_segments.append(f"{ip_part}#{tag_part}")
                    else:
                        return False, f"标签格式不正确：{segment}\n标签不能为空且不能包含逗号、分号等特殊字符"
                else:
                    return False, f"IP段格式不正确：{segment}\n正确格式：192.168.0.0-255 或 192.168.0.0-255#机房A"
            else:
                # 没有标签，只验证IP段格式
                if validate_ip_segment_format(segment):
                    valid_segments.append(segment)
                else:
                    return False, f"IP段格式不正确：{segment}\n正确格式：192.168.0.0-255 或 192.168.0.0-255#机房A"
        
        if not valid_segments:
            return False, "没有有效的IP段"
        
        return True, valid_segments
