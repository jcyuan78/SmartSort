import fitz  # PyMuPDF
from PIL import Image
import pandas as pd
import os
import easyocr
import io
import torch 
from transformers import BlipProcessor, BlipForConditionalGeneration

class LocalExtractor:
    _ocr_reader = None
    _image_captioner = None

    @staticmethod
    def get_ocr_reader():
        """加载 OCR 模型（第一次调用时执行）"""
        if LocalExtractor._ocr_reader is None:
            print("正在加载本地 OCR 模型 (支持中英文)...")
            # 指定支持中英文
            LocalExtractor._ocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=torch.cuda.is_available())
        return LocalExtractor._ocr_reader

    @staticmethod
    def get_image_captioner():
        """加载图片描述模型 (第一次调用时执行)"""
        if LocalExtractor._image_captioner is None:
            print("正在加载本地视觉模型 (BLIP)...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(device)
            LocalExtractor._image_captioner = (processor, model, device)
        return LocalExtractor._image_captioner

    @staticmethod
    def extract_text(file_path):
        """处理纯文本文件"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return (f.read(2000)),"text"  # 只取前2000字作为摘要

    @staticmethod
    def extract_pdf(file_path):
        """处理PDF：提取首页文字和元数据，如果是扫描件则做 OCR"""
        doc = fitz.open(file_path)
        text = ""
        is_scanned = True
        file_type = "pdf"
        
        # 1. 尝试直接提取前 2 页的文字
        for page in doc[:2]:
            text_content = page.get_text()
            if text_content.strip():
                text += text_content
                is_scanned = False
        
        # 2. 如果前2页都没有文字，判定为扫描件，启动本地 OCR
        if is_scanned and len(doc) > 0:
            print(f"检测到扫描版 PDF: {os.path.basename(file_path)}，启动本地 OCR...")
            reader = LocalExtractor.get_ocr_reader()
            
            # 只 OCR 第一页，避免太耗时
            page = doc[0]
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            
            # 使用 EasyOCR 读取
            result = reader.readtext(img_bytes, detail=0)
            text = " ".join(result)
            file_type = "pdf-ocr"
            
        return (f"[PDF 文本 ({'扫描件' if is_scanned else '电子书'})]: " + text[:2000]), file_type

    @staticmethod
    def extract_image_info(file_path):
        """处理图片：提取EXIF元数据，并使用 BLIP 生成图片描述"""
        print(f"正在智能分析图片: {os.path.basename(file_path)}...")
        
        # A. 提取基础元数据
        try:
            with Image.open(file_path) as img:
                basic_info = f"格式: {img.format}, 尺寸: {img.size}, 模式: {img.mode}"
                # B. 使用 BLIP 生成图片描述
                processor, model, device = LocalExtractor.get_image_captioner()
                # 预处理图片
                inputs = processor(img, return_tensors="pt").to(device)
                # 生成描述
                with torch.no_grad():
                    out = model.generate(**inputs)
                caption = processor.decode(out[0], skip_special_tokens=True)
                return (f"[图片基础信息]: {basic_info}\n[图片AI描述]: {caption}", "image")
                
        except Exception as e:
            return f"[图片解析失败]: {e}"
        
    @staticmethod
    def extract_table(file_path):
        """处理Excel/CSV：提取表头和前几行数据"""
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, nrows=5)
        else:
            df = pd.read_excel(file_path, nrows=5)
        return (f"列名: {list(df.columns)}\n数据样例: {df.values.tolist()}"),"table"