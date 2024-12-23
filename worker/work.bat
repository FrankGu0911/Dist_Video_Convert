REM CPU worker
python -m worker.work --name 3700x_vr --type cpu --master http://192.168.3.13:5333 --prefix \\192.168.3.13 --save hdd\ad_video\transcode --vr --crf 20 --preset slow --num 1

REM NVIDIA worker
python -m worker.work --name 2080_2 --type nvenc --master http://192.168.3.13:5333 --prefix \\192.168.3.13 --save hdd\ad_video\transcode --crf 22 --preset p5 --num 1

REM for linux nvidia, mount hdd to /mnt/hdd first
python -m worker.work --name 2080_2 --type nvenc --master http://192.168.3.13:5333 --prefix /mnt --save hdd/ad_video/transcode --crf 22 --preset p5 --num 1
