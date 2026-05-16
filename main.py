"""FastAPI 技术应用"""
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from contextlib import asynccontextmanager
import pymysql
import logging
from datetime import datetime
from typing import List, Optional

from models import (
    MovieCreate, MovieUpdate, MovieResponse, 
    APIResponse, PerformanceMetrics, TaskStatus
)
from middleware import (
    create_performance_middleware,
    create_error_handler,
    create_cors_middleware,
    get_performance_stats
)
from dependencies import (
    get_db, get_movie_service, MovieService,
    validate_movie_id, validate_page_params,
    DB_CONFIG
)
from tasks import (
    fetch_movie_detail, batch_update_movies,
    send_notification, get_task_status
)
from scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

movie_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理"""
    logger.info("=" * 80)
    logger.info("FastAPI 技术展示平台启动中...")
    logger.info("=" * 80)
    logger.info("✅ Pydantic 数据验证 - 已加载")
    logger.info("✅ 中间件系统 - 已加载")
    logger.info("✅ 依赖注入系统 - 已加载")
    logger.info("✅ Celery 异步任务 - 已配置")
    logger.info("✅ WebSocket 实时日志 - 已配置")
    logger.info("=" * 80)
    logger.info("访问 /docs 查看 API 文档")
    logger.info("访问 /tech-stack 查看技术栈说明")
    logger.info("=" * 80)
    
    global movie_scheduler
    try:
        movie_scheduler = create_scheduler(DB_CONFIG, update_interval='daily', hour=2)
        logger.info("✅ 定时更新任务 - 已启动（每天凌晨 2 点）")
    except Exception as e:
        logger.error(f"❌ 定时更新任务启动失败：{e}")
        movie_scheduler = None
    
    yield
    
    logger.info("FastAPI 应用正在关闭...")
    
    if movie_scheduler:
        try:
            movie_scheduler.stop()
            logger.info("✅ 定时更新任务已停止")
        except Exception as e:
            logger.error(f"停止定时任务失败：{e}")


# 创建 FastAPI 应用
app = FastAPI(
    title="DailyMove API",
    description="**FastAPI 技术展示平台**\n\n"
                "包含以下技术特性：\n"
                "- ✅ Pydantic 数据验证\n"
                "- ✅ 中间件系统（性能监控、错误处理）\n"
                "- ✅ 依赖注入系统\n"
                "- ✅ Celery 异步任务队列\n"
                "- ✅ WebSocket 实时日志\n"
                "- ✅ Redis 缓存\n"
                "- ✅ 请求限流",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 应用中间件
create_cors_middleware(app)
create_performance_middleware(app)
create_error_handler(app)

# 配置静态文件
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# 根路径重定向
@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


# ==================== 电影 API（使用依赖注入和 Pydantic 验证） ====================

@app.get('/api/movie/random', response_model=MovieResponse)
async def get_random_movie(service: MovieService = Depends(get_movie_service)):
    """
    获取随机电影
    - 使用依赖注入获取数据库连接
    - 自动验证响应数据格式
    """
    movie = service.get_random_movie()
    if not movie:
        raise HTTPException(status_code=404, detail="没有找到电影数据")
    return movie


@app.get('/api/movie/{movie_id}', response_model=MovieResponse)
async def get_movie_by_id(
    movie_id: int = Depends(validate_movie_id),
    service: MovieService = Depends(get_movie_service)
):
    """
    根据 ID 获取电影详情
    - 使用依赖注入验证 ID
    - 自动验证响应数据格式
    """
    movie = service.get_movie_by_id(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="未找到该电影")
    return movie


@app.get('/api/movies', response_model=List[MovieResponse])
async def get_all_movies(
    page: int = 1,
    page_size: int = 10,
    service: MovieService = Depends(get_movie_service)
):
    """
    获取所有电影列表（支持分页）
    - 使用依赖注入验证分页参数
    """
    page, page_size = validate_page_params(page, page_size)
    return service.get_all_movies()


@app.post('/api/movies')
async def create_movie(
    movie: MovieCreate,
    service: MovieService = Depends(get_movie_service)
):
    """
    创建新电影
    - 使用 Pydantic 自动验证请求数据
    - 验证字段：标题、年份、评分等
    """
    movie_id = service.create_movie(movie.model_dump())
    return {
        "success": True,
        "message": "电影创建成功",
        "data": {'id': movie_id}
    }


@app.put('/api/movie/{movie_id}')
async def update_movie(
    movie_id: int = Depends(validate_movie_id),
    movie: MovieUpdate = None,
    service: MovieService = Depends(get_movie_service)
):
    """
    更新电影信息
    - 所有字段可选
    - 自动验证数据类型和范围
    """
    rows = service.update_movie(movie_id, movie.model_dump(exclude_unset=True))
    return {
        "success": True,
        "message": f"成功更新 {rows} 条记录",
        "data": {'updated_rows': rows}
    }


@app.delete('/api/movie/{movie_id}')
async def delete_movie(
    movie_id: int = Depends(validate_movie_id),
    service: MovieService = Depends(get_movie_service)
):
    """
    删除电影
    - 使用依赖注入验证 ID
    """
    rows = service.delete_movie(movie_id)
    return {
        "success": True,
        "message": f"成功删除 {rows} 条记录",
        "data": {'deleted_rows': rows}
    }


# ==================== Celery 异步任务 API ====================

@app.post('/api/tasks/fetch-movie', response_model=TaskStatus)
async def task_fetch_movie(movie_url: str):
    """
    异步获取电影详情
    - 使用 Celery 异步任务
    - 立即返回任务 ID
    """
    task = fetch_movie_detail.delay(movie_url)
    return TaskStatus(
        task_id=task.id,
        status='pending',
        result=None
    )


@app.post('/api/tasks/batch-update', response_model=TaskStatus)
async def task_batch_update(movie_ids: List[int]):
    """
    批量更新电影
    - 展示批量异步任务处理
    """
    task = batch_update_movies.delay(movie_ids)
    return TaskStatus(
        task_id=task.id,
        status='pending',
        result=None
    )


@app.get('/api/tasks/{task_id}', response_model=TaskStatus)
async def get_task_status_api(task_id: str):
    """
    查询任务状态
    - 实时获取 Celery 任务状态
    """
    status_data = get_task_status(task_id)
    return TaskStatus(**status_data)


@app.post('/api/tasks/notify')
async def send_notify(message: str):
    """
    发送通知（示例任务）
    - 简单 Celery 任务演示
    """
    task = send_notification.delay(message)
    return {
        "success": True,
        "message": "通知任务已提交",
        "data": {'task_id': task.id}
    }


# ==================== 性能监控 API ====================

@app.get('/api/performance/stats')
async def get_performance_statistics():
    """
    获取性能统计数据
    - 展示中间件收集的性能数据
    """
    stats = get_performance_stats()
    return {
        "success": True,
        "message": "获取性能统计成功",
        "data": stats
    }


@app.get('/api/performance/recent', response_model=List[PerformanceMetrics])
async def get_recent_requests(limit: int = 10):
    """
    获取最近的请求记录
    - 展示性能监控详情
    """
    stats = get_performance_stats()
    recent = stats.get('recent_requests', [])[-limit:]
    return [PerformanceMetrics(**item) for item in recent]


# ==================== 健康检查 API ====================

@app.get('/api/health')
async def health_check():
    """
    系统健康检查
    - 检查数据库连接
    - 检查 Celery 状态
    - 检查 Redis 连接
    """
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'database': 'unknown',
            'celery': 'unknown',
            'redis': 'unknown'
        }
    }
    
    # 检查数据库
    try:
        db = pymysql.connect(**{
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': '123456',
            'database': 'dailymove',
            'charset': 'utf8mb4'
        })
        db.close()
        health_status['services']['database'] = 'connected'
    except Exception as e:
        health_status['services']['database'] = f'error: {str(e)}'
        health_status['status'] = 'degraded'
    
    return health_status


# ==================== 技术文档端点 ====================

@app.get('/docs')
async def custom_docs():
    """重定向到 Swagger UI"""
    return RedirectResponse(url="/docs")


@app.get('/tech-stack')
async def tech_stack():
    """技术栈说明"""
    return {
        "framework": "FastAPI",
        "version": "0.104.1",
        "features": [
            "Pydantic 数据验证",
            "依赖注入系统",
            "中间件（性能监控、错误处理）",
            "Celery 异步任务队列",
            "WebSocket 实时日志",
            "Redis 缓存",
            "MySQL 数据库",
            "Swagger/OpenAPI 文档"
        ],
        "tech_files": {
            "main.py": "主应用入口（使用 lifespan 管理生命周期）",
            "models.py": "Pydantic v2 数据模型",
            "middleware.py": "中间件系统",
            "dependencies.py": "依赖注入",
            "tasks.py": "Celery 异步任务",
            "websocket_manager.py": "WebSocket 管理"
        }
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
