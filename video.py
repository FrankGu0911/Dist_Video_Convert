import os,time
import ffmpeg
from tqdm import tqdm
import logging
import subprocess
import re
from datetime import datetime

class Video:
    def __init__(self, video_path):
        self.video_path = video_path
        if not os.path.exists(video_path):
            raise FileNotFoundError("File not found: %s" % video_path)
        self.vr_code = ['SIVR','IPVR','DSVR','KAVR','MDVR','RSRVR','SSR','VR',"FSVSS"]
        self.exclusion_vr_code = ['DVRT']
        self.video_info = self.get_video_info(video_path)
        self.video_codec = self.video_info['streams'][0]['codec_name']
        
        # 处理bit_rate不存在的情况，按优先级尝试不同来源
        try:
            # 1. 首先尝试从视频流中获取bit_rate
            self.video_bitrate = int(self.video_info['streams'][0]['bit_rate'])
        except (KeyError, TypeError):
            try:
                # 2. 尝试从视频流的tags中获取BPS
                self.video_bitrate = int(self.video_info['streams'][0]['tags']['BPS'])
            except (KeyError, TypeError):
                try:
                    # 3. 尝试从format中获取bit_rate
                    self.video_bitrate = int(self.video_info['format']['bit_rate'])
                except (KeyError, TypeError):
                    try:
                        # 4. 如果还是获取不到，使用文件大小和时长估算
                        file_size = os.path.getsize(video_path)  # 字节
                        duration = float(self.video_info['format']['duration'])  # 秒
                        self.video_bitrate = int((file_size * 8) / duration)  # 比特/秒
                    except (KeyError, TypeError, ZeroDivisionError):
                        # 5. 如果还是无法计算，设置为0
                        logging.warning(f"无法获取视频比特率，设置为0: {video_path}")
                        self.video_bitrate = 0
        
        self.video_resolution = (int(self.video_info['streams'][0]['width']), int(self.video_info['streams'][0]['height']))
        
        # 处理duration不存在的情况，按优先级尝试不同来源
        try:
            # 1. 首先尝试从视频流中获取duration
            self.video_duration = float(self.video_info['streams'][0]['duration'])
        except (KeyError, TypeError):
            try:
                # 2. 尝试从视频流的tags中获取DURATION
                duration_str = self.video_info['streams'][0]['tags']['DURATION']
                # 处理类似 "02:43:56.569000000" 格式的时间
                h, m, s = duration_str.split(':')
                self.video_duration = float(h) * 3600 + float(m) * 60 + float(s)
            except (KeyError, TypeError, ValueError):
                try:
                    # 3. 尝试从format中获取duration
                    self.video_duration = float(self.video_info['format']['duration'])
                except (KeyError, TypeError):
                    logging.warning(f"无法获取视频时长，设置为0: {video_path}")
                    self.video_duration = 0
        
        num, den = map(int, self.video_info['streams'][0]['avg_frame_rate'].split('/'))
        self.video_fps = num / den
        self.video_size = os.path.getsize(video_path)
        self.video_name = os.path.basename(video_path)
        self.video_folder = os.path.dirname(video_path)
        self.video_extension = os.path.splitext(video_path)[1]
        self.video_name_noext = os.path.splitext(self.video_name)[0]
        self.is_vr = self.JudgeVR()
        self.identi = self.GetIdentify()
        if self.identi is None:
            raise Exception("%s Identify not found" % self.video_name)
        
    def __str__(self):
        return "Video: %s, Codec: %s, Bitrate: %s, Resolution: %s, Duration: %s, Size: %s, fps: %s" % (self.video_name, self.video_codec, self.convert_bitrate(self.video_bitrate), self.video_resolution, self.video_duration, self.video_size, round(self.video_fps,2))
    
    @staticmethod
    def convert_bitrate(bitrate, unit="", dec=3, seprate=True):
    # convert bitrate to human readable format
        unit_list = ["K", "M", "G", "T"]
        if unit.upper() == "K" or unit.upper() == "KBPS":
            bitrate = bitrate/1000
            unit = "Kbps"
        elif unit.upper() == "M" or unit.upper() == "MBPS":
            bitrate = bitrate/1000000
            unit = "Mbps"
        elif unit.upper() == "G" or unit.upper() == "GBPS":
            bitrate = bitrate/1000000000
            unit = "Gbps"
        elif unit.upper() == "T" or unit.upper() == "TBPS":
            bitrate = bitrate/1000000000000
            unit = "Tbps"
        elif unit=="":
            while bitrate > 10000:
                bitrate /= 1000
                unit = unit_list.pop(0)
            unit = unit + "bps"
        if seprate:
            return int(bitrate), unit
        else:
            return f'{bitrate:.{dec}f}{unit}'

    @staticmethod
    def get_video_info(video_path):
        try:
            return ffmpeg.probe(video_path)
        except ffmpeg.Error as e:
            print(e.stderr)
            raise e
    
    @staticmethod
    def get_video_pathlist_from_path(video_path, exclude_trailer=True, include_substitle=False):
        # get all video files from a folder
        video_path_list = []
        logging.info("Scanning video files from %s" % video_path)
        for root, dirs, files in os.walk(video_path):
            for file in files:
                if '-trailer' in file and exclude_trailer:
                    continue
                if include_substitle:
                    if file.endswith(".srt") or file.endswith(".ass") or file.endswith(".ssa"):
                        video_path_list.append(os.path.join(root, file))
                if file.endswith(".mp4") or file.endswith(".mkv") or file.endswith(".avi") or file.endswith(".flv"):
                    video_path_list.append(os.path.join(root, file))
        return video_path_list

    @staticmethod
    def are_paths_same(path1, path2):
        return os.path.abspath(path1) == os.path.abspath(path2)

    @staticmethod  
    def GetTimeFromString(time_str: str, sep=":", usems=False):
        try:
            if not time_str or not isinstance(time_str, str):
                logging.error(f"无效的时间字符串: {time_str}")
                return 0
                
            time_parts = time_str.split(sep)
            if len(time_parts) != 3:
                logging.error(f"时间格式错误，应为HH:MM:SS格式: {time_str}")
                return 0
                
            # 确保所有部分都是有效的数字
            h = time_parts[0].strip()
            m = time_parts[1].strip()
            s = time_parts[2].strip()
            
            if not (h and m and s):
                logging.error(f"时间部分包含空值: h={h}, m={m}, s={s}")
                return 0
                
            if usems:
                return int(h)*3600000 + int(m)*60000 + int(float(s)*1000)
            else:
                return int(h)*3600 + int(m)*60 + int(float(s))
        except (ValueError, IndexError, TypeError) as e:
            logging.error(f"解析时间字符串时出错: {str(e)}, 输入: {time_str}")
            return 0

    def convert_video_with_progress(self, cmd, progress_callback=None): 
        try:
            loggingfile_name = "logs/ffmpeglog-%s-%s.txt" % (self.video_name_noext, time.strftime("%Y-%m-%d-%H-%M", time.localtime()))
            # 使用 errors='replace' 来处理无法解码的字符
            loggingfile = open(loggingfile_name, "w", encoding='utf-8', errors='replace')
            loggingfile = open(loggingfile_name, "a+", encoding='utf-8', errors='replace')
            loggingread = open(loggingfile_name, "r", encoding='utf-8', errors='replace')
            p = subprocess.Popen(cmd, shell=True, stdout=loggingfile, stderr=loggingfile)
            duration = -1
            
            def clean_log_line(line):
                try:
                    # 移除ANSI转义序列
                    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                    line = ansi_escape.sub('', line)
                    # 移除控制字符
                    line = ''.join(char for char in line if ord(char) >= 32 or char == '\n')
                    return line.strip()
                except Exception as e:
                    logging.warning(f"清理日志行时出错: {str(e)}")
                    return ""
            
            # 尝试获取视频时长
            try:
                while duration == -1 and p.poll() is None:
                    log = loggingread.readline()
                    if not log:
                        time.sleep(0.1)
                        continue
                        
                    log = clean_log_line(log)
                    if not log:
                        continue
                        
                    if "Duration:" in log:
                        try:
                            duration_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', log)
                            if duration_match:
                                h, m, s = duration_match.groups()
                                duration_str = f"{h}:{m}:{s}"
                                duration = self.GetTimeFromString(duration_str)
                                duration_ms = self.GetTimeFromString(duration_str, usems=True)
                                logging.info(f"Duration解析成功: {duration}s ({duration_ms}ms)")
                            else:
                                logging.warning(f"无法从行中解析Duration: {log}")
                                continue
                        except Exception as e:
                            logging.warning(f"解析Duration时出错: {str(e)}")
                            continue
                
                if duration == -1:
                    logging.warning("无法获取视频时长，将不显示进度条")
                    # 如果获取不到时长，就只记录日志
                    while p.poll() is None:
                        log = loggingread.readline()
                        if log:
                            logging.info(clean_log_line(log))
                else:
                    # 显示进度条
                    try:
                        with tqdm(total=duration_ms, desc="Converting %s" % self.video_name) as pbar:
                            while p.poll() is None:
                                try:
                                    log = loggingread.readline()
                                    if not log:
                                        time.sleep(0.1)
                                        continue
                                        
                                    log = clean_log_line(log)
                                    if not log:
                                        continue
                                        
                                    if "time=" in log:
                                        try:
                                            time_match = re.search(r'time=\s*(\d+):(\d+):(\d+\.\d+)', log)
                                            if time_match:
                                                h, m, s = time_match.groups()
                                                timestr = f"{h}:{m}:{s}"
                                                timems = self.GetTimeFromString(timestr, usems=True)
                                                if 0 <= timems <= duration_ms:
                                                    progress = (timems / duration_ms) * 100
                                                    pbar.update(timems - pbar.n)
                                                    if progress_callback:
                                                        try:
                                                            elapsed_time = pbar.format_dict['elapsed']
                                                            its = pbar.format_dict['rate']
                                                            remain = pbar.format_dict['total'] - pbar.format_dict['n']
                                                            remaining_time = remain/its if its and its > 0 else None
                                                            progress_callback(progress, elapsed_time, remaining_time)
                                                        except Exception as e:
                                                            logging.warning(f"回调进度时出错: {str(e)}")
                                        except Exception as e:
                                            logging.warning(f"处理时间信息时出错: {str(e)}")
                                            continue
                                            
                                    if "bitrate=" in log:
                                        try:
                                            bitrate_match = re.search(r'bitrate=\s*([\d.]+\s*\w+)', log)
                                            if bitrate_match:
                                                bitrate = bitrate_match.group(1)
                                                pbar.set_postfix_str("Bitrate: %s" % bitrate)
                                        except Exception as e:
                                            logging.warning(f"处理比特率信息时出错: {str(e)}")
                                            continue
                                except Exception as e:
                                    logging.warning(f"处理进度信息时出错: {str(e)}")
                                    continue
                            
                            # 确保进度条到达100%
                            try:
                                if pbar.n < duration_ms:
                                    pbar.update(duration_ms - pbar.n)
                                if progress_callback:
                                    progress_callback(100, pbar.format_dict['elapsed'], 0)
                            except Exception as e:
                                logging.warning(f"更新最终进度时出错: {str(e)}")
                    except Exception as e:
                        logging.warning(f"显示进度条时出错: {str(e)}")
                        # 如果进度条显示出错，继续读取输出直到结束
                        while p.poll() is None:
                            log = loggingread.readline()
                            if log:
                                logging.info(clean_log_line(log))
            except Exception as e:
                logging.warning(f"处理ffmpeg输出时出错: {str(e)}")
                # 确保进程继续运行到结束
                p.wait()

            if p.returncode != 0:
                raise Exception("Error in ffmpeg")
            
            loggingfile.write("=================%s Done=================\n" % self.video_name)
            loggingfile.close()
            loggingread.close()
                        
        except Exception as e:
            logging.error(f"转码过程中出错: {str(e)}")
            p.kill()
            raise e
        
        return p.returncode

    def check_output_path(self, output_folder):
        if output_folder is None or self.are_paths_same(output_folder, self.video_folder):
            output_folder = self.video_folder
            output_path = os.path.join(output_folder, self.video_name_noext + "_h265.mp4")
        else:
            output_path = os.path.join(output_folder, self.video_name)
        return output_path

    @staticmethod
    def check_nvidia_capabilities():
        """检查NVIDIA显卡的架构和能力
        
        Returns:
            dict: 包含显卡信息的字典，包括：
                - arch: 架构代号（如 Pascal, Turing, Ampere 等）
                - supports_b_ref: 是否支持 b_ref_mode
                - supports_aq: 是否支持自适应量化
        """
        try:
            import subprocess
            result = subprocess.run(['nvidia-smi', '--query-gpu=gpu_name,compute_cap', '--format=csv,noheader'], 
                                 capture_output=True, text=True)
            if result.returncode != 0:
                logging.warning("无法获取NVIDIA显卡信息，将使用基本特性")
                return {'arch': 'unknown', 'supports_b_ref': False, 'supports_aq': False}
            
            # 解析输出
            gpu_info = result.stdout.strip().split(',')
            if len(gpu_info) < 2:
                logging.warning("无法解析NVIDIA显卡信息，将使用基本特性")
                return {'arch': 'unknown', 'supports_b_ref': False, 'supports_aq': False}
            
            gpu_name = gpu_info[0].strip()
            compute_cap = gpu_info[1].strip()
            
            # 根据计算能力判断架构
            # 参考：https://developer.nvidia.com/cuda-gpus
            compute_cap = float(compute_cap)
            if compute_cap >= 8.6:  # Ada Lovelace (RTX 40系列)
                arch = 'Ada'
                supports_b_ref = True
                supports_aq = True
            elif compute_cap >= 8.0:  # Ampere (RTX 30系列)
                arch = 'Ampere'
                supports_b_ref = True
                supports_aq = True
            elif compute_cap >= 7.5:  # Turing (RTX 20系列, GTX 16系列)
                arch = 'Turing'
                supports_b_ref = True
                supports_aq = True
            elif compute_cap >= 6.0:  # Pascal (GTX 10系列)
                arch = 'Pascal'
                supports_b_ref = False
                supports_aq = True
            else:  # 更老的架构
                arch = 'Legacy'
                supports_b_ref = False
                supports_aq = False
            
            logging.info(f"检测到NVIDIA显卡: {gpu_name} (架构: {arch})")
            return {
                'arch': arch,
                'supports_b_ref': supports_b_ref,
                'supports_aq': supports_aq
            }
        except Exception as e:
            logging.warning(f"检测NVIDIA显卡能力时出错: {str(e)}，将使用基本特性")
            return {'arch': 'unknown', 'supports_b_ref': False, 'supports_aq': False}

    def build_ffmpeg_command(self, codec_params):
        """构建ffmpeg命令
        
        Args:
            codec_params (dict): 编码参数字典，必须包含以下键：
                - codec: 编码器名称 (如 'hevc_qsv', 'hevc_nvenc', 'libx265', 'libsvtav1')
                - output_path: 输出文件路径
                其他可选参数：
                - global_quality: QSV的质量参数
                - qmin: NVENC的最小量化参数
                - crf: libx265和av1的CRF值
                - preset: 预设值
                - rate: 帧率
                - extra_params: 额外的编码参数字典
                - hw_decode: 是否启用硬件解码，默认False
                - ffmpeg_path: ffmpeg可执行文件路径，默认为'ffmpeg'
        
        Returns:
            str: 完整的ffmpeg命令
        """
        codec = codec_params['codec']
        output_path = codec_params['output_path']
        hw_decode = codec_params.get('hw_decode', False)
        ffmpeg_path = codec_params.get('ffmpeg_path', 'ffmpeg')
        
        # 根据编码器和硬件解码设置选择解码参数
        if hw_decode:
            if codec == 'hevc_nvenc':
                base_cmd = '%s -y -hwaccel cuda -hwaccel_output_format cuda -i "%s"' % (ffmpeg_path, self.video_path)
            elif codec == 'hevc_qsv':
                base_cmd = '%s -y -hwaccel qsv -i "%s"' % (ffmpeg_path, self.video_path)
            else:
                logging.warning("使用CPU编码时不建议启用硬件解码，将使用软解码")
                base_cmd = '%s -y -i "%s"' % (ffmpeg_path, self.video_path)
        else:
            base_cmd = '%s -y -i "%s"' % (ffmpeg_path, self.video_path)
        
        # 编码器特定参数
        encode_params = []
        
        if codec == 'hevc_qsv':
            encode_params.extend([
                '-c:v hevc_qsv',
                '-preset %s' % codec_params.get('preset', 'medium'),
                '-global_quality %d' % codec_params.get('global_quality', 23),
                '-look_ahead 1',
                '-look_ahead_depth 40'
            ])
        
        elif codec == 'hevc_nvenc':
            # 检查显卡能力
            gpu_caps = self.check_nvidia_capabilities()
            
            # 获取基础质量参数
            target_quality = codec_params.get('qmin', 23)
            qmin = max(1, target_quality - 2)  # 确保qmin不小于1
            qmax = min(51, target_quality + 2)  # 确保qmax不超过51
            
            encode_params.extend([
                '-c:v hevc_nvenc',
                '-preset %s' % codec_params.get('preset', 'p5'),
                '-rc vbr',
                '-tune hq',
                '-qmin %d' % qmin,
                '-qmax %d' % qmax,
                '-rc-lookahead 32'
            ])
            
            # 添加maxrate参数（如果提供）
            if 'maxrate' in codec_params:
                encode_params.extend([
                    '-maxrate %d' % codec_params['maxrate'],
                    '-bufsize %d' % (codec_params['maxrate'] * 2)  # 设置缓冲区大小为maxrate的2倍
                ])
            
            # 根据显卡能力添加高级特性
            if gpu_caps['supports_b_ref']:
                encode_params.append('-b_ref_mode each')
            
            if gpu_caps['supports_aq']:
                encode_params.extend([
                    '-spatial_aq 1',
                    '-aq-strength 8'
                ])
                
            encode_params.extend([
                '-profile:v main',
                '-level 5.2'
            ])
        
        elif codec == 'libx265':
            numa_param = codec_params.get('numa_param')
            x265_params = []
            
            # 如果是VR视频，添加特殊的优化参数
            if self.is_vr:
                x265_params.extend([
                    'aq-mode=2',
                    'psy-rd=2.5',
                    'psy-rdoq=1.5',
                    'rc-lookahead=50',
                    'qcomp=0.7',
                    'profile=main',
                    'level=5.1'
                ])
            
            # 添加NUMA参数（如果有）
            if numa_param:
                x265_params.append('pools="%s"' % numa_param)
            
            # 组合所有x265参数
            if x265_params:
                encode_params.append('-x265-params "%s"' % ':'.join(x265_params))
                
            encode_params.extend([
                '-c:v libx265',
                '-crf %d' % codec_params.get('crf', 22),
                '-preset %s' % codec_params.get('preset', 'medium')
            ])
        
        elif codec == 'libsvtav1':
            encode_params.extend([
                '-c:v libsvtav1',
                '-crf %d' % codec_params.get('crf', 30),
                '-preset %d' % codec_params.get('preset', 8),
                '-pix_fmt yuv420p',
                '-g 240',
                '-svtav1-params "tune=0:lookahead=120"'
            ])
        
        elif codec == 'hevc_ni_logan':
            # VPU编码器参数
            encode_params.extend([
                '-c:v h265_ni_logan_enc',
                '-b:v %d' % codec_params.get('bitrate', 4500000)  # 默认4.5Mbps
            ])
            
            # 构建xcoder-params
            xcoder_params = [
                'RcEnable=1',
                'hvsQPEnable=1',
                'hvsQpScale=2',
                'RcInitDelay=3000',
                'decodingRefreshType=2',
                'repeatHeaders=1'
            ]
            
            # 如果指定了crf，使用crf模式
            if 'crf' in codec_params:
                crf = codec_params['crf']
                xcoder_params.extend([
                    f'crf={crf}',
                    f'minQp={max(1, crf - 2)}',  # crf值减2，但不小于1
                    f'maxQp={min(51, crf + 2)}'  # crf值加2，但不大于51
                ])
            
            # 添加自定义xcoder参数
            custom_xcoder_params = codec_params.get('xcoder_params', {})
            for key, value in custom_xcoder_params.items():
                xcoder_params.append(f'{key}={value}')
            
            encode_params.append('-xcoder-params "%s"' % ':'.join(xcoder_params))
            
            # VPU必须启用硬件解码
            if not codec_params.get('hw_decode', True):
                logging.warning("VPU编码必须启用硬件解码，已自动启用")
            
            # 根据输入视频格式选择解码器
            input_codec = self.video_codec.lower()
            if input_codec == 'h264':
                decoder = 'h264_ni_logan_dec'
            elif input_codec in ['hevc', 'h265']:
                decoder = 'h265_ni_logan_dec'
            else:
                raise ValueError(f"VPU编码器不支持的输入视频编码格式: {input_codec}，仅支持H.264和HEVC/H.265格式")
            
            # 添加解码器参数
            base_cmd = base_cmd.replace('-i', f'-c:v {decoder} -i')
        
        # 通用参数
        rate = codec_params.get('rate')
        if rate:
            if isinstance(rate, int):
                rate = str(rate)
            if rate.isdigit():
                encode_params.append('-r %s' % rate)
        
        # 额外参数
        extra_params = codec_params.get('extra_params', {})
        for key, value in extra_params.items():
            if value is not None:
                encode_params.append(f'-{key} {value}')
        
        # 音频编码（默认复制）
        encode_params.append('-c:a copy')
        
        # 组装完整命令
        return '%s %s "%s"' % (base_cmd, ' '.join(encode_params), output_path)

    def convert_to_hevc_qsv(self, global_quality=23, preset="medium", rate="", output_folder=None, remove_original=False, progress_callback=None, hw_decode=False):
        output_path = self.check_output_path(output_folder)
        logging.info("Converting %s to h265 with global_quality %s" % (self.video_name, global_quality))
        logging.info("Output file: %s" % output_path)
        
        try:
            cmd = self.build_ffmpeg_command({
                'codec': 'hevc_qsv',
                'output_path': output_path,
                'global_quality': global_quality,
                'preset': preset,
                'rate': rate,
                'hw_decode': hw_decode
            })
            logging.info(cmd)
            self.convert_video_with_progress(cmd, progress_callback)
        except Exception as e:
            print(e)
            raise e
        if remove_original:
            os.remove(self.video_path)

    def convert_to_hevc_nvenc(self, qmin=23, preset="p5", rate='', output_folder=None, remove_original=False, progress_callback=None, hw_decode=False):
        output_path = self.check_output_path(output_folder)
        logging.info("Converting %s to h265 with NVENC (qmin=%s, preset=%s)" % (self.video_name, qmin, preset))
        logging.info("Output file: %s" % output_path)
        
        # 预设值映射
        preset_mapping = {
            'veryfast': 'p1',
            'faster': 'p2',
            'fast': 'p3',
            'medium': 'p4',
            'slow': 'p5',
            'slower': 'p6',
            'veryslow': 'p7'
        }
        
        # 处理预设值
        if preset.lower() in preset_mapping:
            preset = preset_mapping[preset.lower()]
        elif preset.lower() in ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']:
            preset = preset.lower()
        else:
            logging.warning(f"未知的预设值: {preset}，使用默认值p5")
            preset = 'p5'
            
        try:
            cmd = self.build_ffmpeg_command({
                'codec': 'hevc_nvenc',
                'output_path': output_path,
                'qmin': qmin,
                'preset': preset,
                'rate': rate,
                'hw_decode': hw_decode
            })
            logging.info(cmd)
            self.convert_video_with_progress(cmd, progress_callback)
        except Exception as e:
            print(e)
            raise e
            
        if remove_original:
            os.remove(self.video_path)

    def convert_to_h265(self, crf=22, preset="medium", rate="", output_folder=None, remove_original=False, numa_param:str=None, progress_callback=None, hw_decode=False):
        output_path = self.check_output_path(output_folder)
        logging.info("Converting %s to h265 with crf %s" % (self.video_name, crf))
        logging.info("Output file: %s" % output_path)
        
        try:
            cmd = self.build_ffmpeg_command({
                'codec': 'libx265',
                'output_path': output_path,
                'crf': crf,
                'preset': preset,
                'rate': rate,
                'numa_param': numa_param,
                'hw_decode': hw_decode
            })
            logging.info(cmd)
            self.convert_video_with_progress(cmd, progress_callback)
        except Exception as e:
            print(e)
            raise e
        if remove_original:
            os.remove(self.video_path)

    def convert_to_av1(self, crf=30, preset=8, output_folder=None, remove_original=False, progress_callback=None, hw_decode=False): 
        output_path = self.check_output_path(output_folder)
        logging.info("Converting %s to av1 with crf %s, preset %s" % (self.video_name, crf, preset))
        logging.info("Output file: %s" % output_path)
        
        try:
            cmd = self.build_ffmpeg_command({
                'codec': 'libsvtav1',
                'output_path': output_path,
                'crf': crf,
                'preset': preset,
                'hw_decode': hw_decode
            })
            logging.info(cmd)
            self.convert_video_with_progress(cmd, progress_callback)
        except Exception as e:
            print(e)
            raise e
        if remove_original:
            os.remove(self.video_path)
    
    def move(self, dest_folder, new_name=""):
        if new_name == "":
            new_name = self.video_name
        if dest_folder.endswith(".mp4") or dest_folder.endswith(".mkv") or dest_folder.endswith(".avi") or dest_folder.endswith(".srt") or dest_folder.endswith(".ass") or dest_folder.endswith(".ssa"):
            dest_path = dest_folder
        else:
            dest_path = os.path.join(dest_folder, new_name)
        logging.info("Moving %s to %s" % (self.video_name, dest_path))
        os.rename(self.video_path, dest_path)
        self.video_path = dest_path

    def copy(self, dest_folder, new_name=""):
        if new_name == "":
            new_name = self.video_name
        dest_path = os.path.join(dest_folder, self.video_name)
        os.copy(self.video_path, dest_path)
        return Video(dest_path)
    
    def JudgeVR(self):
        is_vr = False
        for i in self.vr_code:
            if i in self.video_name.upper():
                is_vr = True
                break
        for i in self.exclusion_vr_code:
            if i in self.video_name.upper():
                is_vr = False
                break
        return is_vr

    def GetIdentify(self):
        if self.is_vr:
            patterns_vr_code = [
                (re.compile(r'[A-Za-z]+-[\d]+'),'-'),
                (re.compile(r'[A-Za-z]+00[\d]+'),'00')
            ]
            video_name = self.video_name_noext.replace(' ','').replace('_','-')
            tmp_filename = ''
            av_code_dash = ''
            av_code_list = []
            for pattern_vr_code in patterns_vr_code:
                if pattern_vr_code[0].search(video_name):
                    av_code = pattern_vr_code[0].search(video_name).group()
                    av_code_list = av_code.upper().split(pattern_vr_code[1])
                    av_code_dash = av_code_list[0]+'-'+av_code_list[1]
                    tmp_filename = video_name.replace(av_code,av_code_dash)
            if tmp_filename == '':
                logging.warning("File name not match: %s" % self.video_name)
                return None
            tmp_filename = tmp_filename.split(av_code_dash)
            if len(tmp_filename) != 2:
                return av_code_dash
            if tmp_filename[1] == '':
                return av_code_dash
            patterns_cd_num = [
                (re.compile(r'part[\d]+'),'part'),
                (re.compile(r'pt[\d]+'),'pt'),
                (re.compile(r'cd[\d]+'),'cd'),
                (re.compile(r'CD[\d]+'),'CD'),
                (re.compile(r'hia[\d]+'),'hia'),
                # (re.compile(r'-[\d]+^'),'-'),
                (re.compile(r'-[\d]+-?'),'-'),
                (re.compile(r'-[A-z]+'),'-'),
                (re.compile(r'[A-z]+'),''),
            ]
            cd_num = ''
            for pattern_cd_num in patterns_cd_num:
                if pattern_cd_num[0].search(tmp_filename[1]):
                    cd_num = pattern_cd_num[0].search(tmp_filename[1]).group()
                    cd_num = cd_num.upper()
                    cd_num = cd_num.replace(pattern_cd_num[1].upper(),'')
                    # 移除对cd_num长度的限制，允许多位数字
                    if cd_num.isdigit():
                        cd_num = 'CD' + cd_num
                    elif len(cd_num) == 1 and ord('A') <= ord(cd_num) <= ord('Z'):
                        cd_num = 'CD' + str(ord(cd_num) - ord('A') + 1)
                    else:
                        logging.warning("Invalid CD number format: %s" % cd_num)
                        continue
                    break
            if cd_num == '':
                logging.warning("File name not match: %s" % self.video_name)
                return None
            return '%s-%s-%s' %(av_code_list[0],av_code_list[1],cd_num)
        else:
            pattern = re.compile(r'[A-Za-z]+-[\d]+')
            avstr = self.video_name_noext.replace(' ','')
            try:
                av_code = pattern.search(avstr).group()
            except Exception as e:
                if avstr == 'dcol022':
                    av_code = 'DCOL-022'
                elif avstr == 'T28-630':
                    av_code = 'T28-630'
                elif avstr == 'T28-625':
                    av_code = 'T28-625'
                elif avstr == 'T28-633':
                    av_code = 'T28-633'
                else:
                    print(e,avstr)
                    print("No av code found")
                    raise e
            return av_code.upper()

    def ModifyName(self):
        is_vr = False
        for i in self.vr_code:
            if i in self.video_name.upper():
                is_vr = True
                break
        for i in self.exclusion_vr_code:
            if i in self.video_name.upper():
                is_vr = False
                break
        if is_vr:
            new_name = self.ModifyVRName()
        else:
            new_name = self.ModifyAVName()
        if new_name == None:
            return None
        else:
            return new_name

    def ModifyVRName(self):
        if self.identi is None:
            raise Exception("VR Identify not found")
        return self.identi+self.video_extension

    def ModifyAVName(self):
        if self.identi is None:
            raise Exception("AV Identify not found")
        if ('6K-C' in self.video_name) or ('3K-C' in self.video_name) or ('2K-C' in self.video_name):
            return self.identi+'-C'+self.video_extension
        elif 'X1080X' in self.video_name:
            return self.identi+'-C'+self.video_extension
        elif 'SEX8.CC' in self.video_name:
            return self.identi+'-C'+self.video_extension
        elif '-C' in self.video_name:
            return self.identi+'-C'+self.video_extension
        elif '-UC' in self.video_name:
            return self.identi+'-C-hack'+self.video_extension
        elif '-U' in self.video_name:
            return self.identi+'-hack'+self.video_extension
        elif '4K' in self.video_name.upper():
            return self.identi+'-4K'+self.video_extension
        elif ('rh2048.com' in self.video_name) or ('hhd800.com@' in self.video_name):
            return self.identi+self.video_extension
        else:
            return self.identi+self.video_extension

    def convert_to_hevc_vpu(self, crf=20, bitrate=4500000, output_folder=None, remove_original=False, progress_callback=None, hw_decode=True, xcoder_params=None):
        """使用VPU将视频转换为HEVC/H.265格式
        
        Args:
            crf (int): CRF值，控制视频质量，默认20
            bitrate (int): 目标比特率，单位bps，默认4.5Mbps
            output_folder (str): 输出文件夹路径，默认为None（使用源文件夹）
            remove_original (bool): 是否删除原始文件，默认False
            progress_callback (callable): 进度回调函数，默认None
            hw_decode (bool): 是否启用硬件解码，默认True（注意：VPU编码必须启用硬件解码，此参数将被忽略）
            xcoder_params (dict): 额外的xcoder参数，默认None
        """
        if not hw_decode:
            logging.warning("VPU编码必须启用硬件解码，已忽略hw_decode=False设置")
            hw_decode = True
            
        output_path = self.check_output_path(output_folder)
        logging.info("Converting %s to h265 with VPU (crf=%s, bitrate=%s)" % (self.video_name, crf, bitrate))
        logging.info("Output file: %s" % output_path)
        
        try:
            cmd = self.build_ffmpeg_command({
                'codec': 'hevc_ni_logan',
                'output_path': output_path,
                'crf': crf,
                'bitrate': bitrate,
                'hw_decode': True,  # 强制启用硬件解码
                'xcoder_params': xcoder_params or {}
            })
            logging.info(cmd)
            self.convert_video_with_progress(cmd, progress_callback)
        except Exception as e:
            print(e)
            raise e
            
        if remove_original:
            os.remove(self.video_path)

