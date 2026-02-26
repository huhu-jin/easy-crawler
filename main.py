"""Easy Crawler 主程序"""
import signal
import sys

from datetime import datetime

from src.config_loader import ConfigLoader
from src.crawler import CrawlerService
from src.storage import StorageService
from src.scheduler import SchedulerService
from src.api import create_app


# 全局变量
scheduler_service = None


def crawl_task():
    """爬取任务"""
    print(f"\n{'='*60}")
    print(f"开始执行爬取任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    try:
        # 加载配置
        config_loader = ConfigLoader()
        urls = config_loader.load()
        
        # 初始化服务
        crawler = CrawlerService()
        storage = StorageService()
        
        # 遍历所有 URL
        total_saved = 0
        for item in urls:
            url = item['url']
            desc = item['desc']
            list_selector = item.get('list_selector')
            content_selector = item.get('content_selector')
            
            # 爬取内容
            results = crawler.check_and_crawl(url, desc, list_selector, content_selector)
            
            # 保存结果
            for title, markdown, original_url in results:
                file_path = storage.save_markdown(markdown, title)
                print(f"已保存: {file_path}")
                total_saved += 1
        
        print(f"\n任务完成，共保存 {total_saved} 个文件\n")
        
    except Exception as e:
        print(f"爬取任务执行失败: {e}")
        import traceback
        traceback.print_exc()


def signal_handler(sig, frame):
    """信号处理器，用于优雅退出"""
    print("\n正在停止服务...")
    if scheduler_service:
        scheduler_service.stop()
    sys.exit(0)


def main():
    """主函数"""
    global scheduler_service
    
    print("=" * 60)
    print("Easy Crawler 启动中...")
    print("=" * 60)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 初始化存储服务（用于 API）
    storage = StorageService()
    
    # 启动调度器
    scheduler_service = SchedulerService(crawl_task)
    scheduler_service.start()
    
    # 创建并启动 Flask 应用
    app = create_app(storage)
    print("\n启动 Flask API 服务...")
    print("API 地址: http://localhost:5000")
    print("  - 健康检查: GET /api/health")
    print("  - 文件列表: GET /api/list?date=YYYY-MM-DD")
    print("  - 文件内容: GET /api/content?date=YYYY-MM-DD&filename=xxx.md")
    print("\n按 Ctrl+C 停止服务\n")
    
    # 运行 Flask（这会阻塞主线程）
    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == "__main__":
    main()

