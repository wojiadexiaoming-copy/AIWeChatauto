
"""
配置服务模块
处理应用配置的加载、保存和验证
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import threading
import time

logger = logging.getLogger(__name__)

class ConfigService:
    """配置服务类"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.skills_dir = "skills"
        self.default_config = self._get_default_config()
        self._start_token_monitor_thread()
        logger.info(f"配置服务初始化完成，配置文件: {self.config_file}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "wechat_appid": "",
            "wechat_appsecret": "",
            "gemini_api_key": "",
            "gemini_model": "gemini-2.5-flash",
            "deepseek_api_key": "",
            "deepseek_model": "deepseek-chat",
            "dashscope_api_key": "",
            "dashscope_model": "qwen-turbo",
            "pexels_api_key": "",
            "coze_token": "",  # 新增coze令牌
            "inodetree_api_key": "",
            "inodetree_model": "inodetree-2.0-flash",
            "image_model": "gemini",  # 默认生图模型
            "author": "AI笔记",
            "content_source_url": "",
            "firecrawl_api_key": "",  # 新增Firecrawl密钥
            "skills": [],  # 动态加载，默认为空
            "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _save_skill_to_disk(self, s: Dict[str, Any]) -> None:
        """把单个人设数据存入对应的子文件夹"""
        skill_id = s.get("id")
        if not skill_id:
            return
        
        path = os.path.join(self.skills_dir, skill_id)
        if not os.path.exists(path):
            os.makedirs(path)
            
        # 写 meta.json
        meta = {
            "name": s.get("name", ""),
            "description": s.get("description", "")
        }
        with open(os.path.join(path, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=4)
            
        # 写 IDENTITY.md
        with open(os.path.join(path, "IDENTITY.md"), "w", encoding="utf-8") as f:
            f.write(s.get("identity", "") or s.get("system_prompt", ""))  # 兼容旧系统提示词
            
        # 写 USER.md
        with open(os.path.join(path, "USER.md"), "w", encoding="utf-8") as f:
            f.write(s.get("user", ""))
            
        # 写 WORKFLOW.md
        with open(os.path.join(path, "WORKFLOW.md"), "w", encoding="utf-8") as f:
            f.write(s.get("workflow", ""))

    def _init_default_skills(self) -> None:
        """初始化默认人设文件夹"""
        if not os.path.exists(self.skills_dir):
            try:
                os.makedirs(self.skills_dir)
                logger.info(f"创建 skills 文件夹: {self.skills_dir}")
            except Exception as e:
                logger.error(f"创建 skills 文件夹失败: {e}")
                return

        # 检查是否为空
        try:
            dirs = [d for d in os.listdir(self.skills_dir) if os.path.isdir(os.path.join(self.skills_dir, d))]
        except Exception as e:
            logger.error(f"读取 skills 文件夹列表失败: {e}")
            dirs = []

        if not dirs:
            logger.info("skills 文件夹为空，开始初始化默认人设")
            default_skills = [
                {
                    "id": "skill_1",
                    "name": "小红书爆款风",
                    "description": "多使用 Emoji 表情符号，用语口语化且具有强烈的情感煽动力，擅长种草和分享日常。",
                    "identity": "你是一位拥有百万粉丝的小红书爆款文案博主。请用活泼、亲切、极其口语化的语气撰写内容。",
                    "user": "你的目标受众主要是年轻群体、寻求生活好物推荐或日常共鸣的读者。",
                    "workflow": "多使用表情符号（如✨, 💡, 🔥, 🙌）来润色文本，分段短小精悍，善于引发读者共鸣、设置悬念和种草推荐。确保段落标题和正文具有极强的吸引力，同时必须保留所有的 HTML 标记规范。"
                },
                {
                    "id": "skill_2",
                    "name": "深度科技评测",
                    "description": "严谨科学、条理清晰，使用专业术语进行细致的客观横向对比，适合深度干货文章。",
                    "identity": "你是一位资深的科技数码主笔与技术分析师。在写作时请保持客观、中立、极其专业的笔调。",
                    "user": "你的目标受众主要是极客、数码发烧友以及对深度科技内容感兴趣的读者。",
                    "workflow": "多引用具体的技术参数、测试数据和行业背景进行横向深度对比。文章结构要非常严谨，段落层级分明，逻辑连贯性强。禁止使用任何轻浮口语或过多的语气助词，直接提供高密度的技术干货信息。"
                },
                {
                    "id": "skill_3",
                    "name": "大众科普风格",
                    "description": "通俗易懂、生动有趣，擅长将复杂的科学原理以打比方、讲故事的形式解释清楚。",
                    "identity": "你是一位知名的大众科普作家。你的任务是将深奥、复杂的科学概念以生动有趣、通俗易懂的方式讲解给普通读者听。",
                    "user": "你的目标受众是普通大众、科学爱好者和求知欲强烈的非专业读者。",
                    "workflow": "请在写作时多采用日常生活中的比喻、类比或趣味小故事。避免生搬硬套难懂的学术词汇，行文要亲切温和、条理清晰，确保读者能轻松理解核心知识并保持好奇心。"
                },
                {
                    "id": "skill_4",
                    "name": "官方公众号创作者",
                    "description": "系统默认人设。文笔端庄大方、专业权威，精通新媒体排版与读者心理分析。",
                    "identity": "你是一位专业的微信公众号内容创作者，拥有丰富的数字媒体经验，精通内容策划、用户心理分析和新媒体营销。",
                    "user": "你的目标受众是微信公众号的广泛读者群体。",
                    "workflow": "你擅长为不同目标受众创作引人入胜、易于传播的内容，熟悉微信公众号的运营规则、排版规范和传播机制。你能够根据主题调整写作风格，结合热点、数据或故事提升文章吸引力，确保高阅读量 and 分享率。"
                }
            ]
            for s in default_skills:
                self._save_skill_to_disk(s)

    def _load_skills_from_disk(self) -> List[Dict[str, Any]]:
        """从 skills/ 目录加载所有子文件夹形式的人设列表"""
        self._init_default_skills()
        skills = []
        try:
            if not os.path.exists(self.skills_dir):
                return skills
                
            for folder_name in os.listdir(self.skills_dir):
                folder_path = os.path.join(self.skills_dir, folder_name)
                if not os.path.isdir(folder_path):
                    continue
                
                # 读取 meta.json
                meta_path = os.path.join(folder_path, "meta.json")
                name = ""
                description = ""
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                            name = meta.get("name", "")
                            description = meta.get("description", "")
                    except Exception as e:
                        logger.error(f"读取 meta.json 失败 {folder_name}: {e}")
                        
                # 读取 IDENTITY.md
                identity = ""
                identity_path = os.path.join(folder_path, "IDENTITY.md")
                if os.path.exists(identity_path):
                    try:
                        with open(identity_path, "r", encoding="utf-8") as f:
                            identity = f.read()
                    except Exception as e:
                        logger.error(f"读取 IDENTITY.md 失败 {folder_name}: {e}")
                        
                # 读取 USER.md
                user = ""
                user_path = os.path.join(folder_path, "USER.md")
                if os.path.exists(user_path):
                    try:
                        with open(user_path, "r", encoding="utf-8") as f:
                            user = f.read()
                    except Exception as e:
                        logger.error(f"读取 USER.md 失败 {folder_name}: {e}")
                        
                # 读取 WORKFLOW.md
                workflow = ""
                workflow_path = os.path.join(folder_path, "WORKFLOW.md")
                if os.path.exists(workflow_path):
                    try:
                        with open(workflow_path, "r", encoding="utf-8") as f:
                            workflow = f.read()
                    except Exception as e:
                        logger.error(f"读取 WORKFLOW.md 失败 {folder_name}: {e}")
                
                skills.append({
                    "id": folder_name,
                    "name": name,
                    "description": description,
                    "identity": identity,
                    "user": user,
                    "workflow": workflow
                })
        except Exception as e:
            logger.error(f"从磁盘加载 skills 失败: {e}")
            
        # 按 id 排序，保证列表顺序稳定
        skills.sort(key=lambda x: x.get("id", ""))
        return skills
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info("从文件加载配置成功")
                    
                # 合并默认配置，确保所有必要字段存在
                merged_config = self.default_config.copy()
                merged_config.update(config)
                
                # 动态加载磁盘中的 skills 并覆盖 config.json 里的旧版 skills
                merged_config["skills"] = self._load_skills_from_disk()
                return merged_config
            else:
                logger.info("配置文件不存在，使用默认配置")
                default_cfg = self.default_config.copy()
                default_cfg["skills"] = self._load_skills_from_disk()
                return default_cfg
                
        except Exception as e:
            logger.error(f"加载配置时发生错误: {str(e)}")
            return self.default_config.copy()
    
    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """保存配置"""
        try:
            # 复制一份，避免修改外部传入的对象
            config_data_copy = dict(config_data)
            
            # 提取 skills list
            skills_list = config_data_copy.pop("skills", None)
            
            # 验证剩余配置数据
            if not self._validate_config(config_data_copy):
                logger.error("配置数据验证失败")
                return False
            
            # 加载现有配置 (同样过滤 skills 键)
            current_config = self.load_config()
            current_config.pop("skills", None)
            
            # 更新配置
            current_config.update(config_data_copy)
            current_config["updated_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 如果是首次创建，设置创建时间
            if not os.path.exists(self.config_file):
                current_config["created_at"] = current_config["updated_at"]
            
            # 保存到 config.json
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, ensure_ascii=False, indent=4)
            
            # 处理 skills 保存
            if skills_list is not None:
                # 获取本次保存的所有的 skill ID
                saved_ids = [s.get("id") for s in skills_list if s.get("id")]
                
                # 删除不在 saved_ids 列表中的本地文件夹 (实现人设删除)
                if os.path.exists(self.skills_dir):
                    try:
                        for folder_name in os.listdir(self.skills_dir):
                            folder_path = os.path.join(self.skills_dir, folder_name)
                            if os.path.isdir(folder_path) and folder_name not in saved_ids:
                                import shutil
                                shutil.rmtree(folder_path)
                                logger.info(f"删除了本地人设文件夹: {folder_path}")
                    except Exception as e:
                        logger.error(f"清理被删除的人设文件夹失败: {e}")
                
                # 保存每一个 skill 到磁盘
                for s in skills_list:
                    self._save_skill_to_disk(s)
            
            logger.info("配置及人设保存成功")
            return True
            
        except Exception as e:
            logger.error(f"保存配置时发生错误: {str(e)}")
            return False
    
    def _validate_config(self, config_data: Dict[str, Any]) -> bool:
        """验证配置数据"""
        required_fields = ['wechat_appid', 'wechat_appsecret', 'gemini_api_key']
        
        for field in required_fields:
            if field in config_data:
                value = config_data[field]
                if not isinstance(value, str) or not value.strip():
                    logger.error(f"必填字段 {field} 不能为空")
                    return False
        
        # 验证模型名称
        if 'gemini_model' in config_data:
            valid_models = ['gemini-2.5-flash', 'gemini-2.5-pro']
            if config_data['gemini_model'] not in valid_models:
                logger.warning(f"未知的Gemini模型: {config_data['gemini_model']}")
        
        return True
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取单个配置值"""
        try:
            config = self.load_config()
            return config.get(key, default)
        except Exception as e:
            logger.error(f"获取配置值时发生错误: {str(e)}")
            return default
    
    def set_config_value(self, key: str, value: Any) -> bool:
        """设置单个配置值"""
        try:
            config = self.load_config()
            config[key] = value
            return self.save_config(config)
        except Exception as e:
            logger.error(f"设置配置值时发生错误: {str(e)}")
            return False
    
    def get_wechat_config(self) -> Dict[str, str]:
        """获取微信配置"""
        config = self.load_config()
        return {
            'appid': config.get('wechat_appid', ''),
            'appsecret': config.get('wechat_appsecret', '')
        }
    
    def get_gemini_config(self) -> Dict[str, str]:
        """获取Gemini配置"""
        config = self.load_config()
        return {
            'api_key': config.get('gemini_api_key', ''),
            'model': config.get('gemini_model', 'gemini-2.5-flash')
        }
    
    def get_deepseek_config(self) -> Dict[str, str]:
        """获取DeepSeek配置"""
        config = self.load_config()
        return {
            'api_key': config.get('deepseek_api_key', ''),
            'model': config.get('deepseek_model', 'deepseek-chat')
        }
    
    def get_dashscope_config(self) -> Dict[str, str]:
        """获取阿里云百炼配置"""
        config = self.load_config()
        return {
            'api_key': config.get('dashscope_api_key', ''),
            'model': config.get('dashscope_model', 'qwen-turbo')
        }
    
    def get_pexels_config(self) -> Dict[str, str]:
        """获取Pexels配置"""
        config = self.load_config()
        return {
            'api_key': config.get('pexels_api_key', '')
        }
    
    def get_coze_config(self) -> Dict[str, str]:
        """获取Coze配置"""
        config = self.load_config()
        return {
            'coze_token': config.get('coze_token', ''),
            'coze_workflow_id': config.get('coze_workflow_id', '')
        }
    
    def get_inodetree_config(self) -> Dict[str, str]:
        """获取 InodeTree 配置"""
        config = self.load_config()
        return {
            'api_key': config.get('inodetree_api_key', ''),
            'model': config.get('inodetree_model', 'inodetree-2.0-flash')
        }

    def is_inodetree_configured(self) -> bool:
        """检查 InodeTree 是否已配置"""
        return bool(self.get_inodetree_config().get('api_key'))

    def get_author_config(self) -> Dict[str, str]:
        """获取作者配置"""
        config = self.load_config()
        return {
            'author': config.get('author', 'AI笔记'),
            'content_source_url': config.get('content_source_url', '')
        }
    
    def get_firecrawl_config(self) -> Dict[str, str]:
        """获取Firecrawl配置"""
        config = self.load_config()
        return {
            'api_key': config.get('firecrawl_api_key', '')
        }
    
    def is_wechat_configured(self) -> bool:
        """检查微信是否已配置"""
        wechat_config = self.get_wechat_config()
        return bool(wechat_config['appid'] and wechat_config['appsecret'])
    
    def is_gemini_configured(self) -> bool:
        """检查Gemini是否已配置"""
        gemini_config = self.get_gemini_config()
        return bool(gemini_config['api_key'])
    
    def is_deepseek_configured(self) -> bool:
        """检查DeepSeek是否已配置"""
        deepseek_config = self.get_deepseek_config()
        return bool(deepseek_config['api_key'])
    
    def is_dashscope_configured(self) -> bool:
        """检查阿里云百炼是否已配置"""
        dashscope_config = self.get_dashscope_config()
        return bool(dashscope_config['api_key'])
    
    def is_pexels_configured(self) -> bool:
        """检查Pexels是否已配置"""
        pexels_config = self.get_pexels_config()
        return bool(pexels_config['api_key'])
    
    def get_config_status(self) -> Dict[str, bool]:
        """获取配置状态"""
        return {
            'wechat_configured': self.is_wechat_configured(),
            'gemini_configured': self.is_gemini_configured(),
            'deepseek_configured': self.is_deepseek_configured(),
            'dashscope_configured': self.is_dashscope_configured(),
            'pexels_configured': self.is_pexels_configured(),
            'inodetree_configured': self.is_inodetree_configured(),
            'config_file_exists': os.path.exists(self.config_file)
        }

    def _start_token_monitor_thread(self):
        def monitor():
            while True:
                try:
                    config = self.load_config()
                    access_token = config.get('wechat_access_token', '')
                    expire_time = int(config.get('wechat_access_token_expire_time', 0))
                    now = int(time.time())
                    remain = expire_time - now if expire_time else None
                    try:
                        now_str = datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        now_str = str(now)
                    try:
                        expire_str = datetime.fromtimestamp(expire_time).strftime('%Y-%m-%d %H:%M:%S') if expire_time else '无'
                    except Exception:
                        expire_str = str(expire_time)
                    # logger.info(f"access_token检查: 当前时间{now_str}, 过期时间{expire_str}, 剩余{remain}秒")
                    # 如果token快到期（2分钟内）或已过期/不存在，则刷新
                    if (access_token and expire_time and remain <= 120) or (not access_token or not expire_time or remain <= 0):
                        logger.info("access_token即将过期或已过期，自动刷新...")
                        wechat_config = self.get_wechat_config()
                        if wechat_config.get('appid') and wechat_config.get('appsecret'):
                            try:
                                from services.wechat_service import WeChatService
                                ws = WeChatService()
                                token_info = ws.get_access_token(
                                    wechat_config['appid'],
                                    wechat_config['appsecret']
                                )
                                if token_info and token_info.get('access_token'):
                                    self.save_config({
                                        'wechat_access_token': token_info['access_token'],
                                        'wechat_access_token_expires_in': token_info['expires_in'],
                                        'wechat_access_token_expire_time': token_info['expire_time'],
                                        'wechat_access_token_expire_time_str': token_info['expire_time_str'],
                                        'wechat_access_token_update_time': token_info['update_time']
                                    })
                                    logger.info("access_token自动刷新成功")
                                else:
                                    logger.warning("自动刷新access_token失败")
                            except Exception as e:
                                logger.error(f"自动刷新access_token时异常: {str(e)}")
                        else:
                            logger.warning("未配置appid/appsecret，无法自动刷新access_token")
                    # 每30秒检查一次
                    time.sleep(30)
                except Exception as e:
                    logger.error(f"access_token自动刷新线程异常: {str(e)}")
                    time.sleep(60)