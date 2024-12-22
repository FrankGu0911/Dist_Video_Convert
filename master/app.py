import eventlet
eventlet.monkey_patch()

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from models import db
from routes import init_app
from config import Config
from scheduler import TaskScheduler
import os
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # 使用stdout，它支持UTF-8
    ]
)

# 设置Flask和Werkzeug的日志级别
logging.getLogger('werkzeug').setLevel(logging.INFO)
logging.getLogger('flask.app').setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# 获取当前脚本的绝对路径
SCRIPT_PATH = os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__)
# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
# 获取前端目录（基于脚本位置）
FRONTEND_DIR = os.path.join(SCRIPT_DIR, 'frontend', 'dist')

logger.info(f"脚本路径: {SCRIPT_PATH}")
logger.info(f"前端目录: {FRONTEND_DIR}")

# 确保前端目录存在
if not os.path.exists(FRONTEND_DIR):
    os.makedirs(FRONTEND_DIR)
    logger.warning(f"前端目录不存在，已创建: {FRONTEND_DIR}")

def create_app():
    app = Flask(__name__, 
        static_folder='frontend/dist',
        static_url_path=''
    )
    CORS(app)

    # 加载配置
    config = Config()
    
    # 配置数据库
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://DistVideoConvertDB:mPKKWmWkMEkdj6wZ@192.168.3.4:53306/DistVideoConvert?charset=utf8mb4'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 初始化数据库
    db.init_app(app)

    # 创建应用上下文
    app.app_context().push()

    # 初始化路由和WebSocket
    socketio = init_app(app)

    # 处理前端路由
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        try:
            if path.startswith('api/'):
                # API 请求交给其他路由处理
                return app.view_functions['api'](path[4:])
            
            # 检查是否是静态文件请求
            if path and os.path.exists(os.path.join(app.static_folder, path)):
                return send_from_directory(app.static_folder, path)
            
            # 对于所有其他请求，返回index.html
            return send_from_directory(app.static_folder, 'index.html')
        except Exception as e:
            logger.error(f"Error serving path '{path}': {str(e)}")
            return jsonify({'code': 500, 'message': '服务器内部错误'}), 500

    @app.errorhandler(404)
    def not_found(e):
        try:
            return send_from_directory(app.static_folder, 'index.html')
        except Exception as e:
            logger.error(f"Error handling 404: {str(e)}")
            return jsonify({'code': 404, 'message': '页面不存在'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({'code': 500, 'message': '服务器内部错误'}), 500

    # 创建数据库表
    db.create_all()

    # 初始化调度器
    if not config.validate_paths():
        logger.error("配置的扫描路径无效，请检查config.ini文件")
    else:
        scheduler = TaskScheduler(app, config.scan_paths, config.scan_interval)
        scheduler.start()
        app.scheduler = scheduler

    return app, socketio

if __name__ == '__main__':
    app, socketio = create_app()
    # 使用socketio运行应用，而不是普通的app.run()
    socketio.run(app, host='0.0.0.0', port=5333, debug=False) 