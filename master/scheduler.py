from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self, app: Flask, scan_paths: list, scan_interval: int = None):
        self.app = app
        self.scan_paths = scan_paths
        self.scheduler = BackgroundScheduler()
        
        # 使用 cron trigger 设置每小时05分执行
        self.scheduler.add_job(
            func=self.scan_videos,
            trigger=CronTrigger(minute=5),  # 每小时的第5分钟执行
            id='scan_videos',
            name='扫描视频文件',
            replace_existing=True
        )

    def start(self):
        try:
            self.scheduler.start()
            logger.info("定时任务调度器已启动，将在每小时05分执行扫描")
        except Exception as e:
            logger.error(f"启动定时任务调度器失败: {str(e)}")

    def stop(self):
        try:
            self.scheduler.shutdown()
            logger.info("定时任务调度器已停止")
        except Exception as e:
            logger.error(f"停止定时任务调度器失败: {str(e)}")

    def scan_videos(self):
        with self.app.app_context():
            try:
                from models import db, VideoInfo, TranscodeLog
                logger.info(f"开始扫描视频文件，路径: {self.scan_paths}")
                
                # ... 其他扫描逻辑保持不变 ...

            except Exception as e:
                logger.error(f"扫描视频文件时出错: {str(e)}")
                # 记录错误日志
                try:
                    error_log = TranscodeLog(
                        log_level=3,  # ERROR
                        log_message=f"扫描视频文件时出错: {str(e)}"
                    )
                    db.session.add(error_log)
                    db.session.commit()
                except Exception as log_error:
                    logger.error(f"记录错误日志失败: {str(log_error)}")