# API 接口文档

## 1. Worker 注册接口

### Register_worker
- **接口**: `/api/v1/worker/register`
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


## 2. Worker 心跳接口

### Heartbeat
- **接口**: `/api/v1/worker/heartbeat`
- **方法**: POST
- **请求参数**:
```json
{
    "worker_id": "int",          // worker ID
    "worker_name": "string"      // worker名称
}
```

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string"          // 响应信息
}
```


## 3. 获取新任务接口

### Get_new_task
- **接口**: `/api/v1/task/new`
- **方法**: GET
- **请求参数**:
```json
{
    "worker_id": "int",          // worker ID
    "worker_name": "string"      // worker名称
}
```

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string",         // 响应信息
    "data": {
        "task_id": "string",     // 任务ID
        "video_path": "string",  // 视频路径
        "dest_path": "string"    // 目标路径
    }
}
```


## 4. 更新任务进度接口

### Update_task_progress
- **接口**: `/api/v1/task/progress`
- **方法**: POST
- **请求参数**:
```json
{
    "task_id": "string",         // 任务ID
    "worker_id": "int",          // worker ID
    "progress": "float",         // 转码进度(0-100)
    "status": "int",             // 任务状态: 0:created, 1:running, 2:completed, 3:failed
    "error_message": "string"    // 错误信息(可选，仅在失败时需要)
}
```

- **响应**:
```json
{
    "code": "int",               // 状态码
    "message": "string"          // 响应信息
}
```


## 状态码说明

| 状态码 | 描述 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 注意事项

1. Worker注册后需要每5秒发送一次心跳请求
2. 如果20秒内未收到心跳，Master会将Worker标记为离线状态
3. 任务进度更新建议按照1%的进度间隔进行上报
4. 所有接口的响应都包含基础的code和message字段
5. 任务失败时，需要在update_task_progress接口中提供详细的错误信息 