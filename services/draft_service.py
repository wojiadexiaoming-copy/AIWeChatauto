"""
草稿服务模块
处理微信公众号草稿相关操作
"""

import requests
import json
import logging
from typing import Dict, Any, Optional
from config.app_config import AppConfig

logger = logging.getLogger(__name__)

class DraftService:
    """草稿服务类"""
    
    def __init__(self):
        self.base_url = AppConfig.WECHAT_BASE_URL
        self.timeout = AppConfig.API_TIMEOUT
        logger.info("草稿服务初始化完成")
    
    def create_draft(self, access_token: str, draft_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        新增草稿
        :param access_token: 访问令牌
        :param draft_data: 草稿数据
        :return: 草稿信息
        """
        url = f"{self.base_url}/cgi-bin/draft/add"
        params = {'access_token': access_token}
        headers = {"Content-Type": "application/json; charset=utf-8"}
        
        try:
            logger.info("开始创建草稿")
            logger.debug(f"草稿数据: {json.dumps(draft_data, ensure_ascii=False, indent=2)}")
            
            response = requests.post(
                url, 
                params=params,
                data=json.dumps(draft_data, ensure_ascii=False), 
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            if 'media_id' in result:
                logger.info(f"草稿创建成功，media_id: {result['media_id']}")
                return result
            else:
                error_code = result.get('errcode', 'unknown')
                error_msg = result.get('errmsg', 'unknown error')
                logger.error(f"创建草稿失败，错误码: {error_code}, 错误信息: {error_msg}")
                return result
                
        except requests.exceptions.RequestException as e:
            logger.error(f"创建草稿网络请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"创建草稿时发生异常: {str(e)}")
            return None
    
    def publish_draft(self, access_token: str, media_id: str) -> Optional[Dict[str, Any]]:
        """
        发布草稿
        :param access_token: 访问令牌
        :param media_id: 草稿media_id
        :return: 发布结果
        """
        url = f"{self.base_url}/cgi-bin/freepublish/submit"
        params = {'access_token': access_token}
        payload = {"media_id": media_id}
        headers = {"Content-Type": "application/json; charset=utf-8"}
        
        try:
            logger.info(f"开始发布草稿，media_id: {media_id}")
            
            response = requests.post(
                url,
                params=params,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            error_code = result.get('errcode', -1)
            error_msg = result.get('errmsg', 'unknown error')
            
            if error_code == 0:
                logger.info(f"草稿发布成功，publish_id: {result.get('publish_id')}")
            else:
                logger.error(f"草稿发布失败，错误码: {error_code}, 错误信息: {error_msg}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"发布草稿网络请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"发布草稿时发生异常: {str(e)}")
            return None
    
    def build_draft_data(self, title: str, content: str, author: str = "AI笔记",
                        digest: str = "", thumb_media_id: str = "", 
                        content_source_url: str = "") -> Dict[str, Any]:
        """
        构建草稿数据
        :param title: 文章标题
        :param content: 文章内容
        :param author: 作者
        :param digest: 摘要
        :param thumb_media_id: 封面图片media_id
        :param content_source_url: 原文链接
        :return: 草稿数据
        """
        logger.info(f"构建草稿数据，标题: {title}")
        
        draft_data = {
            "articles": [{
                "title": title,
                "author": author,
                "digest": digest,
                "content": content,
                "content_source_url": content_source_url,
                "thumb_media_id": thumb_media_id,
                "show_cover_pic": 1 if thumb_media_id else 0,
                "article_type": "news",
                "need_open_comment": 0,
                "only_fans_can_comment": 0
            }]
        }
        
        logger.debug(f"草稿数据构建完成: {json.dumps(draft_data, ensure_ascii=False, indent=2)}")
        return draft_data
    
    def validate_draft_data(self, draft_data: Dict[str, Any]) -> bool:
        """
        验证草稿数据
        :param draft_data: 草稿数据
        :return: 验证结果
        """
        try:
            if 'articles' not in draft_data:
                logger.error("草稿数据缺少articles字段")
                return False
            
            articles = draft_data['articles']
            if not isinstance(articles, list) or len(articles) == 0:
                logger.error("articles字段必须是非空列表")
                return False
            
            for i, article in enumerate(articles):
                if not isinstance(article, dict):
                    logger.error(f"文章{i+1}数据格式错误")
                    return False
                
                # 检查必填字段
                required_fields = ['title', 'content']
                for field in required_fields:
                    if field not in article or not article[field]:
                        logger.error(f"文章{i+1}缺少必填字段: {field}")
                        return False
                
                # 检查内容字符数（官方限制 2万字符）
                if len(article['content']) > 20000:
                    logger.error(f"文章{i+1}内容过长，超过20000字符")
                    return False
                # 检查内容字节大小（官方限制 1MB）
                if len(article['content'].encode('utf-8')) > 1024 * 1024:
                    logger.error(f"文章{i+1}内容超过1MB字节限制")
                    return False
                
                # 检查标题长度
                if len(article['title']) > 64:
                    logger.error(f"文章{i+1}标题过长，超过64字符")
                    return False
            
            logger.info("草稿数据验证通过")
            return True
            
        except Exception as e:
            logger.error(f"验证草稿数据时发生异常: {str(e)}")
            return False
    
    def get_draft_info(self, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取草稿信息摘要
        :param draft_data: 草稿数据
        :return: 草稿信息
        """
        try:
            if 'articles' not in draft_data or not draft_data['articles']:
                return {'article_count': 0}
            
            article = draft_data['articles'][0]  # 取第一篇文章
            
            return {
                'article_count': len(draft_data['articles']),
                'title': article.get('title', ''),
                'author': article.get('author', ''),
                'digest': article.get('digest', ''),
                'has_cover': bool(article.get('thumb_media_id')),
                'content_length': len(article.get('content', '')),
                'has_source_url': bool(article.get('content_source_url'))
            }
            
        except Exception as e:
            logger.error(f"获取草稿信息时发生异常: {str(e)}")
            return {'article_count': 0}