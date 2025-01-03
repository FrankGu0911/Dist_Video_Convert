from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class VideoInfo(db.Model):
    __tablename__ = 'video_info'
    
    id = db.Column(db.Integer, primary_key=True)
    video_path = db.Column(db.String(255), nullable=False)
    identi = db.Column(db.String(255))
    codec = db.Column(db.String(255))
    bitrate_k = db.Column(db.Integer)
    video_size = db.Column(db.Float)  # 文件大小（MB）
    fps = db.Column(db.Float)
    resolutionx = db.Column(db.Integer)
    resolutiony = db.Column(db.Integer)
    resolutionall = db.Column(db.Integer)
    is_vr = db.Column(db.Integer, default=0)
    updatetime = db.Column(db.DateTime, default=datetime.utcnow)  # 记录更新时间
    file_mtime = db.Column(db.DateTime)  # 文件修改时间
    transcode_status = db.Column(db.Integer, default=0)  # 0:not_transcode, 1:wait_transcode, 2:created, 3:running, 4:completed, 5:failed
    transcode_task_id = db.Column(db.Integer)
    exist = db.Column(db.Boolean, default=True)  # 文件是否存在

    def should_transcode(self) -> bool:
        """
        判断视频是否需要转码
        返回:
            bool: True表示需要转码，False表示不需要转码
        """
        # 如果是hevc或av1编码
        if self.codec in ['hevc', 'av1']:
            # 根据分辨率和帧率判断码率限制
            # 根据总像素数和帧率计算目标码率
            # 基准: 1080p@30fps约需3500kbps
            # 计算公式: br_limit = (像素数比例 * 帧率比例 * 基准码率 * 0.8)
            # 0.8是HEVC相对于H264的压缩效率提升
            base_pixels = 1920 * 1080
            base_fps = 30
            base_bitrate = 3500

            if self.is_vr:
                return False
            
            # 计算像素数和帧率的比例
            pixels_ratio = self.resolutionall / base_pixels
            fps_ratio = self.fps / base_fps
            
            # 计算目标码率
            br_limit = int(pixels_ratio * fps_ratio * base_bitrate)
            
            # 设置一些合理的上下限
            br_limit = max(2000, min(br_limit, 25000))

            # 如果码率低于限制，不需要转码
            return self.bitrate_k >= br_limit

        # 如果是h264编码，需要转码
        if self.codec == 'h264':
            return True

        # 其他编码不需要转码
        return False

class TranscodeTask(db.Model):
    __tablename__ = 'transcode_task'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(255), unique=True, nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('transcode_worker.id'))
    worker_name = db.Column(db.String(255))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    task_status = db.Column(db.Integer, default=0)  # 0:created, 1:running, 2:completed, 3:failed
    progress = db.Column(db.Float, default=0.0)
    video_id = db.Column(db.Integer, db.ForeignKey('video_info.id'))
    dest_path = db.Column(db.String(255), nullable=True)  # 允许为空，由客户端决定
    video_path = db.Column(db.String(255))
    error_message = db.Column(db.String(1023), nullable=True)  # 错误信息字段
    elapsed_time = db.Column(db.Integer, default=0)  # 已用时间（秒）
    remaining_time = db.Column(db.Integer, nullable=True)  # 预计剩余时间（秒）
    last_update_time = db.Column(db.DateTime, nullable=True)  # 最后更新时间

class TranscodeWorker(db.Model):
    __tablename__ = 'transcode_worker'
    
    id = db.Column(db.Integer, primary_key=True)
    worker_name = db.Column(db.String(255), unique=True, nullable=False)
    worker_status = db.Column(db.Integer, default=0)  # 0:offline, 1:pending, 2:running, 3:failed
    worker_type = db.Column(db.Integer)  # 0:cpu, 1:nvenc, 2:qsv, 3:vpu
    support_vr = db.Column(db.Integer, default=0)
    last_heartbeat = db.Column(db.DateTime)
    current_task_id = db.Column(db.Integer)

class TranscodeLog(db.Model):
    __tablename__ = 'transcode_log'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('transcode_task.id'))
    log_time = db.Column(db.DateTime, default=datetime.utcnow)
    log_level = db.Column(db.Integer)  # 0:debug, 1:info, 2:warning, 3:error
    log_message = db.Column(db.String(1023)) 