"""
图表服务层
处理图表相关的业务逻辑
"""
from typing import List, Dict, Optional, Any, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from app.models.database import Dataset, ChartConfig
from app.core.chart_generator import get_chart_generator


class ChartService:
    """图表服务"""
    
    def __init__(self):
        self.generator = get_chart_generator()
    
    def load_and_analyze(
        self, 
        file_path: str, 
        sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        加载并分析数据文件
        
        Args:
            file_path: 文件路径
            sheet_name: Excel工作表名称
            
        Returns:
            Dict: 包含数据框和列信息的字典
        """
        df = self.generator.load_data(file_path, sheet_name)
        columns = self.generator.analyze_columns(df)
        
        return {
            "dataframe": df,
            "columns": columns,
            "row_count": len(df),
            "preview": df.head(10).to_dict(orient='records')
        }
    
    def validate_columns(
        self, 
        columns: List[Dict], 
        x_column: str, 
        y_column: str,
        chart_type: str
    ) -> Tuple[bool, str]:
        """
        验证列配置
        
        Args:
            columns: 列信息列表
            x_column: X轴列名
            y_column: Y轴列名
            chart_type: 图表类型
            
        Returns:
            tuple: (是否有效, 错误信息)
        """
        column_names = [c['name'] for c in columns]
        
        if x_column not in column_names:
            return False, f"X轴列 '{x_column}' 不存在"
        
        if y_column not in column_names:
            return False, f"Y轴列 '{y_column}' 不存在"
        
        # 获取列类型
        x_type = next((c['type'] for c in columns if c['name'] == x_column), 'str')
        y_type = next((c['type'] for c in columns if c['name'] == y_column), 'str')
        
        # 根据图表类型验证
        if chart_type in ['line', 'scatter']:
            if x_type not in ['int', 'float', 'datetime']:
                return False, f"{chart_type}图要求X轴为数值或日期类型"
            if y_type not in ['int', 'float']:
                return False, f"{chart_type}图要求Y轴为数值类型"
        
        elif chart_type == 'pie':
            if y_type not in ['int', 'float']:
                return False, "饼图要求数值列为数值类型"
        
        return True, ""
    
    def create_chart(
        self,
        df: pd.DataFrame,
        chart_type: str,
        x_column: str,
        y_column: str,
        x_range: Optional[List] = None,
        y_range: Optional[List] = None,
        filter_config: Optional[Dict] = None,
        style: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        创建图表
        
        Args:
            df: 数据框
            chart_type: 图表类型
            x_column: X轴列名
            y_column: Y轴列名
            x_range: X轴范围
            y_range: Y轴范围
            filter_config: 筛选配置
            style: 样式配置
            
        Returns:
            Dict: 图表结果
        """
        return self.generator.generate_chart(
            df=df,
            chart_type=chart_type,
            x_column=x_column,
            y_column=y_column,
            x_range=x_range,
            y_range=y_range,
            filter_config=filter_config,
            style=style
        )
    
    def save_chart_config(
        self,
        dataset_id: int,
        chart_type: str,
        x_column: str,
        y_column: str,
        db: Session,
        x_range: Optional[List] = None,
        y_range: Optional[List] = None,
        filter_config: Optional[Dict] = None,
        style: Optional[Dict] = None,
        chart_name: Optional[str] = None
    ) -> int:
        """保存图表配置"""
        import json
        
        config = ChartConfig(
            dataset_id=dataset_id,
            chart_name=chart_name or f"Chart_{x_column}_vs_{y_column}",
            chart_type=chart_type,
            x_column=x_column,
            y_column=y_column,
            x_range=json.dumps(x_range) if x_range else None,
            y_range=json.dumps(y_range) if y_range else None,
            filter_config=json.dumps(filter_config) if filter_config else None,
            style_config=json.dumps(style) if style else None
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        
        return config.id
    
    def get_dataset_charts(self, dataset_id: int, db: Session) -> List[Dict]:
        """获取数据集的所有图表配置"""
        charts = db.query(ChartConfig).filter(
            ChartConfig.dataset_id == dataset_id
        ).all()
        
        import json
        result = []
        for chart in charts:
            result.append({
                "id": chart.id,
                "chart_name": chart.chart_name,
                "chart_type": chart.chart_type,
                "x_column": chart.x_column,
                "y_column": chart.y_column,
                "created_at": chart.created_at
            })
        
        return result