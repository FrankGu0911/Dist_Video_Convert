import os,sys
import logging
from datetime import datetime
import ffmpeg
import hashlib
from models import db, VideoInfo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video import Video

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/video_manager.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # 使用stdout，它支持UTF-8
    ]
)
logger = logging.getLogger(__name__)

class VideoManager:
    def __init__(self, scan_paths):
        self.scan_paths = scan_paths
        self.batch_size = 20  # 每100个文件提交一次
        if not os.path.exists('logs'):
            os.makedirs('logs')

    def get_relative_path(self, absolute_path):
        """获取相对于扫描路径的相对路径，统一使用Windows格式的路径分隔符"""
        for scan_path in self.scan_paths:
            if absolute_path.startswith(scan_path):
                # 获取相对路径并统一转换为Windows格式
                rel_path = os.path.relpath(absolute_path, scan_path)
                # 将路径分隔符统一为Windows格式
                rel_path = rel_path.replace('/', '\\')
                # 确保路径以\开头
                return '\\' + rel_path if not rel_path.startswith('\\') else rel_path
        return absolute_path

    def check_file_changes(self, video_file, existing_video):
        """检查文件是否被修改
        使用文件大小和修改时间来判断
        """
        try:
            file_stat = os.stat(video_file)
            file_size = file_stat.st_size / (1024 * 1024)  # 转换为MB
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            
            # 如果文件大小不同，肯定被修改了
            if abs(file_size - existing_video.video_size) > 0.1:  # 允许0.1MB的误差
                logger.info(f"文件大小已改变: {video_file}")
                return True
                
            # 如果文件修改时间晚于记录的文件修改时间
            if existing_video.file_mtime is None or file_mtime > existing_video.file_mtime:
                logger.info(f"文件已被修改: {video_file}")
                return True
                
            return False
        except Exception as e:
            logger.error(f"检查文件变化时出错: {str(e)}")
            return False

    def scan_videos(self):
        """扫描视频文件并更新video_info表"""
        try:
            logger.info("开始扫描视频...")
            
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
                        file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                        
                        # 检查文件是否已存在于数据库
                        relative_path = self.get_relative_path(video_file)
                        existing_video = VideoInfo.query.filter_by(video_path=relative_path).first()
                        
                        if existing_video:
                            # 标记文件为存在
                            existing_video.exist = True
                            
                            # 检查文件是否被修改
                            if self.check_file_changes(video_file, existing_video):
                                # 更新视频信息
                                video_obj = Video(video_file)
                                existing_video.codec = video_obj.video_codec
                                existing_video.bitrate_k = int(video_obj.video_bitrate / 1000)
                                existing_video.video_size = file_size
                                existing_video.fps = video_obj.video_fps
                                existing_video.resolutionx = video_obj.video_resolution[0]
                                existing_video.resolutiony = video_obj.video_resolution[1]
                                existing_video.resolutionall = video_obj.video_resolution[0] * video_obj.video_resolution[1]
                                existing_video.updatetime = datetime.utcnow()
                                existing_video.file_mtime = file_mtime
                                logger.info(f"更新视频信息: {relative_path}")
                            
                            processed_count += 1
                            continue

                        # 处理新文件
                        video_obj = Video(video_file)
                        
                        # 创建视频信息记录
                        video = VideoInfo(
                            video_path=relative_path,
                            identi=video_obj.identi,
                            codec=video_obj.video_codec,
                            bitrate_k=int(video_obj.video_bitrate / 1000),
                            video_size=file_size,
                            fps=video_obj.video_fps,
                            resolutionx=video_obj.video_resolution[0],
                            resolutiony=video_obj.video_resolution[1],
                            resolutionall=video_obj.video_resolution[0] * video_obj.video_resolution[1],
                            is_vr=1 if video_obj.is_vr else 0,
                            updatetime=datetime.utcnow(),
                            file_mtime=file_mtime,
                            transcode_status=0,  # 初始状态：未转码
                            exist=True
                        )

                        # 判断是否需要转码
                        if video.should_transcode():
                            video.transcode_status = 1  # 等待转码
                            logger.info(f"视频需要转码: {relative_path}")
                        else:
                            video.transcode_status = 0  # 不需要转码
                            logger.info(f"视频不需要转码: {relative_path}")

                        db.session.add(video)
                        processed_count += 1
                        
                        # 每处理batch_size个文件就提交一次
                        if processed_count % self.batch_size == 0:
                            logger.info(f"批量提交 {self.batch_size} 个文件的更改")
                            db.session.commit()
                        
                    except Exception as e:
                        logger.error(f"处理视频时出错 {video_file}: {str(e)}")
                        continue
            
            # 提交剩余的更改
            db.session.commit()
            
            # 统计结果
            deleted_count = VideoInfo.query.filter_by(exist=False).count()
            if deleted_count > 0:
                logger.warning(f"发现 {deleted_count} 个文件已被删除")
            
            logger.info("视频扫描完成")
                    
        except Exception as e:
            logger.error(f"扫描视频时出错: {str(e)}")
            db.session.rollback()