import os
import logging
from typing import Optional
import argparse
from datetime import datetime, time
from .base import BasicWorker, WorkerType, TaskStatus
from video import Video

class Worker(BasicWorker):
    def process_task(self, task):
        """处理转码任务
        
        Args:
            task: 任务信息，包含以下字段：
                task_id: 任务ID
                video_path: 视频相对路径
        """
        try:
            # 验证任务数据
            required_fields = ['task_id', 'video_path']
            for field in required_fields:
                if field not in task:
                    raise ValueError(f"任务缺少必需字段: {field}")
                    
            logging.info(f"开始处理任务: {task}")
            
            # 获取完整的视频路径
            video_path = self._get_full_video_path(task["video_path"])
            logging.info(f"视频完整路径: {video_path}")
            
            # 创建必要的目录
            self.tmp_path = os.path.join(self.prefix_path,self.tmp_path,os.path.dirname(task["video_path"]))
            # self.tmp_path = os.path.join(os.path.dirname(video_path), "tmp")
            os.makedirs(self.tmp_path, exist_ok=True)
            logging.info(f"临时目录: {self.tmp_path}")
            
            # 创建日志目录
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            logging.info(f"日志目录: {log_dir}")
            # os.environ["FFMPEG_LOG_DIR"] = log_dir  # 设置环境变量供Video类使用
            
            # 创建Video对象
            video = Video(video_path)
            logging.info(f"视频信息: {str(video)}")
            logging.info(f"是否为VR视频: {video.is_vr}")
            
            # 更新任务状态为运行中
            self.update_task_status(
                task_id=task["task_id"],
                status=TaskStatus.RUNNING,
                progress=0.0,
                elapsed_time=0,
                remaining_time=0
            )
            logging.info("任务状态已更新为运行中")
            
            # 根据worker类型选择不同的转码方法
            logging.info(f"使用 {self.worker_type.name} 模式进行转码")
            if self.worker_type == WorkerType.CPU:
                self._process_cpu_task(video, task)
            elif self.worker_type == WorkerType.NVENC:
                self._process_nvenc_task(video, task)
            elif self.worker_type == WorkerType.QSV:
                self._process_qsv_task(video, task)
            else:
                raise ValueError(f"不支持的worker类型: {self.worker_type}")
                
        except Exception as e:
            error_msg = f"处理任务失败: {str(e)}"
            logging.error(error_msg)
            logging.error(f"任务详情: {task}")
            self.update_task_status(
                task_id=task["task_id"],
                status=TaskStatus.FAILED,
                progress=0.0,
                error_message=error_msg,
                elapsed_time=0,
                remaining_time=0
            )
            raise e

    def _process_cpu_task(self, video: Video, task: dict):
        """处理CPU转码任务"""
        logging.info(f"开始CPU转码任务: {'VR视频' if video.is_vr else '普通视频'}")
        
        def progress_callback(progress: float, elapsed_time: int, remaining_time: Optional[int]):
            self.update_task_status(
                task_id=task["task_id"],
                status=TaskStatus.RUNNING,
                progress=progress,
                elapsed_time=elapsed_time,
                remaining_time=remaining_time if remaining_time is not None else 0
            )
            # if int(progress) % 10 == 0:  # 每进度10%输出一次日志
            #     logging.info(f"转码进度: {progress:.1f}%, 已用时间: {elapsed_time}秒, 预计剩余时间: {remaining_time if remaining_time is not None else '未知'}秒")
        
        # 处理rate参数
        rate_str = str(self.rate) if self.rate is not None else ""
        
        # 如果是VR视频，使用VR专用的参数
        if video.is_vr:
            if not self.support_vr:
                raise ValueError("当前worker不支持VR视频处理")
            logging.info("使用VR视频转码参数")
            # VR视频使用较高质量的参数
            video.convert_to_h265(
                crf=self.crf,  # VR默认20
                preset=self.preset,  # VR默认slow
                rate="",  # VR不支持指定帧率
                output_folder=self.tmp_path,
                remove_original=False,  # 先不删除原文件
                numa_param=self.numa_param,
                progress_callback=progress_callback
            )
        else:
            logging.info("使用普通视频转码参数")
            logging.info(f"转码参数: crf={self.crf}, preset={self.preset}, rate={rate_str}")
            # 普通视频使用标准参数
            video.convert_to_h265(
                crf=self.crf,  # 默认22
                preset=self.preset,  # 默认medium
                rate=rate_str,
                output_folder=self.tmp_path,
                remove_original=False,
                numa_param=self.numa_param,
                progress_callback=progress_callback
            )

        # 转码完成后的处理
        self._handle_completion(video, task)

    def _process_nvenc_task(self, video: Video, task: dict):
        """处理NVENC转码任务"""
        logging.info("开始NVENC转码任务")
        
        def progress_callback(progress: float, elapsed_time: int, remaining_time: Optional[int]):
            self.update_task_status(
                task_id=task["task_id"],
                status=TaskStatus.RUNNING,
                progress=progress,
                elapsed_time=elapsed_time,
                remaining_time=remaining_time if remaining_time is not None else 0
            )
            # if int(progress) % 10 == 0:  # 每进度10%输出一次日志
            #     logging.info(f"转码进度: {progress:.1f}%, 已用时间: {elapsed_time}秒, 预计剩余时间: {remaining_time if remaining_time is not None else '未知'}秒")

        # 处理rate参数
        rate_value = self.rate if self.rate is not None else 30  # NVENC默认使用30fps
        logging.info(f"转码参数: qmin={self.crf}, preset={self.preset}, rate={rate_value}")

        video.convert_to_hevc_nvenc(
            qmin=self.crf,  # 默认23
            preset=self.preset,  # 默认p5
            rate=rate_value,
            output_folder=self.tmp_path,
            remove_original=False,
            progress_callback=progress_callback
        )

        # 转码完成后的处理
        self._handle_completion(video, task)

    def _process_qsv_task(self, video: Video, task: dict):
        """处理QSV转码任务"""
        logging.info("开始QSV转码任务")
        
        def progress_callback(progress: float, elapsed_time: int, remaining_time: Optional[int]):
            self.update_task_status(
                task_id=task["task_id"],
                status=TaskStatus.RUNNING,
                progress=progress,
                elapsed_time=elapsed_time,
                remaining_time=remaining_time if remaining_time is not None else 0
            )
            # if int(progress) % 10 == 0:  # 每进度10%输出一次日志
            #     logging.info(f"转码进度: {progress:.1f}%, 已用时间: {elapsed_time}秒, 预计剩余时间: {remaining_time if remaining_time is not None else '未知'}秒")

        # 处理rate参数
        rate_str = str(self.rate) if self.rate is not None else ""
        logging.info(f"转码参数: global_quality={self.crf}, preset={self.preset}, rate={rate_str}")

        video.convert_to_hevc_qsv(
            global_quality=self.crf,  # 默认23
            preset=self.preset,  # 默认medium
            rate=rate_str,
            output_folder=self.tmp_path,
            remove_original=False,
            progress_callback=progress_callback
        )

        # 转码完成后的处理
        self._handle_completion(video, task)

    def _handle_completion(self, video: Video, task: dict):
        """处理转码完成后的操作"""
        logging.info("开始处理转码完成后的操作")
        
        # 获取临时文件路径
        temp_output = os.path.join(self.tmp_path, video.video_name_noext + "_h265.mp4")
        logging.info(f"临时文件路径: {temp_output}")
        
        if self.save_path == "!replace":
            logging.info("使用替换模式")
            # 替换模式：备份原文件，将新文件移动到原位置
            backup_path = video.video_path + ".bak"
            logging.info(f"备份原文件到: {backup_path}")
            os.rename(video.video_path, backup_path)
            logging.info(f"移动新文件到: {video.video_path}")
            os.rename(temp_output, video.video_path)
            if self.remove_original:
                logging.info("删除备份文件")
                os.remove(backup_path)
        else:
            logging.info("使用另存模式")
            # 另存模式：创建目标目录并移动文件
            save_path = os.path.join(self.prefix_path, self.save_path, os.path.dirname(task["video_path"]), video.video_name)
            os.makedirs(save_path, exist_ok=True)
            logging.info(f"移动新文件到: {save_path}")
            os.rename(temp_output, save_path)
            if self.remove_original:
                logging.info(f"删除原文件: {video.video_path}")
                os.remove(video.video_path)

        # 更新任务状态为完成
        logging.info("更新任务状态为完成")
        # self.update_task_status(
        #     task_id=task["task_id"],
        #     status=TaskStatus.COMPLETED,
        #     progress=100.0,
        #     elapsed_time=0,
        #     remaining_time=0
        # )

if __name__ == "__main__":
    # 设置日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('worker.log', encoding='utf-8')
        ]
    )

    # 创建参数解析器
    parser = argparse.ArgumentParser(description='视频转码Worker')
    
    # 必需参数
    parser.add_argument('--name', required=True, help='worker名称')
    parser.add_argument('--type', required=True, choices=['cpu', 'nvenc', 'qsv'], help='worker类型')
    parser.add_argument('--master', required=True, help='master服务器地址')
    parser.add_argument('--prefix', required=True, help='视频源文件路径前缀')
    parser.add_argument('--save', required=True, help='视频保存路径，使用!replace表示替换原文件')
    
    # 可选参数
    parser.add_argument('--tmp', help='临时文件路径，默认为save_path下的tmp目录')
    parser.add_argument('--vr', action='store_true', help='是否支持VR视频转码（仅CPU模式有效）')
    parser.add_argument('--crf', type=int, help='视频质量(0-51)')
    parser.add_argument('--preset', help='转码预设')
    parser.add_argument('--rate', type=int, choices=[30, 60], help='输出帧率')
    parser.add_argument('--numa', help='NUMA参数，例如"-,-,+,-"')
    parser.add_argument('--remove', action='store_true', help='是否删除原始文件')
    parser.add_argument('--num', type=int, default=-1, help='转码数量限制，默认-1表示不限制')
    parser.add_argument('--start', help='工作开始时间，格式HH:MM，例如22:00')
    parser.add_argument('--end', help='工作结束时间，格式HH:MM，例如06:00')

    # 解析参数
    args = parser.parse_args()

    # 转换worker类型
    worker_type_map = {
        'cpu': WorkerType.CPU,
        'nvenc': WorkerType.NVENC,
        'qsv': WorkerType.QSV
    }
    worker_type = worker_type_map[args.type.lower()]

    # 转换时间格式
    start_time = None
    end_time = None
    if args.start and args.end:
        try:
            start_time = datetime.strptime(args.start, "%H:%M").time()
            end_time = datetime.strptime(args.end, "%H:%M").time()
        except ValueError as e:
            parser.error(f"时间格式错误: {str(e)}")

    # 创建worker
    try:
        worker = Worker(
            worker_name=args.name,
            worker_type=worker_type,
            master_url=args.master,
            prefix_path=args.prefix,
            save_path=args.save,
            tmp_path=args.tmp,
            support_vr=args.vr,
            crf=args.crf,
            preset=args.preset,
            rate=args.rate,
            numa_param=args.numa,
            remove_original=args.remove,
            num=args.num,
            start_time=start_time,
            end_time=end_time
        )

        # 运行worker
        worker.run()
        
    except KeyboardInterrupt:
        logging.info("收到中断信号，worker正在停止...")
    except Exception as e:
        logging.error(f"Worker运行错误: {str(e)}")
        raise e 