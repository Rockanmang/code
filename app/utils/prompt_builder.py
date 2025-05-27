"""
RAG问答系统提示词构建器

负责构建高质量的提示词模板，确保AI返回准确、有引用的答案
"""
from typing import List, Dict, Optional, Any
import json
import re
from app.config import Config

class PromptBuilder:
    """提示词构建器类"""
    
    def __init__(self):
        """初始化提示词构建器"""
        self.max_context_tokens = Config.RAG_MAX_CONTEXT_TOKENS
        self.max_answer_length = Config.RAG_MAX_ANSWER_LENGTH
        
        # 基础系统角色模板
        self.system_role = """你是一个专业的学术文献助手，擅长基于提供的文献内容回答问题。请遵循以下原则：

1. **准确性**：基于提供的文献内容回答，不要编造信息
2. **完整性**：尽可能全面地回答问题，但保持简洁
3. **引用性**：明确标注引用来源，使用【来源X】格式
4. **中文回答**：使用中文回答问题
5. **结构化**：使用清晰的段落和要点组织答案

如果文献内容不足以回答问题，请明确说明并提供部分相关信息。"""

        # 输出格式规范
        self.output_format = """
请按以下格式回答：

**答案：**
[基于文献内容的详细回答]

**引用来源：**
- 【来源1】：[具体引用内容的简要描述]
- 【来源2】：[具体引用内容的简要描述]
（如果需要更多来源）

**置信度：**
[高/中/低] - [简要说明置信度的原因]
"""

    def build_qa_prompt(
        self, 
        question: str, 
        context_chunks: List[Dict], 
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        构建问答提示词
        
        Args:
            question: 用户问题
            context_chunks: 相关文档块列表
            conversation_history: 对话历史（可选）
            
        Returns:
            str: 完整的提示词
        """
        # 构建各个部分
        context_section = self._build_context_section(context_chunks)
        history_section = self._format_conversation_history(conversation_history) if conversation_history else ""
        
        # 组装完整提示词
        prompt_parts = [
            self.system_role,
            context_section,
            history_section,
            f"**用户问题：**\n{question}",
            self.output_format
        ]
        
        # 过滤空部分并连接
        prompt = "\n\n".join(part for part in prompt_parts if part.strip())
        
        # 优化长度
        prompt = self._optimize_prompt_length(prompt)
        
        return prompt

    def _build_context_section(self, context_chunks: List[Dict]) -> str:
        """
        构建上下文部分
        
        Args:
            context_chunks: 文档块列表，每个包含 {text, chunk_index, similarity, ...}
            
        Returns:
            str: 格式化的上下文部分
        """
        if not context_chunks:
            return "**相关文献内容：**\n暂无相关内容"
        
        context_parts = ["**相关文献内容：**"]
        
        for i, chunk in enumerate(context_chunks, 1):
            text = chunk.get('text', '').strip()
            similarity = chunk.get('similarity', 0)
            chunk_index = chunk.get('chunk_index', i)
            
            if text:
                # 格式化文档块
                chunk_header = f"【来源{i}】（相关度：{similarity:.2f}，块ID：{chunk_index}）"
                chunk_content = self._clean_text(text)
                
                context_parts.append(f"{chunk_header}\n{chunk_content}")
        
        return "\n\n".join(context_parts)

    def _format_conversation_history(self, history: List[Dict]) -> str:
        """
        格式化对话历史
        
        Args:
            history: 对话历史列表，每个包含 {role, content, timestamp}
            
        Returns:
            str: 格式化的对话历史
        """
        if not history:
            return ""
        
        history_parts = ["**对话历史：**"]
        
        # 只保留最近几轮对话，避免过长
        recent_history = history[-Config.RAG_CONVERSATION_MAX_TURNS:]
        
        for turn in recent_history:
            role = turn.get('role', 'unknown')
            content = turn.get('content', '').strip()
            
            if content:
                if role == 'user':
                    history_parts.append(f"用户：{content}")
                elif role == 'assistant':
                    # 简化AI回答，只保留核心内容
                    simplified_content = self._simplify_ai_response(content)
                    history_parts.append(f"助手：{simplified_content}")
        
        return "\n".join(history_parts)

    def _simplify_ai_response(self, response: str) -> str:
        """
        简化AI回答，提取关键信息
        
        Args:
            response: 原始AI回答
            
        Returns:
            str: 简化后的回答
        """
        # 提取"答案："部分的内容
        answer_match = re.search(r'\*\*答案：\*\*\s*(.+?)(?=\*\*|$)', response, re.DOTALL)
        if answer_match:
            answer = answer_match.group(1).strip()
            # 限制长度
            if len(answer) > 200:
                answer = answer[:200] + "..."
            return answer
        
        # 如果没有找到格式化的答案，直接截取前200字符
        return response[:200] + "..." if len(response) > 200 else response

    def _clean_text(self, text: str) -> str:
        """
        清理文本内容
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        # 去除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 去除特殊字符（保留中文、英文、数字、常用标点）
        text = re.sub(r'[^\u4e00-\u9fff\w\s.,;:!?()[\]{}"""''·—-]', '', text)
        
        # 限制长度
        max_chunk_length = 1000  # 每个文档块最大长度
        if len(text) > max_chunk_length:
            text = text[:max_chunk_length] + "..."
        
        return text.strip()

    def _optimize_prompt_length(self, prompt: str) -> str:
        """
        优化提示词长度，确保不超过token限制
        
        Args:
            prompt: 原始提示词
            
        Returns:
            str: 优化后的提示词
        """
        # 简单的token估算（1个中文字符≈2个token，1个英文单词≈1个token）
        estimated_tokens = self._estimate_tokens(prompt)
        
        if estimated_tokens <= self.max_context_tokens:
            return prompt
        
        # 如果超长，需要压缩上下文部分
        return self._compress_prompt(prompt)

    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量
        
        Args:
            text: 输入文本
            
        Returns:
            int: 估算的token数量
        """
        # 中文字符数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        # 英文单词数
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        
        # 其他字符数
        other_chars = len(text) - chinese_chars - english_words
        
        # token估算：中文字符*1.5 + 英文单词*1 + 其他字符*0.5
        estimated_tokens = int(chinese_chars * 1.5 + english_words * 1 + other_chars * 0.5)
        
        return estimated_tokens

    def _compress_prompt(self, prompt: str) -> str:
        """
        压缩提示词内容
        
        Args:
            prompt: 原始提示词
            
        Returns:
            str: 压缩后的提示词
        """
        # 简单的压缩策略：减少上下文块的数量和长度
        lines = prompt.split('\n')
        compressed_lines = []
        context_started = False
        context_count = 0
        max_context_blocks = 3  # 最多保留3个上下文块
        
        for line in lines:
            if '【来源' in line:
                context_started = True
                context_count += 1
                
            if context_started and context_count > max_context_blocks:
                # 跳过多余的上下文块
                if '【来源' in line or (context_count > max_context_blocks and not line.startswith('**')):
                    continue
                else:
                    context_started = False
            
            # 压缩长行
            if len(line) > 500:
                line = line[:500] + "..."
            
            compressed_lines.append(line)
        
        return '\n'.join(compressed_lines)

    def build_preset_questions_prompt(self, literature_title: str, literature_summary: str = "") -> List[str]:
        """
        构建预设问题列表
        
        Args:
            literature_title: 文献标题
            literature_summary: 文献摘要（可选）
            
        Returns:
            List[str]: 预设问题列表
        """
        base_questions = [
            "这篇文献的主要论点是什么？",
            "文献中使用了哪些研究方法？",
            "这项研究有什么创新点和贡献？",
            "研究存在哪些局限性？",
            "主要结论和发现是什么？",
            "文献的理论框架是什么？",
            "研究的实际应用价值如何？",
            "文献中提到了哪些未来研究方向？"
        ]
        
        # 根据文献标题生成个性化问题
        if literature_title:
            title_based_questions = [
                f"请解释《{literature_title}》这篇文献的核心内容",
                f"《{literature_title}》与其他相关研究有什么区别？"
            ]
            base_questions.extend(title_based_questions)
        
        return base_questions[:8]  # 返回最多8个问题

    def build_error_response_prompt(self, error_type: str, question: str) -> str:
        """
        构建错误响应提示词
        
        Args:
            error_type: 错误类型
            question: 用户问题
            
        Returns:
            str: 错误响应内容
        """
        error_responses = {
            "no_content": f"抱歉，我在文献中没有找到与问题「{question}」相关的内容。请尝试：\n1. 使用不同的关键词重新提问\n2. 确认问题是否与文献主题相关\n3. 查看预设问题获取灵感",
            "api_error": f"抱歉，AI服务暂时不可用。请稍后重试您的问题：「{question}」",
            "context_too_long": f"问题「{question}」涉及的内容较多，请尝试将问题分解为更具体的小问题。",
            "low_confidence": f"基于现有文献内容，我对问题「{question}」的回答置信度较低。建议查阅更多相关资料。"
        }
        
        return error_responses.get(error_type, f"处理问题「{question}」时出现未知错误，请重试。")

    def validate_prompt_quality(self, prompt: str) -> Dict[str, Any]:
        """
        验证提示词质量
        
        Args:
            prompt: 提示词内容
            
        Returns:
            Dict: 质量评估结果
        """
        validation_result = {
            "is_valid": True,
            "issues": [],
            "token_count": self._estimate_tokens(prompt),
            "has_context": "相关文献内容" in prompt,
            "has_format": "**答案：**" in prompt
        }
        
        # 检查长度
        if validation_result["token_count"] > self.max_context_tokens:
            validation_result["issues"].append("提示词过长")
            validation_result["is_valid"] = False
        
        # 检查必要组件
        if not validation_result["has_context"]:
            validation_result["issues"].append("缺少上下文内容")
        
        if not validation_result["has_format"]:
            validation_result["issues"].append("缺少输出格式规范")
        
        return validation_result 