"""
综述生成模块
基于文献内容自动生成学术综述
"""
from typing import List, Dict, Optional, Iterator
import json

from app.config import config
from app.core.kimi_client import get_kimi_client


class ReviewGenerator:
    """综述生成器"""
    
    def __init__(self):
        self.kimi = get_kimi_client()
    
    def generate_review(
        self,
        topic: str,
        papers: List[Dict],
        word_count: int = 3000,
        language: str = "zh",
        structure: str = "standard",
        stream: bool = True
    ) -> Iterator[str]:
        """
        生成文献综述
        
        Args:
            topic: 综述主题
            papers: 文献列表
            word_count: 字数要求
            language: 输出语言
            structure: 结构类型
            stream: 是否流式输出
            
        Yields:
            str: 生成的文本片段
        """
        if not papers:
            yield "请先上传文献后再生成综述。"
            return
        
        # 构建文献摘要
        papers_summary = []
        for paper in papers:
            papers_summary.append({
                'title': paper.get('title', '未知标题'),
                'authors': paper.get('authors', []),
                'abstract': paper.get('abstract', ''),
                'keywords': paper.get('keywords', [])
            })
        
        # 构建Prompt
        messages = self.kimi.build_review_prompt(
            topic=topic,
            papers_summary=papers_summary,
            word_count=word_count,
            language=language
        )
        
        # 调用Kimi生成
        for chunk in self.kimi.chat_completion(messages, stream=stream, temperature=0.5):
            yield chunk
    
    def generate_review_with_chunks(
        self,
        topic: str,
        papers: List[Dict],
        chunks: List[Dict],
        word_count: int = 3000,
        language: str = "zh",
        stream: bool = True
    ) -> Iterator[str]:
        """
        基于文本块生成更详细的综述
        
        Args:
            topic: 综述主题
            papers: 文献元数据
            chunks: 相关文本块
            word_count: 字数要求
            language: 输出语言
            stream: 是否流式输出
            
        Yields:
            str: 生成的文本片段
        """
        if not papers:
            yield "请先上传文献后再生成综述。"
            return
        
        lang_text = "中文" if language == "zh" else "English"
        
        # 构建系统提示
        system_prompt = f"""你是一位资深的学术综述撰写专家。请基于提供的文献片段内容，撰写一篇高质量的学术综述。

要求：
1. 主题明确，围绕"{topic}"展开
2. 字数约{word_count}字
3. 使用{lang_text}撰写
4. 结构完整，逻辑清晰
5. 深入分析文献内容，不仅仅是罗列摘要
6. 指出研究间的联系、差异和发展趋势
7. 可以适当引用文献中的具体数据和观点"""

        # 构建文献元数据文本
        paper_meta = []
        for i, paper in enumerate(papers[:10], 1):
            title = paper.get('title', '未知标题')
            authors = ', '.join(paper.get('authors', [])[:3])
            paper_meta.append(f"{i}. {title} ({authors})")
        
        # 构建文本块内容
        chunk_texts = []
        for i, chunk in enumerate(chunks[:15], 1):  # 最多15个文本块
            paper_title = chunk.get('paper_title', '未知文献')
            page_num = chunk.get('page_number', '?')
            content = chunk.get('content', '')[:600]  # 限制长度
            
            chunk_texts.append(
                f"【片段 {i}】来源: {paper_title}, 第{page_num}页\n{content}\n"
            )
        
        # 使用变量存储换行符，避免f-string中的反斜杠问题
        newline = "\n"
        paper_meta_text = newline.join(paper_meta)
        chunk_texts_text = newline.join(chunk_texts)
        
        user_prompt = f"""请基于以下文献内容，撰写关于"{topic}"的学术综述：

【文献列表】
{paper_meta_text}

【文献内容片段】
{chunk_texts_text}

【输出格式】
1. 标题（简洁明确，能概括综述主题）
2. 摘要（200-300字，概括综述的核心内容）
3. 引言（研究背景、意义和目的）
4. 研究现状（分小节论述不同方面的研究进展）
5. 主要发现与对比分析（各文献的观点对比和联系）
6. 存在的问题与挑战
7. 未来发展趋势与展望
8. 结论
9. 参考文献列表（列出所有分析的文献）"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 调用Kimi生成
        for chunk in self.kimi.chat_completion(messages, stream=stream, temperature=0.5):
            yield chunk
    
    def generate_outline(
        self,
        topic: str,
        papers: List[Dict]
    ) -> str:
        """
        生成综述大纲
        
        Args:
            topic: 综述主题
            papers: 文献列表
            
        Returns:
            str: 大纲文本
        """
        if not papers:
            return "请先上传文献后再生成大纲。"
        
        # 构建文献列表
        paper_list = []
        for i, paper in enumerate(papers[:10], 1):
            title = paper.get('title', '未知标题')
            keywords = ', '.join(paper.get('keywords', [])[:5])
            paper_list.append(f"{i}. {title}\n   关键词: {keywords}")
        
        # 使用变量避免f-string中的反斜杠问题
        newline = "\n"
        paper_list_text = newline.join(paper_list)
        
        prompt = f"""基于以下关于"{topic}"的文献，请生成一份综述大纲：

【文献列表】
{paper_list_text}

请按以下格式输出大纲：

一、引言
   1.1 研究背景
   1.2 研究意义
   1.3 综述目的

二、相关研究综述
   （根据文献内容自动划分小节）

三、研究方法对比
   3.1 ...
   3.2 ...

四、主要发现与结论

五、研究不足与展望

六、结论

请确保大纲逻辑清晰，涵盖主要文献的核心内容。"""

        return self.kimi.simple_chat(prompt, temperature=0.4)


# 单例模式
_review_generator = None


def get_review_generator() -> ReviewGenerator:
    """获取综述生成器实例"""
    global _review_generator
    if _review_generator is None:
        _review_generator = ReviewGenerator()
    return _review_generator
