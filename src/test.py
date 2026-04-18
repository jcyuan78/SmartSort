import os
import re
import sys
import json

# 将 src 目录加入路径，确保能 import 我们的模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core import SmartSortCore
from brain import SmartBrain

source_dir = "./data"
target_root = "./sorted_files"


def get_existing_dirs(target_root):
    if not os.path.exists(target_root): return []
    files =  [d for d in os.listdir(target_root) if os.path.isdir(os.path.join(target_root, d))]
    for f in files:
        print(f"现有分类: {f}")
    return files

def get_folder_count(target_root, category_path):
    full_path = os.path.join(target_root, category_path)
    if not os.path.exists(full_path):
        return 0
    return len([f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))])

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
    print(f"copy file from: {src} to: {final_path}")


def test_single_file(file_path):
    """
    测试单个文件的提取逻辑
    """
    core = SmartSortCore()
    brain = SmartBrain()
    
    # 定义目前支持的格式

    # 获取当前已经存在的文件夹作为参考
    def get_existing_dirs():
        if not os.path.exists(target_root): return []
        return [d for d in os.listdir(target_root) if os.path.isdir(os.path.join(target_root, d))]

    total_processed = 0
    unsorted = 0
    duplicates = 0
    sorted = 0

#    debug_count = 300
    print(f"\n🧠 正在处理: {file_path}")
#    ext = os.path.splitext(file_path)[1].lower()
    profile = core.generate_file_profile(file_path)
    
    # --- 格式检查, 不符合格式的文件待以后处理 ---
    #if ext not in SUPPORTED_EXTS:
    if not profile:
        print(f"⚠️ 跳过未知格式: {file_path} -> 移至待处理区")
        safe_copy(file_path, UNKNOWN_DIR, "")

        unsorted += 1
        return
    
    # 本地提取摘要，分析失败的文件也放入待处理区，避免干扰分类逻辑
    if (not profile.get('metadata')):
        print(f"⚠️ 文件解析失败: {file_path} -> 移至待处理区")
        safe_copy(file_path, UNKNOWN_DIR, "")

        unsorted += 1
        return
    
    # --- 重复检测，重复文件放入重复区 ---
    file_hash = core.calculate_hash(file_path) # 返回的file_hash是base64编码的字符串
    if core.is_duplicate(file_hash):
        print(f"♻️ 发现重复文件: {file_path} -> 移至重复区")
        safe_copy(file_path, DUPLICATE_DIR, "")
        duplicates += 1
        return
    
    print(f"✅ 文件解析结果: {profile['metadata']['summary']}...")
    print(f"\n")
    return
    # --- 新增：寻找历史参考 (Auto-Heal 准备) ---
    # 搜索最相似的 3 个历史记录
    search_results = core.collection.query(
        query_embeddings=[profile['embedding']],
        n_results=5, include=['metadatas','distances']
    )
    print(f"🔍 搜索历史记录, {search_results}")
            
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
    print(f"🔍 历史参考案例: {historical_context}")
    similarity_score = 1.0 # 默认完全不同
    # 2. AI 决策分类
    existing = get_existing_dirs()
    ai_result = brain.decide_category(
        file_summary = profile['metadata']['summary'], 
        current_filename = file_path,
        historical_context = historical_context,
    )
    category_path = ai_result['category']
    suggested_title = ai_result['suggested_title']
    safe_title = sanitize_filename(suggested_title)
    rename_needed = ai_result['should_rename']

#    print(f"📂 AI 建议分类: {category_path}")
    print(f"✅ 文件分类结果: {category_path}: {safe_title}")
            
    # 3. 执行移动 (或复制)
    ext = os.path.splitext(file_path)[1]
    final_file_path = f"{safe_title}{ext}" if rename_needed else file_path
    final_dir = os.path.join(target_root, category_path)
    print(f"copy file from: {file_path} to: {final_file_path}")
    sorted += 1
    
    # 4. 存入记忆库（方便以后查询）
    #print(f"检索测试结果: {results['ids'][0][0] == file_path and '匹配成功' or '匹配失败'}")

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
        target = sys.argv[1]
        test_single_file(target)
    else:
        print("提示: 你可以通过命令行传入文件路径进行测试。")
        print("用法: python tests/test_extraction.py <文件路径>")