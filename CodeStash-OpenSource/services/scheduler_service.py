
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import atexit
import logging
from datetime import datetime
from services.draft_service import DraftService
from services.history_service import HistoryService
from services.config_service import ConfigService
import requests
from config.app_config import AppConfig

logger = logging.getLogger(__name__)

# 初始化调度器，使用sqlite持久化
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///data/scheduler_jobs.sqlite')
}
scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

draft_service = DraftService()
history_service = HistoryService()
config_service = ConfigService()

def add_publish_job(draft_id, media_id, publish_time, enable_mass_send=False):
    """
    添加定时发布任务：
    直接用已保存的media_id注册定时任务
    """
    # 更新历史状态（如有需要）
    history_service.update_draft_status_by_media_id(media_id, publish_time, enable_mass_send)
    # 转换publish_time为datetime对象
    if isinstance(publish_time, str):
        try:
            publish_time_dt = datetime.strptime(publish_time, '%Y-%m-%d %H:%M:%S')
        except Exception:
            publish_time_dt = datetime.fromisoformat(publish_time)
    else:
        publish_time_dt = publish_time
    # 注册定时任务
    job = scheduler.add_job(
        func=publish_job,
        args=[media_id, enable_mass_send],
        trigger='date',
        run_date=publish_time_dt,
        id=f"publish_{media_id}"
    )
    logger.info(f"定时发布任务已添加，media_id={media_id}，发布时间={publish_time_dt}，群发={enable_mass_send}")
    return job.id

def publish_job(media_id, enable_mass_send=False):
    """
    定时发布任务执行体
    """
    wx_cfg = config_service.get_wechat_config()
    from services.wechat_service import WeChatService
    wechat_service = WeChatService()
    access_token_info = wechat_service.get_access_token(wx_cfg['appid'], wx_cfg['appsecret'])
    if not access_token_info or 'access_token' not in access_token_info:
        logger.error('获取access_token失败，无法发布草稿')
        return
    access_token = access_token_info['access_token']
    result = draft_service.publish_draft(access_token, media_id)
    if result and result.get('errcode', -1) == 0:
        history_service.update_publish_status(media_id, result)
        logger.info(f"定时发布成功，media_id={media_id}")
        
        # 如果启用了群发，则进行群发
        if enable_mass_send:
            try:
                publish_id = result.get('publish_id')
                if publish_id:
                    logger.info(f"开始定时群发，publish_id={publish_id}")
                    mass_result = mass_send_article(publish_id)
                    if mass_result:
                        logger.info(f"定时群发成功，publish_id={publish_id}")
                    else:
                        logger.error(f"定时群发失败，publish_id={publish_id}")
                else:
                    logger.error("定时群发失败，未获取到publish_id")
            except Exception as e:
                logger.error(f"定时群发异常: {e}")
    else:
        logger.error(f"定时发布失败，media_id={media_id}，错误信息：{result}")

def mass_send_article(publish_id):
    """
    群发文章
    :param publish_id: 发布ID
    :return: 是否群发成功
    """
    try:
        wx_cfg = config_service.get_wechat_config()
        from services.wechat_service import WeChatService
        wechat_service = WeChatService()
        access_token_info = wechat_service.get_access_token(wx_cfg['appid'], wx_cfg['appsecret'])
        if not access_token_info or 'access_token' not in access_token_info:
            logger.error('获取access_token失败，无法群发')
            return False
        
        access_token = access_token_info['access_token']
        
        # 调用群发接口
        url = f"{AppConfig.WECHAT_BASE_URL}/cgi-bin/message/mass/send"
        params = {'access_token': access_token}
        
        # 群发给所有粉丝
        payload = {
            "touser": [],  # 空数组表示群发给所有粉丝
            "mpnews": {
                "media_id": publish_id
            },
            "msgtype": "mpnews"
        }
        
        response = requests.post(url, params=params, json=payload, timeout=AppConfig.API_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        
        if result.get('errcode') == 0:
            logger.info(f"群发任务提交成功，msg_id: {result.get('msg_id')}")
            # 更新群发状态到历史记录
            history_service.update_mass_send_status(publish_id, result)
            return True
        else:
            error_msg = result.get('errmsg', '未知错误')
            logger.error(f"群发失败，错误码: {result.get('errcode')}, 错误信息: {error_msg}")
            return False
            
    except Exception as e:
        logger.error(f"群发异常: {str(e)}")
        return False

def remove_publish_job(job_id):
    try:
        scheduler.remove_job(job_id)
        logger.info(f"定时任务已移除：{job_id}")
    except Exception as e:
        logger.error(f"移除定时任务失败：{job_id}，{e}")

def recover_jobs_from_history():
    """
    项目启动时自动恢复未完成的定时任务
    """
    history = history_service.get_generation_history(limit=100)
    now = datetime.now()
    for item in history:
        # 只恢复未发布且有定时发布时间的任务
        if item.get('status') == 'saved' and item.get('publish_time') and item.get('media_id'):
            try:
                publish_time = datetime.strptime(item['publish_time'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                publish_time = datetime.strptime(item['publish_time'], '%Y-%m-%d %H:%M')
            if publish_time > now:
                try:
                    # 恢复时默认不群发，因为历史记录中没有群发设置
                    scheduler.add_job(
                        func=publish_job,
                        args=[item['media_id'], False],
                        trigger='date',
                        run_date=publish_time,
                        id=f"publish_{item['media_id']}"
                    )
                    logger.info(f"恢复定时任务：media_id={item['media_id']}，发布时间={item['publish_time']}")
                except Exception as e:
                    logger.error(f"恢复定时任务失败：media_id={item['media_id']}，{e}") 