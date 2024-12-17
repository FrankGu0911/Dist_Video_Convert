from flask import Blueprint, request, jsonify
from models import db, VideoInfo, TranscodeTask, TranscodeWorker, TranscodeLog
from datetime import datetime
import uuid

worker_bp = Blueprint('worker', __name__)
task_bp = Blueprint('task', __name__)

@worker_bp.route('/register', methods=['POST'])
def register_worker():
    try:
        data = request.get_json()
        worker_name = data.get('worker_name')
        worker_type = data.get('worker_type')
        support_vr = data.get('support_vr')

        if not all([worker_name, worker_type is not None, support_vr is not None]):
            return jsonify({'code': 400, 'message': '参数不完整'}), 400

        # 检查worker是否已存在
        worker = TranscodeWorker.query.filter_by(worker_name=worker_name).first()
        if worker:
            worker.worker_status = 1  # pending
            worker.worker_type = worker_type
            worker.support_vr = support_vr
            worker.last_heartbeat = datetime.utcnow()
        else:
            worker = TranscodeWorker(
                worker_name=worker_name,
                worker_type=worker_type,
                support_vr=support_vr,
                worker_status=1,
                last_heartbeat=datetime.utcnow()
            )
            db.session.add(worker)
        
        db.session.commit()
        return jsonify({
            'code': 200,
            'message': '注册成功',
            'data': {'worker_id': worker.id}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e)}), 500

@worker_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    try:
        data = request.get_json()
        worker_id = data.get('worker_id')
        worker_name = data.get('worker_name')

        if not all([worker_id, worker_name]):
            return jsonify({'code': 400, 'message': '参数不完整'}), 400

        worker = TranscodeWorker.query.get(worker_id)
        if not worker or worker.worker_name != worker_name:
            return jsonify({'code': 404, 'message': 'Worker不存在'}), 404

        worker.last_heartbeat = datetime.utcnow()
        db.session.commit()

        return jsonify({'code': 200, 'message': '心跳更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e)}), 500

@task_bp.route('/new', methods=['GET'])
def get_new_task():
    try:
        worker_id = request.args.get('worker_id')
        worker_name = request.args.get('worker_name')

        if not all([worker_id, worker_name]):
            return jsonify({'code': 400, 'message': '参数不完整'}), 400

        worker = TranscodeWorker.query.get(worker_id)
        if not worker or worker.worker_name != worker_name:
            return jsonify({'code': 404, 'message': 'Worker不存在'}), 404

        # 查找待转码的视频
        video = VideoInfo.query.filter_by(transcode_status=1).first()
        if not video:
            return jsonify({'code': 200, 'message': '没有新任务', 'data': None})

        # 创建新任务
        task_id = str(uuid.uuid4())
        task = TranscodeTask(
            task_id=task_id,
            worker_id=worker_id,
            worker_name=worker_name,
            start_time=datetime.utcnow(),
            video_id=video.id,
            video_path=video.video_path
        )

        # 更新状态
        video.transcode_status = 2  # created
        video.transcode_task_id = task.id
        worker.worker_status = 2  # running
        worker.current_task_id = task.id

        db.session.add(task)
        db.session.commit()

        return jsonify({
            'code': 200,
            'message': '获取任务成功',
            'data': {
                'task_id': task_id,
                'video_path': video.video_path,
                'dest_path': task.dest_path
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e)}), 500

@task_bp.route('/progress', methods=['POST'])
def update_task_progress():
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        worker_id = data.get('worker_id')
        progress = data.get('progress')
        status = data.get('status')
        error_message = data.get('error_message')

        if not all([task_id, worker_id, progress is not None, status is not None]):
            return jsonify({'code': 400, 'message': '参数不完整'}), 400

        task = TranscodeTask.query.filter_by(task_id=task_id).first()
        if not task:
            return jsonify({'code': 404, 'message': '任务不存在'}), 404

        task.progress = progress
        task.task_status = status

        if status == 2:  # completed
            task.end_time = datetime.utcnow()
            video = VideoInfo.query.get(task.video_id)
            if video:
                video.transcode_status = 4  # completed
            worker = TranscodeWorker.query.get(worker_id)
            if worker:
                worker.worker_status = 1  # pending
                worker.current_task_id = None
        elif status == 3:  # failed
            task.end_time = datetime.utcnow()
            video = VideoInfo.query.get(task.video_id)
            if video:
                video.transcode_status = 5  # failed
            worker = TranscodeWorker.query.get(worker_id)
            if worker:
                worker.worker_status = 3  # failed
                worker.current_task_id = None
            # 记录错误日志
            if error_message:
                log = TranscodeLog(
                    task_id=task.id,
                    log_level=3,  # error
                    log_message=error_message
                )
                db.session.add(log)

        db.session.commit()
        return jsonify({'code': 200, 'message': '更新进度成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e)}), 500 