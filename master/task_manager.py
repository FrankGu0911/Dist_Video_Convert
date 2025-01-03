import logging
from datetime import datetime, timedelta
from models import db, TranscodeTask, VideoInfo, TranscodeWorker, TranscodeLog

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self, app, socketio):
        self.app = app
        self.socketio = socketio

    def check_tasks_status(self):
        """检查任务状态，包括超时检测"""
        try:
            logger.debug("开始检查任务状态...")
            current_time = datetime.utcnow()
            
            # 获取所有运行中的任务
            running_tasks = TranscodeTask.query.filter(
                TranscodeTask.task_status == 1  # running
            ).all()
            
            for task in running_tasks:
                # 检查任务是否超时（超过60秒没有更新）
                if task.last_update_time is None or (current_time - task.last_update_time) > timedelta(seconds=60):
                    logger.info(f"任务 {task.task_id} 超时，开始处理")
                    # 更新任务状态
                    task.task_status = 3  # failed
                    task.end_time = current_time
                    task.error_message = "任务超过60秒未更新，判定为超时"
                    
                    # 更新视频状态
                    video = VideoInfo.query.get(task.video_id)
                    if video:
                        video.transcode_status = 5  # failed
                        video.transcode_task_id = None
                    
                    # 更新worker状态
                    worker = TranscodeWorker.query.get(task.worker_id)
                    if worker:
                        worker.worker_status = 1  # pending
                        worker.current_task_id = None
                    
                    # 记录错误日志
                    log = TranscodeLog(
                        task_id=task.id,
                        log_level=3,  # error
                        log_message=f"任务 {task.task_id} 超过60秒未更新，判定为超时"
                    )
                    db.session.add(log)
                    
                    # 通过WebSocket发送任务状态更新
                    task_data = {
                        'task_id': task.task_id,
                        'video_path': task.video_path,
                        'dest_path': task.dest_path,
                        'worker_id': task.worker_id,
                        'worker_name': task.worker_name,
                        'progress': task.progress,
                        'status': task.task_status,
                        'error_message': task.error_message,
                        'elapsed_time': task.elapsed_time,
                        'remaining_time': None
                    }
                    
                    # 发送到特定任务的房间
                    self.socketio.emit('task_update', task_data, room=f'task_{task.task_id}')
                    # 发送到任务列表房间
                    self.socketio.emit('tasks_update', {
                        'type': 'update',
                        'task': task_data
                    }, room='tasks_room')
                    
                    logger.info(f"任务 {task.task_id} 超时处理完成")
            
            # 提交所有更改
            db.session.commit()
                
        except Exception as e:
            logger.error(f"检查任务状态出错: {str(e)}")
            db.session.rollback() 