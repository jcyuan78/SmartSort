import os
from core import SmartSortCore
from brain import SmartBrain

def search_files(query_text):
    core = SmartSortCore()
    brain = SmartBrain()

    llm_terms = brain.generate_search_terms(query_text)

# 1. 构造语义查询文本（将关键词合并，增加检索权重）
    search_query = " ".join(llm_terms.get('keywords', []) + llm_terms.get('tech_terms', []))
    
    # 2. 构造元数据过滤器
    # 如果 LLM 识别出了类别，则进行硬过滤，否则不设限
    metadata_filter = None
    if llm_terms.get('category'):
        metadata_filter = {"category": llm_terms['category']}

    print(f"🔍 搜索关键词: '{search_query}'，元数据过滤: {metadata_filter}")
    # 3. 执行查询
    results = core.query_files(search_query, metadata_filter, top_k=5)
    print(f"🔍 检索结果: '{results}'...")
    for file in results:
        print(f"文件: {file['filename']}")
        print(f"位置: {file['path']}")
        print(f"类别: {file['category']}")
        print(f"摘要预览: {file['summary']}...")
        print(f"相关度评分: {file['similarity']}%")
        print("-" * 50)
#    return format_results(results)


def format_results(results):
    """格式化输出检索到的文件信息"""
    formatted = []
    if not results['ids']:
        return formatted
        
    for i in range(len(results['ids'][0])):
        item = {
            "id": results['ids'][0][i],
            "document": results['documents'][0][i],
            "metadata": results['metadatas'][0][i],
            "distance": results['distances'][0][i] # 距离越小，相关度越高
        }
        formatted.append(item)
    return formatted
    
    print(f"🔍 正在检索: '{query_text}'...")
    
    # 1. 将搜索词转化为向量
    query_embedding = core.model.encode(query_text).tolist()
    
    # 2. 在 ChromaDB 中进行语义搜索
    # n_results=5 表示返回最相关的 5 个结果
    results = core.collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        include=['metadatas', 'distances']
    )
    
    print("\n✨ 找到以下相关文件：")
    print("-" * 50)
    
    found = False
    for i in range(len(results['ids'][0])):
        metadata = results['metadatas'][0][i]
        distance = results['distances'][0][i]
        
        # 距离越小，相似度越高（通常 < 0.5 说明非常相关）
        if distance < 1.2: 
            found = True
            print(f"文件: {os.path.basename(metadata['path'])}")
            print(f"位置: {metadata['category']}")
            print(f"摘要预览: {metadata['summary'][:60]}...")
            print(f"相关度评分: {round((2 - distance) * 50, 1)}%") # 简单的打分逻辑
            print("-" * 50)
            
    if not found:
        print("抱歉，没有找到匹配的文件。")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        search_query = " ".join(sys.argv[1:])
        search_files(search_query)
    else:
        user_input = input("请输入您想查找的内容（例如：含有飞机的照片）：")
        search_files(user_input)