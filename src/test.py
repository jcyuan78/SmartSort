import os
import sys

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


def test_single_file(file_path):
    """
    测试单个文件的提取逻辑
    """
    if not os.path.exists(file_path):
        print(f"❌ 错误: 找不到文件 {file_path}")
        return

    print(f"--- 正在测试文件: {os.path.basename(file_path)} ---")
    
    # 1. 初始化核心（这会加载本地 Embedding 模型）
    core = SmartSortCore()
    brain = SmartBrain() # 初始化 AI 大脑（加载配置）
    
    # 2. 调用提取逻辑
    profile = core.generate_file_profile(file_path)
    
    if not profile:
        print("❌ 提取失败，请检查文件格式或 extractors.py 中的逻辑。")
        return

    print("✅ 提取成功!")
    print(f"ID (路径): {profile['id']}")
    print(f"元数据摘要:\n{profile['metadata']['summary']}")
        
    # 3. 检查向量（Embedding）
    embedding = profile['embedding']
    print(f"向量维度: {len(embedding)}") # 应该是一个固定长度的列表，如 384 或 768
    print(f"向量前5个数值: {embedding[:5]}")

    # 2. AI 决策分类
    existing = get_existing_dirs(target_root)
    category_path = brain.decide_category(profile['metadata']['summary'], existing)
    print(f"📂 AI 建议分类: {category_path}")
        
    # 4. 尝试模拟存入记忆并检索（可选）
    print("\n--- 正在测试记忆存储与检索 ---")
    core.save_to_memory(profile)
    print("已存入 ChromaDB。")
        
    # 模拟：搜索和自己最像的文件（应该是它自己）
    results = core.collection.query(
        query_embeddings=[embedding],
        n_results=1
    )
    print(f"检索测试结果: {results['ids'][0][0] == file_path and '匹配成功' or '匹配失败'}")

if __name__ == "__main__":
    # 允许从命令行传入路径：python tests/test_extraction.py ./data/my_doc.pdf
    if len(sys.argv) > 1:
        target = sys.argv[1]
        test_single_file(target)
    else:
        print("提示: 你可以通过命令行传入文件路径进行测试。")
        print("用法: python tests/test_extraction.py <文件路径>")