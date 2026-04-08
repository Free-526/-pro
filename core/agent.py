"""
智能体核心模块
实现自动任务拆解和多步骤执行
"""
from __future__ import annotations
import json
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from app.core.kimi_client import get_kimi_client

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Task:
    """任务数据类"""
    id: str
    description: str
    type: str  # "retrieve", "summarize", "analyze", "generate"
    params: Dict[str, Any]
    status: str = "pending"  # "pending", "in_progress", "completed", "failed"
    result: Optional[Any] = None


class Agent:
    """智能体类"""
    
    def __init__(self, user_id: str):
        """
        初始化智能体
        
        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.kimi = get_kimi_client()
        self.tasks: List[Task] = []
        self.memory: Dict[str, Any] = {}
        logger.info(f"Agent {self.user_id} 已初始化")
    
    def task_decomposition(self, user_query: str) -> List[Task]:
        """
        任务拆解
        
        Args:
            user_query: 用户查询
            
        Returns:
            List[Task]: 拆解后的任务列表
        """
        system_prompt = """你是一个任务拆解助手，负责将用户的复杂查询拆解为可执行的子任务。

请分析用户的查询，并根据需要拆解为以下类型的子任务：
1. retrieve: 检索相关信息
2. summarize: 总结信息
3. analyze: 分析信息
4. generate: 生成内容

对于每个子任务，请提供：
- id: 任务唯一标识
- type: 任务类型
- description: 任务描述
- params: 任务参数

输出格式必须是纯JSON数组，不要包含任何Markdown格式或其他文本，每个元素包含上述字段。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用户查询: {user_query}"}
        ]
        
        try:
            response = ""
            for chunk in self.kimi.chat_completion(messages, stream=False):
                response += chunk
            
            # 检查响应是否为空
            if not response:
                raise ValueError("AI返回的响应为空")
            
            # 处理Markdown代码块格式
            if response.strip().startswith("```"):
                # 提取代码块内容
                lines = response.strip().split('\n')
                if len(lines) > 2:
                    # 移除第一行的 ```json 和最后一行的 ```
                    code_content = '\n'.join(lines[1:-1])
                    response = code_content
            
            # 打印响应内容（用于调试）
            logger.info(f"AI返回的响应: {response[:200]}...")
            
            # 解析JSON响应
            tasks = json.loads(response)
            
            # 验证任务格式
            validated_tasks = []
            for i, task_data in enumerate(tasks):
                task_id = task_data.get('id', f"task_{i+1}")
                task_type = task_data.get('type', 'retrieve')
                task_desc = task_data.get('description', '')
                task_params = task_data.get('params', {})
                
                task = Task(
                    id=task_id,
                    type=task_type,
                    description=task_desc,
                    params=task_params
                )
                validated_tasks.append(task)
            
            self.tasks = validated_tasks
            logger.info(f"任务拆解完成，生成 {len(validated_tasks)} 个任务")
            return validated_tasks
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            logger.error(f"响应内容: {response}")
            # 回退到默认任务
            default_task = Task(
                id="default_task",
                type="retrieve",
                description="检索相关信息并回答用户问题",
                params={"query": user_query}
            )
            self.tasks = [default_task]
            return [default_task]
        except Exception as e:
            logger.error(f"任务拆解失败: {str(e)}")
            # 回退到默认任务
            default_task = Task(
                id="default_task",
                type="retrieve",
                description="检索相关信息并回答用户问题",
                params={"query": user_query}
            )
            self.tasks = [default_task]
            return [default_task]
    
    def execute_tasks(self, rag_tool) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            rag_tool: RAG工具实例
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        results = {}
        
        for task in self.tasks:
            try:
                task.status = "in_progress"
                logger.info(f"开始执行任务: {task.id} - {task.description}")
                
                if task.type == "rag_answer":
                    query = task.params.get("query", "")
                    top_k = task.params.get("top_k", 5)
                    result = rag_tool.rag_answer(query, top_k=top_k)
                
                elif task.type == "retrieve":
                    query = task.params.get("query", "")
                    top_k = task.params.get("top_k", 5)
                    result = rag_tool.retrieve(query, top_k=top_k)
                
                elif task.type == "summarize":
                    content = task.params.get("content", "")
                    if not content:
                        content = self._get_previous_task_results(results)
                    result = rag_tool.summarize(content)
                
                elif task.type == "analyze":
                    content = task.params.get("content", "")
                    if not content:
                        content = self._get_previous_task_results(results)
                    analysis_type = task.params.get("analysis_type", "")
                    result = rag_tool.analyze(content, analysis_type)
                
                elif task.type == "generate":
                    prompt = task.params.get("prompt", "")
                    context = task.params.get("context", "")
                    if not context:
                        context = self._get_previous_task_results(results)
                    result = rag_tool.generate(prompt, context)
                
                else:
                    result = {"error": f"未知任务类型: {task.type}"}
                
                task.status = "completed"
                task.result = result
                results[task.id] = result
                logger.info(f"任务执行完成: {task.id}")
                
            except Exception as e:
                task.status = "failed"
                task.result = {"error": str(e)}
                results[task.id] = {"error": str(e)}
                logger.error(f"任务执行失败: {task.id} - {str(e)}")
        
        # 整合结果
        final_result = self._integrate_results(results)
        return final_result
    
    def _get_previous_task_results(self, results: Dict[str, Any]) -> str:
        """
        获取前一个任务的结果作为当前任务的输入
        
        Args:
            results: 已完成的任务结果字典
            
        Returns:
            str: 格式化的任务结果字符串
        """
        if not results:
            return ""
        
        content_parts = []
        for task_id, result in results.items():
            if isinstance(result, dict) and "error" not in result:
                # 处理字典类型的结果
                if "analysis" in result:
                    content_parts.append(f"分析结果: {result['analysis']}")
                elif isinstance(result, list):
                    for item in result:
                        if isinstance(item, dict):
                            content_parts.append(f"文献: {item.get('paper_title', '未知')}")
                            content_parts.append(f"内容: {item.get('content', '')[:200]}...")
                else:
                    content_parts.append(str(result))
            elif isinstance(result, list):
                # 处理列表类型的结果（检索结果）
                for item in result:
                    if isinstance(item, dict):
                        content_parts.append(f"文献: {item.get('paper_title', '未知')}")
                        content_parts.append(f"内容: {item.get('content', '')[:200]}...")
            elif isinstance(result, str):
                # 处理字符串类型的结果（总结、生成结果）
                content_parts.append(result)
        
        return "\n\n".join(content_parts) if content_parts else ""
    
    def _integrate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        整合任务结果
        
        Args:
            results: 任务结果字典
            
        Returns:
            Dict[str, Any]: 整合后的结果
        """
        # 转换Task对象为字典，以便序列化
        tasks_dict = []
        for task in self.tasks:
            task_dict = {
                "id": task.id,
                "description": task.description,
                "type": task.type,
                "params": task.params,
                "status": task.status,
                "result": task.result
            }
            tasks_dict.append(task_dict)
        
        # 生成更有意义的总结
        completed_tasks = sum(1 for task in self.tasks if task.status == "completed")
        failed_tasks = sum(1 for task in self.tasks if task.status == "failed")
        
        summary = f"任务执行完成：{completed_tasks}个任务成功，{failed_tasks}个任务失败"
        
        # 这里可以根据实际需求实现更复杂的结果整合逻辑
        return {
            "tasks": tasks_dict,
            "results": results,
            "summary": summary
        }
    
    def close(self):
        """
        关闭智能体
        """
        logger.info(f"Agent {self.user_id} 已关闭")