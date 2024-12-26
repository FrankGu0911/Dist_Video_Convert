#!/bin/bash

# 启动所有worker并记录PID
python -m worker.work --name 2640v4_1 --type cpu --master http://192.168.3.13:5333 --prefix /mnt --save hdd/ad_video/transcode --vr --crf 20 --preset slow --numa -,+ --start 22:00 --end 06:00 --shutdown &
PID1=$!

python -m worker.work --name 2640v4_2 --type cpu --master http://192.168.3.13:5333 --prefix /mnt --save hdd/ad_video/transcode --vr --crf 20 --preset slow --numa -,+ --start 22:00 --end 06:00 --shutdown &
PID2=$!

python -m worker.work --name tesla_p4_1 --type nvenc --master http://192.168.3.13:5333 --prefix /mnt --save hdd/ad_video/transcode --crf 22 --preset p6 --hw-decode --start 22:00 --end 06:00 --shutdown &
PID3=$!

echo "已启动所有worker进程"
echo "Worker 2640v4_1 PID: $PID1"
echo "Worker 2640v4_2 PID: $PID2"
echo "Worker tesla_p4_1 PID: $PID3"

# 等待所有进程完成
wait $PID1 $PID2 $PID3

# 所有进程都结束后关机
echo "所有worker已完成，1分钟后关机..."
shutdown -h +1 