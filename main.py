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
_first_run = True


def crawl_task():
    """爬取任务"""
    global _first_run

    print(f"\n{'='*60}")
    print(f"开始执行爬取任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if _first_run:
        print("（首次运行）")
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
            file_dir = item.get('file_dir', '')
            list_selector = item.get('list_selector')
            list_date_selector = item.get('list_date_selector')
            content_selector = item.get('content_selector')
            pdf_selector = item.get('pdf_selector')

            # 首次运行时使用 init_today，否则用当天（None）
            target_date = None
            if _first_run:
                init_today_str = item.get('init_today')
                if init_today_str:
                    try:
                        target_date = datetime.strptime(init_today_str, '%Y-%m-%d').date()
                        print(f"  [{desc}] 使用初始日期: {target_date}")
                    except ValueError:
                        print(f"  [{desc}] init_today 格式错误（应为 YYYY-MM-DD），使用今天")

            # 爬取并即时保存（生成器：每爬完一篇立即保存）
            for title, markdown, original_url in crawler.check_and_crawl(url, desc, list_selector, content_selector, pdf_selector, list_date_selector, target_date):
                file_path = storage.save_markdown(markdown, title, file_dir=file_dir)
                print(f"已保存: {file_path}")
                total_saved += 1
        
        print(f"\n任务完成，共保存 {total_saved} 个文件\n")

    except Exception as e:
        print(f"爬取任务执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 首次运行结束后，后续均使用当天日期
        _first_run = False


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
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()

