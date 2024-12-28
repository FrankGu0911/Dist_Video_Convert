import requests
import time
import threading
import logging
from enum import Enum
from typing import Optional
import os
from datetime import datetime
from datetime import time as Time

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
                 tmp_path: str = None,
                 support_vr: bool = False,
                 crf: Optional[int] = None,
                 preset: Optional[str] = None,
                 rate: Optional[int] = None,
                 numa_param: Optional[str] = None,
                 thread: Optional[int] = None,
                 remove_original: bool = False,
                 num: int = -1,
                 start_time: Optional[Time] = None,
                 end_time: Optional[Time] = None,
                 hw_decode: bool = False,
                 ffmpeg_path: Optional[str] = None):
        """初始化worker
        Args:
            worker_name: worker名称
            worker_type: worker类型 (0:cpu, 1:nvenc, 2:qsv, 3:vpu)
            master_url: master地址
            prefix_path: 视频前缀路径
            save_path: 视频保存路径 (!replace表示替换原视频)
            tmp_path: 临时文件路径，默认在替换模式下与源视频同目录，另存模式下在save_path下的tmp目录
            support_vr: 是否支持VR (cpu可支持，其他类型worker即使为True，也会被忽略)
            crf: 视频质量 (0-51)
                cpu+vr默认20, cpu+no-vr默认22
                qsv+no-vr默认23, nvenc+no-vr默认23
            preset: 视频质量预设
                cpu+vr默认slow, cpu+no-vr默认medium
                qsv+no-vr默认slow, nvenc+no-vr默认slow
            rate: 视频帧率 (可选30,60，默认不改变，VR视频时强制为None)
            numa_param: numa参数 (只在cpu时有效，如4numa时使用node2: "-,-,+,-")
            thread: 线程数 (只在cpu时有效，默认None表示不指定，由ffmpeg自行决定)
            remove_original: 是否删除原视频
            num: 转码次数限制 (-1表示不限制)
            start_time: 工作开始时间
            end_time: 工作结束时间
            hw_decode: 是否启用硬件解码 (对于CPU编码器会被忽略)
            ffmpeg_path: ffmpeg可执行文件路径 (如果不指定则直接使用ffmpeg命令)
        """
        self.name = worker_name
        self.worker_type = worker_type
        self.master_url = master_url.rstrip("/")
        # 规范化路径
        self.prefix_path = self._normalize_path(prefix_path)
        self.save_path = save_path  # !replace 不需要处理
        
        # 设置临时目录
        if tmp_path:
            self.tmp_path = self._normalize_path(tmp_path)
        else:
            if save_path == "!replace":
                self.tmp_path = ""  # 替换模式下先不设置tmp_path，等处理任务时再设置
            else:
                self.tmp_path = self._normalize_path(os.path.join(save_path, "tmp"))
        
        # 如果不是CPU类型但设置了support_vr=True，发出警告并强制设为False
        if worker_type != WorkerType.CPU and support_vr:
            logging.warning(f"Worker类型为{worker_type.name}，不支持VR视频处理，已忽略support_vr=True设置")
            self.support_vr = False
        else:
            self.support_vr = support_vr
        
        # 设置默认参数
        self.crf = self._get_default_crf() if crf is None else crf
        self.preset = self._get_default_preset() if preset is None else preset
        
        # 如果支持VR，强制rate为None并发出警告
        if self.support_vr and rate is not None:
            logging.warning("VR视频处理模式下不支持指定帧率，已忽略rate设置")
            self.rate = None
        else:
            self.rate = rate
        
        self.numa_param = numa_param if worker_type == WorkerType.CPU else None
        
        # 设置线程数
        if worker_type == WorkerType.CPU:
            self.thread = thread
        else:
            if thread is not None:
                logging.warning(f"Worker类型为{worker_type.name}，不支持设置线程数，已忽略thread设置")
            self.thread = None
        
        self.remove_original = remove_original
        self.num = num
        self.completed_num = 0
        self.start_time = start_time
        self.end_time = end_time

        # 运行时状态
        self.worker_id = None
        self.status = WorkerStatus.OFFLINE
        self.current_task = None
        self.heartbeat_thread = None
        self.running = False
        
        # 硬件解码设置
        if worker_type == WorkerType.CPU and hw_decode:
            logging.warning("CPU编码模式下不支持硬件解码，已忽略hw_decode=True设置")
            self.hw_decode = False
        else:
            self.hw_decode = hw_decode
            
        # ffmpeg路径设置
        self.ffmpeg_path = self._normalize_path(ffmpeg_path) if ffmpeg_path else "ffmpeg"

        # 设置当前进程为较高优先级，确保网络请求等关键操作不受影响
        self._set_process_priority()

        # 连续失败次数计数
        self.consecutive_failures = 0

    def _set_process_priority(self):
        """设置进程优先级
        
        将当前进程（worker进程）设置为较高优先级
        这样即使在转码时CPU负载很高，也能确保网络请求等关键操作正常执行
        """
        try:
            import psutil
            import os
            
            # 获取当前进程
            process = psutil.Process(os.getpid())
            
            if os.name == 'nt':  # Windows系统
                # Windows下设置为HIGH_PRIORITY_CLASS
                import win32api
                import win32process
                import win32con
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, os.getpid())
                win32process.SetPriorityClass(handle, win32process.HIGH_PRIORITY_CLASS)
                logging.info("已将worker进程优先级设置为HIGH_PRIORITY_CLASS")
            else:  # Linux/Unix系统
                # Linux下设置nice值为-10（范围-20到19，默认0，越小优先级越高）
                process.nice(-10)
                logging.info("已将worker进程nice值设置为-10")
        except Exception as e:
            logging.warning(f"设置进程优先级失败: {str(e)}")

    def _set_ffmpeg_priority(self, process):
        """设置ffmpeg进程的优先级
        
        将ffmpeg进程设置为较低优先级，避免影响worker进程的网络请求等操作
        
        Args:
            process: ffmpeg进程对象
        """
        try:
            if os.name == 'nt':  # Windows系统
                import win32api
                import win32process
                import win32con
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, process.pid)
                win32process.SetPriorityClass(handle, win32process.BELOW_NORMAL_PRIORITY_CLASS)
                logging.info("已将ffmpeg进程优先级设置为BELOW_NORMAL_PRIORITY_CLASS")
            else:  # Linux/Unix系统
                # 设置nice值为10，优先级较低
                psutil.Process(process.pid).nice(10)
                logging.info("已将ffmpeg进程nice值设置为10")
        except Exception as e:
            logging.warning(f"设置ffmpeg进程优先级失败: {str(e)}")

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

    def _get_default_thread(self) -> int:
        """获取默认的线程数
        
        如果使用了numa，则返回对应node的cpu数-1
        否则返回系统总cpu数-1
        """
        import psutil
        import re
        
        if self.numa_param:
            # 解析numa参数，找到启用的node
            nodes = self.numa_param.split(',')
            enabled_nodes = [i for i, node in enumerate(nodes) if node.strip() == '+']
            if not enabled_nodes:
                logging.warning("未找到启用的NUMA节点，使用系统总CPU数-1")
                return psutil.cpu_count() - 1
                
            try:
                import subprocess
                # 获取指定node的CPU数量
                result = subprocess.run(['lscpu', '-p=cpu,node'], capture_output=True, text=True)
                if result.returncode != 0:
                    logging.warning("获取NUMA信息失败，使用系统总CPU数-1")
                    return psutil.cpu_count() - 1
                    
                # 解析lscpu输出，统计指定node的CPU数量
                cpu_count = 0
                for line in result.stdout.splitlines():
                    if line.startswith('#'):
                        continue
                    cpu, node = map(int, line.split(','))
                    if node in enabled_nodes:
                        cpu_count += 1
                        
                return max(1, cpu_count - 1)  # 至少返回1
            except Exception as e:
                logging.warning(f"获取NUMA CPU数量失败: {str(e)}，使用系统总CPU数-1")
                return psutil.cpu_count() - 1
        else:
            # 如果没有指定numa，使用系统总CPU数-1
            return psutil.cpu_count() - 1

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
                logging.debug(f"任务状态已更新: {task_id} - {status.name}")
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

                # 检查连续失败次数
                if self.consecutive_failures >= 3:
                    logging.error("连续失败3次，worker强制退出")
                    self.stop_heartbeat()
                    return False

                try:
                    # 检查是否在工作时间范围内
                    if not self._check_time():
                        time.sleep(60)  # 不在工作时间时，每分钟检查一次
                        continue
                except RuntimeError as e:
                    # 如果已经超过结束时间，记录日志并退出
                    logging.info(str(e))
                    logging.info("已超过工作时间，worker退出")
                    self.stop_heartbeat()
                    return True

                if self.status == WorkerStatus.PENDING:
                    task = self.get_new_task()
                    if task:
                        try:
                            success = self.process_task(task)
                            if success:
                                self.consecutive_failures = 0  # 成功时重置失败计数
                            else:
                                self.consecutive_failures += 1  # 失败时增加计数
                                logging.warning(f"任务失败，当前连续失败次数: {self.consecutive_failures}")
                        except FileNotFoundError as e:
                            logging.error(str(e))
                            self.update_task_status(
                                task_id=task["task_id"],
                                status=TaskStatus.FAILED,
                                progress=0.0,
                                error_message=str(e),
                                elapsed_time=0,
                                remaining_time=0
                            )
                            self.consecutive_failures += 1
                            logging.warning(f"文件访问错误，当前连续失败次数: {self.consecutive_failures}")
                            if self.consecutive_failures >= 3:
                                logging.error("由于连续失败3次，worker停止运行")
                                self.stop_heartbeat()
                                return False
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

    def _normalize_path(self, path: str) -> str:
        """根据操作系统规范化路径
        
        Args:
            path: 原始路径
            
        Returns:
            str: 规范化后的路径
        """
        if os.name == 'nt':
            # Windows系统下的处理
            # 检查是否是UNC路径（以//或\\开头）
            if path.startswith('//') or path.startswith('\\\\'):
                # 确保UNC路径以\\开头
                normalized = '\\\\' + path.lstrip('/\\')
            else:
                # 普通路径使用os.path.normpath处理
                normalized = os.path.normpath(path)
            # Windows下统一使用反斜杠
            return normalized.replace('/', '\\')
        else:
            # Linux/Unix系统下的处理
            normalized = os.path.normpath(path)
            # Linux下统一使用正斜杠
            return normalized.replace('\\', '/')

    def _get_full_video_path(self, video_path: str) -> str:
        """获取完整的视频文件路径
        
        Args:
            video_path: 相对视频路径
            
        Returns:
            str: 完整的视频文件路径
            
        Raises:
            FileNotFoundError: 如果文件不存在
        """
        full_path = self._normalize_path(os.path.join(self.prefix_path, video_path))
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"视频文件不存在: {full_path}")
        return full_path

    def _check_time(self) -> bool:
        """检查当前时间是否在工作时间范围内
        
        Returns:
            bool: 如果在工作时间内返回True
                 如果不在工作时间内但还未到开始时间返回False
                 如果已经超过结束时间则抛出RuntimeError
        
        Raises:
            RuntimeError: 当当前时间已超过结束时间时抛出
        """
        if not self.start_time or not self.end_time:
            return True

        current_time = datetime.now().time()
        
        # 特殊处理结束时间为00:00的情况
        if self.end_time.hour == 0 and self.end_time.minute == 0:
            # 将结束时间视为23:59:59
            end_time = Time(23, 59, 59)
        else:
            end_time = self.end_time
            
        # 处理跨天的情况 (如22:00-06:00)
        if self.start_time > end_time:
            # 如果当前时间大于等于开始时间或小于等于结束时间，则在工作时间内
            in_work_time = current_time >= self.start_time or current_time <= self.end_time
            # 如果不在工作时间内，检查是否已过结束时间
            if not in_work_time:
                if current_time > self.end_time and current_time < self.start_time:
                    logging.info(f"当前时间 {current_time.strftime('%H:%M')} 不在工作时间范围内 ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})")
                    logging.info("等待工作时间开始...")
                else:
                    raise RuntimeError(f"当前时间 {current_time.strftime('%H:%M')} 已超过工作时间 ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})")
        else:
            # 如果当前时间在开始时间和结束时间之间，则在工作时间内
            if self.end_time.hour == 0 and self.end_time.minute == 0:
                # 对于结束时间是00:00的情况，特殊处理
                in_work_time = current_time >= self.start_time
            else:
                in_work_time = self.start_time <= current_time <= end_time
                
            # 如果不在工作时间内，检查是否已过结束时间
            if not in_work_time:
                if current_time < self.start_time:
                    logging.info(f"当前时间 {current_time.strftime('%H:%M')} 不在工作时间范围内 ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})")
                    logging.info("等待工作时间开始...")
                else:
                    raise RuntimeError(f"当前时间 {current_time.strftime('%H:%M')} 已超过工作时间 ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})")
        
        return in_work_time

    def update_task_log(self, task_id: str, log_level: int, log_message: str):
        """更新任务日志
        
        Args:
            task_id: 任务ID
            log_level: 日志级别 (0:debug, 1:info, 2:warning, 3:error)
            log_message: 日志内容
        """
        try:
            response = requests.post(
                f"{self.master_url}/api/v1/logs",
                json={
                    "task_id": task_id,
                    "log_level": log_level,
                    "log_message": log_message
                }
            )
            response.raise_for_status()
            data = response.json()
            if data["code"] == 201:
                logging.debug(f"日志已更新: {log_message}")
                return True
            else:
                logging.error(f"更新日志失败: 服务器返回错误 - code: {data.get('code')}, message: {data.get('message')}")
                return False
        except requests.exceptions.RequestException as e:
            logging.error(f"更新日志失败: 网络错误 - {str(e)}")
            if hasattr(e.response, 'text'):
                logging.error(f"服务器响应: {e.response.text}")
            return False
        except Exception as e:
            logging.error(f"更新日志失败: 未知错误 - {str(e)}")
            return False