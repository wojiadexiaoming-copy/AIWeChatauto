import asyncio
import datetime
import logging
from firecrawl import AsyncFirecrawlApp
from services.config_service import ConfigService

logger = logging.getLogger(__name__)


def log_with_timestamp(message: str) -> None:
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f'[{timestamp}] {message}')


async def fetch_douyin_hotspot_markdown(industry: str) -> str:
    log_with_timestamp(f'开始爬取抖音行业热点: {industry}')
    config = ConfigService().load_config()
    api_key = config.get('firecrawl_api_key')
    if not api_key:
        log_with_timestamp('未找到 firecrawl_api_key，请检查配置文件')
        return ''
    url = f'https://www.douyin.com/search/{industry}'
    formats = ['markdown']
    only_main_content = True
    parse_pdf = True

    try:
        app = AsyncFirecrawlApp(api_key=api_key)
        response = await app.scrape_url(
            url=url,
            formats=formats,
            only_main_content=only_main_content,
            parse_pdf=parse_pdf
        )
        if response and hasattr(response, 'markdown'):
            log_with_timestamp(f'爬取成功，markdown长度: {len(response.markdown)}')
            return response.markdown
        else:
            log_with_timestamp('未获取到有效markdown内容')
            return ''
    except Exception as e:
        log_with_timestamp(f'爬取过程发生错误: {str(e)}')
        return ''


def get_douyin_hotspot_markdown(industry: str) -> str:
    """
    同步接口，供外部调用，返回指定行业的抖音热点markdown内容。
    """
    return asyncio.run(fetch_douyin_hotspot_markdown(industry))