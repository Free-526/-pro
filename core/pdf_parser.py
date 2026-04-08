"""
PDF解析模块
支持提取文本、元数据，并进行智能分块
"""
import re
from typing import List, Dict, Optional
import pdfplumber


class PDFParser:
    """PDF解析器"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 128):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def parse(self, file_path: str, max_pages: int = 500) -> Dict:
        """
        解析PDF文件
        
        Args:
            file_path: PDF文件路径
            max_pages: 最大解析页数
            
        Returns:
            Dict: 包含标题、作者、摘要、关键词、文本块等信息
        """
        result = {
            "title": "",
            "authors": [],
            "abstract": "",
            "keywords": [],
            "chunks": [],
            "page_count": 0,
            "full_text": ""
        }
        
        try:
            with pdfplumber.open(file_path) as pdf:
                total_pages = min(len(pdf.pages), max_pages)
                result["page_count"] = total_pages
                
                pages_text = []
                for page_num in range(total_pages):
                    page = pdf.pages[page_num]
                    text = page.extract_text() or ""
                    pages_text.append({
                        "page_num": page_num + 1,
                        "text": text
                    })
                
                # 合并全文
                full_text = "\n\n".join([p["text"] for p in pages_text])
                result["full_text"] = full_text
                
                # 提取元数据
                result["title"] = self._extract_title(full_text)
                result["authors"] = self._extract_authors(full_text)
                result["abstract"] = self._extract_abstract(full_text)
                result["keywords"] = self._extract_keywords(full_text)
                
                # 分块
                result["chunks"] = self._split_into_chunks(pages_text)
                
        except Exception as e:
            raise Exception(f"PDF解析失败: {str(e)}")
        
        return result
    
    def _extract_title(self, text: str) -> str:
        """提取标题（取前1000字符中的第一行非空文本）"""
        # 取前1000字符
        preview = text[:1000]
        lines = [l.strip() for l in preview.split('\n') if l.strip()]
        
        # 过滤掉常见的非标题行
        skip_patterns = [
            r'^\d+$',  # 纯数字
            r'^第[一二三四五六七八九十\d]+章',  # 章节标题
            r'^[\(\[【].*?[\)\]】]$',  # 括号包裹的内容
            r'^Abstract',  # Abstract
            r'^摘要',  # 摘要
        ]
        
        for line in lines[:5]:  # 检查前5行
            is_title = True
            for pattern in skip_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    is_title = False
                    break
            if is_title and len(line) > 5:
                return line
        
        return lines[0] if lines else "Unknown Title"
    
    def _extract_authors(self, text: str) -> List[str]:
        """提取作者（简化版）"""
        authors = []
        
        # 常见的作者格式模式
        patterns = [
            r'(?:Authors?|作者)[:\s]*([^\n]+)',
            r'^([\w\s,]+(?:University|Institute|College|Lab|Center)[\w\s,]*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:2000], re.IGNORECASE)
            if match:
                author_str = match.group(1).strip()
                # 分割多个作者
                authors = [a.strip() for a in re.split(r'[,;，、]', author_str) if a.strip()]
                break
        
        return authors[:10]  # 最多返回10个作者
    
    def _extract_abstract(self, text: str) -> str:
        """提取摘要"""
        # 尝试多种摘要格式
        patterns = [
            r'Abstract[\s:]*(.+?)(?=\n\n|Keywords|关键词|1\s+Introduction|引言)',
            r'摘要[\s:]*(.+?)(?=\n\n|关键词|Abstract|1\s+Introduction|引言)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:5000], re.DOTALL | re.IGNORECASE)
            if match:
                abstract = match.group(1).strip()
                # 清理换行和多余空格
                abstract = re.sub(r'\s+', ' ', abstract)
                return abstract[:2000]  # 限制长度
        
        return ""
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []
        
        patterns = [
            r'Keywords[\s:]*(.+?)(?=\n\n|Abstract|摘要|1\s+Introduction)',
            r'关键词[\s:]*(.+?)(?=\n\n|Abstract|摘要|1\s+Introduction)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:5000], re.IGNORECASE)
            if match:
                kw_str = match.group(1).strip()
                # 分割关键词
                keywords = [k.strip() for k in re.split(r'[,;，、]', kw_str) if k.strip()]
                break
        
        return keywords[:20]  # 最多返回20个关键词
    
    def _split_into_chunks(self, pages_text: List[Dict]) -> List[Dict]:
        """
        将文本分块
        
        Args:
            pages_text: 每页的文本内容 [{"page_num": 1, "text": "..."}, ...]
            
        Returns:
            List[Dict]: 文本块列表
        """
        chunks = []
        
        for page in pages_text:
            page_num = page["page_num"]
            text = page["text"]
            
            # 按段落分割
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            current_chunk = ""
            for para in paragraphs:
                # 如果当前块加上新段落超过限制，保存当前块
                if len(current_chunk) + len(para) > self.chunk_size:
                    if current_chunk:
                        chunks.append({
                            "content": current_chunk.strip(),
                            "page_number": page_num,
                            "char_count": len(current_chunk)
                        })
                    # 保留重叠部分
                    if len(current_chunk) > self.chunk_overlap:
                        current_chunk = current_chunk[-self.chunk_overlap:] + "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    current_chunk += "\n\n" + para if current_chunk else para
            
            # 保存最后一个块
            if current_chunk:
                chunks.append({
                    "content": current_chunk.strip(),
                    "page_number": page_num,
                    "char_count": len(current_chunk)
                })
        
        return chunks


# 单例模式
_pdf_parser = None


def get_pdf_parser() -> PDFParser:
    """获取PDF解析器实例"""
    global _pdf_parser
    if _pdf_parser is None:
        from app.config import config
        _pdf_parser = PDFParser(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP
        )
    return _pdf_parser
