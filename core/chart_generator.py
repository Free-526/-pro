"""
图表生成模块
支持Excel/CSV数据可视化
"""
import os
import io
import base64
import json
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import rcParams

from app.config import config

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")


class ChartGenerator:
    """图表生成器"""
    
    SUPPORTED_CHARTS = ['line', 'bar', 'scatter', 'pie']
    
    def __init__(self):
        self.chart_dir = config.CHART_DIR
        os.makedirs(self.chart_dir, exist_ok=True)
    
    def load_data(
        self, 
        file_path: str, 
        sheet_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        加载数据文件
        
        Args:
            file_path: 文件路径
            sheet_name: Excel工作表名称
            
        Returns:
            pd.DataFrame: 数据框
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.csv':
            # 尝试不同的编码
            for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']:
                try:
                    return pd.read_csv(file_path, encoding=encoding)
                except UnicodeDecodeError:
                    continue
            raise ValueError("无法解析CSV文件编码")
        
        elif file_ext in ['.xlsx', '.xls']:
            return pd.read_excel(file_path, sheet_name=sheet_name or 0)
        
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")
    
    def analyze_columns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        分析数据列类型
        
        Args:
            df: 数据框
            
        Returns:
            List[Dict]: 列信息列表
        """
        columns = []
        for col in df.columns:
            dtype = df[col].dtype
            
            # 判断列类型
            if pd.api.types.is_integer_dtype(dtype):
                col_type = 'int'
            elif pd.api.types.is_float_dtype(dtype):
                col_type = 'float'
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                col_type = 'datetime'
            else:
                col_type = 'str'
            
            # 获取基本统计信息
            stats = {}
            if col_type in ['int', 'float']:
                stats = {
                    'min': float(df[col].min()) if not pd.isna(df[col].min()) else None,
                    'max': float(df[col].max()) if not pd.isna(df[col].max()) else None,
                    'mean': float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                    'count': int(df[col].count())
                }
            else:
                stats = {
                    'unique_count': int(df[col].nunique()),
                    'count': int(df[col].count())
                }
            
            columns.append({
                'name': str(col),
                'type': col_type,
                'stats': stats
            })
        
        return columns
    
    def generate_chart(
        self,
        df: pd.DataFrame,
        chart_type: str,
        x_column: str,
        y_column: str,
        x_range: Optional[List] = None,
        y_range: Optional[List] = None,
        filter_config: Optional[Dict] = None,
        style: Optional[Dict] = None,
        chart_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成图表
        
        Args:
            df: 数据框
            chart_type: 图表类型
            x_column: X轴列名
            y_column: Y轴列名
            x_range: X轴范围
            y_range: Y轴范围
            filter_config: 数据筛选配置
            style: 样式配置
            chart_id: 图表ID
            
        Returns:
            Dict: 包含图表URL和数据的字典
        """
        if chart_type not in self.SUPPORTED_CHARTS:
            raise ValueError(f"不支持的图表类型: {chart_type}")
        
        if x_column not in df.columns:
            raise ValueError(f"X轴列不存在: {x_column}")
        
        if y_column not in df.columns:
            raise ValueError(f"Y轴列不存在: {y_column}")
        
        style = style or {}
        
        # 数据筛选
        df_filtered = self._apply_filters(df, filter_config)
        
        # 范围筛选
        if x_range and len(x_range) == 2:
            df_filtered = df_filtered[
                (df_filtered[x_column] >= x_range[0]) & 
                (df_filtered[x_column] <= x_range[1])
            ]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=style.get('figsize', (10, 6)))
        
        color = style.get('color', '#1890ff')
        title = style.get('title', f'{y_column} vs {x_column}')
        
        try:
            if chart_type == 'line':
                self._draw_line_chart(ax, df_filtered, x_column, y_column, color, style)
            
            elif chart_type == 'bar':
                self._draw_bar_chart(ax, df_filtered, x_column, y_column, color, style)
            
            elif chart_type == 'scatter':
                self._draw_scatter_chart(ax, df_filtered, x_column, y_column, color, style)
            
            elif chart_type == 'pie':
                self._draw_pie_chart(ax, df_filtered, x_column, y_column, color, style)
            
            # 设置标题和标签
            ax.set_title(title, fontsize=14, fontweight='bold')
            
            if chart_type != 'pie':
                ax.set_xlabel(style.get('x_label', x_column), fontsize=12)
                ax.set_ylabel(style.get('y_label', y_column), fontsize=12)
                
                # 设置Y轴范围
                if y_range and len(y_range) == 2:
                    ax.set_ylim(y_range)
                
                # 旋转X轴标签
                if chart_type != 'scatter':
                    plt.xticks(rotation=style.get('x_rotation', 45))
            
            # 添加图例
            if style.get('show_legend', True):
                ax.legend()
            
            # 添加网格
            if style.get('show_grid', True):
                ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # 保存图表
            if chart_id is None:
                import uuid
                chart_id = str(uuid.uuid4())[:8]
            
            chart_filename = f"chart_{chart_id}.png"
            chart_path = os.path.join(self.chart_dir, chart_filename)
            
            fig.savefig(chart_path, format='png', dpi=150, bbox_inches='tight')
            
            # 转为base64
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            
            plt.close(fig)
            
            return {
                'chart_id': chart_id,
                'chart_url': f"/static/charts/{chart_filename}",
                'chart_base64': f"data:image/png;base64,{image_base64}",
                'chart_path': chart_path,
                'data_summary': {
                    'records': len(df_filtered),
                    'x_min': float(df_filtered[x_column].min()) if len(df_filtered) > 0 else None,
                    'x_max': float(df_filtered[x_column].max()) if len(df_filtered) > 0 else None,
                    'y_min': float(df_filtered[y_column].min()) if len(df_filtered) > 0 else None,
                    'y_max': float(df_filtered[y_column].max()) if len(df_filtered) > 0 else None,
                }
            }
            
        except Exception as e:
            plt.close(fig)
            raise Exception(f"生成图表失败: {str(e)}")
    
    def _draw_line_chart(self, ax, df, x_col, y_col, color, style):
        """绘制折线图"""
        marker = style.get('marker', 'o')
        linewidth = style.get('linewidth', 2)
        
        ax.plot(df[x_col], df[y_col], 
               marker=marker, 
               linewidth=linewidth,
               color=color,
               label=y_col,
               markersize=6,
               alpha=0.8)
    
    def _draw_bar_chart(self, ax, df, x_col, y_col, color, style):
        """绘制柱状图"""
        alpha = style.get('alpha', 0.8)
        width = style.get('bar_width', 0.6)
        
        # 如果X轴数据太多，只显示前30个
        if len(df) > 30:
            df = df.head(30)
        
        ax.bar(df[x_col], df[y_col],
              color=color,
              alpha=alpha,
              width=width,
              label=y_col,
              edgecolor='white',
              linewidth=0.5)
    
    def _draw_scatter_chart(self, ax, df, x_col, y_col, color, style):
        """绘制散点图"""
        size = style.get('point_size', 50)
        alpha = style.get('alpha', 0.6)
        
        ax.scatter(df[x_col], df[y_col],
                  c=color,
                  s=size,
                  alpha=alpha,
                  edgecolors='white',
                  linewidth=0.5,
                  label=y_col)
        
        # 添加趋势线
        if style.get('show_trend', False) and len(df) > 1:
            z = pd.np.polyfit(df[x_col].astype(float), df[y_col].astype(float), 1)
            p = pd.np.poly1d(z)
            ax.plot(df[x_col], p(df[x_col]), "r--", alpha=0.8, label='趋势线')
    
    def _draw_pie_chart(self, ax, df, x_col, y_col, color, style):
        """绘制饼图"""
        # 饼图需要聚合数据
        if len(df) > 10:
            # 只显示前10个，其余归为"其他"
            top_10 = df.nlargest(10, y_col)
            others_sum = df[y_col].sum() - top_10[y_col].sum()
            
            if others_sum > 0:
                others_row = pd.DataFrame({x_col: ['其他'], y_col: [others_sum]})
                df = pd.concat([top_10, others_row], ignore_index=True)
            else:
                df = top_10
        
        colors = plt.cm.Set3(range(len(df)))
        explode = [0.02] * len(df)  # 轻微分离
        
        ax.pie(df[y_col], 
              labels=df[x_col],
              autopct='%1.1f%%',
              colors=colors,
              explode=explode,
              shadow=True,
              startangle=90)
        
        ax.axis('equal')
    
    def _apply_filters(self, df: pd.DataFrame, filter_config: Optional[Dict]) -> pd.DataFrame:
        """应用数据筛选"""
        if not filter_config:
            return df
        
        df_filtered = df.copy()
        
        # 行范围筛选
        if 'row_range' in filter_config:
            start, end = filter_config['row_range']
            df_filtered = df_filtered.iloc[start:end]
        
        # 条件筛选
        if 'conditions' in filter_config:
            for condition in filter_config['conditions']:
                col = condition.get('column')
                op = condition.get('operator', 'eq')  # eq, gt, lt, gte, lte, ne
                val = condition.get('value')
                
                if col not in df_filtered.columns:
                    continue
                
                if op == 'eq':
                    df_filtered = df_filtered[df_filtered[col] == val]
                elif op == 'gt':
                    df_filtered = df_filtered[df_filtered[col] > val]
                elif op == 'lt':
                    df_filtered = df_filtered[df_filtered[col] < val]
                elif op == 'gte':
                    df_filtered = df_filtered[df_filtered[col] >= val]
                elif op == 'lte':
                    df_filtered = df_filtered[df_filtered[col] <= val]
                elif op == 'ne':
                    df_filtered = df_filtered[df_filtered[col] != val]
        
        return df_filtered


# 单例模式
_chart_generator = None


def get_chart_generator() -> ChartGenerator:
    """获取图表生成器实例"""
    global _chart_generator
    if _chart_generator is None:
        _chart_generator = ChartGenerator()
    return _chart_generator
