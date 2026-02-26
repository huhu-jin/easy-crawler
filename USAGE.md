# Easy Crawler - 使用说明

## 项目简介

这是一个基于 Python 的网页爬虫项目，主要功能包括：

- 📡 **定时监控** - 启动时和每12小时自动检查配置的 URL
- 🔍 **智能检测** - 只爬取今天更新的内容（基于列表中的日期）
- 📝 **Markdown 转换** - 自动将网页内容转换为 Markdown 格式
- 💾 **按日期存储** - 按 `YYYY-MM-DD` 格式组织文件
- 🌐 **REST API** - 提供 Flask API 查询已爬取的内容

## 技术栈

- **Playwright** - 浏览器自动化，模拟用户操作
- **BeautifulSoup4** - HTML 解析
- **html2text** - HTML 转 Markdown
- **Flask** - Web API 框架
- **APScheduler** - 任务调度

## 安装

### 1. 安装依赖

```bash
uv sync
```

### 2. 安装 Playwright 浏览器

```bash
uv run playwright install chromium
```

## 配置

编辑 `config.json` 文件，添加要监控的 URL：

```json
[
    {
        "url": "https://example.com/news",
        "desc": "示例网站"
    }
]
```

## 运行

```bash
uv run python main.py
```

程序启动后会：
1. 立即执行一次爬取任务
2. 启动 Flask API 服务（端口 5000）
3. 每12小时自动执行爬取任务

## API 接口

### 1. 健康检查

```bash
GET http://localhost:5000/api/health
```

### 2. 获取文件列表

```bash
GET http://localhost:5000/api/list?date=2026-02-16
```

返回示例：
```json
{
    "date": "2026-02-16",
    "count": 3,
    "files": ["article1.md", "article2.md", "article3.md"]
}
```

### 3. 获取文件内容

```bash
GET http://localhost:5000/api/content?date=2026-02-16&filename=article1.md
```

返回示例：
```json
{
    "date": "2026-02-16",
    "filename": "article1.md",
    "content": "# 文章标题\n\n文章内容..."
}
```

## 数据存储

爬取的 Markdown 文件保存在 `data/` 目录下：

```
data/
├── 2026-02-16/
│   ├── article1.md
│   ├── article2.md
│   └── article3.md
└── 2026-02-17/
    └── article4.md
```

## 工作原理

1. **读取配置** - 从 `config.json` 加载要监控的 URL 列表
2. **检测更新** - 访问每个 URL，查找 `<ul><li>` 结构中包含今天日期的项目
3. **提取链接** - 从符合条件的列表项中提取详情页链接
4. **爬取内容** - 使用 Playwright 访问详情页，获取完整 HTML
5. **转换格式** - 将 HTML 转换为 Markdown
6. **保存文件** - 按日期保存到 `data/YYYY-MM-DD/` 目录

## 停止服务

按 `Ctrl+C` 优雅停止服务。

## 项目结构

```
easy-crawler/
├── main.py              # 主程序入口
├── config.json          # URL 配置文件
├── pyproject.toml       # 项目依赖配置
├── data/                # 数据存储目录
└── src/
    ├── __init__.py
    ├── config_loader.py # 配置加载器
    ├── crawler.py       # 爬虫服务
    ├── storage.py       # 存储服务
    ├── scheduler.py     # 调度器
    └── api.py           # Flask API
```
