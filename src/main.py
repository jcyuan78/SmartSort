import os
import re
import sys
import shutil
import csv
import base64
from datetime import datetime
from core import SmartSortCore
from brain import SmartBrain

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
    core = SmartSortCore()
    brain = SmartBrain()
    
    #target_root = "./sorted_files"
    target_root = "C:\\Users\\StorageDV\\Nextcloud\\book"
    # 两个特殊文件夹路径
    DUPLICATE_DIR = os.path.join(target_root, "系统管理/重复文件")
    UNKNOWN_DIR = os.path.join(target_root, "系统管理/待后续解析")
    os.makedirs(UNKNOWN_DIR, exist_ok=True)
    os.makedirs(DUPLICATE_DIR, exist_ok=True)

    # 定义目前支持的格式
    SUPPORTED_EXTS = ['.pdf', '.jpg', '.jpeg', '.png', '.txt', '.md', '.csv', '.xlsx', '.gif']

    # 获取当前已经存在的文件夹作为参考
    def get_existing_dirs():
        if not os.path.exists(target_root): return []
        return [d for d in os.listdir(target_root) if os.path.isdir(os.path.join(target_root, d))]

    total_processed = 0
    unsorted = 0
    duplicates = 0
    sorted = 0

#    debug_count = 300
    for root, _, files in os.walk(source_dir):
#        if debug_count <= 0: break
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if file_name.startswith('.'): continue
#            debug_count -= 1
#            if debug_count < 0: break

            total_processed += 1
            log_entry = {
                "time": datetime.now().isoformat(),
                "path": file_path,
                "filename": file_name,
                "filetype": "UNKNOWN",
                "hash": "",
                "abstract": "",
                "related_info": "",
                "result": "",
                "category": "",
                "final_path": ""
            }

            print(f"\n🧠 正在处理: {file_name}")
            ext = os.path.splitext(file_name)[1].lower()
            # --- 格式检查, 不符合格式的文件待以后处理 ---
            if ext not in SUPPORTED_EXTS:
                print(f"⚠️ 跳过未知格式: {file_name} -> 移至待处理区")
#                target_path = os.path.join(UNKNOWN_DIR, file_name)
                safe_copy(file_path, UNKNOWN_DIR, file_name)
#                shutil.move(file_path, target_path) # 移动过去，以后再管
                log_entry["result"] = "UNKNOWN_FORMAT"
                record_log(log_entry)
                unsorted += 1
                continue

            # 本地提取摘要，分析失败的文件也放入待处理区，避免干扰分类逻辑
            profile = core.generate_file_profile(file_path)
            if (not profile) or (not profile.get('metadata')):
                print(f"⚠️ 文件解析失败: {file_name} -> 移至待处理区")
                safe_copy(file_path, UNKNOWN_DIR, file_name)
                log_entry["result"] = "PARSE_FAILED"
                record_log(log_entry)
                unsorted += 1
                continue

            log_entry["abstract"] = profile['metadata']['summary'][:200]
            log_entry["filetype"] = profile['type']

            # --- 重复检测，重复文件放入重复区 ---
            file_hash = core.calculate_hash(file_path) # 返回的file_hash是base64编码的字符串
            log_entry["hash"] = file_hash

            if core.is_duplicate(file_hash):
                print(f"♻️ 发现重复文件: {file_name} -> 移至重复区")
                target_path = os.path.join(DUPLICATE_DIR, file_name)
#                os.makedirs(DUPLICATE_DIR, exist_ok=True)
                shutil.move(file_path, target_path)
                log_entry["result"] = "DUPLICATE"
                record_log(log_entry)
                duplicates += 1
                continue

            # --- 新增：寻找历史参考 (Auto-Heal 准备) ---
            # 搜索最相似的 3 个历史记录
            search_results = core.collection.query(
                query_embeddings=[profile['embedding']],
                n_results=5, include=['metadatas','distances']
            )
#            print(f"🔍 搜索历史记录, {search_results}")
            
            historical_context = []
            if search_results['metadatas'] and len(search_results['metadatas'][0]) > 0:
                for ii in range(len(search_results['metadatas'][0])):
                    similarity_score = 1.0
                    if search_results['distances'] and len(search_results['distances'][0]) > ii:
                        similarity_score = search_results['distances'][0][ii]
                    meta = search_results['metadatas'][0][ii]
                    ref_category = meta.get('category', '未分类')

                    current_count = get_folder_count(target_root, ref_category)
                    historical_context.append({
                        'summary': meta['summary'],
                        'category': ref_category,
                        'count': current_count,
                        'similarity': similarity_score,
                        'distinct': "高" if similarity_score > 0.4 else "低"
                    })
#            print(f"🔍 历史参考案例: {historical_context}")
            log_entry["related_info"] = f"{(historical_context)}"
            similarity_score = 1.0 # 默认完全不同

            # 2. AI 决策分类
            existing = get_existing_dirs()
            ai_result = brain.decide_category(
                file_summary = profile['metadata']['summary'], 
                current_filename = file_name,
                historical_context = historical_context,
            )
            category_path = ai_result['category']
            suggested_title = ai_result['suggested_title']
            safe_title = sanitize_filename(suggested_title)
            rename_needed = ai_result['should_rename']

#            print(f"📂 AI 建议分类: {category_path}")
            
            # 3. 执行移动 (或复制)
            ext = os.path.splitext(file_name)[1]
            final_file_name = f"{safe_title}{ext}" if rename_needed else file_name
            final_dir = os.path.join(target_root, category_path)
#            os.makedirs(final_dir, exist_ok=True)
#            final_path = os.path.join(final_dir, final_file_name)
#            print(f"copy file from: {file_path} to: {final_path}")
#            shutil.copy2(file_path, final_path) # 使用 copy2 保留元数据
            final_path = safe_copy(file_path, final_dir, final_file_name)
            sorted += 1
            
            # 4. 存入记忆库（方便以后查询）
            profile['metadata'].update({
                "hash": file_hash,
                "category": category_path,
                "title": suggested_title,
                "final_path": final_path
            })
            print(f"✅ 文件分类结果: {category_path}: {safe_title}")
            print(f"已处理: {total_processed} 个文件，未分类: {unsorted} 个，重复: {duplicates} 个，已分类: {sorted} 个")
#            profile['metadata']['hash'] = file_hash
            core.save_to_memory(profile)
            log_entry["result"] = "SORTED"
            log_entry["category"] = category_path
            log_entry["final_path"] = final_path
            record_log(log_entry)

    print("\n✅ 所有文件整理完毕！")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        source_dir = sys.argv[1]
        main(source_dir)