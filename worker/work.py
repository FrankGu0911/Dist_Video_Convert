import os
import logging
from typing import Optional
import argparse
import time
from datetime import datetime
from .base import BasicWorker, WorkerType, TaskStatus
from video import Video

class Worker(BasicWorker):
    def __init__(self, worker_name: str, worker_type: WorkerType, master_url: str, prefix_path: str, save_path: str, tmp_path: str = None, support_vr: bool = False, crf: int = None, preset: str = None, rate: int = None, numa_param: str = None, remove_original: bool = False, num: int = -1, start_time=None, end_time=None, hw_decode: bool = False):
        super().__init__(worker_name, worker_type, master_url, prefix_path, save_path, tmp_path, support_vr, crf, preset, rate, numa_param, None, remove_original, num, start_time, end_time, hw_decode)

    def process_task(self, task):
        """处理转码任务
        
        Args:
            task: 任务信息，包含以下字段：
                task_id: 任务ID
                video_path: 视频相对路径
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 验证任务数据
            required_fields = ['task_id', 'video_path']
            for field in required_fields:
                if field not in task:
                    raise ValueError(f"任务缺少必需字段: {field}")
                    
            logging.info(f"开始处理任务: {task}")
            
            # 获取完整的视频路径
            video_path = self._get_full_video_path(task["video_path"])
            logging.info(f"视频完整路径: {video_path}")
            
            # 创建临时目录
            # 如果是替换模式，使用源视频所在目录
            if self.save_path == "!replace":
                task_tmp_path = self._normalize_path(os.path.dirname(video_path))
                logging.info("替换模式：临时文件将保存在源视频所在目录")
            else:
                # 使用原始的tmp_path和视频的相对路径来构建临时目录
                video_rel_dir = os.path.dirname(task["video_path"])
                task_tmp_path = self._normalize_path(os.path.join(self.prefix_path, self.tmp_path, video_rel_dir))
                os.makedirs(task_tmp_path, exist_ok=True)
            logging.info(f"临时目录: {task_tmp_path}")
            
            # 创建日志目录
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            logging.info(f"日志目录: {log_dir}")
            
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
            
            # 处理任务
            success = self._process_transcode_task(video, task, start_time, task_tmp_path)
                
            return success
                
        except Exception as e:
            error_msg = f"处理任务失败: {str(e)}"
            logging.error(error_msg)
            logging.error(f"任务详情: {task}")
            elapsed_time = int(time.time() - start_time)
            self.update_task_status(
                task_id=task["task_id"],
                status=TaskStatus.FAILED,
                progress=0.0,
                error_message=error_msg,
                elapsed_time=elapsed_time,
                remaining_time=0
            )
            logging.warning("继续等待下一个任务...")
            return False

    def _process_transcode_task(self, video: Video, task: dict, start_time: float, task_tmp_path: str):
        """处理转码任务"""
        logging.info(f"开始转码任务: {'VR视频' if video.is_vr else '普通视频'}")
        
        def progress_callback(progress: float, elapsed_time: int, remaining_time: Optional[int]):
            # 使用实际经过的时间
            real_elapsed_time = int(time.time() - start_time)
            # 如果tqdm计算的剩余时间波动太大，使用基于进度的估算
            if progress > 0:
                estimated_total_time = real_elapsed_time / (progress / 100)
                estimated_remaining = max(0, int(estimated_total_time - real_elapsed_time))
                # 如果tqdm的估算相差太大（超过50%），使用我们的估算
                if remaining_time is None or abs(remaining_time - estimated_remaining) > estimated_remaining * 0.5:
                    remaining_time = estimated_remaining
            
            self.update_task_status(
                task_id=task["task_id"],
                status=TaskStatus.RUNNING,
                progress=progress,
                elapsed_time=real_elapsed_time,
                remaining_time=remaining_time if remaining_time is not None else 0
            )
        
        try:
            # 根据worker类型设置编码器和参数
            if self.worker_type == WorkerType.CPU:
                if video.is_vr and not self.support_vr:
                    raise ValueError("当前worker不支持VR视频处理")
                codec = 'libx265'
                rate_str = str(self.rate) if self.rate is not None else ""
                codec_params = {
                    'codec': codec,
                    'crf': self.crf,
                    'preset': self.preset,
                    'rate': rate_str,
                    'numa_param': self.numa_param,
                    'hw_decode': self.hw_decode
                }
            elif self.worker_type == WorkerType.NVENC:
                codec = 'hevc_nvenc'
                rate_value = self.rate if self.rate is not None else 30
                codec_params = {
                    'codec': codec,
                    'qmin': self.crf,
                    'preset': self.preset,
                    'rate': rate_value,
                    'hw_decode': self.hw_decode
                }
            elif self.worker_type == WorkerType.QSV:
                codec = 'hevc_qsv'
                rate_str = str(self.rate) if self.rate is not None else ""
                codec_params = {
                    'codec': codec,
                    'global_quality': self.crf,
                    'preset': self.preset,
                    'rate': rate_str,
                    'hw_decode': self.hw_decode
                }
            else:
                raise ValueError(f"不支持的worker类型: {self.worker_type}")
            
            # 设置输出路径
            output_path = os.path.join(
                task_tmp_path, 
                video.video_name if not os.path.dirname(video.video_path) == task_tmp_path 
                else video.video_name_noext + "_h265.mp4"
            )
            codec_params['output_path'] = self._normalize_path(output_path)
            
            # 获取ffmpeg命令
            cmd = video.build_ffmpeg_command(codec_params)
            
            # 记录转码命令到日志
            self.update_task_log(
                task_id=task["task_id"],
                log_level=1,  # info级别
                log_message=f"FFmpeg command: {cmd}"
            )
            
            # 执行转码
            video.convert_video_with_progress(cmd, progress_callback)

            # 转码完成后的处理
            self._handle_completion(video, task, start_time, task_tmp_path)
            return True
            
        except Exception as e:
            raise e

    def _handle_completion(self, video: Video, task: dict, start_time: float, task_tmp_path: str):
        """处理转码完成后的操作"""
        logging.info("开始处理转码完成后的操作")
        
        # 获取临时文件路径
        if os.path.dirname(video.video_path) == task_tmp_path:
            temp_output = self._normalize_path(os.path.join(task_tmp_path, video.video_name_noext + "_h265.mp4"))
        else:
            temp_output = self._normalize_path(os.path.join(task_tmp_path, video.video_name))
        logging.info(f"临时文件路径: {temp_output}")
        
        if self.save_path == "!replace":
            logging.info("使用替换模式")
            backup_path = self._normalize_path(video.video_path + ".bak")
            logging.info(f"备份原文件到: {backup_path}")
            os.rename(video.video_path, backup_path)
            logging.info(f"移动新文件到: {video.video_path}")
            os.rename(temp_output, video.video_path)
            if self.remove_original:
                logging.info("删除备份文件")
                os.remove(backup_path)
        else:
            logging.info("使用另存模式")
            rel_path = os.path.normpath(video.video_path[len(self.prefix_path):])
            if rel_path.startswith(os.path.sep):
                rel_path = rel_path[1:]
                
            save_dir = self._normalize_path(os.path.join(self.prefix_path, self.save_path, os.path.dirname(rel_path)))
            save_path = self._normalize_path(os.path.join(save_dir, video.video_name))
            
            logging.info(f"创建目标目录: {save_dir}")
            os.makedirs(save_dir, exist_ok=True)
            
            logging.info(f"移动新文件到: {save_path}")
            os.rename(temp_output, save_path)
            if self.remove_original:
                logging.info(f"删除原文件: {video.video_path}")
                os.remove(video.video_path)

        # 计算实际总耗时
        total_elapsed_time = int(time.time() - start_time)
        logging.info(f"任务总耗时: {total_elapsed_time}秒")
        
        # 更新任务状态为完成，使用实际耗时
        logging.info("更新任务状态为完成")
        self.update_task_status(
            task_id=task["task_id"],
            status=TaskStatus.COMPLETED,
            progress=100.0,
            elapsed_time=total_elapsed_time,
            remaining_time=0
        )

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

    # 创建参数��析器
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
    parser.add_argument('--hw-decode', action='store_true', help='是否启用硬件解码（仅NVENC和QSV模式有效）')
    parser.add_argument('--shutdown', action='store_true', help='任务完成后关机')

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
    if args.start or args.end:
        if not (args.start and args.end):
            parser.error("start和end参数必须同时提供")
        try:
            start_time = datetime.strptime(args.start, "%H:%M").time()
            end_time = datetime.strptime(args.end, "%H:%M").time()
            logging.info(f"工作时间设置为: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")
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
            end_time=end_time,
            hw_decode=args.hw_decode
        )

        # 运行worker
        success = worker.run()
        
        # 如果正常完成并设置了关机，执行关机
        if success and args.shutdown:
            logging.info("任务已完成，准备关机...")
            if os.name == 'nt':  # Windows
                os.system('shutdown /s /t 60')  # 60秒后关机
            else:  # Linux/Unix
                os.system('shutdown -h +1')  # 1分钟后关机
        
    except KeyboardInterrupt:
        logging.info("收到中断信号，worker正在停止...")
    except Exception as e:
        logging.error(f"Worker运行错误: {str(e)}")
        raise e 