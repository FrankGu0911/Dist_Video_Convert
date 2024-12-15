# 数据库设计

## 表1: 视频信息表 video_info

| 字段名 | 类型 | 描述 |
| ------ | ---- | ---- |
| id | int | 主键 |
| video_path | varchar(255) | 视频路径 |
| identi | varchar(255) | 番号 |
| codec | varchar(255) | 编码格式 |
| bitrate_k | int | 码率 |
| video_size | float | 视频大小 |
| fps | float | 帧率 |
| resolutionx | int | 分辨率x |
| resolutiony | int | 分辨率y |
| resolutionall | int | 分辨率 |
| is_vr | int | 是否是VR视频 |
| updatetime | datetime | 更新时间 |
| transcode_status | int | 转码状态: 0:not_transcode, 1:wait_transcode, 2:created, 3:running, 4:completed, 5:failed |
| transcode_task_id | int | 转码任务id |

## 表2: 转码任务表 transcode_task

| 字段名 | 类型 | 描述 |
| ------ | ---- | ---- |
| id | int | 主键 |
| task_id | varchar(255) | 任务id |
| worker_name | varchar(255) | 执行任务的worker |
| start_time | datetime | 开始时间 |
| end_time | datetime | 结束时间 |
| task_status | int | 任务状态: 0:created, 1:running, 2:completed, 3:failed |
| progress | int | 任务进度 |
| dest_path | varchar(255) | 转码后的视频路径 |
| video_path | varchar(255) | 原始视频路径 |

## 表3: 转码worker表 transcode_worker

| 字段名 | 类型 | 描述 |
| ------ | ---- | ---- |
| id | int | 主键 |
| worker_name | varchar(255) | worker名称 |
| worker_status | int | worker状态: 0:offline, 1:pending, 2:running, 3:failed |
| worker_type | varchar(255) | worker类型: 0:cpu, 1:nvenc, 2:qsv, 3:vpu |
| support_vr | int | 是否支持VR: 0:no, 1:yes |
| last_heartbeat | datetime | 最后一次心跳时间 |
| current_task_id | int | 当前任务id |

# 表4: 转码任务日志表 transcode_log

| 字段名 | 类型 | 描述 |
| ------ | ---- | ---- |
| id | int | 主键 |
| task_id | int | 任务id |
| log_time | datetime | 日志时间 |
| log_level | int | 日志级别: 0:debug, 1:info, 2:warning, 3:error |
| log_message | varchar(1023) | 日志信息 |


