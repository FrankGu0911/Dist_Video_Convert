from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from video_manager import VideoManager
from worker_manager import WorkerManager
import logging
import os
from flask import current_app
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self, app, scan_paths, scan_interval):
        self.app = app
        self.scheduler = BackgroundScheduler()
        self.video_manager = VideoManager(scan_paths)
        self.worker_manager = WorkerManager()
        self.scan_interval = scan_interval
        
        if not os.path.exists('logs'):
            os.makedirs('logs')

    def start(self):
        """启动调度器"""
        try:
            # 添加视频扫描任务
            self.scheduler.add_job(
                func=self._scan_videos_task,
                trigger=IntervalTrigger(minutes=self.scan_interval),
                id='scan_videos',
                name='扫描视频文件',
                replace_existing=True
            )
            
            # 添加worker状态检查任务，每30秒执行一次
            self.scheduler.add_job(
                func=self._check_workers_task,
                trigger=IntervalTrigger(seconds=30),
                id='check_workers',
                name='检查worker状态',
                replace_existing=True
            )
            
            # 立即执行一次扫描和检查
            self._scan_videos_task()
            self._check_workers_task()
            
            # 启动调度器
            self.scheduler.start()
            logger.info(f"调度器已启动，视频扫描间隔：{self.scan_interval}分钟，worker检查间隔：30秒")
        except Exception as e:
            logger.error(f"启动调度器时出错: {str(e)}")

    def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown()
            logger.info("调度器已停止")
        except Exception as e:
            logger.error(f"停止调度器时出错: {str(e)}")

    def _scan_videos_task(self):
        """视频扫描任务包装器"""
        with self.app.app_context():
            try:
                self.video_manager.scan_videos()
            except Exception as e:
                logger.error(f"执行视频扫描任务时出错: {str(e)}")

    def _check_workers_task(self):
        """Worker状态检查任务包装器"""
        with self.app.app_context():
            try:
                self.worker_manager.check_workers_status()
            except Exception as e:
                logger.error(f"执行worker状态检查任务时出错: {str(e)}")

    def get_worker_manager(self):
        """获取worker管理器实例"""
        return self.worker_manager 