import os
import configparser
import logging

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
        
        if not os.path.exists(self.config_file):
            self._create_default_config()
        
        self.config.read(self.config_file, encoding='utf-8')
    
    def _create_default_config(self):
        """创建默认配置文件"""
        self.config['paths'] = {
            'scan_paths': '/path/to/videos/folder1, /path/to/videos/folder2'
        }
        self.config['scheduler'] = {
            'scan_interval': '30'
        }
        
        with open(self.config_file, 'w') as f:
            self.config.write(f)
        
        logger.info(f"已创建默认配置文件: {self.config_file}")
    
    @property
    def scan_paths(self):
        """获取视频扫描路径列表"""
        paths = self.config.get('paths', 'scan_paths', fallback='')
        return [path.strip() for path in paths.split(',') if path.strip()]
    
    @property
    def scan_interval(self):
        """获取扫描间隔时间（分钟）"""
        return self.config.getint('scheduler', 'scan_interval', fallback=30)
    
    def validate_paths(self):
        """验证所有配置的路径是否存在"""
        invalid_paths = []
        for path in self.scan_paths:
            if not os.path.exists(path):
                invalid_paths.append(path)
        
        if invalid_paths:
            logger.warning(f"以下路径不存在: {', '.join(invalid_paths)}")
            return False
        return True 