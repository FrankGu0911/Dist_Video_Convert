REM CPU worker
python -m worker.work --name 3700x_vr --type cpu --master http://192.168.3.13:5333 --prefix \\192.168.3.13 --save hdd\ad_video\transcode --vr --crf 20 --preset slow --num 1

REM NVIDIA worker
python -m worker.work --name 2080_2 --type nvenc --master http://192.168.3.13:5333 --prefix \\192.168.3.13 --save hdd\ad_video\transcode --crf 22 --preset p5 --num 1

REM for linux nvidia, mount hdd to /mnt/hdd first
python -m worker.work --name 2080_2 --type nvenc --master http://192.168.3.13:5333 --prefix /mnt --save hdd/ad_video/transcode --crf 22 --preset p5 --num 1

REM for 2640v4x2 + tesla p4
python -m worker.work --name 2640v4_1 --type cpu --master http://192.168.3.13:5333 --prefix /mnt --save hdd/ad_video/transcode --vr --crf 20 --preset slow --numa 01 --num 1 --start 22:00 --end 06:00
python -m worker.work --name 2640v4_2 --type cpu --master http://192.168.3.13:5333 --prefix /mnt --save hdd/ad_video/transcode --vr --crf 20 --preset slow --numa 10 --start 22:00 --end 06:00
python -m worker.work --name tesla_p4_1 --type nvenc --master http://192.168.3.13:5333 --prefix /mnt --save hdd/ad_video/transcode --crf 22 --preset p6 --hw-decode --ffmpeg /home/frank/code/nvenc_ffmpeg/ffmpeg/ffmpeg
sudo python -m worker.work --name t408_2 --type vpu --master http://192.168.3.13:5333 --prefix /mnt --save hdd/ad_video/transcode --crf 20 --ffmpeg /home/frank/code/t408/V3.5.1/FFmpeg/ffmpeg