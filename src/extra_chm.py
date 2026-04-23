import os
import sys
import subprocess
import shutil
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
from urllib.parse import urljoin
import traceback


temp_dir = "C:\\Users\\jcyua\\workspace\\SmartSort\\temp"

def extra_chm(chm_path, output_path):
    """
    将 CHM 文件转换为 PDF
    原理：7z 解压 -> 找到主页 -> wkhtmltopdf 转换
    """
    # 1. 创建临时文件夹存放解压出的 HTML
#    temp_dir = chm_path + "_temp"
    print(f"📦 正在解压 CHM: {os.path.basename(chm_path)} to {output_path}")
    os.makedirs(output_path, exist_ok=True)
    
    try:
        # 2. 使用 7-Zip 解压 CHM (假设你已安装 7z 并加入环境变量)
        # 如果没有 7z，Windows 下也可以尝试用 hh.exe -decompile
        print(f"📦 正在解压 CHM: {os.path.basename(chm_path)}")
        subprocess.run(['7z', 'x', chm_path, f'-o{output_path}', '-y'], 
                       check=True, stdout=subprocess.DEVNULL)
        
        # 3. 寻找主页（通常是 index.html, default.htm 或跟文件名相同）
        # 这里使用一种简单策略：找目录下最大的 html 文件，或者 index.html
#        html_files = []
#        for root, dirs, files in os.walk(output_path):
#            for f in files:
#                if f.lower().endswith(('.html', '.htm')):
#                    html_files.append(os.path.join(root, f))

        return True
        if not html_files:
            return False, "未能在 CHM 中找到 HTML 内容"

        # 排序：优先选择 index.html，否则选体积最大的
        html_files.sort(key=lambda x: (not x.lower().endswith('index.html'), -os.path.getsize(x)))
        main_html = html_files[0]

        # 4. 调用 wkhtmltopdf 转换为 PDF
        print(f"📑 正在转换为 PDF...")
        subprocess.run(['wkhtmltopdf', '--enable-local-file-access', main_html, output_pdf_path], 
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return True, "转换成功"
    
    except Exception as e:
        print(f"❌ 解压失败: {str(e)}")
        traceback.print_exc()
        return False, f"转换失败: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) > 2:
        src_path = sys.argv[1]
        dst_path = sys.argv[2]
        extra_chm(src_path, dst_path)
#        smart_html_to_pdf(src_path, dst_path)