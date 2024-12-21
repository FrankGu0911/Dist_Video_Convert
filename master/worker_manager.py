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
                
                # 如果worker有当前任务，更新任务的worker_name
                if worker.current_task_id:
                    task = TranscodeTask.query.get(worker.current_task_id)
                    if task and not task.worker_name:
                        task.worker_name = worker.worker_name
                
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
                running_tasks = TranscodeTask.query.filter_by(
                    worker_id=worker.id,
                    task_status=1  # running
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