"""依赖注入系统 - 数据库连接、服务类、验证"""
from fastapi import Depends, HTTPException, status
from typing import Generator
import pymysql
import logging
from contextlib import contextmanager

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'dailymove',
    'charset': 'utf8mb4'
}


@contextmanager
def get_db_context() -> Generator[pymysql.Connection, None, None]:
    """数据库连接上下文管理器"""
    db = None
    try:
        db = pymysql.connect(**DB_CONFIG)
        yield db
    finally:
        if db:
            db.close()


def get_db() -> Generator[pymysql.Connection, None, None]:
    """数据库连接依赖注入"""
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


class MovieService:
    """电影服务类"""
    
    def __init__(self, db: pymysql.Connection):
        self.db = db
        self.cursor = db.cursor(pymysql.cursors.DictCursor)
    
    def __del__(self):
        if hasattr(self, 'cursor') and self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass
    
    def get_all_movies(self):
        self.cursor.execute('SELECT * FROM movies ORDER BY id')
        return self.cursor.fetchall()
    
    def get_movie_by_id(self, movie_id: int):
        self.cursor.execute('SELECT * FROM movies WHERE id = %s', (movie_id,))
        return self.cursor.fetchone()
    
    def get_random_movie(self):
        self.cursor.execute('SELECT * FROM movies ORDER BY RAND() LIMIT 1')
        return self.cursor.fetchone()
    
    def create_movie(self, movie_data: dict):
        try:
            self.cursor.execute('SELECT MAX(id) as max_id FROM movies')
            result = self.cursor.fetchone()
            max_id = result['max_id'] if result else 0
            new_id = (max_id or 0) + 1
            
            title = str(movie_data.get('title', '')).strip()
            year = int(movie_data.get('year', 2024))
            tag = str(movie_data.get('tag', '剧情'))
            score = float(movie_data.get('score', 0.0))
            desc = str(movie_data.get('desc', ''))
            bg = str(movie_data.get('bg', ''))
            director = str(movie_data.get('director', '未知'))
            actor = str(movie_data.get('actor', '未知'))
            video_url = str(movie_data.get('video_url', ''))
            
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
        if not movie_data:
            return 0
        
        allowed_fields = ['title', 'year', 'tag', 'score', 'desc', 'director', 'actor', 'video_url', 'bg']
        safe_data = {k: v for k, v in movie_data.items() if k in allowed_fields and v is not None}
        
        if not safe_data:
            return 0
        
        set_clause = ', '.join([f"`{k}` = %s" for k in safe_data.keys()])
        values = list(safe_data.values()) + [movie_id]
        
        sql = f'UPDATE movies SET {set_clause} WHERE id = %s'
        self.cursor.execute(sql, values)
        self.db.commit()
        return self.cursor.rowcount
    
    def delete_movie(self, movie_id: int):
        self.cursor.execute('DELETE FROM movies WHERE id = %s', (movie_id,))
        self.db.commit()
        return self.cursor.rowcount


def get_movie_service(db: pymysql.Connection = Depends(get_db)) -> MovieService:
    """电影服务依赖注入"""
    return MovieService(db)


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
