# Worker 参数列表
参数名 | 类型 | 描述 | 是否必填 | 备注
worker_name | string | worker名称 | 是 | 
worker_type | int | worker类型 | 是 | 0:cpu, 1:nvenc, 2:qsv, 3:vpu
support_vr | int | 是否支持VR | 是 | 0:no, 1:yes, cpu可支持，其他类型worker即使填1，也会被忽略
master_url | string | master地址 | 是 | 
prefix_path | string | 视频前缀路径 | 是 |
save_path | string | 视频保存路径 | 是 | 表示保存路径，填入!replace时代表替换原视频
crf | int | 视频质量 | 否 | 0-51, cpu+vr时默认20, cpu+no-vr时默认22, qsv+no-vr时默认23, nvenc+no-vr时默认23
preset | string | 视频质量 | 否 |  cpu+vr时默认slow, cpu+no-vr时默认medium, qsv+no-vr时默认slow, nvenc+no-vr时默认slow
rate | int | 视频帧率 | 否 | 默认为空("")即不改变帧率, 可选30,60
numa_param | string | numa参数 | 否 | 只在cpu时有效，默认为None，例：4numa时想使用node2，则填"-,-,+,-"
thread | int | 线程数 | 否 | 只在cpu时有效，默认None表示不指定，由ffmpeg自行决定
remove_original | int | 是否删除原视频 | 否 | 0:不删除, 1:删除, 默认不删除
num | int | 转码个数 | 否 | 默认-1，表示不限制
