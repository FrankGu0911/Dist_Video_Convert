import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.test import TestWorker
from worker.base import WorkerType

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试worker实例
    worker = TestWorker(
        worker_name="test_worker",
        worker_type=WorkerType.CPU,
        master_url="http://localhost:5000",  # 修改为正确的端口
        prefix_path=r"C:\Users\adsfv\Desktop\frank\Dist_Video_Convert\test_media",  # 修改为实际的视频路径
        save_path="!replace",  # 替换原视频
        support_vr=True,
        crf=20,  # 可选
        preset="slow",  # 可选
        rate=30,  # 可选
        numa_param="-,-,+,-",  # 可选
        remove_original=False,  # 可选
        num=1   # 可选
    )
    
    # 运行worker
    worker.run() 