from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import os
import logging
from worker_manager import WorkerManager
from video_manager import VideoManager

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
        with self.app.app_context():
            try:
                from models import db, VideoInfo, TranscodeLog
                logger.info(f"开始扫描视频文件，路径: {self.scan_paths}")
                
                # 获取所有数据库中的视频记录
                all_videos = VideoInfo.query.all()
                for video in all_videos:
                    video.exist = False  # 初始化所有记录为不存在
                
                processed_count = 0  # 处理文件计数
                
                # 扫描所有路径
                for scan_path in self.scan_paths:
                    logger.info(f"扫描目录: {scan_path}")
                    # 获取所有视频文件
                    video_files = []
                    for root, _, files in os.walk(scan_path):
                        for file in files:
                            if file.endswith(('.mp4', '.mkv', '.avi', '.flv')):
                                if '-trailer' in file.lower():
                                    logger.debug(f"跳过预告片: {file}")
                                    continue
                                video_files.append(os.path.join(root, file))

                    for video_file in video_files:
                        try:
                            # 获取文件状态
                            file_stat = os.stat(video_file)
                            file_size = file_stat.st_size / (1024 * 1024)  # 转换为MB
                            
                            # 获取相对路径
                            relative_path = self.video_manager.get_relative_path(video_file)
                            
                            # 查找数据库中是否存在该视频记录
                            existing_video = VideoInfo.query.filter_by(video_path=relative_path).first()
                            
                            if existing_video:
                                # 视频已存在，检查是否需要更新
                                existing_video.exist = True
                                if self.video_manager.check_file_changes(video_file, existing_video):
                                    # 文件已修改，更新记录
                                    existing_video.video_size = file_size
                                    existing_video.last_modified = datetime.utcnow()
                                    existing_video.transcode_status = 0  # 重置转码状态
                                    logger.info(f"更新视频记录: {relative_path}")
                            else:
                                # 新视频，创建记录
                                new_video = VideoInfo(
                                    video_path=relative_path,
                                    video_size=file_size,
                                    exist=True,
                                    transcode_status=1 if VideoInfo.should_transcode() else 0,  # 判断是否需要转码
                                    last_modified=datetime.utcnow()
                                )
                                db.session.add(new_video)
                                logger.info(f"添加新视频: {relative_path}")
                            
                            processed_count += 1
                            if processed_count % 20 == 0:  # 每处理20个文件提交一次
                                db.session.commit()
                                
                        except Exception as e:
                            logger.error(f"处理视频文件时出错 {video_file}: {str(e)}")
                            continue
                            
                # 最后一次提交
                db.session.commit()
                
                # 处理不存在的视频记录
                non_exist_videos = VideoInfo.query.filter_by(exist=False).all()
                for video in non_exist_videos:
                    logger.info(f"删除不存在的视频记录: {video.video_path}")
                    db.session.delete(video)
                
                db.session.commit()
                logger.info("视频扫描完成")

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

    def check_tasks(self):
        """检查任务状态的定时任务"""
        with self.app.app_context():
            try:
                logger.debug("开始检查任务状态...")
                self.worker_manager.check_tasks_status()
            except Exception as e:
                logger.error(f"检查任务状态时出错: {str(e)}")