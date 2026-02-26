"""调度器服务模块"""
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import Callable


class SchedulerService:
    """任务调度服务"""
    
    def __init__(self, crawl_callback: Callable):
        """
        初始化调度器
        
        Args:
            crawl_callback: 爬取任务的回调函数
        """
        self.scheduler = BackgroundScheduler()
        self.crawl_callback = crawl_callback
    
    def start(self):
        """启动调度器"""
        # 添加定时任务：每12小时执行一次
        self.scheduler.add_job(
            self.crawl_callback,
            trigger=IntervalTrigger(hours=12),
            id='crawl_task',
            name='爬取任务',
            replace_existing=True
        )
        
        # 启动调度器
        self.scheduler.start()
        print(f"调度器已启动，下次执行时间: {self.scheduler.get_job('crawl_task').next_run_time}")
        
        # 立即执行一次
        print("执行初始爬取任务...")
        self.crawl_callback()
    
    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("调度器已停止")
