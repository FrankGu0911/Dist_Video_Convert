import requests
import time
import threading
import logging
from enum import Enum
from typing import Optional

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
    def __init__(self, 
                 worker_name: str,
                 worker_type: WorkerType,
                 master_url: str,
                 prefix_path: str,
                 save_path: str,
                 support_vr: bool = False,
                 crf: Optional[int] = None,
                 preset: Optional[str] = None,
                 rate: Optional[int] = None,
                 numa_param: Optional[str] = None,
                 remove_original: bool = False,
                 num: int = -1):
        """初始化worker
        Args:
            worker_name: worker名称
            worker_type: worker类型 (0:cpu, 1:nvenc, 2:qsv, 3:vpu)
            master_url: master地址
            prefix_path: 视频前缀路径
            save_path: 视频保存路径 (!replace表示替换原视频)
            support_vr: 是否支持VR (cpu可支持，其他类型worker即使为True，也会被忽略)
            crf: 视频质量 (0-51)
                cpu+vr默认20, cpu+no-vr默认22
                qsv+no-vr默认23, nvenc+no-vr默认23
            preset: 视频质量预设
                cpu+vr默认slow, cpu+no-vr默认medium
                qsv+no-vr默认slow, nvenc+no-vr默认slow
            rate: 视频帧率 (可选30,60，默认不改变)
            numa_param: numa参数 (只在cpu时有效，如4numa时使用node2: "-,-,+,-")
            remove_original: 是否删除原视频
            num: 转码次数限制 (-1表示不限制)
        """
        self.name = worker_name
        self.worker_type = worker_type
        self.master_url = master_url.rstrip("/")
        self.prefix_path = prefix_path
        self.save_path = save_path
        self.support_vr = support_vr
        
        # 设置默认参数
        self.crf = self._get_default_crf() if crf is None else crf
        self.preset = self._get_default_preset() if preset is None else preset
        self.rate = rate
        self.numa_param = numa_param if worker_type == WorkerType.CPU else None
        self.remove_original = remove_original
        self.num = num
        self.completed_num = 0

        # 运行时状态
        self.worker_id = None
        self.status = WorkerStatus.OFFLINE
        self.current_task = None
        self.heartbeat_thread = None
        self.running = False

    def _get_default_crf(self) -> int:
        """获取默认的crf值"""
        if self.worker_type == WorkerType.CPU:
            return 20 if self.support_vr else 22
        elif self.worker_type in [WorkerType.QSV, WorkerType.NVENC]:
            return 23
        return 22  # 默认值

    def _get_default_preset(self) -> str:
        """获取默认的preset值"""
        if self.worker_type == WorkerType.CPU:
            return "slow" if self.support_vr else "medium"
        elif self.worker_type in [WorkerType.QSV, WorkerType.NVENC]:
            return "slow"
        return "medium"  # 默认值

    def register(self):
        """注册worker到master"""
        try:
            request_data = {
                "worker_name": self.name,
                "worker_type": self.worker_type.value,
                "support_vr": 1 if self.support_vr else 0
            }
            logging.info(f"正在注册worker: {request_data} (本地转码限制: {self.num if self.num != -1 else '无限制'})")
            
            response = requests.post(
                f"{self.master_url}/api/v1/workers",
                json=request_data
            )
            response.raise_for_status()
            data = response.json()
            if data["code"] in [200, 201]:  # 同时接受200和201状态码
                self.worker_id = data["data"]["worker_id"]
                self.status = WorkerStatus.PENDING
                logging.info(f"Worker {self.name} registered successfully with ID {self.worker_id}")
                return True
            else:
                logging.error(f"注册失败: 服务器返回错误 - code: {data.get('code')}, message: {data.get('message')}")
                return False
        except requests.exceptions.RequestException as e:
            logging.error(f"注册失败: 网络错误 - {str(e)}")
            if hasattr(e.response, 'text'):
                logging.error(f"服务器响应: {e.response.text}")
            return False
        except Exception as e:
            logging.error(f"注册失败: 未知错误 - {str(e)}")
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
            request_data = {
                "worker_id": self.worker_id,
                "worker_type": self.worker_type.value,
                "support_vr": 1 if self.support_vr else 0,
                "dest_path": self.save_path
            }
            logging.debug(f"正在请求新任务: {request_data}")
            
            response = requests.post(
                f"{self.master_url}/api/v1/tasks",
                json=request_data
            )
            response.raise_for_status()
            data = response.json()
            if data["code"] in [200, 201]:  # 同时接受200和201状态码
                self.current_task = data["data"]
                self.status = WorkerStatus.RUNNING
                logging.info(f"获取到新任务: {self.current_task}")
                return self.current_task
            else:
                if data["code"] == 404:
                    logging.info("当前没有可处理的任务")
                else:
                    logging.error(f"获取任务失败: 服务器返回错误 - code: {data.get('code')}, message: {data.get('message')}")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"获取任务失败: 网络错误 - {str(e)}")
            if hasattr(e.response, 'text'):
                logging.error(f"服务器响应: {e.response.text}")
            return None
        except Exception as e:
            logging.error(f"获取任务失败: 未知错误 - {str(e)}")
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
                logging.info(f"任务状态已更新: {task_id} - {status.name}")
                if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    self.status = WorkerStatus.PENDING
                    self.current_task = None
                    # 无论成功还是失败都计入完成次数
                    self.completed_num += 1
                    logging.info(f"已完成 {self.completed_num}/{self.num if self.num != -1 else '∞'} 个转码任务")
                return True
            else:
                logging.error(f"更新任务状态失败: 服务器返回错误 - code: {data.get('code')}, message: {data.get('message')}")
                return False
        except requests.exceptions.RequestException as e:
            logging.error(f"更新任务状态失败: 网络错误 - {str(e)}")
            if hasattr(e.response, 'text'):
                logging.error(f"服务器响应: {e.response.text}")
            return False
        except Exception as e:
            logging.error(f"更新任务状态失败: 未知错误 - {str(e)}")
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
                if self.num != -1 and self.completed_num >= self.num:
                    logging.info(f"已完成指定的{self.num}次转码任务，worker退出")
                    self.stop_heartbeat()
                    return True

                if self.status == WorkerStatus.PENDING:
                    task = self.get_new_task()
                    if task:
                        self.process_task(task)
                    elif self.num != -1:  # 如果有转码次数限制，且没有新任务，等待一段时间后重试
                        logging.info(f"没有新任务，已完成 {self.completed_num}/{self.num} 个转码任务")
                        time.sleep(5)
                    else:  # 如果没有转码次数限制，继续等待新任务
                        time.sleep(1)
                else:
                    time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Worker stopping...")
        finally:
            self.stop_heartbeat()