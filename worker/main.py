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
        master_url="http://localhost:5000",
        prefix_path="",  # 不设置前缀，让Worker自动处理
        save_path="!replace",  # 替换原视频
        support_vr=True,
        crf=20,
        preset="slow",
        rate=30,
        numa_param="-,-,+,-",
        remove_original=False,
        num=1
    )
    
    # 运行worker
    worker.run() 