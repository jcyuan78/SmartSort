import os
import sys
import subprocess
import shutil
#import pypandoc
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
from urllib.parse import urljoin
import traceback
import re


current_path = os.getcwd()
temp_dir = os.path.join(current_path, "testdata\\temp")

def extra_chm(chm_path, output_path):
    """
    将 CHM 文件转换为 PDF
    原理：7z 解压 -> 找到主页 -> wkhtmltopdf 转换
    """
    # 1. 创建临时文件夹存放解压出的 HTML
#    temp_dir = chm_path + "_temp"
    os.makedirs(output_path, exist_ok=True)
    
    try:
        # 2. 使用 7-Zip 解压 CHM (假设你已安装 7z 并加入环境变量)
        # 如果没有 7z，Windows 下也可以尝试用 hh.exe -decompile
        print(f"📦 正在解压 CHM: {os.path.basename(chm_path)}")
        subprocess.run(['7z', 'x', chm_path, f'-o{output_path}', '-y'], 
                       check=True, stdout=subprocess.DEVNULL)
        
        # 3. 寻找主页（通常是 index.html, default.htm 或跟文件名相同）
        # 这里使用一种简单策略：找目录下最大的 html 文件，或者 index.html
        html_files = []
        for root, dirs, files in os.walk(output_path):
            for f in files:
                if f.lower().endswith(('.html', '.htm')):
                    html_files.append(os.path.join(root, f))
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
        return False, f"转换失败: {str(e)}"
    
# 转换一页html到pdf，如果遇到链接，则递归调用
def convert_html_page(entry_html, output_pdf, processed, out_pages):
    # 1. 解析 HTML，转换当前page
#    full_path = os.path.normpath(os.path.join(base_dir, href))

    index = out_pages.__len__() + 1
    out_page = f"{output_pdf}_part{index}.pdf"
    print(f"正在处理页面：{entry_html} => {out_page} ...")
    subprocess.run(['wkhtmltopdf', '--enable-local-file-access', '--encoding', 'utf-8', 
        entry_html, out_page], 
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out_pages.append(out_page)
    processed.append(entry_html)
    
    # 2. 解析 HTML，寻找链接，递归调用 convert_html_page
    with open(entry_html, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    base_dir = os.path.dirname(os.path.abspath(entry_html))
    for a in soup.find_all('a', href=True):
        href = a['href'].split('#')[0]  # 去掉锚点
        if not href or href.startswith(('http', 'mailto', 'javascript')):
            continue
        full_path = os.path.normpath(os.path.join(base_dir, href))
        if not os.path.exists(full_path) or full_path in processed:
            continue
        convert_html_page(full_path, output_pdf, processed, out_pages)


def smart_html_to_pdf(entry_html, output_pdf):
    processed = []
    out_pages = []
    try:
        # 1. 从入口 HTML 开始，递归爬取链接并转换每个页面为 PDF
        convert_html_page(entry_html, output_pdf, processed, out_pages)
        print(f"🔗 发现并编排了 {len(processed)} 个页面片段")

        # 3. 进行合并转换
        page_nr = out_pages.__len__()
        merger = PdfMerger()
        for pdf in out_pages:
            merger.append(pdf)
        merger.write(f"{output_pdf}.pdf")
        merger.close()

        # 删除中间结果
        for pdf in out_pages:
            os.remove(pdf)

        print(f"✅ 成功生成 PDF: {output_pdf}, 共 {page_nr} 页")
        return True, f"成功生成: {output_pdf}"

    except Exception as e:
        print(f"❌ 转换失败: {str(e)}")
        traceback.print_exc()
        return False, f"转换失败: {str(e)}"
    
def make_pages_to_pdf(src_path, pages, output_pdf):
    out_pages = []
    try:
        # 1. 从入口 HTML 开始，递归爬取链接并转换每个页面为 PDF
        for page in pages:
            entry_html = os.path.normpath(os.path.join(src_path, page['path']))

            index = out_pages.__len__() + 1
            out_page = os.path.join(temp_dir, f"page_{index}.pdf")
            print(f"正在处理页面：{entry_html} => {out_page} ...")
            subprocess.run(['wkhtmltopdf', '--enable-local-file-access', '--encoding', 'utf-8', 
                entry_html, out_page], 
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            out_pages.append(out_page)

        # 3. 进行合并转换
        page_nr = out_pages.__len__()
        merger = PdfMerger()
        for pdf in out_pages:
            merger.append(pdf)
        merger.write(f"{output_pdf}.pdf")
        merger.close()

        # 删除中间结果
        for pdf in out_pages:
            os.remove(pdf)

        print(f"✅ 成功生成 PDF: {output_pdf}, 共 {page_nr} 页")
        return True, f"成功生成: {output_pdf}"

    except Exception as e:
        print(f"❌ 转换失败: {str(e)}")
        traceback.print_exc()
        return False, f"转换失败: {str(e)}"    


#    finally:
        # 5. 清理临时文件夹
#        if os.path.exists(temp_dir):
#            shutil.rmtree(temp_dir)
def smart_html_to_pdf_1(entry_point_html, output_pdf):
    """
    entry_point_html: 电子书的入口文件（如 index.html）
    output_pdf: 最终生成的 PDF 路径
    """
    base_dir = os.path.dirname(os.path.abspath(entry_point_html))
    processed_files = [entry_point_html]
    pdf_pages = []
    
    # 1. 自动爬取链接（简单的递归深度为1，适合大多数电子书结构）
    try:
        with open(entry_point_html, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        index =1;    
        # 寻找所有指向本地 HTML 的链接
        for a in soup.find_all('a', href=True):
            href = a['href'].split('#')[0]  # 去掉锚点
            if not href or href.startswith(('http', 'mailto', 'javascript')):
                continue
            
            full_path = os.path.normpath(os.path.join(base_dir, href))
            if os.path.exists(full_path) and full_path not in processed_files:
                processed_files.append(full_path)
                out_page = f"{output_pdf}_part{index}.pdf"
                print(f"正在处理页面：{full_path} => {out_page} ...")
                subprocess.run(['wkhtmltopdf', '--enable-local-file-access', '--encoding', 'utf-8', 
                        full_path, out_page], 
                        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                pdf_pages.append(out_page)
                index += 1

        print(f"🔗 发现并编排了 {len(processed_files)} 个页面片段")

        # 2. 调用 pypandoc 进行合并转换
        # extra_args 可以添加样式、页码等高级配置
#        output = pypandoc.convert_file(
#            processed_files, 
#            'pdf', 
#            outputfile=output_pdf,
#            extra_args=[
#                '--pdf-engine=wkhtmltopdf', # 指定渲染引擎
#                '--metadata', 'title=SmartSort自动转换文档',
#                '--toc', # 自动生成目录
#                '--variable', 'margin-top=20mm'
#            ]
#        )
        merger = PdfMerger()
        for pdf in pdf_pages:
            merger.append(pdf)
        merger.write(f"{output_pdf}.pdf")
        merger.close()

        print(f"✅ 成功生成 PDF: {output_pdf}")
        return True, f"成功生成: {output_pdf}"

    except Exception as e:
        print(f"❌ 转换失败: {str(e)}")
        return False, f"转换失败: {str(e)}"
    

def parse_chm_contents(hhc_path, extract_dir):
    """
    解析 .hhc 文件并返回有序的 HTML 文件完整路径列表
    """
    ordered_files = []
    
    # 1. 尝试使用 GBK 编码读取（CHM 常见中文编码），失败则尝试 UTF-8
    content = ""
    try:
        with open(hhc_path, 'r', encoding='gbk', errors='ignore') as f:
            content = f.read()
            print(f"✅ 成功使用 GBK 编码读取 .hhc 文件: {hhc_path}")
    except Exception:
        with open(hhc_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            print(f"✅ 成功使用 UTF-8 编码读取 .hhc 文件: {hhc_path}")

    if not content:
        print(f"❌ 无法读取文件内容: {hhc_path}")
        return []

    try:
        # 2. 使用 BeautifulSoup 解析
        soup = BeautifulSoup(content, 'html.parser')
        
        # 3. 寻找所有包含页面信息的 <object> 标签
        # CHM 的目录项通常包裹在 <object type="text/sitemap"> 中
        objects = soup.find_all('OBJECT', attrs={'type': 'text/sitemap'})
        print(f"🔍 在 .hhc 中找到了 {len(objects)} 个目录项")
        
        for obj in objects:
            # 寻找 name="Local" 的 param 标签，它指向具体的 HTML 路径
            param_local = obj.find('param', attrs={'name': 'Local'})
            
            if param_local and 'value' in param_local.attrs:
                relative_path = param_local['value']
                
                # 4. 路径清洗：CHM 内部多使用反斜杠 \，需转为正斜杠 /
                relative_path = relative_path.replace('\\', '/')
                
                # 拼接成完整路径
                full_path = os.path.normpath(os.path.join(extract_dir, relative_path))
                
                # 5. 去重并检查文件是否存在（有些条目可能只指向书签或不存在）
                if os.path.exists(full_path) and full_path not in ordered_files:
                    # 确保是 HTML 文件
                    if full_path.lower().endswith(('.html', '.htm')):
                        ordered_files.append(full_path)

        print(f"✅ 从 .hhc 中提取了 {len(ordered_files)} 个有序页面")
        return ordered_files

    except Exception:
        print("❌ 解析 .hhc 时发生错误:")
        traceback.print_exc()
        return []

def fast_parse_hhc(hhc_path):
   
    # 1. 尝试使用 GBK 编码读取（CHM 常见中文编码），失败则尝试 UTF-8
    content = ""
    try:
        with open(hhc_path, 'r', encoding='gbk', errors='ignore') as f:
            content = f.read()
            print(f"✅ 成功使用 GBK 编码读取 .hhc 文件: {hhc_path}")
    except Exception:
        with open(hhc_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            print(f"✅ 成功使用 UTF-8 编码读取 .hhc 文件: {hhc_path}")

    if not content:
        print(f"❌ 无法读取文件内容: {hhc_path}")
        return []

    # 2. 匹配所有 <OBJECT ...> </OBJECT> 块
    # 使用 re.DOTALL 确保 . 可以匹配换行符，re.IGNORECASE 忽略大小写
    object_pattern = re.compile(r'<OBJECT[^>]*>(.*?)</OBJECT>', re.DOTALL | re.IGNORECASE)
    
    # 3. 在块内匹配 Name 和 Local 的参数
    # 重点匹配 value="xxx" 部分
    name_pattern = re.compile(r'<param\s+name="Name"\s+value="(.*?)"', re.IGNORECASE)
    local_pattern = re.compile(r'<param\s+name="Local"\s+value="(.*?)"', re.IGNORECASE)

    results = []
    
    for obj_chunk in object_pattern.findall(content):
        # 提取标题和路径
        name_match = name_pattern.search(obj_chunk)
        local_match = local_pattern.search(obj_chunk)
        
        if local_match:
            title = name_match.group(1) if name_match else "Unknown Title"
            path = local_match.group(1).replace('\\', '/') # 统一斜杠
            
            # 过滤掉不含 .htm 的非页面条目
            if path.lower().endswith(('.htm', '.html')):
                results.append({
                    "title": title,
                    "path": path
                })

    print(f"🚀 正则模式成功提取了 {len(results)} 个页面路径")
    return results


if __name__ == "__main__":
    if len(sys.argv) > 2:
        src_path = sys.argv[1]
        dst_path = sys.argv[2]
#        extra_chm(src_path, dst_path)
#        smart_html_to_pdf(src_path, dst_path)

#        pages = parse_chm_contents(src_path, "temp\\")
        pages = fast_parse_hhc(src_path)
        src_dir = os.path.dirname(src_path)
        make_pages_to_pdf(src_dir, pages, dst_path)

#        index = 1;
#        for page in pages:
#            print(f"page:[{index}], title: {page['title']}, path: {page['path']}")
#            index += 1

