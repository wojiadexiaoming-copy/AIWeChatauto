
"""
应用配置模块
管理应用的基本配置设置
"""

import os
import logging
from datetime import datetime

# 日志配置
def setup_logging():
    """设置日志配置"""
    os.makedirs('logs', exist_ok=True)
    
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 文件日志处理器
    file_handler = logging.FileHandler(
        f'logs/app_{datetime.now().strftime("%Y%m%d")}.log', 
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    
    # 控制台日志处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    
    # 根日志配置
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

# 应用配置类
class AppConfig:
    """应用配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get("SESSION_SECRET", "wechat-gemini-publisher-secret-key")
    DEBUG = True
    
    # 文件夹配置
    CACHE_FOLDER = 'cache'
    LOGS_FOLDER = 'logs'
    STATIC_FOLDER = 'static'
    TEMPLATES_FOLDER = 'templates'
    
    # 微信API配置
    WECHAT_BASE_URL = "https://api.weixin.qq.com"
    
    # Gemini AI配置
    GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"
    GEMINI_IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"
    
    # DeepSeek AI配置
    DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"
    
    # 请求超时配置
    API_TIMEOUT = 60
    
    # 日志保留配置
    MAX_LOG_ENTRIES = 100
    
    @staticmethod
    def create_directories():
        """创建必要的目录"""
        directories = [
            AppConfig.CACHE_FOLDER,
            AppConfig.LOGS_FOLDER,
            AppConfig.STATIC_FOLDER,
            AppConfig.TEMPLATES_FOLDER
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
        logging.info("应用目录创建完成")

# 环境变量配置
class EnvConfig:
    """环境变量配置"""
    
    @staticmethod
    def get_gemini_api_key():
        """获取Gemini API密钥"""
        return os.environ.get("GEMINI_API_KEY")
    
    @staticmethod
    def set_gemini_api_key(api_key):
        """设置Gemini API密钥"""
        os.environ["GEMINI_API_KEY"] = api_key
        logging.info("Gemini API密钥已设置")
    
    @staticmethod
    def get_session_secret():
        """获取会话密钥"""
        return os.environ.get("SESSION_SECRET", AppConfig.SECRET_KEY)