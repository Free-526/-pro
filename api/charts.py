"""
图表生成API路由
"""
import os
import shutil
from typing import Optional

import data
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db, Dataset, ChartConfig, User
from app.models.schemas import ResponseModel, ChartGenerateRequest, DatasetResponse
from app.core.chart_generator import get_chart_generator
from app.core.auth import get_current_user
from app.core.analytics import Tracker
from app.config import config

router = APIRouter()


@router.post("/datasets/upload", response_model=ResponseModel)
async def upload_dataset(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传数据文件（Excel或CSV）
    
    - **file**: Excel或CSV文件
    - **sheet_name**: Excel工作表名称（可选）
    """
    # 检查文件类型
    allowed_extensions = ['.csv', '.xlsx', '.xls']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式，请上传 {', '.join(allowed_extensions)} 文件"
        )
    
    try:
        # 按用户隔离文件存储路径
        user_upload_dir = os.path.join(config.UPLOAD_DIR, str(current_user.id))
        os.makedirs(user_upload_dir, exist_ok=True)
        file_path = os.path.join(user_upload_dir, file.filename)
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # 分析数据
        generator = get_chart_generator()
        df = generator.load_data(file_path, sheet_name)
        columns = generator.analyze_columns(df)
        
        # 保存到数据库
        file_type = "excel" if file_ext in ['.xlsx', '.xls'] else "csv"
        dataset = Dataset(
            user_id=current_user.id,
            file_name=file.filename,
            file_path=file_path,
            file_type=file_type,
            sheet_name=sheet_name,
            columns=str(columns),
            row_count=len(df)
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        # 记录数据集上传事件
        Tracker.track_event(
            db=db,
            user_id=current_user.id,
            event_name="upload_dataset",
            event_type="data",
            properties={
                "file_name": file.filename,
                "file_type": file_type,
                "row_count": len(df),
                "column_count": len(columns)
            }
        )
        
        # 增加数据集上传计数
        Tracker.increment_metric(db, current_user.id, "dataset_count")
        
        # 生成预览数据（前10行）
        preview = df.head(10).to_dict(orient='records')
        
        return ResponseModel(
            code=200,
            message="上传成功",
            data={
                "id": dataset.id,
                "file_name": dataset.file_name,
                "file_type": dataset.file_type,
                "sheet_name": dataset.sheet_name,
                "columns": columns,
                "row_count": dataset.row_count,
                "preview": preview,
                "upload_time": dataset.upload_time
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")


@router.get("/datasets", response_model=ResponseModel)
async def list_datasets(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取数据集列表"""
    query = db.query(Dataset).filter(Dataset.user_id == current_user.id)
    total = query.count()
    datasets = query.order_by(Dataset.upload_time.desc()).offset((page - 1) * size).limit(size).all()
    
    items = []
    for ds in datasets:
        import ast
        try:
            columns = ast.literal_eval(ds.columns) if ds.columns else []
        except:
            columns = []
        
        items.append({
            "id": ds.id,
            "file_name": ds.file_name,
            "file_type": ds.file_type,
            "sheet_name": ds.sheet_name,
            "columns": columns,
            "row_count": ds.row_count,
            "upload_time": ds.upload_time
        })
    
    return ResponseModel(
        code=200,
        data={
            "total": total,
            "items": items
        }
    )


@router.get("/datasets/{dataset_id}", response_model=ResponseModel)
async def get_dataset(
    dataset_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取数据集详情"""
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == current_user.id
    ).first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在或无权访问")
    
    import ast
    try:
        columns = ast.literal_eval(dataset.columns) if dataset.columns else []
    except:
        columns = []
    
    # 加载数据获取预览
    try:
        generator = get_chart_generator()
        df = generator.load_data(dataset.file_path, dataset.sheet_name)
        preview = df.head(10).to_dict(orient='records')
    except:
        preview = []
    
    return ResponseModel(
        code=200,
        data={
            "id": dataset.id,
            "file_name": dataset.file_name,
            "file_type": dataset.file_type,
            "sheet_name": dataset.sheet_name,
            "columns": columns,
            "row_count": dataset.row_count,
            "preview": preview,
            "upload_time": dataset.upload_time
        }
    )


@router.post("/generate", response_model=ResponseModel)
async def generate_chart(
    request: ChartGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成图表
    
    - **dataset_id**: 数据集ID
    - **chart_type**: 图表类型（line/bar/scatter/pie）
    - **x_column**: X轴列名
    - **y_column**: Y轴列名
    - **x_range**: X轴范围（可选）
    - **y_range**: Y轴范围（可选）
    - **filter_config**: 数据筛选配置（可选）
    - **style**: 样式配置（可选）
    """
    # 获取数据集（检查用户权限）
    dataset = db.query(Dataset).filter(
        Dataset.id == request.dataset_id,
        Dataset.user_id == current_user.id
    ).first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在或无权访问")
    
    try:
        # 加载数据
        generator = get_chart_generator()
        df = generator.load_data(dataset.file_path, dataset.sheet_name)
        
        # 验证列存在
        if request.x_column not in df.columns:
            raise HTTPException(status_code=400, detail=f"X轴列 '{request.x_column}' 不存在")
        
        if request.y_column not in df.columns:
            raise HTTPException(status_code=400, detail=f"Y轴列 '{request.y_column}' 不存在")
        
        # 生成图表
        result = generator.generate_chart(
            df=df,
            chart_type=request.chart_type,
            x_column=request.x_column,
            y_column=request.y_column,
            x_range=request.x_range,
            y_range=request.y_range,
            filter_config=request.filter_config,
            style=request.style
        )
        
        # 保存图表配置
        import json
        chart_config = ChartConfig(
            dataset_id=request.dataset_id,
            chart_name=request.style.get('title', f"Chart_{request.x_column}_vs_{request.y_column}"),
            chart_type=request.chart_type,
            x_column=request.x_column,
            y_column=request.y_column,
            x_range=str(request.x_range) if request.x_range else None,
            y_range=str(request.y_range) if request.y_range else None,
            filter_config=str(request.filter_config) if request.filter_config else None,
            style_config=str(request.style) if request.style else None
        )
        db.add(chart_config)
        db.commit()
        
        # 记录图表生成事件
        Tracker.track_event(
            db=db,
            user_id=current_user.id,
            event_name="generate_chart",
            event_type="chart",
            properties={
                "chart_type": request.chart_type,
                "dataset_id": request.dataset_id,
                "x_column": request.x_column,
                "y_column": request.y_column
            }
        )
        
        # 增加图表生成计数
        Tracker.increment_metric(db, current_user.id, "chart_count")
        
        return ResponseModel(
            code=200,
            message="图表生成成功",
            data={
                "chart_id": result['chart_id'],
                "chart_url": result['chart_url'],
                "chart_base64": result['chart_base64'],
                "data_summary": result['data_summary']
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成图表失败: {str(e)}")


@router.delete("/datasets/{dataset_id}", response_model=ResponseModel)
async def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """删除数据集"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 删除文件
    try:
        if os.path.exists(dataset.file_path):
            os.remove(dataset.file_path)
    except:
        pass
    
    db.delete(dataset)
    db.commit()
    
    return ResponseModel(code=200, message="删除成功")


@router.get("/export/{chart_id}")
async def export_chart(
    chart_id: str,
    format: str = "png",
    db: Session = Depends(get_db)
):
    """
    导出图表
    
    - **chart_id**: 图表ID
    - **format**: 导出格式（png/jpg/svg/pdf）
    """
    from fastapi.responses import FileResponse
    
    # 查找图表文件
    chart_path = os.path.join(config.CHART_DIR, f"chart_{chart_id}.png")
    
    if not os.path.exists(chart_path):
        raise HTTPException(status_code=404, detail="图表不存在")
    
    if format == "png":
        return FileResponse(chart_path, media_type="image/png", filename=f"chart_{chart_id}.png")
    
    # TODO: 实现其他格式转换
    return FileResponse(chart_path, media_type="image/png", filename=f"chart_{chart_id}.png")
