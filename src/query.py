# 假设只查询了一个 profile['embedding']
results = core.collection.query(
    query_embeddings=[profile['embedding']],
    n_results=1
)

# 1. 检查是否有结果返回
if results['distances'] and len(results['distances'][0]) > 0:
    # 2. 提取第一个匹配项的距离值
    similarity_score = results['distances'][0][0]
    
    # 3. 根据距离做逻辑判断
    if similarity_score < 0.4:
        print("发现高度相似的历史分类！")
    else:
        print("这是一个较新的内容领域。")