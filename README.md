# CineDaily - 现代化电影聚合平台

基于 FastAPI + Vue.js 的电影聚合平台，支持自动化爬取、智能筛选、随机抽样更新。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 启动 FastAPI 应用
python main.py

# 启动 Celery Worker（可选）
celery -A tasks worker --loglevel=info --pool=solo
```

### 3. 访问页面

- **电影首页**: http://localhost:8000
- **管理后台**: http://localhost:8000/static/admin.html
- **API 文档**: http://localhost:8000/docs

---

## 📁 项目结构

```
CineDaily/
├── main.py                      # FastAPI 主应用
├── models.py                    # Pydantic 数据模型
├── middleware.py                # 中间件系统
├── dependencies.py              # 依赖注入
├── tasks.py                     # Celery 异步任务
├── websocket_manager.py         # WebSocket 管理
├── scheduler.py                 # 定时任务
├── get_high_score_movies.py     # 高评分电影爬虫 ⭐
├── static/
│   ├── index.html               # 电影首页
│   ├── detail.html              # 电影详情页（带滚动演员列表）
│   └── admin.html               # 管理后台 ⭐
└── requirements.txt
```

---

## 🎯 核心功能

### 1. 智能电影爬虫 ⭐

```bash
# 运行高评分电影爬虫（从 100+ 部中随机选择 20 部）
python get_high_score_movies.py
```

**特性**：
- ✅ 扫描 150 页高评分电影（9.0-10.0 分）
- ✅ 自动去重（基于 URL）
- ✅ 从 100+ 部候选电影中**随机抽取** 20 部
- ✅ 避免重复更新，每次获得不同电影组合
- ✅ 自动获取详情：主演、导演、评分、简介

### 2. 定时更新

`scheduler.py` 配置每天凌晨 2 点自动更新电影数据。

**启动 FastAPI 时自动运行定时任务**。

### 3. 电影管理后台

访问 **http://localhost:8000/static/admin.html**：
- 📊 数据统计（电影总数、平均评分、最新年份）
- ➕ 添加新电影
- ✏️ 编辑电影信息
- 🗑️ 删除电影
- 🔄 实时刷新列表

### 4. 电影详情页特性

- 🎬 视频播放（支持 iframe 嵌入 + HTML5 播放器）
- 👥 演员列表滚动展示（一次显示 3 个，自定义滚动条）
- 🎨 导演独立卡片展示
- 📱 响应式设计（Tailwind CSS）

### 5. RESTful API

```bash
GET  /api/movies          # 获取所有电影
GET  /api/movie/random    # 随机推荐
GET  /api/movie/{id}      # 电影详情
POST /api/movies          # 添加电影
PUT  /api/movie/{id}      # 更新电影
DELETE /api/movie/{id}    # 删除电影
```

---

## 🔧 技术特性

### 1. Pydantic v2 数据验证
- 自动验证请求数据
- 字段长度、范围验证
- 类型检查和转换

### 2. 中间件系统
- 性能监控（记录每个请求的处理时间）
- 全局错误处理
- CORS 跨域支持

### 3. 依赖注入
- 数据库连接自动管理
- 服务层封装
- 资源自动清理

### 4. Celery 异步任务
- Redis 消息队列
- 异步获取电影详情
- 批量任务处理

### 5. WebSocket 实时日志
- 实时推送系统日志
- 监控系统运行状态

---

## 📊 数据库

### movies 表结构

```sql
CREATE TABLE movies (
  id INT NOT NULL AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  year INT NOT NULL,
  tag VARCHAR(50) DEFAULT '剧情',
  score FLOAT DEFAULT 7.0,
  `desc` TEXT,
  bg VARCHAR(500),
  director VARCHAR(100) DEFAULT '未知',
  actor VARCHAR(500) DEFAULT '未知',
  video_url VARCHAR(500),
  PRIMARY KEY (id)
);
```

---

## 🔍 常见问题

### Q: 如何手动更新电影数据？

```bash
python get_high_score_movies.py
```

### Q: 如何确保每次更新不同的电影？

爬虫会自动从 100+ 部符合条件的电影中**随机抽取** 20 部，每次运行都会得到不同的组合。

### Q: 定时任务不执行？

确保 FastAPI 应用正在运行，定时任务会随应用启动。

### Q: Celery Worker 无法连接 Redis？

1. 确认 Redis 服务已启动：`Get-Service redis*`
2. 检查 Redis 配置：`tasks.py` 中的 Redis 地址

### Q: 如何修改数据库配置？

编辑 `main.py`、`dependencies.py`、`get_high_score_movies.py` 中的 `DB_CONFIG`。

---

## 📝 使用示例

### 添加电影

```bash
curl -X POST "http://localhost:8000/api/movies" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "新电影",
    "year": 2024,
    "tag": "剧情",
    "score": 8.5,
    "desc": "电影简介",
    "director": "导演名",
    "actor": "主演名",
    "video_url": "https://..."
  }'
```

### 获取随机电影

```bash
curl "http://localhost:8000/api/movie/random"
```

---

## 🎓 技术栈

- **后端框架**: FastAPI
- **数据库**: MySQL
- **消息队列**: Redis + Celery
- **前端**: Vue 3 + Tailwind CSS
- **数据验证**: Pydantic v2
- **实时通信**: WebSocket
- **爬虫**: BeautifulSoup + Requests

---

## 📄 项目亮点

1. **智能随机抽样**：从大量候选中随机选择，避免重复
2. **现代化 UI**：Tailwind CSS + Vue 3 响应式设计
3. **演员滚动列表**：自定义滚动条，一次显示 3 个演员
4. **独立导演卡片**：与演员列表分离展示
5. **视频播放集成**：支持 iframe 嵌入和 HTML5 播放器
6. **完整后台管理**：CRUD 操作一应俱全

---

## 💡 下一步

1. **添加更多电影源**
2. **实现用户系统**
3. **添加收藏功能**
4. **部署到生产环境**

---

**作者**: CineDaily Team  
**版本**: 3.0.0  
**更新时间**: 2026-05-06
