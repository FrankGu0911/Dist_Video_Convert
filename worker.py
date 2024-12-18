import requests
import time
import threading
import logging
from enum import Enum

class WorkerType(Enum):
    CPU = 0
    NVENC = 1 
    QSV = 2
    VPU = 3

class WorkerStatus(Enum):
    OFFLINE = 0
    PENDING = 1
    RUNNING = 2
    FAILED = 3

class TaskStatus(Enum):
    CREATED = 0
    RUNNING = 1
    COMPLETED = 2
    FAILED = 3

class BasicWorker:
    def __init__(self, name: str, worker_type: WorkerType, support_vr: bool = False, master_url: str = "http://localhost:8000"):
        self.name = name
        self.worker_type = worker_type
        self.support_vr = support_vr
        self.master_url = master_url.rstrip("/")
        self.worker_id = None
        self.status = WorkerStatus.OFFLINE
        self.current_task = None
        self.heartbeat_thread = None
        self.running = False

    def register(self):
        """注册worker到master"""
        try:
            response = requests.post(
                f"{self.master_url}/api/v1/workers",
                json={
                    "worker_name": self.name,
                    "worker_type": self.worker_type.value,
                    "support_vr": 1 if self.support_vr else 0
                }
            )
            response.raise_for_status()
            data = response.json()
            if data["code"] == 200:
                self.worker_id = data["data"]["worker_id"]
                self.status = WorkerStatus.PENDING
                logging.info(f"Worker {self.name} registered successfully with ID {self.worker_id}")
                return True
            else:
                logging.error(f"Failed to register worker: {data['message']}")
                return False
        except Exception as e:
            logging.error(f"Error registering worker: {str(e)}")
            return False

    def start_heartbeat(self):
        """启动心跳线程"""
        def heartbeat_loop():
            while self.running:
                try:
                    response = requests.post(
                        f"{self.master_url}/api/v1/workers/heartbeat",
                        json={
                            "worker_name": self.name,
                            "worker_id": self.worker_id
                        }
                    )
                    response.raise_for_status()
                    logging.debug(f"Heartbeat sent for worker {self.name}")
                except Exception as e:
                    logging.error(f"Error sending heartbeat: {str(e)}")
                time.sleep(5)  # 每5秒发送一次心跳

        self.running = True
        self.heartbeat_thread = threading.Thread(target=heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

    def stop_heartbeat(self):
        """停止心跳线程"""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join()

    def get_new_task(self):
        """获取新任务"""
        try:
            response = requests.post(
                f"{self.master_url}/api/v1/tasks",
                json={
                    "worker_id": self.worker_id,
                    "worker_type": self.worker_type.value,
                    "support_vr": 1 if self.support_vr else 0
                }
            )
            response.raise_for_status()
            data = response.json()
            if data["code"] == 200:
                self.current_task = data["data"]
                self.status = WorkerStatus.RUNNING
                logging.info(f"Got new task: {self.current_task}")
                return self.current_task
            else:
                logging.info(f"No new task available: {data['message']}")
                return None
        except Exception as e:
            logging.error(f"Error getting new task: {str(e)}")
            return None

    def update_task_status(self, task_id: str, status: TaskStatus, progress: float = 0.0, 
                          error_message: str = None, elapsed_time: int = 0, remaining_time: int = 0):
        """更新任务状态"""
        try:
            data = {
                "worker_id": self.worker_id,
                "progress": progress,
                "status": status.value,
                "elapsed_time": elapsed_time,
                "remaining_time": remaining_time
            }
            if error_message:
                data["error_message"] = error_message

            response = requests.patch(
                f"{self.master_url}/api/v1/tasks/{task_id}",
                json=data
            )
            response.raise_for_status()
            data = response.json()
            if data["code"] == 200:
                logging.info(f"Task status updated: {task_id} - {status.name}")
                if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    self.status = WorkerStatus.PENDING
                    self.current_task = None
                return True
            else:
                logging.error(f"Failed to update task status: {data['message']}")
                return False
        except Exception as e:
            logging.error(f"Error updating task status: {str(e)}")
            return False

    def process_task(self, task):
        """处理任务的抽象方法，需要被子类实现"""
        raise NotImplementedError("Subclasses must implement process_task method")

    def run(self):
        """运行worker的主循环"""
        if not self.register():
            return False

        self.start_heartbeat()
        
        try:
            while True:
                if self.status == WorkerStatus.PENDING:
                    task = self.get_new_task()
                    if task:
                        self.process_task(task)
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Worker stopping...")
        finally:
            self.stop_heartbeat()

class TestWorker(BasicWorker):
    def process_task(self, task):
        """测试用的任务处理方法，只打印路径并返回失败状态"""
        task_id = task["task_id"]
        video_path = task["video_path"]
        
        logging.info(f"Processing task {task_id} with video: {video_path}")
        
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

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试worker实例
    worker = TestWorker(
        name="test_worker",
        worker_type=WorkerType.CPU,
        support_vr=True,
        master_url="http://localhost:8000"
    )
    
    # 运行worker
    worker.run() 