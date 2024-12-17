from flask import Flask, jsonify
from models import db
from routes import worker_bp, task_bp
import os

app = Flask(__name__)

# 配置数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'master.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 注册蓝图
app.register_blueprint(worker_bp, url_prefix='/api/v1/worker')
app.register_blueprint(task_bp, url_prefix='/api/v1/task')

@app.errorhandler(404)
def not_found(error):
    return jsonify({'code': 404, 'message': '资源不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'code': 500, 'message': '服务器内部错误'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000) 