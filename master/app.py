from flask import Flask, jsonify, send_from_directory
from models import db
from routes import worker_bp, task_bp, video_bp, log_bp
from scheduler import TaskScheduler
from config import Config
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

app = Flask(__name__, 
    static_folder='frontend/dist',
    static_url_path=''
)

# 加载配置
config = Config()

# 配置数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://DistVideoConvertDB:mPKKWmWkMEkdj6wZ@192.168.3.4:53306/DistVideoConvert?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 处理前端路由
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path.startswith('api/'):
        # API 请求交给其他路由处理
        return app.view_functions['api'](path[4:])
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(404)
def not_found(e):
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'code': 500, 'message': '服务器内部错误'}), 500

# 初始化调度器
scheduler = None

def init_scheduler():
    global scheduler
    if scheduler is None:
        # 验证路径
        if not config.validate_paths():
            logger.error("配置的扫描路径无效，请检查config.ini文件")
            return
        
        scheduler = TaskScheduler(app, config.scan_paths, config.scan_interval)
        scheduler.start()
        # 将scheduler添加到app对象中，以便在其他地方使用
        app.scheduler = scheduler

# 注册蓝图
app.register_blueprint(worker_bp, url_prefix='/api/v1/workers')
app.register_blueprint(task_bp, url_prefix='/api/v1/tasks')
app.register_blueprint(video_bp, url_prefix='/api/v1/videos')
app.register_blueprint(log_bp, url_prefix='/api/v1/logs')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # 在应用上下文中初始化调度器
        init_scheduler()
    app.run(debug=False, host='0.0.0.0', port=5333) 