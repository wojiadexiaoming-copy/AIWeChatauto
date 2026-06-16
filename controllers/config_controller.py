
"""
配置控制器模块
处理配置相关的HTTP请求
"""

import logging
from flask import request, jsonify
from typing import Dict, Any
from services.config_service import ConfigService
from services.wechat_service import WeChatService
from services.gemini_service import GeminiService
from services.deepseek_service import DeepSeekService
from services.dashscope_service import DashScopeService
from services.inodetree_service import InodeTreeService
import requests

logger = logging.getLogger(__name__)

class ConfigController:
    """配置控制器类"""
    
    def __init__(self):
        self.config_service = ConfigService()
        self.wechat_service = WeChatService()
        self.gemini_service = GeminiService()
        self.deepseek_service = DeepSeekService()
        self.dashscope_service = DashScopeService()
        logger.info("配置控制器初始化完成")
    
    def handle_config_request(self) -> Dict[str, Any]:
        """
        处理配置请求
        :return: 响应数据
        """
        try:
            if request.method == 'GET':
                return self._get_config()
            elif request.method == 'POST':
                return self._save_config()
            else:
                return {
                    'success': False,
                    'message': '不支持的请求方法'
                }
        except Exception as e:
            logger.error(f"处理配置请求时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'服务器错误: {str(e)}'
            }
    
    def _get_config(self) -> Dict[str, Any]:
        """获取配置"""
        try:
            logger.info("开始获取配置信息")
            config = self.config_service.load_config()
            # 直接返回真实配置信息，不隐藏敏感信息
            logger.info("配置信息获取成功")
            return {
                'success': True,
                'data': config,
                'message': '配置加载成功'
            }
        except Exception as e:
            logger.error(f"获取配置时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'加载配置失败: {str(e)}'
            }
    
    def _save_config(self) -> Dict[str, Any]:
        """保存配置"""
        try:
            config_data = request.get_json()
            if not config_data:
                logger.error("请求数据为空")
                return {
                    'success': False,
                    'message': '请求数据为空'
                }
            
            logger.info("开始保存配置")
            logger.info(f"接收到的配置数据: {config_data}")
            
            # 验证必填字段
            validation_result = self._validate_config_data(config_data)
            if not validation_result['valid']:
                logger.error(f"配置验证失败: {validation_result['message']}")
                return {
                    'success': False,
                    'message': validation_result['message']
                }
            
            # 保存配置
            save_result = self.config_service.save_config(config_data)
            logger.info(f"配置保存结果: {save_result}")
            
            if save_result:
                # 验证保存是否成功
                saved_config = self.config_service.load_config()
                logger.info(f"保存后读取的配置: {saved_config}")
                
                logger.info("配置保存成功")
                return {
                    'success': True,
                    'message': '配置保存成功',
                    'data': saved_config
                }
            else:
                logger.error("配置保存失败")
                return {
                    'success': False,
                    'message': '配置保存失败'
                }
                
        except Exception as e:
            logger.error(f"保存配置时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'保存配置失败: {str(e)}'
            }
    
    def _validate_config_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证配置数据"""
        logger.info(f"开始验证配置数据: {config_data}")
        
        # 检查必填字段，但允许部分为空以支持分步配置
        required_fields = {
            'wechat_appid': '微信AppID',
            'wechat_appsecret': '微信AppSecret', 
            # 其他不做强制校验，coze_token 不做强制校验
            # firecrawl_api_key 不做强制校验
        }
        
        # 只验证存在且非空的字段
        for field, label in required_fields.items():
            if field in config_data and config_data[field]:
                value = config_data[field]
                if not isinstance(value, str) or not value.strip():
                    logger.error(f"字段 {field} 值无效: {value}")
                    return {
                        'valid': False,
                        'message': f'{label}格式错误'
                    }
                
                # 验证微信AppID格式（如果提供）
                if field == 'wechat_appid':
                    wechat_appid = value.strip()
                    if not wechat_appid.startswith('wx') or len(wechat_appid) != 18:
                        return {
                            'valid': False,
                            'message': '微信AppID格式不正确，应为wx开头的18位字符'
                        }
                
                # 验证Gemini API密钥格式（如果提供）
                if field == 'gemini_api_key':
                    gemini_api_key = value.strip()
                    if not gemini_api_key.startswith('AIza'):
                        return {
                            'valid': False,
                            'message': 'Gemini API密钥格式不正确，应以AIza开头'
                        }
        
        logger.info("配置数据验证通过")
        return {'valid': True}
    
    def test_wechat_connection(self) -> Dict[str, Any]:
        """测试微信连接，并保存access_token等信息到配置"""
        try:
            logger.info("开始测试微信API连接")
            # 获取当前配置
            config = self.config_service.load_config()
            logger.info(f"当前完整配置: {config}")
            wechat_config = self.config_service.get_wechat_config()
            logger.info(f"微信配置: appid={wechat_config.get('appid', 'None')[:10]}..., appsecret={'已设置' if wechat_config.get('appsecret') else '未设置'}")
            if not wechat_config['appid'] or not wechat_config['appsecret']:
                logger.error(f"微信配置不完整: appid={bool(wechat_config.get('appid'))}, appsecret={bool(wechat_config.get('appsecret'))}")
                return {
                    'success': False,
                    'message': '请先配置微信公众号信息',
                    'debug_info': {
                        'has_appid': bool(wechat_config.get('appid')),
                        'has_appsecret': bool(wechat_config.get('appsecret')),
                        'config_keys': list(config.keys())
                    }
                }
            # 获取access_token
            token_info = self.wechat_service.get_access_token(
                wechat_config['appid'],
                wechat_config['appsecret']
            )
            if token_info and token_info.get('access_token'):
                # 保存access_token等信息到config.json
                config_update = {
                    'wechat_access_token': token_info['access_token'],
                    'wechat_access_token_expires_in': token_info['expires_in'],
                    'wechat_access_token_expire_time': token_info['expire_time'],
                    'wechat_access_token_expire_time_str': token_info['expire_time_str'],
                    'wechat_access_token_update_time': token_info['update_time']
                }
                self.config_service.save_config(config_update)
                logger.info("微信API连接测试成功，access_token已保存到配置")
                return {
                    'success': True,
                    'message': '微信API连接成功，access_token已保存',
                    'data': config_update
                }
            else:
                logger.error("微信API连接测试失败，未能获取access_token")
                return {
                    'success': False,
                    'message': '微信API连接失败，未能获取access_token，请检查AppID和AppSecret是否正确或IP白名单设置',
                }
        except Exception as e:
            logger.error(f"测试微信连接时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'测试失败: {str(e)}'
            }
    
    def test_gemini_connection(self) -> Dict[str, Any]:
        """测试Gemini连接"""
        try:
            logger.info("开始测试Gemini AI连接")
            
            # 获取当前配置
            config = self.config_service.load_config()
            logger.info(f"当前完整配置: {config}")
            
            gemini_config = self.config_service.get_gemini_config()
            logger.info(f"Gemini配置: api_key={'已设置' if gemini_config.get('api_key') else '未设置'}, model={gemini_config.get('model', 'None')}")
            
            if not gemini_config['api_key']:
                logger.error(f"Gemini API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置Gemini API密钥',
                    'debug_info': {
                        'has_api_key': bool(gemini_config.get('api_key')),
                        'config_keys': list(config.keys())
                    }
                }
            
            # 设置API密钥
            self.gemini_service.set_api_key(gemini_config['api_key'])
            
            result = self.gemini_service.test_connection(gemini_config['model'])
            
            logger.info(f"Gemini连接测试完整结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"测试Gemini连接时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'测试失败: {str(e)}'
            }
    
    def get_gemini_models(self) -> Dict[str, Any]:
        """获取Gemini可用模型列表"""
        try:
            logger.info("开始获取Gemini可用模型列表")
            
            # 获取当前配置
            config = self.config_service.load_config()
            gemini_config = self.config_service.get_gemini_config()
            
            if not gemini_config['api_key']:
                logger.error("Gemini API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置Gemini API密钥',
                    'data': {
                        'models': [],
                        'current_model': gemini_config.get('model', 'gemini-2.5-flash')
                    }
                }
            
            # 设置API密钥
            self.gemini_service.set_api_key(gemini_config['api_key'])
            
            # 获取可用模型列表
            models = self.gemini_service.get_available_models()
            
            logger.info(f"成功获取到 {len(models)} 个可用模型")
            return {
                'success': True,
                'message': '模型列表获取成功',
                'data': {
                    'models': models,
                    'current_model': gemini_config.get('model', 'gemini-2.5-flash')
                }
            }
            
        except Exception as e:
            logger.error(f"获取Gemini模型列表时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'获取模型列表失败: {str(e)}',
                'data': {
                    'models': [],
                    'current_model': 'gemini-2.5-flash'
                }
            }
    
    def test_deepseek_connection(self) -> Dict[str, Any]:
        """测试DeepSeek连接"""
        try:
            logger.info("开始测试DeepSeek AI连接")
            
            # 获取当前配置
            config = self.config_service.load_config()
            logger.info(f"当前完整配置: {config}")
            
            deepseek_config = self.config_service.get_deepseek_config()
            logger.info(f"DeepSeek配置: api_key={'已设置' if deepseek_config.get('api_key') else '未设置'}, model={deepseek_config.get('model', 'None')}")
            
            if not deepseek_config['api_key']:
                logger.error(f"DeepSeek API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置DeepSeek API密钥',
                    'debug_info': {
                        'has_api_key': bool(deepseek_config.get('api_key')),
                        'config_keys': list(config.keys())
                    }
                }
            
            # 设置API密钥
            self.deepseek_service.set_api_key(deepseek_config['api_key'])
            
            result = self.deepseek_service.test_connection(deepseek_config['model'])
            
            logger.info(f"DeepSeek连接测试完整结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"测试DeepSeek连接时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'测试失败: {str(e)}'
            }
    
    def get_deepseek_models(self) -> Dict[str, Any]:
        """获取DeepSeek可用模型列表"""
        try:
            logger.info("开始获取DeepSeek可用模型列表")
            
            # 获取当前配置
            config = self.config_service.load_config()
            deepseek_config = self.config_service.get_deepseek_config()
            
            if not deepseek_config['api_key']:
                logger.error("DeepSeek API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置DeepSeek API密钥',
                    'data': {
                        'models': [],
                        'current_model': deepseek_config.get('model', 'deepseek-chat')
                    }
                }
            
            # 设置API密钥
            self.deepseek_service.set_api_key(deepseek_config['api_key'])
            
            # 获取可用模型列表
            models = self.deepseek_service.get_available_models()
            
            logger.info(f"成功获取到 {len(models)} 个可用模型")
            return {
                'success': True,
                'message': '模型列表获取成功',
                'data': {
                    'models': models,
                    'current_model': deepseek_config.get('model', 'deepseek-chat')
                }
            }
            
        except Exception as e:
            logger.error(f"获取DeepSeek模型列表时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'获取模型列表失败: {str(e)}',
                'data': {
                    'models': [],
                    'current_model': 'deepseek-chat'
                }
            }
    
    def get_deepseek_debug_info(self) -> Dict[str, Any]:
        """获取DeepSeek调试信息"""
        try:
            logger.info("开始获取DeepSeek调试信息")
            
            # 获取当前配置
            config = self.config_service.load_config()
            deepseek_config = self.config_service.get_deepseek_config()
            
            if not deepseek_config['api_key']:
                return {
                    'success': False,
                    'message': 'DeepSeek API密钥未配置',
                    'debug_info': {
                        'has_api_key': False,
                        'config_keys': list(config.keys())
                    }
                }
            
            # 设置API密钥
            self.deepseek_service.set_api_key(deepseek_config['api_key'])
            
            # 获取API详细信息
            api_info = self.deepseek_service.get_api_info()
            
            return {
                'success': True,
                'message': '调试信息获取成功',
                'data': {
                    'api_info': api_info,
                    'config': deepseek_config
                }
            }
            
        except Exception as e:
            logger.error(f"获取DeepSeek调试信息时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'获取调试信息失败: {str(e)}'
            }
    
    def test_inodetree_connection(self) -> Dict[str, Any]:
        """测试 InodeTree 连接"""
        try:
            logger.info("开始测试 InodeTree 连接")
            inodetree_config = self.config_service.get_inodetree_config()
            api_key = inodetree_config.get('api_key', '')
            if not api_key:
                return {'success': False, 'message': '请先配置 InodeTree API Key'}
            from services.inodetree_service import InodeTreeService
            inodetree = InodeTreeService(api_key)
            result = inodetree.test_connection()
            status_el = 'inodetree-status'
            if result.get('success'):
                logger.info("InodeTree 连接测试成功")
                return {
                    'success': True,
                    'message': result.get('message', 'InodeTree 连接成功'),
                    'data': {'api_key_set': True, 'model': inodetree.model}
                }
            else:
                logger.error(f"InodeTree 连接测试失败: {result.get('message')}")
                return {'success': False, 'message': result.get('message', 'InodeTree 连接失败')}
        except Exception as e:
            logger.error(f"测试 InodeTree 连接时发生异常: {e}")
            return {'success': False, 'message': str(e)}

    def get_config_status(self) -> Dict[str, Any]:
        """获取配置状态"""
        try:
            status = self.config_service.get_config_status()
            
            return {
                'success': True,
                'data': status,
                'message': '配置状态获取成功'
            }
            
        except Exception as e:
            logger.error(f"获取配置状态时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'获取配置状态失败: {str(e)}'
            }
    
    def test_dashscope_connection(self) -> Dict[str, Any]:
        """测试阿里云百炼连接"""
        try:
            logger.info("开始测试阿里云百炼连接")
            
            # 获取当前配置
            config = self.config_service.load_config()
            logger.info(f"当前完整配置: {config}")
            
            dashscope_config = self.config_service.get_dashscope_config()
            logger.info(f"阿里云百炼配置: api_key={'已设置' if dashscope_config.get('api_key') else '未设置'}, model={dashscope_config.get('model', 'None')}")
            
            if not dashscope_config['api_key']:
                logger.error(f"阿里云百炼API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置阿里云百炼API密钥',
                    'debug_info': {
                        'has_api_key': bool(dashscope_config.get('api_key')),
                        'config_keys': list(config.keys())
                    }
                }
            
            # 设置API密钥
            self.dashscope_service = DashScopeService(dashscope_config['api_key'])
            
            result = self.dashscope_service.test_connection(dashscope_config['model'])
            
            logger.info(f"阿里云百炼连接测试完整结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"测试阿里云百炼连接时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'测试失败: {str(e)}'
            }
    
    def get_dashscope_models(self) -> Dict[str, Any]:
        """获取阿里云百炼可用模型列表"""
        try:
            logger.info("开始获取阿里云百炼可用模型列表")
            
            # 获取当前配置
            config = self.config_service.load_config()
            dashscope_config = self.config_service.get_dashscope_config()
            
            if not dashscope_config['api_key']:
                logger.error("阿里云百炼API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置阿里云百炼API密钥',
                    'data': {
                        'models': [],
                        'current_model': dashscope_config.get('model', 'qwen-turbo')
                    }
                }
            
            # 设置API密钥
            self.dashscope_service = DashScopeService(dashscope_config['api_key'])
            
            # 获取可用模型列表
            models = self.dashscope_service.get_models()
            
            logger.info(f"成功获取到 {len(models)} 个可用模型")
            return {
                'success': True,
                'message': '模型列表获取成功',
                'data': {
                    'models': models,
                    'current_model': dashscope_config.get('model', 'qwen-turbo')
                }
            }
            
        except Exception as e:
            logger.error(f"获取阿里云百炼模型列表时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'获取模型列表失败: {str(e)}',
                'data': {
                    'models': [],
                    'current_model': 'qwen-turbo'
                }
            }
    
    def get_dashscope_debug_info(self) -> Dict[str, Any]:
        """获取阿里云百炼调试信息"""
        try:
            logger.info("开始获取阿里云百炼调试信息")
            
            # 获取当前配置
            config = self.config_service.load_config()
            dashscope_config = self.config_service.get_dashscope_config()
            
            if not dashscope_config['api_key']:
                return {
                    'success': False,
                    'message': '阿里云百炼API密钥未配置',
                    'debug_info': {
                        'has_api_key': False,
                        'config_keys': list(config.keys())
                    }
                }
            
            # 设置API密钥
            self.dashscope_service = DashScopeService(dashscope_config['api_key'])
            
            # 获取API详细信息
            api_info = self.dashscope_service.get_api_info()
            
            return {
                'success': True,
                'message': '调试信息获取成功',
                'data': {
                    'api_info': api_info,
                    'config': dashscope_config
                }
            }
            
        except Exception as e:
            logger.error(f"获取阿里云百炼调试信息时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'获取调试信息失败: {str(e)}'
            }
    
    def test_pexels_connection(self) -> Dict[str, Any]:
        """测试Pexels连接"""
        try:
            logger.info("开始测试Pexels连接")
            
            # 获取当前配置
            config = self.config_service.load_config()
            logger.info(f"当前完整配置: {config}")
            
            pexels_config = self.config_service.get_pexels_config()
            logger.info(f"Pexels配置: api_key={'已设置' if pexels_config.get('api_key') else '未设置'}")
            
            if not pexels_config['api_key']:
                logger.error(f"Pexels API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置Pexels API密钥',
                    'debug_info': {
                        'has_api_key': bool(pexels_config.get('api_key')),
                        'config_keys': list(config.keys())
                    }
                }
            
            # 导入图像服务进行测试
            from services.image_service import ImageService
            image_service = ImageService()
            
            # 测试Pexels搜索功能
            test_title = "technology"
            image_path = image_service._search_with_pexels(test_title, "测试图片搜索")
            
            if image_path:
                logger.info(f"Pexels连接测试成功，获取到图片: {image_path}")
                return {
                    'success': True,
                    'message': 'Pexels连接测试成功',
                    'data': {
                        'test_title': test_title,
                        'image_path': image_path,
                        'config': pexels_config
                    }
                }
            else:
                logger.warning("Pexels连接测试失败，未获取到图片")
                return {
                    'success': False,
                    'message': 'Pexels连接测试失败，请检查API密钥是否正确',
                    'data': {
                        'test_title': test_title,
                        'config': pexels_config
                    }
                }
            
        except Exception as e:
            logger.error(f"测试Pexels连接时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'测试失败: {str(e)}'
            }
    
    def test_firecrawl_connection(self) -> Dict[str, Any]:
        """测试Firecrawl连接"""
        try:
            logger.info("开始测试Firecrawl连接")
            config = self.config_service.load_config()
            firecrawl_config = self.config_service.get_firecrawl_config()
            api_key = firecrawl_config.get('api_key', '')
            if not api_key:
                logger.error("Firecrawl API密钥未配置")
                return {
                    'success': False,
                    'message': '请先配置Firecrawl API密钥',
                    'debug_info': {
                        'has_api_key': bool(api_key),
                        'config_keys': list(config.keys())
                    }
                }
            # 用/scrape接口抓取firecrawl官网主页测试密钥有效性
            url = 'https://api.firecrawl.dev/v1/scrape'
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'url': 'https://firecrawl.dev',
                'formats': ['markdown'],
                'onlyMainContent': True
            }
            try:
                import json
                resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
                if resp.status_code == 200:
                    return {
                        'success': True,
                        'message': 'Firecrawl连接测试成功',
                        'data': resp.json()
                    }
                elif resp.status_code == 401:
                    return {
                        'success': False,
                        'message': 'API密钥无效或未提供',
                        'status_code': resp.status_code
                    }
                elif resp.status_code == 429:
                    return {
                        'success': False,
                        'message': 'API请求频率超限',
                        'status_code': resp.status_code
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Firecrawl API请求失败，状态码: {resp.status_code}',
                        'status_code': resp.status_code,
                        'response': resp.text
                    }
            except Exception as e:
                logger.error(f"Firecrawl API请求异常: {str(e)}")
                return {
                    'success': False,
                    'message': f'Firecrawl API请求异常: {str(e)}'
                }
        except Exception as e:
            logger.error(f"测试Firecrawl连接时发生错误: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'测试Firecrawl连接失败: {str(e)}'
            }