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
    "code": "int",               // 状态码
    "message": "string",         // 响应信息
    "data": {
        "worker_id": "int"       // 分配的worker ID
    }
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

### 获取任务列表
- **接口**: `/api/v1/tasks`
- **方法**: GET
- **请求参数**: 
```
status (可选): 任务状态过滤
worker_id (可选): worker ID过滤
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