import os
import sys
import hashlib
import base64
from extractors import LocalExtractor
from sentence_transformers import SentenceTransformer
import chromadb

class SmartSortCore:
    def __init__(self):
        # 加载本地轻量级模型 (支持中英文)
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        # 初始化本地向量数据库
        self.client = chromadb.PersistentClient(path="./smartsort_db")
        self.collection = self.client.get_or_create_collection(name="file_memory")

    def generate_file_profile(self, file_path):
        """为文件创建本地画像"""
        ext = os.path.splitext(file_path)[1].lower()
        content_summary = ""
        file_type = "unknown"
        
        try:
            if ext in ['.txt', '.md', '.py']:
                content_summary,file_type = LocalExtractor.extract_text(file_path)
            elif ext == '.pdf':
                content_summary,file_type = LocalExtractor.extract_pdf(file_path)
            elif ext in ['.jpg', '.png', '.jpeg', '.gif']:
                content_summary,file_type = LocalExtractor.extract_image_info(file_path)
            elif ext in ['.csv', '.xlsx']:
                content_summary,file_type = LocalExtractor.extract_table(file_path)
            elif ext in ['.docx', '.doc']:
                content_summary, file_type = LocalExtractor.extract_word(file_path)
            elif ext in ['.pptx', '.ppt']:
                content_summary, file_type = LocalExtractor.extract_pptx(file_path)
            elif ext in ['.html', '.htm']:
                content_summary, file_type = LocalExtractor.extract_html(file_path)
            elif ext == '.epub':
                content_summary, file_type = LocalExtractor.extract_epub(file_path)            
            else :
                return None
            
            # 组合元数据
            profile = f"文件名: {os.path.basename(file_path)}\n内容摘要: {content_summary}"
            
            # 生成向量
            embedding = self.model.encode(profile).tolist()
            
            return {
                "id": file_path,
                "type": file_type,
                "embedding": embedding,
                "metadata": {"summary": profile[:500], "path": file_path}
            }
        except Exception as e:
            print(f"解析文件 {file_path} 失败: {e}")
            return None

    def save_to_memory(self, file_info):
        """存入向量库，方便后续分类一致性检查"""
        if file_info:
            self.collection.add(
                embeddings=[file_info["embedding"]],
                documents=[file_info["metadata"]["summary"]],
                ids=[file_info["id"]],
                metadatas=[file_info["metadata"]]
            )

    @staticmethod
    def calculate_hash(file_path):
        """计算文件的 SHA256 指纹"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # 分块读取，防止大文件撑爆内存
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        # 1. 获取原始的二进制字节码 (digest)
        digest = sha256_hash.digest()
        
        # 2. 转换为 Base64 编码
        # .decode('utf-8') 是为了将 bytes 转换为普通的字符串，方便存入 CSV
        b64_hash = base64.b64encode(digest).decode('utf-8')
        return b64_hash
#        return sha256_hash.hexdigest()

    def is_duplicate(self, file_hash):
        """检查哈希值是否已在数据库中"""
        results = self.collection.get(where={"hash": file_hash})
        return len(results['ids']) > 0