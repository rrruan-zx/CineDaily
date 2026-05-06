"""
依赖注入系统 - 展示 FastAPI 的依赖注入功能
包含：数据库连接、缓存服务、验证服务
"""
from fastapi import Depends, HTTPException, status
from typing import Generator, Optional
import pymysql
import logging
from contextlib import contextmanager

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'dailymove',
    'charset': 'utf8mb4'
}


class DatabaseDependency:
    """数据库依赖类"""
    
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(**DB_CONFIG)
            return self.connection
        except pymysql.Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"数据库连接失败：{str(e)}"
            )
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


@contextmanager
def get_db_context() -> Generator[pymysql.Connection, None, None]:
    """
    数据库连接上下文管理器
    使用 yield 实现资源的自动清理
    """
    db = None
    try:
        db = pymysql.connect(**DB_CONFIG)
        yield db
    finally:
        if db:
            db.close()


def get_db() -> Generator[pymysql.Connection, None, None]:
    """
    数据库连接依赖注入函数
    用于 FastAPI 路由的 Depends()
    确保连接在使用后自动关闭
    """
    db = None
    try:
        db = pymysql.connect(**DB_CONFIG)
        yield db
    except pymysql.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库错误：{str(e)}"
        )
    finally:
        if db:
            db.close()
            db = None


def get_db_cursor(db: pymysql.Connection = Depends(get_db)):
    """
    数据库游标依赖注入
    返回字典格式的游标
    """
    cursor = db.cursor(pymysql.cursors.DictCursor)
    try:
        yield cursor
    finally:
        cursor.close()


class MovieService:
    """电影服务依赖类"""
    
    def __init__(self, db: pymysql.Connection):
        self.db = db
        self.cursor = db.cursor(pymysql.cursors.DictCursor)
    
    def __del__(self):
        """析构函数，确保关闭游标"""
        if hasattr(self, 'cursor') and self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass
    
    def get_all_movies(self):
        """获取所有电影"""
        self.cursor.execute('SELECT * FROM movies ORDER BY id')
        return self.cursor.fetchall()
    
    def get_movie_by_id(self, movie_id: int):
        """根据 ID 获取电影"""
        self.cursor.execute('SELECT * FROM movies WHERE id = %s', (movie_id,))
        return self.cursor.fetchone()
    
    def get_random_movie(self):
        """随机获取一部电影"""
        self.cursor.execute('SELECT * FROM movies ORDER BY RAND() LIMIT 1')
        return self.cursor.fetchone()
    
    def create_movie(self, movie_data: dict):
        """创建电影"""
        try:
            # 获取当前最大 ID
            self.cursor.execute('SELECT MAX(id) as max_id FROM movies')
            result = self.cursor.fetchone()
            max_id = result['max_id'] if result else 0
            new_id = (max_id or 0) + 1
            
            # 确保所有必需字段都有值
            title = str(movie_data.get('title', '')).strip()
            year = int(movie_data.get('year', 2024))
            tag = str(movie_data.get('tag', '剧情'))
            score = float(movie_data.get('score', 0.0))
            desc = str(movie_data.get('desc', ''))
            bg = str(movie_data.get('bg', ''))
            director = str(movie_data.get('director', '未知'))
            actor = str(movie_data.get('actor', '未知'))
            video_url = str(movie_data.get('video_url', ''))
            
            # 验证必填字段
            if not title:
                raise ValueError('电影标题不能为空')
            
            sql = '''
                INSERT INTO movies 
                (id, title, year, tag, score, `desc`, bg, director, actor, video_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            self.cursor.execute(sql, (
                new_id, title, year, tag, score, desc, bg, director, actor, video_url
            ))
            self.db.commit()
            return new_id
        except Exception as e:
            self.db.rollback()
            logger = logging.getLogger(__name__)
            logger.error(f"创建电影失败：{str(e)}")
            raise e
    
    def update_movie(self, movie_id: int, movie_data: dict):
        """更新电影"""
        # 验证数据不为空
        if not movie_data:
            return 0
        
        # 白名单验证字段名，防止 SQL 注入
        allowed_fields = ['title', 'year', 'tag', 'score', 'desc', 'director', 'actor', 'video_url', 'bg']
        safe_data = {k: v for k, v in movie_data.items() if k in allowed_fields and v is not None}
        
        # 如果没有要更新的数据，直接返回
        if not safe_data:
            return 0
        
        # 使用反引号包裹字段名，进一步防止 SQL 注入
        set_clause = ', '.join([f"`{k}` = %s" for k in safe_data.keys()])
        values = list(safe_data.values()) + [movie_id]
        
        sql = f'UPDATE movies SET {set_clause} WHERE id = %s'
        self.cursor.execute(sql, values)
        self.db.commit()
        return self.cursor.rowcount
    
    def delete_movie(self, movie_id: int):
        """删除电影"""
        self.cursor.execute('DELETE FROM movies WHERE id = %s', (movie_id,))
        self.db.commit()
        return self.cursor.rowcount
    
    def close(self):
        """关闭游标"""
        self.cursor.close()


def get_movie_service(db: pymysql.Connection = Depends(get_db)) -> MovieService:
    """电影服务依赖注入"""
    service = MovieService(db)
    return service


# 验证相关的依赖注入
def validate_movie_id(movie_id: int) -> int:
    """验证电影 ID"""
    if movie_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="电影 ID 必须是正整数"
        )
    return movie_id


def validate_page_params(page: int = 1, page_size: int = 10) -> tuple:
    """验证分页参数"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 10
    return page, page_size


# 缓存服务依赖（示例）
class CacheService:
    """缓存服务（使用内存模拟 Redis）"""
    
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str):
        """获取缓存"""
        return self._cache.get(key)
    
    def set(self, key: str, value, ttl: int = 300):
        """设置缓存"""
        self._cache[key] = value
    
    def delete(self, key: str):
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()


def get_cache_service() -> CacheService:
    """缓存服务依赖注入"""
    return CacheService()
