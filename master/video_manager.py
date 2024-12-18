import os
import logging
from datetime import datetime
import ffmpeg
import hashlib
from models import db, VideoInfo
from video import Video

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/video_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VideoManager:
    def __init__(self, scan_paths):
        self.scan_paths = scan_paths
        if not os.path.exists('logs'):
            os.makedirs('logs')

    def get_relative_path(self, absolute_path):
        """获取相对于扫描路径的相对路径"""
        for scan_path in self.scan_paths:
            if absolute_path.startswith(scan_path):
                return os.path.relpath(absolute_path, scan_path)
        return absolute_path

    def calculate_md5(self, file_path, block_size=8192):
        """计算文件的MD5值"""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                md5.update(data)
        return md5.hexdigest()

    def check_file_changes(self, video_file, existing_video):
        """检查文件是否被修改"""
        try:
            current_md5 = self.calculate_md5(video_file)
            if current_md5 != existing_video.md5:
                logger.info(f"文件已被修改: {video_file}")
                return True
            return False
        except Exception as e:
            logger.error(f"检查文件MD5时出错: {str(e)}")
            return False

    def scan_videos(self):
        """扫描视频文件并更新video_info表"""
        try:
            logger.info("开始扫描视频...")
            
            # 获取所有数据库中的视频记录
            all_videos = VideoInfo.query.all()
            for video in all_videos:
                video.exist = False  # 初始化所有记录为不存在
            
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
                                existing_video.video_size = video_obj.video_size / (1024 * 1024)
                                existing_video.fps = video_obj.video_fps
                                existing_video.resolutionx = video_obj.video_resolution[0]
                                existing_video.resolutiony = video_obj.video_resolution[1]
                                existing_video.resolutionall = video_obj.video_resolution[0] * video_obj.video_resolution[1]
                                existing_video.updatetime = datetime.utcnow()
                                existing_video.md5 = self.calculate_md5(video_file)
                                logger.info(f"更新视频信息: {relative_path}")
                            
                            continue

                        # 处理新文件
                        video_obj = Video(video_file)
                        
                        # 创建视频信息记录
                        video = VideoInfo(
                            video_path=relative_path,
                            identi=video_obj.identi,
                            codec=video_obj.video_codec,
                            bitrate_k=int(video_obj.video_bitrate / 1000),
                            video_size=video_obj.video_size / (1024 * 1024),  # 转换为MB
                            fps=video_obj.video_fps,
                            resolutionx=video_obj.video_resolution[0],
                            resolutiony=video_obj.video_resolution[1],
                            resolutionall=video_obj.video_resolution[0] * video_obj.video_resolution[1],
                            is_vr=1 if video_obj.is_vr else 0,
                            updatetime=datetime.utcnow(),
                            transcode_status=0,  # 初始状态：未转码
                            md5=self.calculate_md5(video_file),
                            exist=True
                        )
                        
                        db.session.add(video)
                        logger.info(f"添加新视频信息: {relative_path}")
                        
                    except Exception as e:
                        logger.error(f"处理视频时出错 {video_file}: {str(e)}")
                        continue
            
            # 提交所有更改
            db.session.commit()
            
            # 统计结果
            deleted_count = VideoInfo.query.filter_by(exist=False).count()
            if deleted_count > 0:
                logger.warning(f"发现 {deleted_count} 个文件已被删除")
            
            logger.info("视频扫描完成")
                    
        except Exception as e:
            logger.error(f"扫描视频时出错: {str(e)}")
            db.session.rollback() 