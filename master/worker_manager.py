import logging
from datetime import datetime, timedelta
from models import db, TranscodeWorker, TranscodeTask, VideoInfo

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/worker_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WorkerManager:
    def __init__(self, heartbeat_timeout=30):
        """
        初始化WorkerManager
        :param heartbeat_timeout: worker心跳超时时间（秒）
        """
        self.heartbeat_timeout = heartbeat_timeout

    def update_worker_heartbeat(self, worker_id):
        """
        更新worker的心跳时间
        :param worker_id: worker ID
        """
        try:
            worker = TranscodeWorker.query.get(worker_id)
            if worker:
                worker.last_heartbeat = datetime.utcnow()
                
                # 如果worker有当前任务，更新任务的worker_name和视频状态
                if worker.current_task_id:
                    task = TranscodeTask.query.get(worker.current_task_id)
                    if task:
                        task.worker_name = worker.worker_name
                        # 如果任务正在运行，更新视频状态为转码中
                        if task.task_status == 1:  # running
                            video = VideoInfo.query.get(task.video_id)
                            if video:
                                video.transcode_status = 2  # 转码中
                
                worker.worker_status = 1  # 在线
                db.session.commit()
                logger.debug(f"更新worker心跳时间: {worker_id}")
        except Exception as e:
            logger.error(f"更新worker心跳时间出错: {str(e)}")
            db.session.rollback()

    def check_workers_status(self):
        """
        检查所有worker的状态，将超时的worker标记为离线
        """
        try:
            logger.debug("开始检查worker状态...")
            current_time = datetime.utcnow()
            timeout_threshold = current_time - timedelta(seconds=self.heartbeat_timeout)

            # 查找所有在线但超时的worker
            workers = TranscodeWorker.query.filter(
                TranscodeWorker.worker_status != 0,  # 不是离线状态
                TranscodeWorker.last_heartbeat <= timeout_threshold
            ).all()

            offline_count = 0
            for worker in workers:
                offline_count += 1
                worker.worker_status = 0  # 标记为离线
                logger.info(f"Worker {worker.worker_name} (ID: {worker.id}) 已离线")

                # 查找该worker的所有运行中的任务
                running_tasks = TranscodeTask.query.filter(
                    TranscodeTask.worker_id == worker.id,
                    TranscodeTask.task_status == 1  # running
                ).all()

                for task in running_tasks:
                    logger.info(f"将离线worker的任务 {task.task_id} 标记为失败")
                    task.task_status = 3  # failed
                    task.end_time = current_time
                    task.error_message = "Worker离线，任务自动终止"
                    
                    # 更新视频状态
                    video = VideoInfo.query.get(task.video_id)
                    if video:
                        logger.info(f"更新视频 {video.id} 的转码状态为失败")
                        video.transcode_status = 5  # failed
                        video.transcode_task_id = None  # 清除任务ID
                        video.error_message = "Worker离线，任务自动终止"  # 添加错误信息
                    else:
                        logger.warning(f"未找到任务 {task.task_id} 对应的视频记录")

                # 清除worker的当前任务
                worker.current_task_id = None

            if offline_count > 0:
                logger.warning(f"发现 {offline_count} 个worker离线")
                db.session.commit()
                logger.info("数据库更新完成")

        except Exception as e:
            logger.error(f"检查worker状态时出错: {str(e)}")
            db.session.rollback()

    def get_worker_status(self, worker_id):
        """
        获取worker的当前状态
        :param worker_id: worker ID
        :return: (is_online, status_code)
        """
        try:
            worker = TranscodeWorker.query.get(worker_id)
            if not worker:
                return False, None

            current_time = datetime.utcnow()
            if worker.last_heartbeat and (current_time - worker.last_heartbeat) > timedelta(seconds=self.heartbeat_timeout):
                worker.worker_status = 0  # 离线
                db.session.commit()
                return False, worker.worker_status

            return True, worker.worker_status

        except Exception as e:
            logger.error(f"获取worker状态时出错: {str(e)}")
            return False, None 

    def update_task_status(self, task_id: str, worker_id: str, status: int, progress: float = 0.0,
                          error_message: str = None, elapsed_time: int = 0, remaining_time: int = 0):
        """
        更新任务状态
        :param task_id: 任务ID
        :param worker_id: worker ID
        :param status: 任务状态
        :param progress: 进度
        :param error_message: 错误信息
        :param elapsed_time: 已用时间
        :param remaining_time: 预计剩余时间
        """
        try:
            task = TranscodeTask.query.get(task_id)
            if not task:
                logger.error(f"未找到任务: {task_id}")
                return False

            # 验证worker_id
            if task.worker_id != worker_id:
                logger.error(f"任务 {task_id} 不属于worker {worker_id}")
                return False

            # 更新任务状态
            task.task_status = status
            task.progress = progress
            task.elapsed_time = elapsed_time
            task.remaining_time = remaining_time
            
            if error_message:
                task.error_message = error_message

            # 更新视频状态
            video = VideoInfo.query.get(task.video_id)
            if video:
                if status == 1:  # running
                    video.transcode_status = 2  # 转码中
                elif status == 2:  # completed
                    video.transcode_status = 3  # 已完成
                    video.transcode_task_id = None
                elif status == 3:  # failed
                    video.transcode_status = 5  # 失败
                    video.transcode_task_id = None
                    video.error_message = error_message if error_message else "转码失败"

            db.session.commit()
            logger.debug(f"任务 {task_id} 状态已更新: status={status}, progress={progress}%")
            return True

        except Exception as e:
            logger.error(f"更新任务状态时出错: {str(e)}")
            db.session.rollback()
            return False 

    def check_tasks_status(self):
        """
        检查所有运行中的任务状态，如果对应的worker离线则标记为失败
        """
        try:
            logger.debug("开始检查任务状态...")
            current_time = datetime.utcnow()
            timeout_threshold = current_time - timedelta(seconds=self.heartbeat_timeout)

            # 查找所有运行中的任务
            running_tasks = TranscodeTask.query.filter(
                TranscodeTask.task_status == 1  # running
            ).all()

            failed_count = 0
            for task in running_tasks:
                # 检查worker是否存在且在线
                worker = TranscodeWorker.query.get(task.worker_id)
                if not worker or worker.worker_status == 0 or worker.last_heartbeat <= timeout_threshold:
                    failed_count += 1
                    logger.info(f"任务 {task.task_id} 的worker {task.worker_id} 已离线，将任务标记为失败")
                    
                    # 更新任务状态
                    task.task_status = 3  # failed
                    task.end_time = current_time
                    task.error_message = "Worker离线，任务自动终止"
                    
                    # 更新视频状态
                    video = VideoInfo.query.get(task.video_id)
                    if video:
                        logger.info(f"更新视频 {video.id} 的转码状态为失败")
                        video.transcode_status = 5  # failed
                        video.transcode_task_id = None
                        video.error_message = "Worker离线，任务自动终止"
                    else:
                        logger.warning(f"未找到任务 {task.task_id} 对应的视频记录")

            if failed_count > 0:
                logger.warning(f"发现 {failed_count} 个失败任务")
                db.session.commit()
                logger.info("数据库更新完成")

        except Exception as e:
            logger.error(f"检查任务状态时出错: {str(e)}")
            db.session.rollback()