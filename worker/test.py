import logging
import time
import os
from .base import BasicWorker, TaskStatus, WorkerType

class TestWorker(BasicWorker):
    def process_task(self, task):
        """测试用的任务处理方法，只打印路径并返回失败状态"""
        task_id = task["task_id"]
        video_path = task["video_path"]
        
        # 使用基类的方法构建完整路径（如果文件不存在会抛出FileNotFoundError）
        full_video_path = self._get_full_video_path(video_path)
        
        logging.info(f"Processing task {task_id}")
        logging.info(f"Original video path: {video_path}")
        logging.info(f"Full video path: {full_video_path}")
        logging.info(f"Save path: {self.save_path}")
        logging.info(f"Worker config:")
        logging.info(f"  - Type: {self.worker_type.name}")
        logging.info(f"  - Support VR: {self.support_vr}")
        logging.info(f"  - CRF: {self.crf}")
        logging.info(f"  - Preset: {self.preset}")
        logging.info(f"  - Rate: {self.rate}")
        logging.info(f"  - NUMA: {self.numa_param}")
        logging.info(f"  - Remove original: {self.remove_original}")
        
        # 更新为运行状态
        self.update_task_status(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            progress=0.0,
            elapsed_time=0,
            remaining_time=10
        )
        
        # 等待1秒模拟处理
        time.sleep(1)
        
        # 更新为失败状态
        self.update_task_status(
            task_id=task_id,
            status=TaskStatus.FAILED,
            progress=0.0,
            error_message="Test worker always fails",
            elapsed_time=1,
            remaining_time=0
        ) 