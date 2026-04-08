"""
Kimi API 客户端模块
封装Moonshot AI API调用
"""
import os
from typing import List, Dict, Iterator, Optional
import openai

from app.config import config


class KimiClient:
    """Kimi API客户端"""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化Kimi客户端
        
        Args:
            api_key: API密钥，默认从环境变量读取
            model: 模型名称，默认使用配置中的模型
        """
        self.api_key = api_key or config.KIMI_API_KEY
        self.model = model or config.KIMI_MODEL
        self.base_url = config.KIMI_BASE_URL
        
        if not self.api_key:
            raise ValueError("KIMI_API_KEY未设置")
        
        # 移除可能冲突的代理环境变量
        self._clean_proxy_env()
        
        try:
            # 尝试新版本的初始化方式
            import httpx
            http_client = httpx.Client(timeout=60.0)
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                http_client=http_client
            )
        except (TypeError, ImportError):
            # 回退到旧版本方式
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
    
    def _clean_proxy_env(self):
        """清理代理环境变量，避免与openai库冲突"""
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            if key in os.environ:
                del os.environ[key]
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Iterator[str]:
        """
        调用Kimi对话接口
        
        Args:
            messages: 消息列表
            stream: 是否流式输出
            temperature: 温度参数
            max_tokens: 最大token数
            
        Yields:
            str: 生成的文本片段
        """
        try:
            # 打印调试信息
            print(f"[AI调用] 模型: {self.model}, 消息数: {len(messages)}")
            
            # 智谱AI参数适配
            api_params = {
                "model": self.model,
                "messages": messages,
                "stream": stream,
                "temperature": min(max(temperature, 0.0), 1.0),  # 限制在0-1范围内
            }
            
            # 智谱AI某些模型不支持max_tokens或范围不同
            if "glm-4" in self.model:
                api_params["max_tokens"] = min(max_tokens, 4096)  # 智谱AI通常最大4096
            else:
                api_params["max_tokens"] = max_tokens
            
            response = self.client.chat.completions.create(**api_params)
            
            if stream:
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                yield response.choices[0].message.content
                
        except Exception as e:
            error_str = str(e)
            print(f"[AI调用错误] {error_str}")
            
            if "401" in error_str or "Authentication" in error_str:
                yield "抱歉，AI服务暂时不可用（API认证失败）。\n\n"
                yield "您可以:\n"
                yield "1. 检查 .env 文件中的 KIMI_API_KEY 配置是否正确\n"
                yield "2. 确认API Key未过期\n\n"
            elif "400" in error_str or "1210" in error_str:
                yield "抱歉，AI服务参数有误。\n\n"
                yield "可能原因：\n"
                yield "1. API Key格式不正确（应以sk-开头）\n"
                yield "2. 模型名称不正确，尝试使用 glm-4\n"
                yield "3. 请检查 .env 文件中的配置\n\n"
            else:
                yield f"调用AI服务时出错: {error_str}"
    
    def build_rag_prompt(
        self,
        query: str,
        contexts: List[Dict],
        chat_history: List[Dict] = None,
        system_prompt: str = None
    ) -> List[Dict]:
        """
        构建RAG对话的Prompt
        
        Args:
            query: 用户问题
            contexts: 检索到的上下文
            chat_history: 历史对话
            system_prompt: 自定义系统提示
            
        Returns:
            List[Dict]: 消息列表
        """
        if system_prompt is None:
            system_prompt = """你是一位专业的学术助手，擅长分析和总结学术论文。
请基于提供的文献内容回答用户问题。如果文献内容不足以回答问题，请明确告知。

回答时请遵循以下规则：
1. 基于文献内容作答，不要编造信息
2. 如涉及多个文献，请分别说明
3. 引用格式：[文献标题, 第X页]
4. 回答要简洁明了，突出重点"""

        # 构建上下文文本
        context_parts = []
        for i, ctx in enumerate(contexts[:5], 1):  # 最多使用5个上下文
            paper_title = ctx.get('paper_title', '未知文献')
            page_num = ctx.get('page_number', '?')
            content = ctx.get('content', '')[:800]  # 限制每段长度
            
            context_parts.append(
                f"【文献片段 {i}】\n"
                f"来源: {paper_title}, 第{page_num}页\n"
                f"内容: {content}\n"
            )
        
        context_text = "\n".join(context_parts) if context_parts else "无相关文献内容"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"【相关文献内容】\n{context_text}\n\n【用户问题】\n{query}"}
        ]
        
        return messages
    
    def build_review_prompt(
        self,
        topic: str,
        papers_summary: List[Dict],
        word_count: int = 3000,
        language: str = "zh"
    ) -> List[Dict]:
        """
        构建综述生成的Prompt
        
        Args:
            topic: 综述主题
            papers_summary: 文献摘要列表
            word_count: 字数要求
            language: 输出语言
            
        Returns:
            List[Dict]: 消息列表
        """
        lang_text = "中文" if language == "zh" else "English"
        
        system_prompt = f"""你是一位资深的学术综述撰写专家。请基于提供的文献内容，撰写一篇高质量的学术综述。

要求：
1. 主题明确，围绕"{topic}"展开
2. 字数约{word_count}字
3. 使用{lang_text}撰写
4. 结构完整，逻辑清晰
5. 客观总结各文献的观点和发现
6. 指出研究间的联系和差异"""

        # 构建文献摘要文本
        summary_parts = []
        for i, paper in enumerate(papers_summary[:10], 1):  # 最多10篇文献
            title = paper.get('title', '未知标题')
            abstract = paper.get('abstract', '')[:500]
            authors = ', '.join(paper.get('authors', [])[:3])
            
            summary_parts.append(
                f"【文献 {i}】\n"
                f"标题: {title}\n"
                f"作者: {authors}\n"
                f"摘要: {abstract}\n"
            )
        
        papers_text = "\n".join(summary_parts)
        
        user_prompt = f"""请基于以下文献，撰写关于"{topic}"的学术综述：

【文献列表】
{papers_text}

【输出格式】
1. 标题（简洁明确）
2. 摘要（200-300字）
3. 引言（研究背景和意义）
4. 主体内容（分章节论述，每章可包含多个文献的观点对比）
5. 总结与展望
6. 参考文献列表（列出所有引用的文献标题）"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def simple_chat(self, message: str, temperature: float = 0.7) -> str:
        """
        简单对话（非流式）
        
        Args:
            message: 用户消息
            temperature: 温度参数
            
        Returns:
            str: 完整回复
        """
        messages = [{"role": "user", "content": message}]
        result = []
        for chunk in self.chat_completion(messages, stream=False, temperature=temperature):
            result.append(chunk)
        return "".join(result)


# 单例模式
_kimi_client = None


def get_kimi_client() -> KimiClient:
    """获取Kimi客户端实例"""
    global _kimi_client
    if _kimi_client is None:
        _kimi_client = KimiClient()
    return _kimi_client
