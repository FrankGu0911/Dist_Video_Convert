from flask import Blueprint, request, jsonify
from models import db, VideoInfo, TranscodeTask, TranscodeWorker, TranscodeLog
from datetime import datetime, timedelta
import uuid

worker_bp = Blueprint('worker', __name__)
task_bp = Blueprint('task', __name__)

# Worker 相关路由
@worker_bp.route('', methods=['POST'])
def create_worker():
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
            worker.worker_status = 1  # 在线
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
            'code': 201,
            'message': '注册成功',
            'data': {'worker_id': worker.id}
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e)}), 500

@worker_bp.route('', methods=['GET'])
def list_workers():
    try:
        workers = TranscodeWorker.query.all()
        # 检查心跳超时
        current_time = datetime.utcnow()
        worker_list = []
        for worker in workers:
            # 如果超过30秒没有心跳，标记为离线
            if worker.last_heartbeat and (current_time - worker.last_heartbeat) > timedelta(seconds=30):
                worker.worker_status = 0  # 离线
                # 如果worker有正在执行的任务，将任务标记为失败
                if worker.current_task_id:
                    task = TranscodeTask.query.get(worker.current_task_id)
                    if task and task.task_status == 1:  # running
                        task.task_status = 3  # failed
                        task.end_time = current_time
                        video = VideoInfo.query.get(task.video_id)
                        if video:
                            video.transcode_status = 5  # failed
            
            worker_list.append({
                'worker_id': worker.id,
                'worker_name': worker.worker_name,
                'worker_type': worker.worker_type,
                'support_vr': worker.support_vr,
                'status': worker.worker_status
            })
        
        db.session.commit()
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': worker_list
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e)}), 500

@worker_bp.route('/<int:worker_id>', methods=['GET'])
def get_worker(worker_id):
    try:
        worker = TranscodeWorker.query.get(worker_id)
        if not worker:
            return jsonify({'code': 404, 'message': 'Worker不存在'}), 404

        # 检查心跳超时
        if worker.last_heartbeat and (datetime.utcnow() - worker.last_heartbeat) > timedelta(seconds=30):
            worker.worker_status = 0  # 离线
            db.session.commit()

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'worker_id': worker.id,
                'worker_name': worker.worker_name,
                'worker_type': worker.worker_type,
                'support_vr': worker.support_vr,
                'status': worker.worker_status
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@worker_bp.route('/<int:worker_id>', methods=['PUT'])
def update_worker(worker_id):
    try:
        worker = TranscodeWorker.query.get(worker_id)
        if not worker:
            return jsonify({'code': 404, 'message': 'Worker不存在'}), 404

        data = request.get_json()
        worker.worker_name = data.get('worker_name', worker.worker_name)
        worker.worker_type = data.get('worker_type', worker.worker_type)
        worker.support_vr = data.get('support_vr', worker.support_vr)

        db.session.commit()
        return jsonify({'code': 200, 'message': '更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e)}), 500

@worker_bp.route('/<int:worker_id>', methods=['DELETE'])
def delete_worker(worker_id):
    try:
        worker = TranscodeWorker.query.get(worker_id)
        if not worker:
            return jsonify({'code': 404, 'message': 'Worker不存在'}), 404

        db.session.delete(worker)
        db.session.commit()
        return jsonify({'code': 200, 'message': '删除成功'})
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
        worker.worker_status = 1  # 在线
        db.session.commit()

        return jsonify({'code': 200, 'message': '心跳更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e)}), 500

# Task 相关路由
@task_bp.route('', methods=['POST'])
def create_task():
    try:
        data = request.get_json()
        worker_id = data.get('worker_id')
        worker_type = data.get('worker_type')
        support_vr = data.get('support_vr')
        dest_path = data.get('dest_path')

        if not all([worker_id, worker_type is not None, support_vr is not None]):
            return jsonify({'code': 400, 'message': '参数不完整'}), 400

        # 更新worker心跳
        current_app.scheduler.get_worker_manager().update_worker_heartbeat(worker_id)

        # 查找待转码的视频
        video = VideoInfo.query.filter_by(transcode_status=1).first()
        if not video:
            return jsonify({'code': 404, 'message': '没有待转码的视频'}), 404

        # 创建新任务
        task_id = str(uuid.uuid4())
        task = TranscodeTask(
            task_id=task_id,
            worker_id=worker_id,
            start_time=datetime.utcnow(),
            video_id=video.id,
            video_path=video.video_path,
            dest_path=dest_path
        )

        db.session.add(task)
        db.session.commit()

        return jsonify({
            'code': 201,
            'message': '创建任务成功',
            'data': {
                'task_id': task_id,
                'video_path': video.video_path
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e)}), 500

@task_bp.route('', methods=['GET'])
def list_tasks():
    try:
        status = request.args.get('status', type=int)
        worker_id = request.args.get('worker_id', type=int)

        query = TranscodeTask.query
        if status is not None:
            query = query.filter_by(task_status=status)
        if worker_id is not None:
            query = query.filter_by(worker_id=worker_id)

        tasks = query.all()
        task_list = [{
            'task_id': task.task_id,
            'video_path': task.video_path,
            'dest_path': task.dest_path,
            'worker_id': task.worker_id,
            'progress': task.progress,
            'status': task.task_status,
            'elapsed_time': task.elapsed_time,
            'remaining_time': task.remaining_time
        } for task in tasks]

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': task_list
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@task_bp.route('/<string:task_id>', methods=['GET'])
def get_task(task_id):
    try:
        task = TranscodeTask.query.filter_by(task_id=task_id).first()
        if not task:
            return jsonify({'code': 404, 'message': '任务不存在'}), 404

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'task_id': task.task_id,
                'video_path': task.video_path,
                'dest_path': task.dest_path,
                'worker_id': task.worker_id,
                'progress': task.progress,
                'status': task.task_status,
                'error_message': task.error_message if hasattr(task, 'error_message') else None,
                'elapsed_time': task.elapsed_time,
                'remaining_time': task.remaining_time
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@task_bp.route('/<string:task_id>', methods=['PATCH'])
def update_task(task_id):
    try:
        data = request.get_json()
        worker_id = data.get('worker_id')
        progress = data.get('progress')
        status = data.get('status')
        error_message = data.get('error_message')
        elapsed_time = data.get('elapsed_time')
        remaining_time = data.get('remaining_time')

        if not all([worker_id, progress is not None, status is not None]):
            return jsonify({'code': 400, 'message': '参数不完整'}), 400

        # 更新worker心跳
        current_app.scheduler.get_worker_manager().update_worker_heartbeat(worker_id)

        task = TranscodeTask.query.filter_by(task_id=task_id).first()
        if not task:
            return jsonify({'code': 404, 'message': '任务不存在'}), 404

        task.progress = progress
        task.task_status = status
        if elapsed_time is not None:
            task.elapsed_time = elapsed_time
        if remaining_time is not None:
            task.remaining_time = remaining_time

        if status == 2:  # completed
            task.end_time = datetime.utcnow()
            task.remaining_time = 0  # 完成时剩余时间为0
            video = VideoInfo.query.get(task.video_id)
            if video:
                video.transcode_status = 4  # completed
            worker = TranscodeWorker.query.get(worker_id)
            if worker:
                worker.worker_status = 1  # pending
                worker.current_task_id = None
        elif status == 3:  # failed
            task.end_time = datetime.utcnow()
            task.remaining_time = None  # 失败时剩余时间为空
            video = VideoInfo.query.get(task.video_id)
            if video:
                video.transcode_status = 5  # failed
            worker = TranscodeWorker.query.get(worker_id)
            if worker:
                worker.worker_status = 1  # pending
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
        return jsonify({'code': 200, 'message': '更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e)}), 500 