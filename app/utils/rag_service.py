"""
RAG问答系统核心服务

统筹整个RAG问答流程，协调各个组件完成智能问答
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import traceback

# 导入相关组件
from app.utils.embedding_service import embedding_service
from app.utils.vector_store import vector_store
from app.utils.prompt_builder import PromptBuilder
from app.utils.answer_processor import AnswerProcessor
from app.config import Config

# Google AI 相关导入
import google.generativeai as genai

class RAGService:
    """RAG问答系统核心服务类"""
    
    def __init__(self):
        """初始化RAG服务"""
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.prompt_builder = PromptBuilder()
        self.answer_processor = AnswerProcessor()
        
        # 配置参数
        self.max_context_tokens = Config.RAG_MAX_CONTEXT_TOKENS
        self.top_k_retrieval = Config.RAG_TOP_K_RETRIEVAL
        self.ai_timeout = Config.RAG_AI_TIMEOUT
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        
        # 初始化Google AI
        self._init_google_ai()

    def _init_google_ai(self):
        """初始化Google AI服务"""
        try:
            # 配置Google AI
            genai.configure(api_key=Config.GOOGLE_API_KEY)
            
            # 创建生成模型
            self.model = genai.GenerativeModel('gemini-pro')
            
            self.logger.info("Google AI服务初始化成功")
        except Exception as e:
            self.logger.error(f"Google AI服务初始化失败: {str(e)}")
            self.model = None

    async def process_question(
        self,
        question: str,
        literature_id: str,
        group_id: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        处理用户问题的完整RAG流程
        
        Args:
            question: 用户问题
            literature_id: 文献ID
            group_id: 研究组ID
            session_id: 会话ID（可选）
            conversation_history: 对话历史（可选）
            top_k: 检索数量（可选）
            
        Returns:
            Dict: 处理结果
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"开始处理问题: {question[:50]}... (文献ID: {literature_id})")
            
            # 1. 问题预处理和验证
            validated_question = self._preprocess_question(question)
            if not validated_question:
                return self._create_error_response("invalid_question", question)
            
            # 2. 并行执行Embedding生成和历史处理
            embedding_task = self._generate_question_embedding(validated_question)
            history_task = self._process_conversation_history(conversation_history)
            
            # 等待并行任务完成
            question_embedding, processed_history = await asyncio.gather(
                embedding_task, history_task, return_exceptions=True
            )
            
            # 检查并行任务结果
            if isinstance(question_embedding, Exception):
                self.logger.error(f"Embedding生成失败: {str(question_embedding)}")
                return self._create_error_response("embedding_failed", question)
            
            if isinstance(processed_history, Exception):
                self.logger.warning(f"历史处理失败: {str(processed_history)}")
                processed_history = []
            
            # 3. 检索相关文档块
            context_chunks = await self._retrieve_relevant_chunks(
                question_embedding, literature_id, group_id, top_k or self.top_k_retrieval
            )
            
            if not context_chunks:
                return self._create_error_response("no_relevant_content", question)
            
            # 4. 构建提示词
            prompt = self.prompt_builder.build_qa_prompt(
                validated_question, context_chunks, processed_history
            )
            
            # 验证提示词质量
            prompt_validation = self.prompt_builder.validate_prompt_quality(prompt)
            if not prompt_validation["is_valid"]:
                self.logger.warning(f"提示词质量问题: {prompt_validation['issues']}")
                # 尝试压缩提示词
                prompt = self.prompt_builder._compress_prompt(prompt)
            
            # 5. 调用AI生成答案
            raw_answer = await self._generate_ai_answer(prompt)
            if not raw_answer:
                return self._create_error_response("ai_generation_failed", question)
            
            # 6. 处理答案
            processed_answer = self.answer_processor.process_answer(
                raw_answer, context_chunks, validated_question, literature_id
            )
            
            # 7. 添加元数据
            processing_time = (datetime.now() - start_time).total_seconds()
            processed_answer["metadata"].update({
                "session_id": session_id,
                "group_id": group_id,
                "processing_time": processing_time,
                "prompt_tokens": self.prompt_builder._estimate_tokens(prompt),
                "chunks_retrieved": len(context_chunks)
            })
            
            self.logger.info(f"问题处理完成，耗时: {processing_time:.2f}秒")
            return processed_answer
            
        except Exception as e:
            self.logger.error(f"RAG处理出错: {str(e)}\n{traceback.format_exc()}")
            return self._create_error_response("system_error", question)

    def _preprocess_question(self, question: str) -> Optional[str]:
        """
        预处理用户问题
        
        Args:
            question: 原始问题
            
        Returns:
            Optional[str]: 处理后的问题，如果无效则返回None
        """
        if not question or not question.strip():
            return None
        
        # 清理和标准化问题
        cleaned_question = question.strip()
        
        # 长度检查
        if len(cleaned_question) < 2:
            return None
        if len(cleaned_question) > 1000:
            cleaned_question = cleaned_question[:1000] + "..."
        
        # 移除多余的空白字符
        cleaned_question = ' '.join(cleaned_question.split())
        
        return cleaned_question

    async def _generate_question_embedding(self, question: str) -> List[float]:
        """
        生成问题的embedding
        
        Args:
            question: 用户问题
            
        Returns:
            List[float]: 问题的embedding向量
        """
        try:
            # 使用异步方式生成embedding
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                self.embedding_service.generate_query_embedding, 
                question
            )
            return embedding
        except Exception as e:
            self.logger.error(f"生成问题embedding失败: {str(e)}")
            raise

    async def _process_conversation_history(self, history: Optional[List[Dict]]) -> List[Dict]:
        """
        处理对话历史
        
        Args:
            history: 原始对话历史
            
        Returns:
            List[Dict]: 处理后的对话历史
        """
        if not history:
            return []
        
        try:
            # 过滤和清理历史记录
            processed_history = []
            for turn in history[-Config.RAG_CONVERSATION_MAX_TURNS:]:
                if isinstance(turn, dict) and turn.get("content"):
                    processed_turn = {
                        "role": turn.get("role", "user"),
                        "content": turn["content"][:500],  # 限制长度
                        "timestamp": turn.get("timestamp", "")
                    }
                    processed_history.append(processed_turn)
            
            return processed_history
        except Exception as e:
            self.logger.warning(f"处理对话历史失败: {str(e)}")
            return []

    async def _retrieve_relevant_chunks(
        self, 
        question_embedding: List[float], 
        literature_id: str, 
        group_id: str, 
        top_k: int
    ) -> List[Dict]:
        """
        检索相关文档块
        
        Args:
            question_embedding: 问题embedding
            literature_id: 文献ID
            group_id: 研究组ID
            top_k: 检索数量
            
        Returns:
            List[Dict]: 相关文档块列表
        """
        try:
            # 使用异步方式检索
            loop = asyncio.get_event_loop()
            chunks = await loop.run_in_executor(
                None,
                self.vector_store.search_similar_chunks,
                question_embedding,
                group_id,
                literature_id,
                top_k * 2  # 检索更多候选，然后重排序
            )
            
            # 重排序和过滤
            reranked_chunks = self._rerank_chunks(chunks, top_k)
            
            return reranked_chunks
            
        except Exception as e:
            self.logger.error(f"检索相关文档块失败: {str(e)}")
            return []

    def _rerank_chunks(self, chunks: List[Dict], top_k: int) -> List[Dict]:
        """
        重排序文档块
        
        Args:
            chunks: 原始文档块
            top_k: 返回数量
            
        Returns:
            List[Dict]: 重排序后的文档块
        """
        if not chunks:
            return []
        
        # 基于相似度和其他因素重排序
        scored_chunks = []
        for chunk in chunks:
            similarity = chunk.get("similarity", 0)
            text_length = len(chunk.get("text", ""))
            
            # 综合评分：相似度 + 长度因子
            length_factor = min(text_length / 500, 1.0)  # 适中长度加分
            score = similarity * 0.8 + length_factor * 0.2
            
            chunk["final_score"] = score
            scored_chunks.append(chunk)
        
        # 按评分排序并返回top_k
        scored_chunks.sort(key=lambda x: x["final_score"], reverse=True)
        return scored_chunks[:top_k]

    async def _generate_ai_answer(self, prompt: str) -> Optional[str]:
        """
        使用AI生成答案
        
        Args:
            prompt: 完整的提示词
            
        Returns:
            Optional[str]: AI生成的答案
        """
        if not self.model:
            self.logger.error("Google AI模型未初始化")
            return None
        
        try:
            # 使用异步方式调用AI
            loop = asyncio.get_event_loop()
            
            # 生成配置
            generation_config = genai.types.GenerationConfig(
                temperature=0.3,  # 较低的温度保证准确性
                top_p=0.8,
                max_output_tokens=2000,
                candidate_count=1
            )
            
            # 异步调用
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt, 
                    generation_config=generation_config
                )
            )
            
            if response and response.text:
                return response.text
            else:
                self.logger.warning("AI返回空响应")
                return None
                
        except Exception as e:
            self.logger.error(f"AI生成答案失败: {str(e)}")
            return None

    def get_preset_questions(self, literature_id: str, literature_title: str = "") -> List[str]:
        """
        获取预设问题列表
        
        Args:
            literature_id: 文献ID
            literature_title: 文献标题
            
        Returns:
            List[str]: 预设问题列表
        """
        try:
            return self.prompt_builder.build_preset_questions_prompt(literature_title)
        except Exception as e:
            self.logger.error(f"生成预设问题失败: {str(e)}")
            return [
                "这篇文献的主要论点是什么？",
                "文献中使用了哪些研究方法？",
                "这项研究有什么创新点？",
                "研究存在哪些局限性？",
                "主要结论是什么？"
            ]

    def _create_error_response(self, error_type: str, question: str) -> Dict[str, Any]:
        """
        创建错误响应
        
        Args:
            error_type: 错误类型
            question: 用户问题
            
        Returns:
            Dict: 错误响应
        """
        error_messages = {
            "invalid_question": "问题格式不正确，请重新输入。",
            "embedding_failed": "问题理解失败，请重试。",
            "no_relevant_content": "未找到相关内容，请尝试其他问题。",
            "ai_generation_failed": "AI服务暂时不可用，请稍后重试。",
            "system_error": "系统错误，请联系管理员。"
        }
        
        return {
            "answer": error_messages.get(error_type, "未知错误"),
            "sources": [],
            "confidence": 0.1,
            "quality_score": {
                "relevance": 0.1,
                "completeness": 0.1,
                "accuracy": 0.1,
                "clarity": 0.1,
                "citation": 0.1
            },
            "metadata": {
                "question": question,
                "timestamp": datetime.now().isoformat(),
                "error_type": error_type,
                "is_error": True
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        系统健康检查
        
        Returns:
            Dict: 健康检查结果
        """
        health_status = {
            "status": "healthy",
            "components": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 检查Embedding服务
            try:
                test_embedding = await self._generate_question_embedding("测试")
                health_status["components"]["embedding_service"] = {
                    "status": "healthy" if test_embedding else "unhealthy",
                    "details": f"返回{len(test_embedding)}维向量" if test_embedding else "无法生成embedding"
                }
            except Exception as e:
                health_status["components"]["embedding_service"] = {
                    "status": "unhealthy",
                    "details": str(e)
                }
            
            # 检查向量数据库
            try:
                vector_health = self.vector_store.health_check()
                health_status["components"]["vector_store"] = vector_health
            except Exception as e:
                health_status["components"]["vector_store"] = {
                    "status": "unhealthy",
                    "details": str(e)
                }
            
            # 检查AI服务
            try:
                if self.model:
                    # 简单测试
                    test_response = await self._generate_ai_answer("你好，这是一个测试。请简单回复。")
                    health_status["components"]["ai_service"] = {
                        "status": "healthy" if test_response else "unhealthy",
                        "details": "AI服务正常" if test_response else "AI服务无响应"
                    }
                else:
                    health_status["components"]["ai_service"] = {
                        "status": "unhealthy",
                        "details": "AI模型未初始化"
                    }
            except Exception as e:
                health_status["components"]["ai_service"] = {
                    "status": "unhealthy",
                    "details": str(e)
                }
            
            # 综合状态判断
            unhealthy_components = [
                name for name, component in health_status["components"].items()
                if component["status"] != "healthy"
            ]
            
            if unhealthy_components:
                health_status["status"] = "degraded" if len(unhealthy_components) == 1 else "unhealthy"
                health_status["unhealthy_components"] = unhealthy_components
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status

    def get_service_stats(self) -> Dict[str, Any]:
        """
        获取服务统计信息
        
        Returns:
            Dict: 服务统计信息
        """
        return {
            "service_name": "RAG问答服务",
            "version": "1.0.0",
            "config": {
                "max_context_tokens": self.max_context_tokens,
                "top_k_retrieval": self.top_k_retrieval,
                "ai_timeout": self.ai_timeout
            },
            "components": {
                "prompt_builder": "PromptBuilder",
                "answer_processor": "AnswerProcessor",
                "embedding_service": "EmbeddingService",
                "vector_store": "VectorStore"
            },
            "timestamp": datetime.now().isoformat()
        }


# 创建全局RAG服务实例
rag_service = RAGService() 