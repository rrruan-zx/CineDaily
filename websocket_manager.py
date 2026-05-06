"""
WebSocket 实时日志管理
展示 WebSocket 实时通信技术
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import logging
from datetime import datetime
import asyncio

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 存储所有活跃的 WebSocket 连接
        self.active_connections: List[WebSocket] = []
        # 按房间分组连接
        self.rooms: Dict[str, List[WebSocket]] = {}
        # 日志队列
        self.log_queue = asyncio.Queue()
    
    async def connect(self, websocket: WebSocket, room: str = "default"):
        """接受 WebSocket 连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # 加入房间
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)
        
        logger.info(f"新的 WebSocket 连接，当前连接数：{len(self.active_connections)}")
        
        # 发送欢迎消息
        await self.send_personal_message(
            websocket,
            {
                'type': 'welcome',
                'message': '已连接到实时日志服务',
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def disconnect(self, websocket: WebSocket):
        """断开 WebSocket 连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # 从所有房间移除
        for room in self.rooms:
            if websocket in self.rooms[room]:
                self.rooms[room].remove(websocket)
        
        logger.info(f"WebSocket 连接断开，当前连接数：{len(self.active_connections)}")
    
    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败：{e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict, room: str = None):
        """
        广播消息
        :param room: 指定房间，None 表示所有连接
        """
        disconnected = []
        
        if room:
            # 广播到指定房间
            connections = self.rooms.get(room, [])
        else:
            # 广播到所有连接
            connections = self.active_connections
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"广播消息失败：{e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)
    
    async def log_message(self, level: str, message: str, source: str = ""):
        """
        发送日志消息到所有连接
        """
        log_data = {
            'type': 'log',
            'level': level,
            'message': message,
            'source': source,
            'timestamp': datetime.now().isoformat()
        }
        
        # 添加到队列
        await self.log_queue.put(log_data)
        
        # 广播到所有连接
        await self.broadcast(log_data)
    
    async def process_log_queue(self):
        """处理日志队列"""
        while True:
            try:
                log_data = await asyncio.wait_for(
                    self.log_queue.get(),
                    timeout=1.0
                )
                # 可以在这里添加额外的日志处理逻辑
                logger.info(f"[{log_data['level']}] {log_data['message']}")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"处理日志队列失败：{e}")


# 创建全局 WebSocket 管理器实例
websocket_manager = WebSocketManager()


# WebSocket 日志处理器
class WebSocketLogHandler(logging.Handler):
    """将 Python 日志发送到 WebSocket"""
    
    def __init__(self, manager: WebSocketManager):
        super().__init__()
        self.manager = manager
        self.setLevel(logging.INFO)
    
    def emit(self, record):
        """发射日志记录"""
        try:
            log_entry = self.format(record)
            asyncio.create_task(
                self.manager.log_message(
                    level=record.levelname,
                    message=log_entry,
                    source=record.name
                )
            )
        except Exception as e:
            print(f"发送日志到 WebSocket 失败：{e}")


def setup_websocket_logger(manager: WebSocketManager):
    """设置 WebSocket 日志处理器"""
    handler = WebSocketLogHandler(manager)
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logging.getLogger().addHandler(handler)
    return handler
