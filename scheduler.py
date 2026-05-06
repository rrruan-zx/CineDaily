"""
定时更新模块
使用 APScheduler 实现定时更新电影数据
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from get_random_movies import get_topic_movies, update_database
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ScheduledMovieUpdater:
    """定时电影更新器"""
    
    def __init__(self, db_config: dict):
        """
        初始化定时更新器
        
        Args:
            db_config: 数据库配置
        """
        self.db_config = db_config
        self.scheduler = BackgroundScheduler()
        
    def start(self, update_interval: str = 'daily', hour: int = 2, minute: int = 0):
        """
        启动定时更新任务
        
        Args:
            update_interval: 更新间隔 ('daily', 'weekly', 'hourly')
            hour: 每天几点执行（0-23）
            minute: 每分钟的第几分（0-59）
        """
        # 根据间隔类型设置触发器
        if update_interval == 'hourly':
            trigger = CronTrigger(minute=minute)
            desc = f"每小时第 {minute} 分钟"
        elif update_interval == 'daily':
            trigger = CronTrigger(hour=hour, minute=minute)
            desc = f"每天 {hour:02d}:{minute:02d}"
        elif update_interval == 'weekly':
            trigger = CronTrigger(day_of_week='mon', hour=hour, minute=minute)
            desc = f"每周一 {hour:02d}:{minute:02d}"
        else:
            raise ValueError(f"不支持的更新间隔：{update_interval}")
        
        # 添加定时任务
        self.scheduler.add_job(
            func=self._update_movies,
            trigger=trigger,
            id='update_movies',
            name='定时更新电影数据',
            replace_existing=True
        )
        
        # 启动调度器
        self.scheduler.start()
        
        print(f"[OK] 定时更新任务已启动")
        print(f"     更新频率：{desc}")
        print(f"     下次执行时间：{self.scheduler.get_job('update_movies').next_run_time}")
        logger.info(f"定时更新任务已启动 - {desc}")
    
    def _update_movies(self):
        """执行更新任务（内部方法）"""
        try:
            logger.info("开始执行定时电影数据更新...")
            print("\n正在从茶杯狐获取最新电影...")
            
            # 获取电影并更新数据库
            movies = get_topic_movies(count=10)
            
            if movies:
                update_database(movies)
                logger.info("电影数据更新成功")
                print("[OK] 定时更新完成")
            else:
                logger.error("电影数据更新失败")
                print("[ERROR] 定时更新失败")
                
        except Exception as e:
            logger.error(f"定时更新出错：{e}", exc_info=True)
            print(f"[ERROR] 定时更新出错：{e}")
    
    def stop(self):
        """停止定时更新"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("[OK] 定时更新任务已停止")
            logger.info("定时更新任务已停止")
    
    def get_status(self) -> dict:
        """
        获取定时任务状态
        
        Returns:
            状态字典
        """
        if not self.scheduler.running:
            return {'running': False, 'message': '定时任务未运行'}
        
        job = self.scheduler.get_job('update_movies')
        if job:
            return {
                'running': True,
                'next_run': job.next_run_time,
                'trigger': str(job.trigger)
            }
        else:
            return {'running': True, 'message': '未找到更新任务'}


def create_scheduler(db_config: dict, update_interval: str = 'daily', hour: int = 2):
    """
    创建并启动定时更新器
    
    Args:
        db_config: 数据库配置
        update_interval: 更新间隔
        hour: 每天几点执行
        
    Returns:
        ScheduledMovieUpdater 实例
    """
    updater = ScheduledMovieUpdater(db_config)
    updater.start(update_interval=update_interval, hour=hour)
    return updater


# 测试函数
if __name__ == '__main__':
    import time
    
    # 数据库配置
    DB_CONFIG = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'database': 'dailymove',
        'charset': 'utf8mb4'
    }
    
    print("测试定时更新功能...")
    print("=" * 80)
    
    # 创建定时更新器
    scheduler = create_scheduler(DB_CONFIG, update_interval='daily', hour=14)
    
    # 显示状态
    status = scheduler.get_status()
    print(f"\n定时任务状态：{status}")
    
    # 保持运行 10 秒后停止
    print("\n等待 10 秒后停止定时任务...")
    time.sleep(10)
    
    scheduler.stop()
    print("\n测试完成！")
