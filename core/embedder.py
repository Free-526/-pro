"""
文本向量化模块
使用sentence-transformers进行文本嵌入
"""
import os
import re
import hashlib
import numpy as np
from typing import List, Union
from collections import Counter

# 设置 Hugging Face 镜像（国内加速）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 尝试导入sentence-transformers，如果失败则使用备用方案
try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False


class TextEmbedder:
    """文本嵌入器"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化文本嵌入器
        
        Args:
            model_name: 模型名称
                - "all-MiniLM-L6-v2": 轻量级，384维，英文效果好
                - "BAAI/bge-large-zh-v1.5": 中文效果好，1024维
                - "paraphrase-multilingual-MiniLM-L12-v2": 多语言，384维
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        try:
            # 设置本地缓存目录
            cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'models')
            os.makedirs(cache_dir, exist_ok=True)
            
            self.model = SentenceTransformer(
                self.model_name,
                cache_folder=cache_dir
            )
            print(f"成功加载模型: {self.model_name}")
        except Exception as e:
            raise Exception(f"模型加载失败: {str(e)}")
    
    @property
    def dimension(self) -> int:
        """获取向量维度"""
        if self.model is None:
            return 384
        return self.model.get_sentence_embedding_dimension()
    
    def encode(
        self, 
        texts: Union[str, List[str]], 
        normalize: bool = True,
        batch_size: int = 32
    ) -> np.ndarray:
        """
        将文本编码为向量
        
        Args:
            texts: 单个文本或文本列表
            normalize: 是否进行L2归一化（使内积等价于余弦相似度）
            batch_size: 批处理大小
            
        Returns:
            np.ndarray: 向量数组，shape为(n, dimension)
        """
        if self.model is None:
            raise Exception("模型未加载")
        
        # 确保是列表
        if isinstance(texts, str):
            texts = [texts]
        
        # 过滤空文本
        texts = [t.strip() if t else "" for t in texts]
        
        # 编码
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 100,
            convert_to_numpy=True,
            normalize_embeddings=normalize
        )
        
        return embeddings.astype('float32')
    
    def encode_queries(self, queries: Union[str, List[str]]) -> np.ndarray:
        """
        编码查询文本（可用于特殊处理查询）
        
        Args:
            queries: 查询文本
            
        Returns:
            np.ndarray: 向量数组
        """
        # 对于BGE模型，查询文本可以添加前缀
        if "bge" in self.model_name.lower():
            if isinstance(queries, str):
                queries = f"represent this sentence for searching relevant passages: {queries}"
            else:
                queries = [f"represent this sentence for searching relevant passages: {q}" for q in queries]
        
        return self.encode(queries)
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            float: 余弦相似度 (-1 到 1)
        """
        embeddings = self.encode([text1, text2], normalize=True)
        similarity = np.dot(embeddings[0], embeddings[1])
        return float(similarity)


class SimpleEmbedder:
    """简单的备用嵌入器（无需下载模型）
    使用简单的哈希特征 + TF-IDF 思想生成向量
    """
    
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.vocab = {}
        self.idf = {}
        print(f"使用简单备用嵌入器 (维度: {dim})")
    
    def _tokenize(self, text: str) -> List[str]:
        """简单的分词"""
        # 提取中文字符和英文单词
        chinese = re.findall(r'[\u4e00-\u9fff]', text)
        english = re.findall(r'[a-zA-Z]+', text.lower())
        return chinese + english
    
    def _get_vector(self, text: str) -> np.ndarray:
        """基于哈希的向量生成"""
        tokens = self._tokenize(text)
        if not tokens:
            return np.zeros(self.dim)
        
        # 使用多个哈希函数生成向量
        vec = np.zeros(self.dim)
        for token in tokens:
            # 使用哈希确定位置
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            pos = h % self.dim
            # 使用另一个哈希确定符号和权重
            weight = (h >> 10) % 100 / 100.0 + 0.5
            vec[pos] += weight
        
        # L2归一化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec
    
    def encode(self, texts, normalize=True, batch_size=32):
        """编码文本"""
        if isinstance(texts, str):
            texts = [texts]
        
        vectors = []
        for text in texts:
            vec = self._get_vector(text)
            vectors.append(vec)
        
        result = np.array(vectors, dtype='float32')
        if normalize:
            norms = np.linalg.norm(result, axis=1, keepdims=True)
            norms[norms == 0] = 1
            result = result / norms
        return result
    
    @property
    def dimension(self):
        return self.dim


# 单例模式
_embedder = None
USE_ADVANCED_MODEL = os.environ.get('USE_ADVANCED_MODEL', 'false').lower() == 'true'


def get_embedder():
    """获取文本嵌入器实例"""
    global _embedder
    if _embedder is None:
        # 默认使用简单嵌入器（避免下载卡住）
        # 如需使用高级模型，设置环境变量 USE_ADVANCED_MODEL=true
        if USE_ADVANCED_MODEL and ST_AVAILABLE:
            try:
                print("尝试加载 sentence-transformers 模型...")
                _embedder = TextEmbedder("all-MiniLM-L6-v2")
                print("✅ 高级模型加载成功")
            except Exception as e:
                print(f"⚠️ 高级模型加载失败，使用备用嵌入器: {e}")
                _embedder = SimpleEmbedder(dim=384)
        else:
            print("使用简单备用嵌入器（如需高级模型，设置 USE_ADVANCED_MODEL=true）")
            _embedder = SimpleEmbedder(dim=384)
    return _embedder


def reset_embedder():
    """重置嵌入器（用于切换模型）"""
    global _embedder
    _embedder = None
