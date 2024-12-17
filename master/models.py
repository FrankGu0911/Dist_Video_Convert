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
    video_size = db.Column(db.Float)
    fps = db.Column(db.Float)
    resolutionx = db.Column(db.Integer)
    resolutiony = db.Column(db.Integer)
    resolutionall = db.Column(db.Integer)
    is_vr = db.Column(db.Integer, default=0)
    updatetime = db.Column(db.DateTime, default=datetime.utcnow)
    transcode_status = db.Column(db.Integer, default=0)  # 0:not_transcode, 1:wait_transcode, 2:created, 3:running, 4:completed, 5:failed
    transcode_task_id = db.Column(db.Integer)

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