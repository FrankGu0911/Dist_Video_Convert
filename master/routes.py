from flask import Blueprint, request, jsonify
from models import db, VideoInfo, TranscodeTask, TranscodeWorker, TranscodeLog
from datetime import datetime, timedelta
from sqlalchemy import desc, asc
import uuid
from flask_socketio import SocketIO, emit, join_room, leave_room
import logging

# 配置日志
logger = logging.getLogger(__name__)

worker_bp = Blueprint('worker', __name__)
task_bp = Blueprint('task', __name__)
video_bp = Blueprint('video', __name__)
log_bp = Blueprint('log', __name__)

# 创建SocketIO实例
socketio = None

# 初始化函数
def init_app(app):
    global socketio
    if socketio is None:
        socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='eventlet',  # 使用eventlet作为异步模式
            transport='websocket',  # 只使用WebSocket传输
            ping_timeout=10,  # ping超时时间（秒）
            ping_interval=5,   # ping间隔时间（秒）
            logger=logger,     # 使用我们的日志记录器
            engineio_logger=logger  # 同样用于engineio的日志
        )
        
        # WebSocket事件处理
        @socketio.on('connect')
        def handle_connect():
            logger.info('Client connected')

        @socketio.on('disconnect')
        def handle_disconnect():
            logger.info('Client disconnected')

        @socketio.on('subscribe')
        def handle_subscribe(data):
            if 'task_id' in data:
                join_room(f'task_{data["task_id"]}')
                logger.info(f'Client subscribed to task {data["task_id"]}')
            elif 'room' in data and data['room'] == 'tasks_room':
                join_room('tasks_room')
                logger.info('Client subscribed to tasks room')

        @socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            if 'task_id' in data:
                leave_room(f'task_{data["task_id"]}')
                logger.info(f'Client unsubscribed from task {data["task_id"]}')
            elif 'room' in data and data['room'] == 'tasks_room':
                leave_room('tasks_room')
                logger.info('Client unsubscribed from tasks room')

    # 添加请求日志中间件
    @app.before_request
    def log_request_info():
        # 忽略对静态文件的请求日志
        if not request.path.startswith('/api/'):
            return
        logger.info(f'Request: {request.method} {request.path} - Data: {request.get_json() if request.is_json else request.args}')

    @app.after_request
    def log_response_info(response):
        # 只记录API请求的响应日志
        if request.path.startswith('/api/'):
            try:
                response_data = response.get_data(as_text=True)
                logger.info(f'Response: {response.status} - {response_data}')
            except Exception as e:
                logger.error(f'Error logging response: {str(e)}')
        return response

    app.register_blueprint(task_bp, url_prefix='/api/v1/tasks')
    app.register_blueprint(worker_bp, url_prefix='/api/v1/workers')
    app.register_blueprint(video_bp, url_prefix='/api/v1/videos')
    app.register_blueprint(log_bp, url_prefix='/api/v1/logs')

    return socketio

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
        current_time = datetime.utcnow()
        
        if worker:
            # 检查worker状态
            if worker.worker_status == 0:  # 离线状态
                # 直接更新为在线
                worker.worker_status = 1
                worker.worker_type = worker_type
                worker.support_vr = support_vr
                worker.last_heartbeat = current_time
                worker.current_task_id = None
                worker.offline_action = None
            else:  # 在线状态
                # 检查心跳是否超时
                if worker.last_heartbeat and (current_time - worker.last_heartbeat) > timedelta(seconds=30):
                    # 心跳超时，认为旧Worker已离线
                    logger.info(f"Worker {worker_name} 心跳超时，处理旧任务并允许新注册")
                    
                    # 处理旧Worker的任务
                    if worker.current_task_id:
                        task = TranscodeTask.query.get(worker.current_task_id)
                        if task and task.task_status == 1:  # 如果有运行中的任务
                            task.task_status = 3  # failed
                            task.end_time = current_time
                            task.error_message = "Worker心跳超时，任务终止"
                            # 更新视频状态
                            video = VideoInfo.query.get(task.video_id)
                            if video:
                                video.transcode_status = 5  # failed
                                video.transcode_task_id = None
                                
                            # 通过WebSocket发送任务状态更新
                            task_data = {
                                'task_id': task.task_id,
                                'video_path': task.video_path,
                                'dest_path': task.dest_path,
                                'worker_id': task.worker_id,
                                'worker_name': task.worker_name,
                                'progress': task.progress,
                                'status': task.task_status,
                                'error_message': task.error_message,
                                'elapsed_time': task.elapsed_time,
                                'remaining_time': None
                            }
                            socketio.emit('task_update', task_data, room=f'task_{task.task_id}')
                            socketio.emit('tasks_update', {
                                'type': 'update',
                                'task': task_data
                            }, room='tasks_room')
                    
                    # 更新Worker状态
                    worker.worker_status = 1  # 在线
                    worker.worker_type = worker_type
                    worker.support_vr = support_vr
                    worker.last_heartbeat = current_time
                    worker.current_task_id = None
                    worker.offline_action = None
                else:
                    # 心跳正常，拒绝注册
                    return jsonify({
                        'code': 409,
                        'message': f'Worker {worker_name} 已在线，注册失败'
                    }), 409
        else:
            # Worker不存在，创建新Worker
            worker = TranscodeWorker(
                worker_name=worker_name,
                worker_type=worker_type,
                support_vr=support_vr,
                worker_status=1,  # 注册时就设置为在线
                last_heartbeat=current_time
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
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 检查心跳超时
        current_time = datetime.utcnow()
        
        # 构建查询
        query = TranscodeWorker.query
        
        # 执行分页查询
        pagination = query.paginate(page=page, per_page=per_page)
        workers = pagination.items
        
        worker_list = []
        for worker in workers:
            # 如果超过30秒没有心跳，标记为离线
            if worker.last_heartbeat and (current_time - worker.last_heartbeat) > timedelta(seconds=30):
                worker.worker_status = 0  # 离线
                worker.offline_action = None  # 清除下线指令
                # 如果worker有正在执行的任务，将任务标记为失败
                if worker.current_task_id:
                    task = TranscodeTask.query.get(worker.current_task_id)
                    if task and task.task_status == 1:  # running
                        task.task_status = 3  # failed
                        task.end_time = current_time
                        task.error_message = "Worker离线,任务终止"
                        video = VideoInfo.query.get(task.video_id)
                        if video:
                            video.transcode_status = 5  # failed
                            video.transcode_task_id = None
                        
                        # 通过WebSocket发送任务状态更新
                        task_data = {
                            'task_id': task.task_id,
                            'video_path': task.video_path,
                            'dest_path': task.dest_path,
                            'worker_id': task.worker_id,
                            'worker_name': task.worker_name,
                            'progress': task.progress,
                            'status': task.task_status,
                            'error_message': task.error_message,
                            'elapsed_time': task.elapsed_time,
                            'remaining_time': None
                        }
                        # 发送到特定任务的房间
                        socketio.emit('task_update', task_data, room=f'task_{task.task_id}')
                        # 发送到任务列表房间
                        socketio.emit('tasks_update', {
                            'type': 'update',
                            'task': task_data
                        }, room='tasks_room')
                worker.current_task_id = None
            
            worker_list.append({
                'worker_id': worker.id,
                'worker_name': worker.worker_name,
                'worker_type': worker.worker_type,
                'support_vr': worker.support_vr,
                'status': worker.worker_status,
                'offline_action': worker.offline_action
            })
        
        db.session.commit()
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'workers': worker_list,
                'pagination': {
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'current_page': pagination.page,
                    'per_page': pagination.per_page,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }
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

@worker_bp.route('/<int:worker_id>/offline', methods=['POST'])
def set_worker_offline(worker_id):
    """设置worker下线"""
    try:
        data = request.get_json()
        action = data.get('action')
        if action not in ['offline', 'shutdown']:
            return jsonify({
                'code': 400,
                'message': '无效的下线动作'
            })
            
        worker = TranscodeWorker.query.get(worker_id)
        if not worker:
            return jsonify({
                'code': 404,
                'message': 'Worker不存在'
            })
            
        worker.offline_action = action
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '下线指令已发送'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': str(e)
        })

@worker_bp.route('/<int:worker_id>/offline', methods=['DELETE'])
def cancel_worker_offline(worker_id):
    """取消worker下线指令"""
    try:
        worker = TranscodeWorker.query.get(worker_id)
        if not worker:
            return jsonify({
                'code': 404,
                'message': 'Worker不存在'
            })
            
        worker.offline_action = None
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '下线指令已取消'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': str(e)
        })

def check_tasks_timeout():
    """检查任务超时的定时任务"""
    try:
        current_time = datetime.utcnow()
        # 获取所有运行中且最后更新时间超过60秒的任务
        running_tasks = TranscodeTask.query.filter(
            TranscodeTask.task_status == 1,  # running
            TranscodeTask.last_update_time != None,
            current_time - TranscodeTask.last_update_time > timedelta(seconds=60)
        ).all()
        
        for task in running_tasks:
            logger.info(f"任务 {task.task_id} 超时，开始处理")
            # 更新任务状态
            task.task_status = 3  # failed
            task.end_time = current_time
            task.error_message = "任务超过60秒未更新，判定为超时"
            
            # 更新视频状态
            video = VideoInfo.query.get(task.video_id)
            if video:
                video.transcode_status = 5  # failed
                video.transcode_task_id = None
            
            # 更新worker状态
            worker = TranscodeWorker.query.get(task.worker_id)
            if worker:
                worker.worker_status = 1  # pending
                worker.current_task_id = None
                worker.offline_action = None  # 清除下线指令
            
            # 记录错误日志
            log = TranscodeLog(
                task_id=task.id,
                log_level=3,  # error
                log_message=f"任务 {task.task_id} 超过60秒未更新，判定为超时"
            )
            db.session.add(log)
            
            # 通过WebSocket发送任务状态更新
            task_data = {
                'task_id': task.task_id,
                'video_path': task.video_path,
                'dest_path': task.dest_path,
                'worker_id': task.worker_id,
                'worker_name': task.worker_name,
                'progress': task.progress,
                'status': task.task_status,
                'error_message': task.error_message,
                'elapsed_time': task.elapsed_time,
                'remaining_time': None
            }
            
            # 发送到特定任务的房间
            socketio.emit('task_update', task_data, room=f'task_{task.task_id}')
            # 发送到任务列表房间
            socketio.emit('tasks_update', {
                'type': 'update',
                'task': task_data
            }, room='tasks_room')
            
            logger.info(f"任务 {task.task_id} 超时处理完成")
        
        if running_tasks:
            db.session.commit()
            
    except Exception as e:
        logger.error(f"检查任务超时出错: {str(e)}")
        db.session.rollback()

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

        # 获取worker信息
        worker = TranscodeWorker.query.get(worker_id)
        if not worker:
            return jsonify({'code': 404, 'message': 'Worker不存在'}), 404
            
        # 检查worker是否有下线指令
        if worker.offline_action:
            return jsonify({
                'code': 205,
                'message': 'worker should offline',
                'data': {
                    'action': worker.offline_action
                }
            })

        # 查找待转码的视频
        query = VideoInfo.query.filter(
            # VideoInfo.transcode_status.in_([1, 5]),  # 等待转码或转码失败
            VideoInfo.exist == True  # 文件必须存在
            
        )
        if worker_type == 0 or worker_type == 2:
            query = query.filter(VideoInfo.transcode_status.in_([1, 5]))
        # nvenc
        elif worker_type == 1 or worker_type == 3:
            query = query.filter(VideoInfo.transcode_status.in_([1]))
        # 根据worker是否支持VR筛选视频
        if support_vr:
            query = query.filter(VideoInfo.is_vr == 1)
        else:
            query = query.filter(VideoInfo.is_vr == 0)

        # 如果不是CPU worker，限制只能转码1080p及以下且帧率31帧及以下的视频
        if worker_type != 0:  # 非CPU类型
            query = query.filter(VideoInfo.resolutionall <= 1920*1080+100)
            query = query.filter(VideoInfo.fps <= 31)
            query = query.filter(VideoInfo.codec == 'h264')

        # 按照码率降序排序
        video = query.order_by(
            VideoInfo.bitrate_k.desc()
        ).first()

        if not video:
            return jsonify({'code': 404, 'message': '没有待转码的视频'}), 404

        # 创建新任务
        task_id = str(uuid.uuid4())
        current_time = datetime.utcnow()
        task = TranscodeTask(
            task_id=task_id,
            worker_id=worker_id,
            worker_name=worker.worker_name,
            start_time=current_time,
            last_update_time=current_time,  # 初始化最后更新时间
            video_id=video.id,
            video_path=video.video_path,
            dest_path=dest_path,
            task_status=1  # 设置为运行状态
        )

        # 更新视频状态为已创建任务
        video.transcode_status = 2  # created
        video.transcode_task_id = task.id

        # 更新worker状态和当前任务
        worker.worker_status = 2  # running

        db.session.add(task)
        db.session.flush()  # 获取 task.id
        worker.current_task_id = task.id
        db.session.commit()

        # 创建新任务成功后，广播到tasks_room
        task_data = {
            'task_id': task_id,
            'video_path': video.video_path,
            'dest_path': dest_path,
            'worker_id': worker_id,
            'worker_name': worker.worker_name,
            'progress': 0,
            'status': 1,  # running
            'elapsed_time': 0,
            'remaining_time': None
        }
        socketio.emit('tasks_update', {
            'type': 'create',
            'task': task_data
        }, room='tasks_room')

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
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 获取查询参数
        status = request.args.getlist('status[]', type=int)
        sort_by = request.args.get('sort_by', 'start_time')
        order = request.args.get('order', 'desc')
        
        # 构建查询
        query = TranscodeTask.query
        
        # 应用过滤条件
        if status:
            query = query.filter(TranscodeTask.task_status.in_(status))
            
        # 应用排序
        sort_column = getattr(TranscodeTask, sort_by, TranscodeTask.start_time)
        if order == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
            
        # 执行分页查询
        pagination = query.paginate(page=page, per_page=per_page)
        tasks = pagination.items
        
        # 构建响应数据
        tasks_list = [{
            'task_id': task.task_id,
            'video_path': task.video_path,
            'dest_path': task.dest_path,
            'worker_id': task.worker_id,
            'worker_name': task.worker_name,
            'progress': task.progress,
            'status': task.task_status,
            'elapsed_time': task.elapsed_time,
            'remaining_time': task.remaining_time
        } for task in tasks]

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'tasks': tasks_list,
                'pagination': {
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'current_page': pagination.page,
                    'per_page': pagination.per_page,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取任务列表失败: {str(e)}'
        }), 500

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
                'worker_name': task.worker_name,
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

        task = TranscodeTask.query.filter_by(task_id=task_id).first()
        if not task:
            return jsonify({'code': 404, 'message': '任务不存在'}), 404

        task.progress = progress
        task.task_status = status
        task.last_update_time = datetime.utcnow()  # 更新最后更新时间
        if elapsed_time is not None:
            task.elapsed_time = elapsed_time
        if remaining_time is not None:
            task.remaining_time = remaining_time

        # 更新视频状态
        video = VideoInfo.query.get(task.video_id)
        if video:
            if status == 1:  # running
                video.transcode_status = 3  # transcoding
                video.transcode_task_id = task.id
            elif status == 2:  # completed
                task.end_time = datetime.utcnow()
                task.remaining_time = 0  # 完成时剩余时间为0
                video.transcode_status = 4  # completed
                video.transcode_task_id = None
                worker = TranscodeWorker.query.get(worker_id)
                if worker:
                    worker.worker_status = 1  # pending
                    worker.current_task_id = None
            elif status == 3:  # failed
                task.end_time = datetime.utcnow()
                task.remaining_time = None  # 失败时剩余时间为空
                video.transcode_status = 5  # failed
                video.transcode_task_id = None
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

        # 通过WebSocket发送任务状态更新
        task_data = {
            'task_id': task.task_id,
            'video_path': task.video_path,
            'dest_path': task.dest_path,
            'worker_id': task.worker_id,
            'worker_name': task.worker_name,
            'progress': task.progress,
            'status': task.task_status,
            'error_message': error_message if error_message else None,
            'elapsed_time': task.elapsed_time,
            'remaining_time': task.remaining_time
        }
        # 发送到特定任务的房间
        socketio.emit('task_update', task_data, room=f'task_{task_id}')
        # 发送到任务列表房间
        socketio.emit('tasks_update', {
            'type': 'update',
            'task': task_data
        }, room='tasks_room')

        return jsonify({'code': 200, 'message': '更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e)}), 500

@video_bp.route('', methods=['GET'])
def list_videos():
    try:
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)  # 默认每页20条
        
        # 获取查询参数
        transcode_status = request.args.getlist('transcode_status[]', type=int)
        is_vr = request.args.get('is_vr', type=int)
        codec = request.args.getlist('codec[]')
        min_bitrate = request.args.get('min_bitrate', type=int)  # 最小码率(Kbps)
        max_bitrate = request.args.get('max_bitrate', type=int)  # 最大码率(Kbps)
        min_size = request.args.get('min_size', type=float)      # 最小文件大小(MB)
        max_size = request.args.get('max_size', type=float)      # 最大文件大小(MB)
        
        # 排序参数
        sort_by = request.args.get('sort_by', 'updatetime')  # 默认按更新时间排序
        order = request.args.get('order', 'desc')            # 默认降序
        
        query = VideoInfo.query.filter(VideoInfo.exist == True)
        
        # 应用过滤条件
        if transcode_status:
            query = query.filter(VideoInfo.transcode_status.in_(transcode_status))
        if is_vr is not None:
            query = query.filter(VideoInfo.is_vr == is_vr)
        if codec:
            query = query.filter(VideoInfo.codec.in_(codec))
        if min_bitrate is not None:
            query = query.filter(VideoInfo.bitrate_k >= min_bitrate)
        if max_bitrate is not None:
            query = query.filter(VideoInfo.bitrate_k <= max_bitrate)
        if min_size is not None:
            query = query.filter(VideoInfo.video_size >= min_size)
        if max_size is not None:
            query = query.filter(VideoInfo.video_size <= max_size)
            
        # 应用排序
        sort_column = getattr(VideoInfo, sort_by, VideoInfo.updatetime)
        if order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
            
        # 执行分页查询
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        videos = pagination.items
        
        video_list = [{
            'id': video.id,
            'video_path': video.video_path,
            'codec': video.codec,
            'bitrate_k': video.bitrate_k,
            'video_size': video.video_size,
            'fps': video.fps,
            'resolution': {
                'width': video.resolutionx,
                'height': video.resolutiony
            },
            'is_vr': video.is_vr,
            'transcode_status': video.transcode_status,
            'transcode_task_id': video.transcode_task_id,
            'update_time': video.updatetime.isoformat() if video.updatetime else None
        } for video in videos]

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'videos': video_list,
                'pagination': {
                    'total': pagination.total,        # 总记录数
                    'pages': pagination.pages,        # 总页数
                    'current_page': pagination.page,  # 当前页
                    'per_page': pagination.per_page,  # 每页记录数
                    'has_next': pagination.has_next,  # 是否有下一页
                    'has_prev': pagination.has_prev   # 是否有上一页
                }
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@video_bp.route('/<int:video_id>', methods=['GET'])
def get_video(video_id):
    try:
        video = VideoInfo.query.get(video_id)
        if not video or not video.exist:
            return jsonify({'code': 404, 'message': '视频不存在'}), 404

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'id': video.id,
                'video_path': video.video_path,
                'codec': video.codec,
                'bitrate_k': video.bitrate_k,
                'video_size': video.video_size,
                'fps': video.fps,
                'resolution': {
                    'width': video.resolutionx,
                    'height': video.resolutiony
                },
                'is_vr': video.is_vr,
                'transcode_status': video.transcode_status,
                'transcode_task_id': video.transcode_task_id,
                'update_time': video.updatetime.isoformat() if video.updatetime else None
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

# 添加日志相关路由
@log_bp.route('', methods=['GET'])
def get_logs():
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        log_level = request.args.getlist('log_level[]')  # 修改为 getlist
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        sort_by = request.args.get('sort_by', 'log_time')
        order = request.args.get('order', 'desc')

        # 构建查询
        query = TranscodeLog.query

        # 应用筛选
        if log_level:
            # 转换为整数列表
            level_list = [int(l) for l in log_level if l.isdigit()]
            if level_list:  # 只有在列表非空时才应用过滤
                query = query.filter(TranscodeLog.log_level.in_(level_list))
        
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            query = query.filter(TranscodeLog.log_time >= start_dt)
        
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            query = query.filter(TranscodeLog.log_time <= end_dt)

        # 应用排序
        sort_column = getattr(TranscodeLog, sort_by, TranscodeLog.log_time)
        if order == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # 执行分页查询
        try:
            pagination = query.paginate(page=page, per_page=per_page)
            logs = pagination.items
        except Exception as e:
            print(f"Pagination error: {e}")
            return jsonify({
                'code': 400,
                'message': '分页参数错误'
            }), 400

        # 构建响应数据
        logs_list = [{
            'id': log.id,
            'task_id': log.task_id,
            'log_time': log.log_time.isoformat(),
            'log_level': log.log_level,
            'log_message': log.log_message
        } for log in logs]

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'logs': logs_list,
                'pagination': {
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'current_page': pagination.page,
                    'per_page': pagination.per_page,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }
        })

    except Exception as e:
        print(f"Error in get_logs: {str(e)}")  # 添加调试日志
        return jsonify({
            'code': 500,
            'message': f'获取日志失败: {str(e)}'
        }), 500

@log_bp.route('', methods=['POST'])
def create_log():
    try:
        data = request.get_json()
        
        # 必需参数
        task_id = data.get('task_id')
        log_level = data.get('log_level')
        log_message = data.get('log_message')
        
        # 参数验证
        if not all([task_id, log_level is not None, log_message]):
            return jsonify({
                'code': 400,
                'message': '缺少必需参数'
            }), 400
            
        # 验证日志级别是否合法（0-debug, 1-info, 2-warning, 3-error）
        if log_level not in [0, 1, 2, 3]:
            return jsonify({
                'code': 400,
                'message': '无效的日志级别'
            }), 400
            
        # 验证task是否存在
        task = TranscodeTask.query.filter_by(task_id=task_id).first()
        if not task:
            return jsonify({
                'code': 404,
                'message': '任务不存在'
            }), 404
        
        # 创建日志记录
        log = TranscodeLog(
            task_id=task.id,  # 使用task的数据库ID
            log_level=log_level,
            log_message=log_message
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'code': 201,
            'message': '日志创建成功',
            'data': {
                'id': log.id,
                'task_id': task_id,
                'log_time': log.log_time.isoformat(),
                'log_level': log.log_level,
                'log_message': log.log_message
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'创建日志失败: {str(e)}'
        }), 500