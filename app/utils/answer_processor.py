"""
RAG问答系统答案处理器

负责处理AI生成的答案，提取引用来源，计算置信度，格式化输出
"""
from typing import Dict, List, Optional, Any, Tuple
import re
import json
from datetime import datetime
from app.config import Config

class AnswerProcessor:
    """答案处理器类"""
    
    def __init__(self):
        """初始化答案处理器"""
        self.min_confidence = Config.RAG_MIN_CONFIDENCE
        self.max_answer_length = Config.RAG_MAX_ANSWER_LENGTH
        self.min_answer_length = Config.RAG_MIN_ANSWER_LENGTH
        
        # 置信度关键词映射
        self.confidence_keywords = {
            "高": 0.8,
            "中": 0.6,
            "低": 0.4,
            "very high": 0.9,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
            "very low": 0.3
        }

    def process_answer(
        self, 
        raw_answer: str, 
        context_chunks: List[Dict],
        question: str,
        literature_id: str
    ) -> Dict[str, Any]:
        """
        处理AI原始答案
        
        Args:
            raw_answer: AI生成的原始答案
            context_chunks: 相关文档块
            question: 用户问题
            literature_id: 文献ID
            
        Returns:
            Dict: 处理后的答案数据
        """
        try:
            # 解析答案结构
            parsed_answer = self._parse_answer_structure(raw_answer)
            
            # 提取引用来源
            sources = self._extract_sources(parsed_answer, context_chunks)
            
            # 计算置信度
            confidence = self._calculate_confidence(parsed_answer, sources, context_chunks)
            
            # 格式化答案
            formatted_answer = self._format_answer(parsed_answer["answer"])
            
            # 质量检验
            quality_score = self._assess_answer_quality(formatted_answer, sources, question)
            
            # 构建结果
            result = {
                "answer": formatted_answer,
                "sources": sources,
                "confidence": confidence,
                "quality_score": quality_score,
                "metadata": {
                    "literature_id": literature_id,
                    "question": question,
                    "timestamp": datetime.now().isoformat(),
                    "chunks_used": len(context_chunks),
                    "raw_answer": raw_answer
                }
            }
            
            # 验证结果
            if self._validate_answer(result):
                return result
            else:
                return self._create_fallback_answer(question, "validation_failed")
                
        except Exception as e:
            print(f"答案处理出错: {str(e)}")
            return self._create_fallback_answer(question, "processing_error")

    def _parse_answer_structure(self, raw_answer: str) -> Dict[str, str]:
        """
        解析答案结构
        
        Args:
            raw_answer: 原始答案
            
        Returns:
            Dict: 解析后的答案结构
        """
        parsed = {
            "answer": "",
            "sources": "",
            "confidence": "",
            "reasoning": ""
        }
        
        # 提取答案部分
        answer_match = re.search(r'\*\*答案：?\*\*\s*(.*?)(?=\*\*|$)', raw_answer, re.DOTALL)
        if answer_match:
            parsed["answer"] = answer_match.group(1).strip()
        
        # 提取引用来源部分
        sources_match = re.search(r'\*\*引用来源：?\*\*\s*(.*?)(?=\*\*|$)', raw_answer, re.DOTALL)
        if sources_match:
            parsed["sources"] = sources_match.group(1).strip()
        
        # 提取置信度部分
        confidence_match = re.search(r'\*\*置信度：?\*\*\s*(.*?)(?=\*\*|$)', raw_answer, re.DOTALL)
        if confidence_match:
            parsed["confidence"] = confidence_match.group(1).strip()
        
        # 如果没有找到结构化的答案，使用整个内容作为答案
        if not parsed["answer"]:
            parsed["answer"] = raw_answer.strip()
        
        return parsed

    def _extract_sources(self, parsed_answer: Dict[str, str], context_chunks: List[Dict]) -> List[Dict]:
        """
        提取引用来源
        
        Args:
            parsed_answer: 解析后的答案
            context_chunks: 文档块列表
            
        Returns:
            List[Dict]: 引用来源列表
        """
        sources = []
        
        # 从答案文本中查找引用标记
        answer_text = parsed_answer["answer"]
        source_text = parsed_answer["sources"]
        
        # 查找【来源X】标记
        source_refs = re.findall(r'【来源(\d+)】', answer_text + source_text)
        
        for ref_num in source_refs:
            try:
                source_index = int(ref_num) - 1  # 转换为0基索引
                if 0 <= source_index < len(context_chunks):
                    chunk = context_chunks[source_index]
                    
                    # 提取引用描述
                    ref_description = self._extract_source_description(source_text, ref_num)
                    
                    source_info = {
                        "source_id": ref_num,
                        "chunk_index": chunk.get("chunk_index", source_index),
                        "text": chunk.get("text", "").strip()[:500],  # 限制长度
                        "similarity": chunk.get("similarity", 0),
                        "description": ref_description,
                        "page_number": chunk.get("page_number"),
                        "section": chunk.get("section")
                    }
                    sources.append(source_info)
            except (ValueError, IndexError):
                continue
        
        # 如果没有找到明确的引用，使用相似度最高的块
        if not sources and context_chunks:
            for i, chunk in enumerate(context_chunks[:3]):  # 最多3个来源
                source_info = {
                    "source_id": str(i + 1),
                    "chunk_index": chunk.get("chunk_index", i),
                    "text": chunk.get("text", "").strip()[:500],
                    "similarity": chunk.get("similarity", 0),
                    "description": f"相关度最高的文档块{i + 1}",
                    "page_number": chunk.get("page_number"),
                    "section": chunk.get("section")
                }
                sources.append(source_info)
        
        return sources

    def _extract_source_description(self, source_text: str, ref_num: str) -> str:
        """
        提取引用来源的描述
        
        Args:
            source_text: 来源文本
            ref_num: 引用编号
            
        Returns:
            str: 来源描述
        """
        # 查找对应的来源描述
        pattern = rf'【来源{ref_num}】[：:]?\s*(.*?)(?=【来源|\n|$)'
        match = re.search(pattern, source_text)
        if match:
            description = match.group(1).strip()
            # 清理描述文本
            description = re.sub(r'^[-•·]\s*', '', description)  # 移除列表标记
            return description[:200]  # 限制长度
        
        return f"来源{ref_num}的相关内容"

    def _calculate_confidence(
        self, 
        parsed_answer: Dict[str, str], 
        sources: List[Dict],
        context_chunks: List[Dict]
    ) -> float:
        """
        计算答案置信度
        
        Args:
            parsed_answer: 解析后的答案
            sources: 引用来源
            context_chunks: 文档块
            
        Returns:
            float: 置信度分数 (0-1)
        """
        confidence_score = 0.5  # 基础分数
        
        # 1. 从AI明确给出的置信度提取
        ai_confidence = self._extract_ai_confidence(parsed_answer["confidence"])
        if ai_confidence:
            confidence_score = ai_confidence
        
        # 2. 基于引用来源质量调整
        if sources:
            avg_similarity = sum(s.get("similarity", 0) for s in sources) / len(sources)
            source_factor = min(avg_similarity * 1.2, 1.0)  # 相似度加权
            confidence_score = (confidence_score + source_factor) / 2
        
        # 3. 基于答案长度和结构调整
        answer_text = parsed_answer["answer"]
        if answer_text:
            # 长度适中的答案更可信
            length_factor = self._calculate_length_factor(len(answer_text))
            confidence_score *= length_factor
            
            # 结构化的答案更可信
            if self._has_good_structure(answer_text):
                confidence_score *= 1.1
        
        # 4. 基于文档块数量调整
        if len(context_chunks) >= 3:
            confidence_score *= 1.05  # 多个来源支持
        elif len(context_chunks) == 0:
            confidence_score *= 0.3  # 没有相关内容
        
        # 确保在有效范围内
        return max(0.1, min(1.0, confidence_score))

    def _extract_ai_confidence(self, confidence_text: str) -> Optional[float]:
        """
        从AI回答中提取置信度
        
        Args:
            confidence_text: 置信度文本
            
        Returns:
            Optional[float]: 置信度数值
        """
        if not confidence_text:
            return None
        
        # 查找关键词
        for keyword, score in self.confidence_keywords.items():
            if keyword in confidence_text.lower():
                return score
        
        # 查找数字
        number_match = re.search(r'(\d+(?:\.\d+)?)', confidence_text)
        if number_match:
            try:
                value = float(number_match.group(1))
                if value <= 1.0:
                    return value
                elif value <= 100:
                    return value / 100
            except ValueError:
                pass
        
        return None

    def _calculate_length_factor(self, length: int) -> float:
        """
        基于答案长度计算调整因子
        
        Args:
            length: 答案长度
            
        Returns:
            float: 长度调整因子
        """
        if length < self.min_answer_length:
            return 0.7  # 太短
        elif length > self.max_answer_length:
            return 0.8  # 太长
        elif 100 <= length <= 800:
            return 1.1  # 适中长度
        else:
            return 1.0  # 正常长度

    def _has_good_structure(self, text: str) -> bool:
        """
        检查答案是否有良好的结构
        
        Args:
            text: 答案文本
            
        Returns:
            bool: 是否有良好结构
        """
        structure_indicators = [
            r'\d+[.、]',  # 数字列表
            r'[一二三四五六七八九十][、.]',  # 中文数字列表
            r'[（(]\d+[）)]',  # 带括号的数字
            r'首先|其次|然后|最后|另外',  # 连接词
            r'第一|第二|第三',  # 序数词
            r'总结|综上|因此|所以'  # 结论词
        ]
        
        return sum(1 for pattern in structure_indicators if re.search(pattern, text)) >= 2

    def _format_answer(self, answer_text: str) -> str:
        """
        格式化答案文本
        
        Args:
            answer_text: 原始答案文本
            
        Returns:
            str: 格式化后的答案
        """
        if not answer_text:
            return "抱歉，无法生成答案。"
        
        # 清理文本
        formatted = re.sub(r'\s+', ' ', answer_text)  # 标准化空白字符
        formatted = re.sub(r'\n\s*\n', '\n\n', formatted)  # 规范化段落间距
        
        # 移除重复的标点符号
        formatted = re.sub(r'[。！？]{2,}', '。', formatted)
        formatted = re.sub(r'[,，]{2,}', '，', formatted)
        
        # 确保适当的长度
        if len(formatted) > self.max_answer_length:
            # 在句号处截断
            truncate_pos = formatted.rfind('。', 0, self.max_answer_length)
            if truncate_pos > self.max_answer_length * 0.8:
                formatted = formatted[:truncate_pos + 1]
            else:
                formatted = formatted[:self.max_answer_length] + "..."
        
        return formatted.strip()

    def _assess_answer_quality(self, answer: str, sources: List[Dict], question: str) -> Dict[str, float]:
        """
        评估答案质量
        
        Args:
            answer: 格式化后的答案
            sources: 引用来源
            question: 用户问题
            
        Returns:
            Dict[str, float]: 质量评分
        """
        quality_scores = {
            "relevance": 0.7,  # 相关性
            "completeness": 0.6,  # 完整性
            "accuracy": 0.8,  # 准确性
            "clarity": 0.7,  # 清晰度
            "citation": 0.5   # 引用质量
        }
        
        # 相关性评估
        question_keywords = self._extract_keywords(question)
        answer_keywords = self._extract_keywords(answer)
        keyword_overlap = len(set(question_keywords) & set(answer_keywords))
        if keyword_overlap > 0:
            quality_scores["relevance"] = min(1.0, 0.5 + keyword_overlap * 0.1)
        
        # 完整性评估
        if len(answer) >= 200:
            quality_scores["completeness"] = 0.8
        elif len(answer) >= 100:
            quality_scores["completeness"] = 0.7
        
        # 引用质量评估
        if sources:
            avg_similarity = sum(s.get("similarity", 0) for s in sources) / len(sources)
            quality_scores["citation"] = min(1.0, avg_similarity * 1.5)
        
        # 清晰度评估（基于结构和可读性）
        if self._has_good_structure(answer):
            quality_scores["clarity"] = 0.9
        
        return quality_scores

    def _extract_keywords(self, text: str) -> List[str]:
        """
        提取文本关键词
        
        Args:
            text: 输入文本
            
        Returns:
            List[str]: 关键词列表
        """
        # 简单的关键词提取（移除停用词）
        stopwords = {'的', '是', '在', '有', '和', '与', '对', '为', '了', '也', '可以', '能够', '这个', '那个', '什么', '如何', '怎么'}
        
        # 提取中文词汇和英文单词
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', text)
        english_words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # 过滤停用词和短词
        keywords = []
        for word in chinese_words + english_words:
            if len(word) >= 2 and word not in stopwords:
                keywords.append(word)
        
        return keywords[:10]  # 返回前10个关键词

    def _validate_answer(self, result: Dict[str, Any]) -> bool:
        """
        验证答案质量
        
        Args:
            result: 答案结果
            
        Returns:
            bool: 是否通过验证
        """
        answer = result.get("answer", "")
        confidence = result.get("confidence", 0)
        
        # 基本验证
        if len(answer) < self.min_answer_length:
            return False
        
        if confidence < self.min_confidence:
            return False
        
        # 检查是否包含错误内容
        error_indicators = ["抱歉", "无法", "不知道", "不清楚", "错误"]
        if any(indicator in answer[:50] for indicator in error_indicators):
            return False
        
        return True

    def _create_fallback_answer(self, question: str, error_type: str) -> Dict[str, Any]:
        """
        创建降级答案
        
        Args:
            question: 用户问题
            error_type: 错误类型
            
        Returns:
            Dict: 降级答案
        """
        fallback_messages = {
            "no_content": "抱歉，我在文献中没有找到与您的问题相关的内容。请尝试重新表述问题或查看预设问题。",
            "validation_failed": "抱歉，生成的答案质量不够理想。请重新提问或尝试更具体的问题。",
            "processing_error": "处理您的问题时出现了技术问题。请稍后重试。"
        }
        
        return {
            "answer": fallback_messages.get(error_type, "抱歉，无法处理您的问题。"),
            "sources": [],
            "confidence": 0.1,
            "quality_score": {"relevance": 0.1, "completeness": 0.1, "accuracy": 0.1, "clarity": 0.1, "citation": 0.1},
            "metadata": {
                "question": question,
                "timestamp": datetime.now().isoformat(),
                "error_type": error_type,
                "is_fallback": True
            }
        }

    def format_response_for_api(self, processed_answer: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化答案用于API响应
        
        Args:
            processed_answer: 处理后的答案
            
        Returns:
            Dict: API格式的响应
        """
        return {
            "answer": processed_answer["answer"],
            "sources": [
                {
                    "id": source["source_id"],
                    "text": source["text"][:300],  # 限制返回长度
                    "similarity": source["similarity"],
                    "description": source["description"],
                    "chunk_index": source["chunk_index"]
                }
                for source in processed_answer["sources"]
            ],
            "confidence": round(processed_answer["confidence"], 2),
            "metadata": {
                "timestamp": processed_answer["metadata"]["timestamp"],
                "quality": round(
                    sum(processed_answer["quality_score"].values()) / len(processed_answer["quality_score"]), 
                    2
                )
            }
        } 