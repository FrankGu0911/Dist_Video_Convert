# 传输模式支持改造方案

## 概述
本文档描述了在现有的 SMB 挂载方案基础上，增加 HTTP 流式传输支持的具体改造方案。新方案允许 worker 通过命令行参数选择使用 SMB 挂载或 HTTP 流式传输的方式进行文件传输。对于 HTTP 模式，增加了必要的鉴权机制以确保安全性。

## 改造范围

### Master 端改造

#### 1. 新增流式传输接口
- 文件：`master/routes.py`
- 新增路由：
  ```python
  @stream_bp.route('/source/<string:task_id>', methods=['GET'])  # 源文件流式下载
  @stream_bp.route('/result/<string:task_id>', methods=['PUT'])  # 转码结果流式上传
  ```

#### 2. 新增鉴权支持
- 文件：`master/models.py`
- 在 TranscodeWorker 表中添加字段：
  ```python
  class TranscodeWorker(db.Model):
      __tablename__ = 'transcode_worker'
      
      id = db.Column(db.Integer, primary_key=True)
      worker_name = db.Column(db.String(255), unique=True, nullable=False)
      worker_status = db.Column(db.Integer, default=0)  # 0:offline, 1:pending, 2:running, 3:failed
      worker_type = db.Column(db.Integer)  # 0:cpu, 1:nvenc, 2:qsv, 3:vpu
      support_vr = db.Column(db.Integer, default=0)
      last_heartbeat = db.Column(db.DateTime)
      current_task_id = db.Column(db.Integer)
      offline_action = db.Column(db.String(10), nullable=True)  # offline或shutdown
      api_key = db.Column(db.String(64), nullable=True)  # API Key
      api_key_created_at = db.Column(db.DateTime)  # API Key 创建时间
  ```

- 文件：`master/auth.py`
- 新增鉴权装饰器：
  ```python
  def require_api_key(f):
      @wraps(f)
      def decorated(*args, **kwargs):
          # 仅在 HTTP 模式下进行鉴权
          if request.args.get('mode') != 'http':
              return f(*args, **kwargs)
              
          api_key = request.headers.get('X-API-Key')
          worker_name = request.headers.get('X-Worker-Name')
          
          if not api_key or not worker_name:
              return jsonify({'code': 401, 'message': '缺少认证信息'})
              
          worker = TranscodeWorker.query.filter_by(worker_name=worker_name).first()
          if not worker or worker.api_key != api_key:
              return jsonify({'code': 401, 'message': '无效的认证信息'})
              
          return f(*args, **kwargs)
      return decorated
  ```

- 文件：`master/routes.py`
- 新增 API Key 管理接口：
  ```python
  @worker_bp.route('/api_key', methods=['POST'])
  def generate_api_key():
      """生成新的 API Key"""
      worker_name = request.json.get('worker_name')
      if not worker_name:
          return jsonify({'code': 400, 'message': '缺少 worker_name'})
          
      worker = TranscodeWorker.query.filter_by(worker_name=worker_name).first()
      if not worker:
          return jsonify({'code': 404, 'message': 'Worker不存在'})
          
      # 生成随机的 API Key
      api_key = secrets.token_hex(32)
      
      # 更新 API Key
      worker.api_key = api_key
      worker.api_key_created_at = datetime.utcnow()
      db.session.commit()
      
      return jsonify({
          'code': 200,
          'message': 'API Key 生成成功',
          'data': {'api_key': api_key}
      })
  ```

#### 3. 应用鉴权到流式接口
```python
@stream_bp.route('/source/<string:task_id>', methods=['GET'])
@require_api_key
def stream_source(task_id):
    ...

@stream_bp.route('/result/<string:task_id>', methods=['PUT'])
@require_api_key
def stream_result(task_id):
    ...
```

### Worker 端改造

#### 1. 命令行参数添加
- 文件：`worker/work.py`
- 修改内容：
  ```python
  parser.add_argument('--transfer-mode', choices=['smb', 'http'], default='smb',
                     help='File transfer mode (smb or http)')
  parser.add_argument('--api-key', help='API key for HTTP mode authentication')
  ```

#### 2. Video 类改造
- 文件：`worker/video.py`
- 改造内容：
  ```python
  def build_ffmpeg_command(self, task_id: str, dest_path: str, transfer_mode: str, 
                          master_url: str = None, worker_name: str = None, api_key: str = None, **kwargs):
      """构建 ffmpeg 命令"""
      if transfer_mode == "http":
          if not all([master_url, worker_name, api_key]):
              raise ValueError("HTTP mode requires master_url, worker_name and api_key")
              
          # 构造认证头（使用双引号包裹值，避免引号嵌套问题）
          headers = {
              'X-API-Key': api_key,
              'X-Worker-Name': worker_name
          }
          
          # 将多个头部合并为一个字符串
          headers_str = '\\'.join([f"{k}:{v}" for k, v in headers.items()])
          
          # 构造输入输出 URL
          input_path = f"{master_url}/api/v1/stream/source/{task_id}?mode=http|headers={headers_str}"
          output_path = f"{master_url}/api/v1/stream/result/{task_id}?mode=http|headers={headers_str}"
      else:  # smb mode
          input_path = self.path
          output_path = dest_path
      
      # 构建命令
      cmd = [
          'ffmpeg', '-y',
          '-i', input_path,
          '-c:v', 'hevc_nvenc',
          '-preset', self._get_nvenc_preset(kwargs.get('preset'))
      ]
      
      # HTTP 模式添加流式输出参数
      if transfer_mode == "http":
          cmd.extend(['-f', 'mp4', '-movflags', 'frag_keyframe+empty_moov'])
      
      # 添加输出路径
      cmd.append(output_path)
      
      return cmd
  ```

- FFmpeg 命令示例：
  ```bash
  # SMB 模式
  ffmpeg -y -i "\\192.168.3.13\videos\input.mp4" \
      -c:v hevc_nvenc \
      -preset p4 \
      "\\192.168.3.13\videos\output.mp4"

  # HTTP 模式
  ffmpeg -y -i "http://localhost:5000/api/v1/stream/source/12345?mode=http|headers=X-API-Key:abcd1234\X-Worker-Name:worker1" \
      -c:v hevc_nvenc \
      -preset p4 \
      -f mp4 \
      -movflags frag_keyframe+empty_moov \
      "http://localhost:5000/api/v1/stream/result/12345?mode=http|headers=X-API-Key:abcd1234\X-Worker-Name:worker1"
  ```

- 注意事项：
  1. HTTP 模式特殊处理：
     - 添加认证头到 URL
     - 使用流式输出参数
     - 添加 mode=http 查询参数触发服务端鉴权
  
  2. 认证头格式：
     - 使用 headers 参数传递
     - 多个头部用反斜杠分隔
     - 避免使用引号防止解析错误
  
  3. 输出格式：
     - HTTP 模式使用 MP4 格式
     - 启用 frag_keyframe 和 empty_moov 标志
     - 支持流式传输

## 路径处理设计

### 1. 数据库表关系
- VideoInfo 表：
  ```sql
  video_path: 原始视频路径
  transcode_task_id: 关联到转码任务的ID
  ```

- TranscodeTask 表：
  ```sql
  video_path: 原始视频路径
  dest_path: 目标路径
  task_id: 唯一任务标识
  task_status: 任务状态（0:created, 1:running, 2:completed, 3:failed）
  ```

### 2. 路径配置
- Master 端固定配置：
  ```python
  PREFIX_PATH = r"\\192.168.3.13"  # SMB 服务器路径
  SAVE_PATH = r"hdd\ad_video\transcode"  # 转码文件保存路径
  ```

### 3. 路径转换逻辑
```python
def get_transcode_paths(task_dest_path: str):
    """
    处理转码路径，生成临时文件和最终文件的路径
    
    Args:
        task_dest_path: 数据库中的目标路径
        
    Returns:
        (temp_path, final_path): 临时文件路径和最终文件路径的元组
        
    Raises:
        ValueError: 如果路径为空或无效
    """
    if not task_dest_path:
        raise ValueError("目标路径不能为空")
        
    # 标准化路径（统一使用反斜杠）
    task_path = task_dest_path.replace('/', '\\').strip()
    if not task_path:
        raise ValueError("无效的目标路径")
    
    # 获取相对路径（去除前缀）
    if task_path.startswith(PREFIX_PATH):
        rel_path = task_path[len(PREFIX_PATH):].lstrip('\\')
    else:
        rel_path = task_path
        
    # 检查路径是否包含非法字符
    if any(c in rel_path for c in ['<', '>', ':', '"', '|', '?', '*']):
        raise ValueError("路径包含非法字符")
        
    # 构建临时文件和最终文件路径
    temp_path = os.path.join(PREFIX_PATH, SAVE_PATH, "tmp", rel_path)
    final_path = os.path.join(PREFIX_PATH, SAVE_PATH, rel_path)
    
    return temp_path, final_path
```

### 4. 路径示例
假设数据库中的目标路径为：`hdd\ad_video\Giants\JAV_output\1.mp4`
- 临时文件路径：`\\192.168.3.13\hdd\ad_video\transcode\tmp\hdd\ad_video\Giants\JAV_output\1.mp4`
- 最终文件路径：`\\192.168.3.13\hdd\ad_video\transcode\hdd\ad_video\Giants\JAV_output\1.mp4`

### 5. 路径处理流程
1. 任务创建时：
   - 检查 `dest_path` 是否有效
   - 生成临时文件和最终文件路径
   - 确保目标目录存在

2. 文件上传时：
   ```python
   @stream_bp.route('/result/<string:task_id>', methods=['PUT'])
   def stream_result(task_id):
       try:
           task = TranscodeTask.query.filter_by(task_id=task_id).first()
           if not task:
               raise InvalidTaskError(f"Task {task_id} not found")
               
           # 检查任务状态
           if task.task_status not in [1]:  # 1: running
               raise InvalidTaskError(f"Task {task_id} is not in running state")
               
           # 检查目标路径
           if not task.dest_path:
               raise InvalidTaskError(f"Task {task_id} has no destination path")
               
           # 获取临时文件路径
           temp_path, _ = get_transcode_paths(task.dest_path)
           
           # 确保临时目录存在
           os.makedirs(os.path.dirname(temp_path), exist_ok=True)
           
           # 使用临时文件处理上传
           temp_file = temp_path + '.part'
           ...
   ```

3. 任务完成时：
   - 检查任务状态（必须是首次完成）
   - 获取临时文件和最终文件路径
   - 确保目标目录存在
   - 移动文件到最终位置

### 6. 错误处理
1. 路径相关错误：
   - 空路径
   - 无效路径
   - 非法字符
   - 目录创建失败
   - 文件移动失败

2. 任务状态错误：
   - 任务不存在
   - 任务状态不正确
   - 重复完成

3. 文件系统错误：
   - 磁盘空间不足
   - 权限不足
   - 文件已存在
   - 源文件不存在

### 7. 注意事项
1. 路径处理：
   - 统一使用反斜杠作为路径分隔符
   - 去除路径首尾空白字符
   - 检查非法字符
   - 处理相对路径和绝对路径

2. 文件操作：
   - 使用 .part 后缀标识未完成的上传
   - 确保目录存在后再操作文件
   - 使用原子操作移动文件
   - 及时清理临时文件

3. 状态检查：
   - 上传前检查任务状态
   - 移动文件时检查任务状态
   - 避免重复处理完成状态

4. 错误恢复：
   - 上传失败时清理临时文件
   - 移动失败时回滚状态更新
   - 记录详细的错误信息

## 文件处理流程

### 1. 文件上传（stream_result）
```python
@stream_bp.route('/result/<string:task_id>', methods=['PUT'])
def stream_result(task_id):
    """接收转码结果流"""
    try:
        task = TranscodeTask.query.filter_by(task_id=task_id).first()
        if not task:
            raise InvalidTaskError(f"Task {task_id} not found")
            
        # 获取临时文件路径
        temp_path, _ = get_transcode_paths(task.dest_path)
        
        # 确保临时目录存在
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        # 使用临时文件处理上传
        temp_file = temp_path + '.part'
        try:
            with open(temp_file, 'wb') as f:
                while True:
                    chunk = request.stream.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            
            # 上传完成后，重命名临时文件（移除.part后缀）
            os.replace(temp_file, temp_path)
            
            return jsonify({'code': 200, 'message': 'Upload successful'})
            
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except Exception as e:
        logger.exception(f"Failed to handle upload for task {task_id}")
        return jsonify({
            'code': 500,
            'message': str(e),
            'error_type': type(e).__name__
        })
```

### 2. 文件移动（update_task）
```python
@task_bp.route('/<string:task_id>', methods=['PATCH'])
def update_task(task_id):
    """更新任务状态"""
    try:
        data = request.get_json()
        task = TranscodeTask.query.filter_by(task_id=task_id).first()
        if not task:
            return jsonify({'code': 404, 'message': '任务不存在'})
            
        # 只在任务首次完成时移动文件
        if (data.get('status') == TaskStatus.COMPLETED and 
            task.status != TaskStatus.COMPLETED):
            
            # 获取临时文件和最终文件路径
            temp_path, final_path = get_transcode_paths(task.dest_path)
            
            try:
                # 确保目标目录存在
                os.makedirs(os.path.dirname(final_path), exist_ok=True)
                
                # 移动文件到最终位置
                if os.path.exists(temp_path):
                    os.replace(temp_path, final_path)
                else:
                    raise FileNotFoundError(f"Temporary file not found: {temp_path}")
                    
                # 更新任务状态
                for key, value in data.items():
                    setattr(task, key, value)
                db.session.commit()
                
                return jsonify({'code': 200, 'message': '任务更新成功'})
                
            except Exception as e:
                # 如果移动失败，回滚状态更新
                db.session.rollback()
                logger.error(f"Failed to move file for task {task_id}: {e}")
                return jsonify({
                    'code': 500,
                    'message': f'文件移动失败: {str(e)}',
                    'error_type': type(e).__name__
                })
        
        # 如果任务已经完成，直接返回成功
        elif (data.get('status') == TaskStatus.COMPLETED and 
              task.status == TaskStatus.COMPLETED):
            return jsonify({'code': 200, 'message': '任务已完成'})
            
        # 其他状态更新
        for key, value in data.items():
            setattr(task, key, value)
        db.session.commit()
        
        return jsonify({'code': 200, 'message': '任务更新成功'})
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Failed to update task {task_id}")
        return jsonify({
            'code': 500,
            'message': str(e),
            'error_type': type(e).__name__
        })
```

## 错误处理

### 1. Master 端错误处理
- 任务不存在
- 源文件不存在或无访问权限
- 存储空间不足
- 上传失败
- 未知错误

### 2. Worker 端错误处理
- 配置验证错误
- 网络连接错误
- FFmpeg 执行错误
- 文件传输错误

## 使用方式

### 1. SMB 模式（默认）
```bash
python work.py --name worker1 --type nvenc --master http://localhost:5000 \
               --transfer-mode smb [其他参数]
```

### 2. HTTP 模式
1. 首先获取 API Key：
```bash
curl -X POST http://localhost:5000/api/v1/workers/api_key \
     -H "Content-Type: application/json" \
     -d '{"worker_name": "worker1"}'
```

2. 使用 API Key 启动 worker：
```bash
python work.py --name worker1 --type nvenc --master http://localhost:5000 \
               --transfer-mode http --api-key your_api_key [其他参数]
```

## 注意事项

1. 安全性考虑：
   - HTTP 模式必须配置 API Key
   - API Key 应通过安全渠道传输
   - 建议使用 HTTPS 传输
   - 定期轮换 API Key
   - 记录 API Key 的使用情况

2. 传输模式选择：
   - 内网环境推荐使用 SMB 模式（无需鉴权）
   - 公网环境必须使用 HTTP 模式并配置鉴权
   - 跨网络环境建议使用 HTTP 模式

3. API Key 管理：
   - API Key 存储在数据库中
   - 支持为每个 worker 生成独立的 Key
   - 记录 Key 的创建和最后使用时间
   - 可以随时重新生成 Key

4. 错误处理：
   - 鉴权失败返回 401 错误
   - 记录鉴权失败的日志
   - 多次鉴权失败可能触发临时封禁

5. 性能考虑：
   - SMB 模式适合局域网环境
   - HTTP 模式适合跨网络环境
   - 根据实际网络条件选择合适的模式

6. 文件处理注意事项：
   - 使用 .part 后缀标识未完成的上传
   - 文件移动仅在任务首次完成时执行
   - 文件移动和状态更新在同一事务中
   - 重复的完成状态更新不会触发重复的文件移动 