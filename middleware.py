"""
中间件系统 - 展示 FastAPI 中间件技术
包含：性能监控、请求日志、错误处理
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import time
import logging
from datetime import datetime
from typing import Callable

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 存储性能数据
performance_data = []


def create_performance_middleware(app):
    """
    创建性能监控中间件
    记录每个请求的处理时间
    """
    @app.middleware("http")
    async def performance_monitor(request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # 处理请求
        response = await call_next(request)
        
        # 计算处理时间
        process_time = (time.time() - start_time) * 1000  # 毫秒
        
        # 添加到响应头
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        response.headers["X-Request-ID"] = f"req-{int(time.time() * 1000)}"
        
        # 记录性能数据
        performance_data.append({
            'endpoint': request.url.path,
            'method': request.method,
            'response_time_ms': round(process_time, 2),
            'status_code': response.status_code,
            'timestamp': datetime.now().isoformat()
        })
        
        # 只保留最近 100 条记录
        if len(performance_data) > 100:
            performance_data.pop(0)
        
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.2f}ms"
        )
        
        return response
    
    return performance_monitor


def create_error_handler(app):
    """
    创建全局错误处理器
    统一处理所有异常
    """
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"全局异常：{exc}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务器内部错误",
                "error": str(exc),
                "path": request.url.path
            }
        )
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "请求的资源不存在",
                "path": request.url.path
            }
        )
    
    return global_exception_handler


def create_cors_middleware(app):
    """
    创建 CORS 中间件
    处理跨域请求
    """
    from fastapi.middleware.cors import CORSMiddleware
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app


def get_performance_stats():
    """获取性能统计数据"""
    if not performance_data:
        return {
            'total_requests': 0,
            'avg_response_time': 0,
            'max_response_time': 0,
            'min_response_time': 0
        }
    
    response_times = [item['response_time_ms'] for item in performance_data]
    
    return {
        'total_requests': len(performance_data),
        'avg_response_time': round(sum(response_times) / len(response_times), 2),
        'max_response_time': round(max(response_times), 2),
        'min_response_time': round(min(response_times), 2),
        'recent_requests': performance_data[-10:]  # 最近 10 条
    }
