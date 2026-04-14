import json
import os
from openai import OpenAI # DeepSeek 兼容 OpenAI 格式
import google.generativeai as genai

class SmartBrain:
    def __init__(self, config_path="config.json"):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"找不到配置文件: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.active = self.config['active_model']
        self.model_cfg = self.config['models'][self.active]
        print(f"🧠 SmartSort 已唤醒，当前使用大脑: {self.active.upper()}")

    def _call_llm(self, prompt):
        """统一调用接口"""
        if self.active == "deepseek":
            client = OpenAI(api_key=self.model_cfg['api_key'], 
                            base_url=self.model_cfg['base_url'])
            response = client.chat.completions.create(
                model=self.model_cfg['model_name'],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        
        elif self.active == "gemini":
            genai.configure(api_key=self.model_cfg['api_key'])
            model = genai.GenerativeModel(self.model_cfg['model_name'])
            response = model.generate_content(prompt)
            return response.text

#     def decide_category(self, file_summary, existing_categories):
#         """
#         核心决策：根据文件摘要和现有分类，返回目标文件夹路径
#         """
#         prompt = f"""
# 你是一个专业的文件整理助手 SmartSort。
# 任务：根据给出的文件摘要，决定该文件应该放入哪个文件夹。

# [现有文件夹列表]:
# {existing_categories if existing_categories else "目前尚无分类，请根据内容创建第一个"}

# [待分类文件摘要]:
# {file_summary}

# [规则]:
# 1. 如果摘要中包含英文描述（如图片 AI 描述），请先理解其含义。
# 2. 优先匹配现有文件夹。如果没有合适的，请创建一个简洁的中文文件夹名。
# 3. 返回格式必须为纯路径，例如：账务/2026/收据 或 学习/数理逻辑。
# 4. 文件夹层级建议不要超过3层。

# 请只返回文件夹路径，不要有任何解释文字。
# """
#         return self._call_llm(prompt).strip()

    def decide_category(self, file_summary, current_filename, historical_context,
                        existing_info="", similarity_score=1.0):
        """
        要求 LLM 同时决定分类路径、建议标题，并判断是否需要更名
        file_summary: 待分类摘要
        current_filename: 当前文件名（含后缀）
        existing_info: 包含现有文件夹及其文件数量、相似案例的字典
        similarity_score: ChromaDB 返回的距离 (越小越像)
        """
        # 构建参考案例字符串
        reference_str = ""
        if historical_context:
            reference_str = "\n".join([
                f"- 类似文件摘要: {item['summary'][:100]}, 已存入文件夹: {item['category']}, 该文件夹中文件数: {item['count']}, 相似度: {item['similarity']}, 语义差异: {item['distinct']}  "
                for item in historical_context
            ])
        else:
            reference_str = "无（这是该类别的第一个文件）"

#        categories_str = ", ".join(existing_categories) if existing_categories else "无"
        # 判定语义差异
#        is_distinct = "高 (内容差异较大)" if similarity_score > 0.4 else "低 (内容很接近)"


        
        prompt = f"""
你是一个专业的文件整理助手 SmartSort。请根据摘要和参考信息输出分类。
任务：分析文件摘要，决定其应该放入哪个文件夹（分类路径）和其正式标题。

[待分类文件摘要]:{file_summary}
[当前文件名]: {current_filename}
[历史参考案例（来自数据库）]: 
{reference_str}

[规则]:
1. 如果摘要中包含英文描述（如图片 AI 描述），请先理解其含义。
2. 分类路径：优先匹配现有文件夹（分类），或创建新的分类路径（如：工作/合同）。
2. 语义隔离：如果[语义差异度]为“高”，严禁放入参考案例的文件夹，必须开辟新类别。
3. 容量封顶：如果某个现有文件夹文件数已达上限（50个），请在该路径下细分子目录，或创建平行的新类别。
4. 精细化：避免使用“其他”、“杂项”等模糊词汇。
5. 建议标题：根据内容提取一个准确、简短的中文标题（不含后缀）。
6. 判断更名：如果当前文件名是乱码、日期或无法反映内容，请建议更名。
7. 必须只返回一个 JSON 对象，格式如下：
请返回 JSON:
{{
  "category": "精细的路径",
  "suggested_title": "文件名",
  "should_rename": true/false,
  "reason": "为何选择此类或为何新开一类"
}}

"""
#        print(f"prompt: {prompt}")
        response_text = self._call_llm(prompt)
        try:
            # 提取并清理 JSON 字符串（防止 AI 返回 Markdown 代码块）
#            clean_json = response_text.strip().replace('```json', '').replace('```', '')
#            print(f"LLM 原始响应: {response_text}")
            return json.loads(response_text)
        except Exception as e:
            print(f"❌ JSON 解析失败: {e}")
            return {
                "category": "系统管理/未分类",
                "suggested_title": current_filename.split('.')[0],
                "should_rename": False,
                "reason": "LLM 响应无法解析，默认分类为未分类，保持原名"
            }

def decide_smart_category(self, file_summary, existing_info, similarity_score):
        """
        file_summary: 待分类摘要
        existing_info: 包含现有文件夹及其文件数量、相似案例的字典
        similarity_score: ChromaDB 返回的距离 (越小越像)
        """
        
        # 判定语义差异
        is_distinct = "高 (内容差异较大)" if similarity_score > 0.4 else "低 (内容很接近)"
        
        prompt = f"""
你是一个精细的文件管理助手。请根据摘要和参考信息输出分类 JSON。

[待分类文件摘要]: {file_summary}
[语义差异度]: {is_distinct} (评分: {similarity_score})

[参考案例与容量]:
{existing_info}

[特殊规则]:
1. **语义隔离**：如果【语义差异度】为“高”，严禁放入参考案例的文件夹，必须开辟新类别。
2. **容量封顶**：如果某个现有文件夹文件数已达上限（如15-20个），请在该路径下细分子目录，或创建平行的新类别。
3. **精细化**：避免使用“其他”、“杂项”等模糊词汇。

请返回 JSON:
{{
  "category": "精细的路径",
  "suggested_title": "文件名",
  "should_rename": true/false,
  "reason": "为何选择此类或为何新开一类"
}}
"""
        # 调用之前配置好的 _call_llm_json (response_format={"type": "json_object"})
        return self._call_llm_json(prompt)        

def decide_with_consistency(self, file_summary, existing_categories, historical_context):
        """
        带有一致性检查的决策逻辑
        historical_context: 格式为 [{'summary': '...', 'category': '...'}, ...]
        """
        # 构建参考案例字符串
        reference_str = ""
        if historical_context:
            reference_str = "\n".join([
                f"- 类似文件摘要: {item['summary'][:100]}... -> 已存入文件夹: {item['category']}" 
                for item in historical_context
            ])
        else:
            reference_str = "无（这是该类别的第一个文件）"

        prompt = f"""
你是一个专业的文件整理助手 SmartSort，现在正在执行【一致性校准】模式。

[当前任务]
为新文件决定最合适的中文文件夹路径。

[现有文件夹列表]
{", ".join(existing_categories) if existing_categories else "无"}

[历史参考案例（来自数据库）]
{reference_str}

[待分类文件摘要]
{file_summary}

[规则]
1. **一致性优先**：如果待分类文件与“历史参考案例”中的文件语义高度相似，请尽量沿用相同的路径。
2. **逻辑自愈**：如果你发现现有的某个文件夹名称不够准确，可以建议一个更好的路径，但要确保同类文件未来都能对齐。
3. **返回格式**：只返回路径字符串，如：工作/合同/2026。

请直接输出路径：
"""
        return self._call_llm(prompt).strip().replace('`', '').replace('"', '')