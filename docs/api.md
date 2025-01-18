# RESTful API 接口文档

## 1. Worker 资源

### 注册 Worker
- **接口**: `/api/v1/workers`
- **方法**: POST
- **请求参数**:
```json
{
    "worker_name": "string",     // worker名称
    "worker_type": "int",        // worker类型: 0:cpu, 1:nvenc, 2:qsv, 3:vpu
    "support_vr": "int"          // 是否支持VR: 0:no, 1:yes
}
```

- **响应**:
```json
{
    "code": "int",               // 状态码: 201-注册成功, 409-Worker已在线
    "message": "string",         // 响应信息
    "data": {
        "worker_id": "int"       // 分配的worker ID
    }
}
```

- **注册机制**:
  1. Worker不存在：直接注册为新Worker
  2. Worker存在但离线：更新为在线状态，清除旧任务和下线指令
  3. Worker存在且在线：
     - 如果心跳超时（30秒）：更新为在线状态，处理旧任务，清除下线指令
     - 如果心跳正常：拒绝注册，返回409错误

- **错误响应**:
```json
{
    "code": 400,
    "message": "参数不完整"
}
```
```json
{
    "code": 409,
    "message": "Worker xxx 已在线，注册失败"
}
```

### 查询 Worker 列表
- **接口**: `/api/v1/workers`
- **方法**: GET
- **请求参数**: 无

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string",         // 响应信息
    "data": [{
        "worker_id": "int",      // worker ID
        "worker_name": "string", // worker名称
        "worker_type": "int",    // worker类型
        "support_vr": "int",     // 是否支持VR
        "status": "int"          // worker状态: 0:离线, 1:在线
    }]
}
```

### 查询单个 Worker
- **接口**: `/api/v1/workers/{worker_id}`
- **方法**: GET
- **请求参数**: 无

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string",         // 响应信息
    "data": {
        "worker_id": "int",      // worker ID
        "worker_name": "string", // worker名称
        "worker_type": "int",    // worker类型
        "support_vr": "int",     // 是否支持VR
        "status": "int"          // worker状态: 0:离线, 1:在线
    }
}
```

### 更新 Worker
- **接口**: `/api/v1/workers/{worker_id}`
- **方法**: PUT
- **请求参数**:
```json
{
    "worker_name": "string",     // worker名称
    "worker_type": "int",        // worker类型
    "support_vr": "int"          // 是否支持VR
}
```

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string"          // 响应信息
}
```

### 删除 Worker
- **接口**: `/api/v1/workers/{worker_id}`
- **方法**: DELETE
- **请求参数**: 无

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string"          // 响应信息
}
```

### Worker心跳
- **接口**: `/api/v1/workers/heartbeat`
- **方法**: POST
- **请求参数**:
```json
{
    "worker_name": "string",      // worker名称
    "worker_id": "int"           // worker ID
}
```

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string"          // 响应信息
}
```

### 设置 Worker 下线
- 请求方法：`POST`
- 请求路径：`/api/v1/workers/{worker_id}/offline`
- 请求参数：
  ```json
  {
    "action": "offline" // 或 "shutdown"，offline表示仅下线，shutdown表示下线并关机
  }
  ```
- 响应示例：
  ```json
  {
    "code": 200,
    "message": "下线指令已发送"
  }
  ```
- 错误响应：
  ```json
  {
    "code": 400,
    "message": "无效的下线动作"
  }
  ```
  ```json
  {
    "code": 404,
    "message": "Worker不存在"
  }
  ```

### 取消 Worker 下线
- 请求方法：`DELETE`
- 请求路径：`/api/v1/workers/{worker_id}/offline`
- 响应示例：
  ```json
  {
    "code": 200,
    "message": "下线指令已取消"
  }
  ```
- 错误响应：
  ```json
  {
    "code": 404,
    "message": "Worker不存在"
  }
  ```

## 2. 任务资源

### 创建任务
- **接口**: `/api/v1/tasks`
- **方法**: POST
- **请求参数**:
```json
{
    "worker_id": "int",          // worker ID
    "worker_type": "int",        // worker类型: 0:cpu, 1:nvenc, 2:qsv, 3:vpu
    "support_vr": "int",         // 是否支持VR: 0:no, 1:yes
    "dest_path": "string"        // 目标路径
}
```

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string",         // 响应信息
    "data": {
        "task_id": "string",     // 任务ID
        "video_path": "string",  // 源视频路径
    }
}
```

### 查询任务列表
- **接口**: `/api/v1/tasks`
- **方法**: GET
- **请求参数**:
```json
{
    "page": "int",                // 页码，默认1
    "per_page": "int",           // 每页记录数，默认20
    "status[]": "int[]",         // 任务状态数组
    "sort_by": "string",         // 排序字段，可选值: start_time, progress, status
    "order": "string"            // 排序方式: asc, desc
}
```

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string",         // 响应信息
    "data": [{
        "task_id": "string",     // 任务ID
        "video_path": "string",  // 视频路径
        "dest_path": "string",   // 目标路径
        "worker_id": "int",      // 处理该任务的worker ID
        "worker_name": "string", // 处理该任务的worker名称
        "progress": "float",     // 转码进度
        "status": "int",         // 任务状态: 0:created, 1:running, 2:completed, 3:failed
        "elapsed_time": "int",   // 已用时间（秒）
        "remaining_time": "int"  // 预计剩余时间（秒）
    }]
}
```

### 获取单个任务
- **接口**: `/api/v1/tasks/{task_id}`
- **方法**: GET
- **请求参数**: 无

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string",         // 响应信息
    "data": {
        "task_id": "string",     // 任务ID
        "video_path": "string",  // 视频路径
        "dest_path": "string",   // 目标路径
        "worker_id": "int",      // 处理该任务的worker ID
        "worker_name": "string", // 处理该任务的worker名称
        "progress": "float",     // 转码进度
        "status": "int",         // 任务状态
        "error_message": "string", // 错误信息(如果有)
        "elapsed_time": "int",   // 已用时间（秒）
        "remaining_time": "int"  // 预计剩余时间（秒）
    }
}
```

### 更新任务状态
- **接口**: `/api/v1/tasks/{task_id}`
- **方法**: PATCH
- **请求参数**:
```json
{
    "worker_id": "int",          // worker ID
    "progress": "float",         // 转码进度(0-100)
    "status": "int",             // 任务状态: 0:created, 1:running, 2:completed, 3:failed
    "error_message": "string",   // 错误信息(可选，仅在失败时需要)
    "elapsed_time": "int",       // 已用时间（秒）
    "remaining_time": "int"      // 预计剩余时间（秒）
}
```

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string"          // 响应信息
}
```

## 3. 视频资源

### 查询视频列表
- **接口**: `/api/v1/videos`
- **方法**: GET
- **请求参数**:
```json
{
    "page": "int",                    // 页码，默认1
    "per_page": "int",               // 每页记录数，默认20
    "transcode_status[]": "int[]",   // 转码状态数组
    "is_vr": "int",                  // 是否VR: 0:no, 1:yes
    "codec[]": "string[]",           // 编码格式数组
    "sort_by": "string",             // 排序字段，可选值: video_path, codec, bitrate_k, resolutionall, video_size, transcode_status, updatetime
    "order": "string"                // 排序方式: asc, desc
}
```

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string",         // 响应信息
    "data": {
        "videos": [{
            "id": "int",            // 视频ID
            "video_path": "string", // 视频路径
            "codec": "string",      // 视频编码
            "bitrate_k": "int",     // 码率(Kbps)
            "video_size": "float",  // 文件大小(MB)
            "fps": "float",         // 帧率
            "resolution": {         // 分辨率
                "width": "int",     // 宽度
                "height": "int"     // 高度
            },
            "is_vr": "int",        // 是否VR视频
            "transcode_status": "int", // 转码状态
            "transcode_task_id": "int", // 转码任务ID
            "update_time": "string"    // 更新时间
        }],
        "pagination": {
            "total": "int",        // 总记录数
            "pages": "int",        // 总页数
            "current_page": "int", // 当前页
            "per_page": "int",     // 每页记录数
            "has_next": "bool",    // 是否有下一页
            "has_prev": "bool"     // 是否有上一页
        }
    }
}
```

## 4. 日志资源

### 查询日志列表
- **接口**: `/api/v1/logs`
- **方法**: GET
- **请求参数**: 
```json
{
    "page": "int",                // 页码，默认1
    "per_page": "int",           // 每页记录数，默认20
    "log_level[]": "int[]",      // 日志级别数组
    "start_time": "string",      // 开始时间 (ISO格式)
    "end_time": "string",        // 结束时间 (ISO格式)
    "sort_by": "string",         // 排序字段，可选值: id, log_time, log_level
    "order": "string"            // 排序方式: asc, desc
}
```

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string",         // 响应信息
    "data": {
        "logs": [{
            "id": "int",            // 日志ID
            "task_id": "int",       // 相关任务ID（如果有）
            "log_time": "string",   // 日志时间
            "log_level": "int",     // 日志级别
            "log_message": "string" // 日志内容
        }],
        "pagination": {
            "total": "int",        // 总记录数
            "pages": "int",        // 总页数
            "current_page": "int", // 当前页
            "per_page": "int",     // 每页记录数
            "has_next": "bool",    // 是否有下一页
            "has_prev": "bool"     // 是否有上一页
        }
    }
}
```

## HTTP状态码说明

| 状态码 | 描述 |
|--------|------|
| 200 | OK - 请求成功 |
| 201 | Created - 资源创建成功 |
| 400 | Bad Request - 请求参数错误 |
| 401 | Unauthorized - 未授权 |
| 404 | Not Found - 资源不存在 |
| 409 | Conflict - 资源冲突 |
| 500 | Internal Server Error - 服务器内部错误 |

## 注意事项

1. Worker注册后需要每5秒发送一次心跳请求
2. 如果30秒内未收到心跳，Master会将Worker标记为离线状态，同时将worker当前正在执行的task状态更新为failed
3. 任务进度更新建议按照1%的进度间隔进行上报
4. 所有接口的响应都包含基础的code和message字段
5. 任务失败时，需要在更新任务状态时提供详细的错误信息
6. 时间相关字段（elapsed_time和remaining_time）单位均为秒
7. 任务完成时remaining_time会被自动设置为0，失败时会被设置为null