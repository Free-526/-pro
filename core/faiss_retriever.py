"""
FAISS向量检索模块
实现高效的相似度搜索
"""
import os
import pickle
import numpy as np
from typing import List, Dict, Tuple, Optional
import faiss

from app.config import config


class FAISSRetriever:
    """FAISS向量检索器"""
    
    def __init__(self, dim: int = 384, index_path: str = None):
        """
        初始化FAISS检索器
        
        Args:
            dim: 向量维度
            index_path: 索引文件保存路径
        """
        self.dim = dim
        self.index_path = index_path or config.VECTOR_INDEX_PATH
        self.index = None
        self.metadata: Dict[int, Dict] = {}  # faiss_id -> chunk_info
        self.is_trained = False
        
        self._init_index()
    
    def _init_index(self):
        """初始化索引"""
        if os.path.exists(self.index_path):
            self.load_index()
        else:
            # 创建新的索引
            # IndexFlatIP: 使用内积（已归一化向量等价于余弦相似度）
            self.index = faiss.IndexFlatIP(self.dim)
            self.is_trained = True
            print(f"创建新的FAISS索引，维度: {self.dim}")
    
    def add_vectors(
        self, 
        vectors: np.ndarray, 
        metadata_list: List[Dict]
    ) -> List[int]:
        """
        添加向量到索引
        
        Args:
            vectors: 向量数组，shape为(n, dim)
            metadata_list: 每个向量的元数据列表
            
        Returns:
            List[int]: 分配的FAISS ID列表
        """
        if len(vectors) != len(metadata_list):
            raise ValueError("向量和元数据数量不匹配")
        
        if len(vectors) == 0:
            return []
        
        # 确保向量是float32类型
        vectors = vectors.astype('float32')
        
        # 获取起始ID
        start_id = self.index.ntotal
        
        # 添加向量
        self.index.add(vectors)
        
        # 保存元数据
        faiss_ids = []
        for i, meta in enumerate(metadata_list):
            faiss_id = start_id + i
            self.metadata[faiss_id] = meta
            faiss_ids.append(faiss_id)
        
        print(f"添加 {len(vectors)} 个向量到索引，当前总数: {self.index.ntotal}")
        return faiss_ids
    
    def search(
        self, 
        query_vector: np.ndarray, 
        top_k: int = 5,
        threshold: float = None
    ) -> List[Dict]:
        """
        搜索最相似的向量
        
        Args:
            query_vector: 查询向量，shape为(1, dim)或(dim,)
            top_k: 返回结果数量
            threshold: 相似度阈值
            
        Returns:
            List[Dict]: 检索结果列表，每个结果包含metadata和score
        """
        if self.index.ntotal == 0:
            return []
        
        threshold = threshold or config.SIMILARITY_THRESHOLD
        
        # 确保查询向量形状正确
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        query_vector = query_vector.astype('float32')
        
        # 执行搜索
        distances, indices = self.index.search(query_vector, min(top_k * 2, self.index.ntotal))
        
        # 构建结果
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            
            # 过滤低于阈值的
            if dist < threshold:
                continue
            
            meta = self.metadata.get(int(idx), {})
            result = {
                "faiss_id": int(idx),
                "score": float(dist),
                **meta
            }
            results.append(result)
        
        # 按相似度排序并限制数量
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def batch_search(
        self, 
        query_vectors: np.ndarray, 
        top_k: int = 5
    ) -> List[List[Dict]]:
        """
        批量搜索
        
        Args:
            query_vectors: 查询向量数组，shape为(n, dim)
            top_k: 每个查询返回的结果数量
            
        Returns:
            List[List[Dict]]: 每个查询的结果列表
        """
        if self.index.ntotal == 0:
            return [[] for _ in range(len(query_vectors))]
        
        query_vectors = query_vectors.astype('float32')
        
        distances, indices = self.index.search(query_vectors, min(top_k, self.index.ntotal))
        
        all_results = []
        for i in range(len(query_vectors)):
            results = []
            for dist, idx in zip(distances[i], indices[i]):
                if idx == -1:
                    continue
                meta = self.metadata.get(int(idx), {})
                result = {
                    "faiss_id": int(idx),
                    "score": float(dist),
                    **meta
                }
                results.append(result)
            results.sort(key=lambda x: x["score"], reverse=True)
            all_results.append(results)
        
        return all_results
    
    def delete_vectors(self, faiss_ids: List[int]) -> bool:
        """
        删除向量（注意：FAISS不支持直接删除，这里只是标记删除）
        
        Args:
            faiss_ids: 要删除的FAISS ID列表
            
        Returns:
            bool: 是否成功
        """
        for fid in faiss_ids:
            if fid in self.metadata:
                self.metadata[fid]["deleted"] = True
        return True
    
    def get_stats(self) -> Dict:
        """
        获取索引统计信息
        
        Returns:
            Dict: 统计信息
        """
        total_vectors = self.index.ntotal if self.index else 0
        active_vectors = sum(1 for meta in self.metadata.values() if not meta.get("deleted", False))
        
        return {
            "total_vectors": total_vectors,
            "active_vectors": active_vectors,
            "deleted_vectors": total_vectors - active_vectors,
            "dimension": self.dim,
            "index_type": type(self.index).__name__ if self.index else None
        }
    
    def save_index(self):
        """保存索引到磁盘"""
        if self.index is None:
            return
        
        try:
            # 保存FAISS索引
            faiss.write_index(self.index, self.index_path)
            
            # 保存元数据
            meta_path = self.index_path + ".meta"
            with open(meta_path, "wb") as f:
                pickle.dump(self.metadata, f)
            
            print(f"索引已保存到: {self.index_path}")
        except Exception as e:
            print(f"保存索引失败: {str(e)}")
    
    def load_index(self):
        """从磁盘加载索引"""
        try:
            # 加载FAISS索引
            self.index = faiss.read_index(self.index_path)
            self.dim = self.index.d
            self.is_trained = True
            
            # 加载元数据
            meta_path = self.index_path + ".meta"
            if os.path.exists(meta_path):
                with open(meta_path, "rb") as f:
                    self.metadata = pickle.load(f)
            
            print(f"已加载索引，包含 {self.index.ntotal} 个向量，维度: {self.dim}")
        except Exception as e:
            print(f"加载索引失败: {str(e)}")
            # 创建新索引
            self.index = faiss.IndexFlatIP(self.dim)
            self.is_trained = True


# 单例模式
_retriever = None


def get_retriever() -> FAISSRetriever:
    """获取FAISS检索器实例"""
    global _retriever
    if _retriever is None:
        from app.core.embedder import get_embedder
        embedder = get_embedder()
        _retriever = FAISSRetriever(dim=embedder.dimension)
    return _retriever
