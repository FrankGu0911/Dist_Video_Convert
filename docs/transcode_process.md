# 转码任务分配流程

## 1. Master上线，启动扫描指定目录视频的定时任务（30min一次），并落库

## 2. Worker启动，调用Register_worker接口，注册到Master

## 3. Master收到Register_worker请求，更新worker数据库，并返回Register_worker响应，worker收到响应后，开启5s一次的heartbeat，

## 4. Worker请求获取新任务，调用Get_new_task接口

## 5. Master收到Get_new_task请求，匹配符合worker条件，并未在转码的视频（暂时只有是否vr一个条件，默认cpu的worker可以vr，其他类型worker不可以），创建新任务，记录到任务数据库，修改视频状态，修改worker状态，返回Get_new_task响应

## 6. Worker收到Get_new_task响应，根据相对路径与前缀找到视频，启动ffmpeg转码，并更新进度到更新进度的接口

## 7. Master收到更新进度的接口，更新任务数据库，并更新视频状态

## 8. Worker完成转码后，调用更新进度的接口，更新成任务完成

## 9. Master收到更新进度的接口，更新任务数据库，并更新视频状态

## 10. Worker根据本地参数（转码几次，或者当前时间）判断需不需要继续，如果需要，则调用Get_new_task接口，获取新任务，循环

# 错误处理机制

## 1. 如果worker在20s内没有收到heartbeat，则认为worker挂了，将worker状态改为offline，并标记task失败，同步到视频数据库，任务数据库

## 2. 如果worker在转码过程中，出现错误，worker调用更新任务状态接口，并上报错误信息，master将task状态改为failed，同步到视频数据库，任务数据库

# 状态转换说明

## 1. 视频状态：
0:not_transcode 不需要转码, 
1:wait_transcode->2:created->3:running->4:completed/5:failed

## 2. worker状态：
0:offline->1:pending(等待任务)->2:running(执行任务)->1:pending(完成后，等待任务)/3:failed(执行失败)

## 3. task状态：
0:created->1:running->2:completed/3:failed


