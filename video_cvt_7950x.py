from video import Video
import logging,os
logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s]%(message)s')

# video_path = "C:/Users/adsfv/Desktop/1/mdvr-248"
video_path = '\\\\192.168.3.31\\ad_video\\transcode\\7950x'
video_save_path = "\\\\192.168.3.31\\ad_video\\Giants"
subs_save_path = "\\\\192.168.3.31\\ad_video\\Giants"
video_path_list = Video.get_video_pathlist_from_path(video_path,include_substitle=True)
print(video_path_list)
for video_path in video_path_list:
    if video_path.endswith(".srt") or video_path.endswith(".ass") or video_path.endswith(".ssa"):
        dst_path = os.path.join(subs_save_path,os.path.basename(video_path))
        os.rename(video_path,dst_path)
        continue
    video = Video(video_path)
    video_bitrate_k, video_bitrate_unit = video.convert_bitrate(video.video_bitrate,unit="K",dec=0, seprate=True)
    if video.video_codec == 'hevc' or video.video_codec == 'av1':
        if video.video_resolution[0] == 1920 and video.video_fps<=30:
            br_limit = 3000
        elif video.video_resolution[0] == 1920 and video.video_fps>30 and video.video_fps<=60:
            br_limit = 6000
        elif video.video_resolution[0] == 3840 and video.video_fps<=30:
            br_limit = 12000
        elif video.video_resolution[0] == 3840 and video.video_fps>30 and video.video_fps<=60:
            br_limit = 24000
        if video_bitrate_k < br_limit:
            logging.info(f'{video.video_name}: HEVC with bitrate {video_bitrate_k}kbps, not transcode')
            video.move(video_save_path)
            continue
    if video.video_codec == 'hevc' or video.video_codec == 'av1':
        if video.is_vr:
            br_limit = 24000
        else:
            br_limit = 4000
        if video_bitrate_k < br_limit:
            logging.info(f'{video.video_name}: HEVC with bitrate {video_bitrate_k}kbps, not transcode')
            video.move(video_save_path)
            continue
    
    if video.is_vr:
        # logging.warning('Need CPU convert, pass')
        # pass
        video.convert_to_h265(crf=20,preset='slow',output_folder=video_save_path, remove_original=True)
        # video.convert_to_av1(crf=26,preset=6,output_folder=video_save_path, remove_original=True)
    else:
        video.convert_to_h265(crf=22,preset='medium',rate=30,output_folder=video_save_path, remove_original=True)
        # video.convert_to_av1(crf=30,preset=8,output_folder=video_save_path, remove_original=True)
        # video.convert_to_hevc_qsv(global_quality=22,preset='slow',output_folder=video_save_path, remove_original=True)
        # pass
    # video.convert_to_hevc_qsv(output_folder=video_save_path, remove_original=False)
    logging.info("Done: %s" % video.video_name)