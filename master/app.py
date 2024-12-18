from flask import Flask, jsonify
from models import db
from routes import worker_bp, task_bp
from scheduler import TaskScheduler
from config import Config
import os

app = Flask(__name__)

# 加载配置
config = Config()

# 配置数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'master.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 注册蓝图
app.register_blueprint(worker_bp, url_prefix='/api/v1/workers')
app.register_blueprint(task_bp, url_prefix='/api/v1/tasks')

@app.errorhandler(404)
def not_found(error):
    return jsonify({'code': 404, 'message': '资源不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'code': 500, 'message': '服务器内部错误'}), 500

# 初始化调度器
scheduler = None

@app.before_first_request
def init_scheduler():
    global scheduler
    if scheduler is None:
        # 验证路径
        if not config.validate_paths():
            app.logger.error("配置的扫描路径无效，请检查config.ini文件")
            return
        
        scheduler = TaskScheduler(app, config.scan_paths, config.scan_interval)
        scheduler.start()
        # 将scheduler添加到app对象中，以便在其他地方使用
        app.scheduler = scheduler

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000) 