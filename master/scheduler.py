from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import os
import logging
from worker_manager import WorkerManager
from video_manager import VideoManager
from video import Video

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self, app: Flask, scan_paths: list, scan_interval: int = None):
        self.app = app
        self.scan_paths = scan_paths
        self.scheduler = BackgroundScheduler()
        self.worker_manager = WorkerManager()
        self.video_manager = VideoManager(scan_paths)
        # 使用 cron trigger 设置每小时05分执行视频扫描
        self.scheduler.add_job(
            func=self.scan_videos,
            trigger=CronTrigger(minute=5),  # 每小时的第5分钟执行
            id='scan_videos',
            name='扫描视频文件',
            replace_existing=True
        )
        
        # 添加检查worker状态的定时任务，每30秒执行一次
        self.scheduler.add_job(
            func=self.check_workers,
            trigger='interval',
            seconds=30,
            id='check_workers',
            name='检查worker状态',
            replace_existing=True
        )

        # 添加检查任务状态的定时任务，每30秒执行一次
        self.scheduler.add_job(
            func=self.check_tasks,
            trigger='interval',
            seconds=30,
            id='check_tasks',
            name='检查任务状态',
            replace_existing=True
        )

    def start(self):
        try:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")
            logger.info("- 视频扫描任务：每小时05分执行")
            logger.info("- Worker状态检查：每30秒执行一次")
            logger.info("- 任务状态检查：每30秒执行一次")
        except Exception as e:
            logger.error(f"启动定时任务调度器失败: {str(e)}")

    def stop(self):
        try:
            self.scheduler.shutdown()
            logger.info("定时任务调度器已停止")
        except Exception as e:
            logger.error(f"停止定时任务调度器失败: {str(e)}")

    def check_workers(self):
        """检查worker状态的定时任务"""
        with self.app.app_context():
            try:
                logger.debug("开始检查worker状态...")
                self.worker_manager.check_workers_status()
            except Exception as e:
                logger.error(f"检查worker状态时出错: {str(e)}")

    def scan_videos(self):
        """扫描视频文件的定时任务"""
        with self.app.app_context():
            try:
                logger.info(f"开始扫描视频文件，路径: {self.scan_paths}")
                # 使用 VideoManager 的 scan_videos 方法
                self.video_manager.scan_videos()
            except Exception as e:
                logger.error(f"扫描视频文件时出错: {str(e)}")
                # 记录错误日志
                try:
                    from models import db, TranscodeLog
                    error_log = TranscodeLog(
                        log_level=3,  # ERROR
                        log_message=f"扫描视频文件时出错: {str(e)}"
                    )
                    db.session.add(error_log)
                    db.session.commit()
                except Exception as log_error:
                    logger.error(f"记录错误日志失败: {str(log_error)}")

    def check_tasks(self):
        """检查任务状态的定时任务"""
        with self.app.app_context():
            try:
                logger.debug("开始检查任务状态...")
                self.worker_manager.check_tasks_status()
            except Exception as e:
                logger.error(f"检查任务状态时出错: {str(e)}")