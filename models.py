"""
Pydantic 数据模型 - 展示 FastAPI 的数据验证能力
使用 Pydantic v2 新特性
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class MovieBase(BaseModel):
    """电影基础模型"""
    title: str = Field(..., min_length=1, max_length=200, description="电影标题")
    year: int = Field(..., ge=1900, le=2030, description="上映年份")
    tag: str = Field(default="剧情", max_length=50, description="电影类型")
    score: float = Field(..., ge=0, le=10, description="评分")
    desc: str = Field(default="", max_length=2000, description="电影简介")
    director: str = Field(default="未知", max_length=100, description="导演")
    actor: str = Field(default="未知", max_length=500, description="主演")


class MovieCreate(MovieBase):
    """创建电影时的验证模型"""
    video_url: str = Field(..., max_length=500, description="视频链接")
    bg: str = Field(default="", max_length=500, description="背景图片链接")
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v):
        """验证标题不为空"""
        if not v.strip():
            raise ValueError('电影标题不能为空')
        return v.strip()
    
    @field_validator('score')
    @classmethod
    def score_valid(cls, v):
        """验证评分合理性"""
        if v < 0 or v > 10:
            raise ValueError('评分必须在 0-10 之间')
        return round(v, 1)


class MovieUpdate(BaseModel):
    """更新电影时的验证模型（所有字段可选）"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    year: Optional[int] = Field(None, ge=1900, le=2030)
    tag: Optional[str] = Field(None, max_length=50)
    score: Optional[float] = Field(None, ge=0, le=10)
    desc: Optional[str] = Field(None, max_length=2000)
    director: Optional[str] = Field(None, max_length=100)
    actor: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    bg: Optional[str] = Field(None, max_length=500)


class MovieResponse(MovieBase):
    """电影响应模型"""
    id: int
    video_url: str
    bg: str
    
    model_config = {'from_attributes': True}


class APIResponse(BaseModel):
    """通用 API 响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PerformanceMetrics(BaseModel):
    """性能指标模型"""
    endpoint: str
    method: str
    response_time_ms: float
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.now)


class TaskStatus(BaseModel):
    """异步任务状态模型"""
    task_id: str
    status: str  # pending, processing, completed, failed
    result: Optional[dict] = None
    error: Optional[str] = None


class LogMessage(BaseModel):
    """日志消息模型"""
    level: str  # INFO, WARNING, ERROR
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = ""
