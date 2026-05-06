"""
Celery 异步任务配置
展示异步任务队列技术
"""
from celery import Celery
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery 配置
# 生产环境：使用 Redis 作为消息代理和结果存储
celery_app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',  # Redis 作为消息代理
    backend='redis://localhost:6379/1',  # Redis 存储结果
)

# 配置优化
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 任务超时 5 分钟
    task_always_eager=False,  # 异步执行
)

# 检查 Redis 连接
def check_redis_connection():
    """检查 Redis 连接状态"""
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        redis_client.ping()
        logger.info("✅ Redis 连接成功")
        return True
    except Exception as e:
        logger.warning(f"⚠️  Redis 未连接：{e}")
        logger.warning("Celery 将使用同步模式（task_always_eager=True）")
        # 自动切换到同步模式
        celery_app.conf.task_always_eager = True
        return False

# 启动时检查 Redis 连接
check_redis_connection()


@celery_app.task(bind=True, max_retries=3)
def fetch_movie_detail(self, movie_url: str):
    """
    异步获取电影详情
    展示 Celery 任务的基本用法
    """
    try:
        logger.info(f"开始获取电影详情：{movie_url}")
        update_task_status(self.request.id, 'processing', {'url': movie_url})
        
        # 模拟网络请求延迟
        time.sleep(2)
        
        # 模拟返回结果
        result = {
            'title': f'Movie from {movie_url}',
            'status': 'success',
            'fetched_at': datetime.now().isoformat()
        }
        
        logger.info(f"电影详情获取成功：{result['title']}")
        update_task_status(self.request.id, 'completed', result)
        
        return result
        
    except Exception as e:
        logger.error(f"获取电影详情失败：{e}")
        # 重试逻辑
        try:
            raise self.retry(exc=e, countdown=5)
        except Exception:
            update_task_status(self.request.id, 'failed', {'error': str(e)})
            raise


@celery_app.task(bind=True)
def batch_update_movies(self, movie_ids: list):
    """
    批量更新电影信息
    展示批量任务处理
    """
    try:
        logger.info(f"开始批量更新 {len(movie_ids)} 部电影")
        update_task_status(self.request.id, 'processing', {'total': len(movie_ids)})
        
        results = []
        for i, movie_id in enumerate(movie_ids, 1):
            # 模拟更新操作
            time.sleep(0.5)
            results.append({
                'movie_id': movie_id,
                'status': 'updated',
                'progress': f"{i}/{len(movie_ids)}"
            })
            
            # 更新任务进度
            update_task_status(
                self.request.id, 
                'processing', 
                {'progress': f"{i}/{len(movie_ids)}", 'current': movie_id}
            )
        
        logger.info(f"批量更新完成，共 {len(results)} 部")
        update_task_status(self.request.id, 'completed', {'results': results})
        
        return {'success': True, 'count': len(results)}
        
    except Exception as e:
        logger.error(f"批量更新失败：{e}")
        update_task_status(self.request.id, 'failed', {'error': str(e)})
        raise


@celery_app.task
def send_notification(message: str):
    """
    发送通知（示例任务）
    展示简单任务
    """
    logger.info(f"发送通知：{message}")
    time.sleep(1)  # 模拟发送延迟
    return {'status': 'sent', 'message': message}


@celery_app.task
def cleanup_old_data(days: int = 30):
    """
    清理旧数据（示例任务）
    展示定时清理任务
    """
    logger.info(f"开始清理 {days} 天前的数据")
    time.sleep(2)  # 模拟清理操作
    return {'status': 'cleaned', 'days': days}


# 任务状态管理
task_status_store = {}


def update_task_status(task_id: str, status: str, data: dict = None):
    """更新任务状态"""
    task_status_store[task_id] = {
        'task_id': task_id,
        'status': status,
        'data': data,
        'updated_at': datetime.now().isoformat()
    }
    logger.info(f"任务 {task_id} 状态更新为：{status}")


def get_task_status(task_id: str):
    """获取任务状态"""
    return task_status_store.get(task_id, {
        'task_id': task_id,
        'status': 'unknown',
        'data': None
    })


# 健康检查
@celery_app.task
def health_check():
    """Celery 健康检查"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'worker': celery_app.control.inspect().active()
    }
