import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from master.models import db, TranscodeTask, TranscodeWorker, VideoInfo
import shutil

# 创建Flask应用
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://DistVideoConvertDB:mPKKWmWkMEkdj6wZ@192.168.3.4:53306/DistVideoConvert?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

def get_nvenc_tasks():
    """获取所有符合条件的NVENC任务
    
    条件：
    1. 任务状态为成功（status=2）
    2. 任务开始时间在2025-1-20 00:00之后
    3. worker类型为NVENC（worker_type=1）
    
    Returns:
        list: 符合条件的任务列表
    """
    
    with app.app_context():
        try:
            # 设置筛选时间
            target_date = datetime(2025, 1, 20, 2, 59, 0)
            
            # 查询符合条件的任务
            tasks = TranscodeTask.query.join(
                TranscodeWorker,
                TranscodeTask.worker_id == TranscodeWorker.id
            ).filter(
                and_(
                    TranscodeTask.task_status == 2,  # 成功完成的任务
                    TranscodeTask.start_time >= target_date,  # 2025-1-20之后的任务
                    TranscodeWorker.worker_type == 1  # NVENC worker
                )
            ).all()
            
            # 构建结果列表
            result = []
            for task in tasks:
                result.append({
                    'task_id': task.task_id,
                    'video_path': task.video_path,
                    'video_id': task.video_id,
                    'worker_name': task.worker_name,
                    'start_time': task.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': task.end_time.strftime('%Y-%m-%d %H:%M:%S') if task.end_time else None,
                    'elapsed_time': task.elapsed_time
                })
                
            return result
            
        except Exception as e:
            print(f"查询出错: {str(e)}")
            return []

if __name__ == '__main__':
    # 获取并打印结果
    src_prefix = '\\\\192.168.3.13'
    transcode_prefix = '\\\\192.168.3.13\\hdd\\ad_video\\transcode'
    nvenc_prefix = '\\\\192.168.3.13\\hdd\\ad_video\\transcode\\nvenc'
    if not os.path.exists(nvenc_prefix):
        os.makedirs(nvenc_prefix)
    if not os.path.exists('nvenc_list.txt'):
        f = open('nvenc_list.txt', 'w',encoding='utf-8')
        f.close()
    tasks = get_nvenc_tasks()
    print(f"找到 {len(tasks)} 个符合条件的任务：")
    for task in tasks:
        src_path = os.path.join(src_prefix, task['video_path'])
        transcode_path = os.path.join(transcode_prefix, task['video_path'])
        nvenc_path = os.path.join(nvenc_prefix, task['video_path'])
        if os.path.exists(transcode_path):
            dir_path = os.path.dirname(nvenc_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            shutil.move(transcode_path, nvenc_path)
            print(f"移动 {transcode_path} 到 {nvenc_path}")
            # 标记对应video状态为失败
            with app.app_context():
                video = db.session.get(VideoInfo, task['video_id'])  # 使用新的 session.get() 方法
                if video:
                    video.transcode_status = 5
                    video.updatetime = datetime.now()
                    db.session.commit()
        else:
            print(f"transcode_path {transcode_path} 不存在")
            f = open('nvenc_list.txt', 'a',encoding='utf-8')
            f.write(task['video_path'] + '\n')
            f.close()

        
        # print("\n任务信息：")
        # print(f"任务ID: {task['task_id']}")
        # print(f"视频路径: {task['video_path']}")
        # print(f"Worker名称: {task['worker_name']}")
        # print(f"开始时间: {task['start_time']}")
        # print(f"结束时间: {task['end_time']}")
        # print(f"耗时: {task['elapsed_time']} 秒")
