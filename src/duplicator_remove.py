# 对本地文件进行重复性扫描，如果重复则删除

import os
import re
import sys
import shutil
import csv
import base64
from datetime import datetime
from core import SmartSortCore
from brain import SmartBrain
import json

def record_log(log_data):
    """将处理记录写入 CSV 文件"""
    log_file = "smartsort_run.log"
    file_exists = os.path.isfile(log_file)
    
    with open(log_file, 'a', encoding='utf-8-sig', newline='') as f:
        f.write(
            f"[{log_data['time']}]\n"
            f"<source>:   {log_data['path']}\n"
            f"<type>:     {log_data['filetype']}\n"
            f"<hash>:     {log_data['hash']}\n"
            f"<abstract>: {log_data['abstract']}\n"
            f"<related>:  {log_data['related_info']}\n"
            f"<result>:   {log_data['result']}\n"
            f"<category>: {log_data['category']} \n"
            f"<path>:     {log_data['final_path']}\n\n")

def sanitize_filename(filename, replacement="_"):
    # 清理文件名，使其符合 Windows 文件命名规范

    # Windows 禁止的字符: \ / : * ? " < > |, 以及控制字符 (0-31)
    invalid_chars = r'[\\/:\*\?"<>|]'
    # 1. 替换非法字符为下划线（或其他指定字符）
    sanitized = re.sub(invalid_chars, replacement, filename)
    # 2. 去除文件名首尾的空格和点（Windows 会忽略首尾的点，可能导致找不到文件）
    sanitized = sanitized.strip().strip('.')
    # 3. 处理 Windows 预留名称 (如 CON, PRN, AUX, NUL, COM1 等)
    reserved_names = {
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", 
        "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", 
        "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    if sanitized.upper() in reserved_names:
        sanitized = f"{sanitized}_safe"
    # 4. 限制长度（Windows 路径总长通常限制在 260 字符，文件名建议不超过 200）
    return sanitized[:128]

def get_unique_path(target_dir, filename):
    """
    如果文件名冲突，自动生成带序号的唯一路径
    例如: test.pdf -> test(1).pdf -> test(2).pdf
    """
    base, ext = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    unique_path = os.path.join(target_dir, unique_filename)

    # 循环检查，直到找到一个不存在的路径
    while os.path.exists(unique_path):
        unique_filename = f"{base}({counter}){ext}"
        unique_path = os.path.join(target_dir, unique_filename)
        counter += 1
    
    if counter > 1:
        print(f"⚠️ 文件名冲突，已自动重命名为: {unique_filename}")
    return unique_path, unique_filename

def safe_copy(src, dst_dir, dst_fn):
    """
    安全复制文件，避免覆盖已有文件
    如果目标路径已存在，则自动生成一个带序号的唯一路径
    """
    os.makedirs(dst_dir, exist_ok=True)
    final_path, final_name = get_unique_path(dst_dir, dst_fn)
#    print(f"copy file from: {src} to: {final_path}")
    shutil.move(src, final_path)
    return final_path

def get_folder_count(target_root, category_path):
    full_path = os.path.join(target_root, category_path)
    if not os.path.exists(full_path):
        return 0
    return len([f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))])

def main(source_dir):
    # 从source_dir中检查出重复文件，不重复的copy到一个临时文件夹。这个工作为了操作终端后恢复
    core = SmartSortCore()
    
    # 两个特殊文件夹路径
#    os.makedirs(UNKNOWN_DIR, exist_ok=True)
#    os.makedirs(DUPLICATE_DIR, exist_ok=True)

    total_processed = 0
    total_size = 0
    duplicates = 0
    dup_size = 0

    file_dir = {}

    for root, _, files in os.walk(source_dir):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if file_name.startswith('.'): continue

            total_processed += 1
            file_size = os.path.getsize(file_path)
            total_size += file_size

            print(f"\n🧠 正在处理: {file_name}")
            ext = os.path.splitext(file_name)[1].lower()

            # --- 重复检测，重复文件放入重复区 ---
            file_hash = core.calculate_hash(file_path) # 返回的file_hash是base64编码的字符串
            if (file_hash in file_dir):
                print(f"♻️ 发现重复文件: {file_name}, 原文件: {file_dir[file_hash]}")
                os.remove(file_path)
                duplicates += 1
                dup_size += file_size
            else:
                file_dir[file_hash] = file_path
#                print(f"✅ 新文件: {file_name}，已记录哈希值。")
            print(f"✅ 已处理 {total_processed} 个文件，当前重复文件数: {duplicates}\n")

    print(f"\n✅ 所有文件整理完毕！检查{total_processed}个文件，重复文件{duplicates}")
    print(f"\n总共{total_size/1024/1024:.2f} MB，节省空间{dup_size/1024/1024:.2f} MB。")

if __name__ == "__main__":
    # 1. 加载配置
    config_path = "config.json"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"找不到配置文件: {config_path}")
        
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    target_root = config['settings']['target_root']
    DUPLICATE_DIR = os.path.join(target_root, config['settings']['duplicate_dir'])
    UNKNOWN_DIR = os.path.join(target_root, config['settings']['unknown_dir'])

    if len(sys.argv) > 1:
        source_dir = sys.argv[1]
        main(source_dir)