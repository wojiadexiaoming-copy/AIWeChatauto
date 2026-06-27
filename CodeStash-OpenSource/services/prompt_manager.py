
"""
AI提示词管理模块
统一管理所有AI模型的提示词模板（文章、摘要、生图、Pexels搜索等）
"""

import logging

class PromptManager:
    """AI提示词统一管理"""

    # 角色定位
    ROLE_PROMPT = """
你是一位专业的微信公众号内容创作者，拥有丰富的数字媒体经验，精通内容策划、用户心理分析和新媒体营销。你擅长为不同目标受众（如年轻人、职场人士、兴趣爱好者等）创作引人入胜、易于传播的内容，熟悉微信公众号的运营规则、排版规范和传播机制。你能够根据主题和用户需求，灵活调整写作风格（例如专业干货、轻松幽默、温暖治愈），并结合热点、数据或故事提升文章吸引力，确保高阅读量和分享率。
"""

    # 文章生成提示词（通用，Gemini/DeepSeek/阿里云百炼）
    @staticmethod
    def article_prompt(title, word_count=None, char_limit=20000, format_template=None, role_prompt=None):
        from datetime import datetime
        current_date = datetime.now().strftime("现在是%Y年%m月%d日")
        word_count_str = f"{word_count}字" if word_count else "1200-1800字"
        role_desc = role_prompt if role_prompt else PromptManager.ROLE_PROMPT
        if format_template:
            return f"{current_date}\n{role_desc}\n请根据以下HTML格式模板，生成一篇关于‘{title}’的公众号文章，排版核心风格要与模板一致，字数约{word_count_str}，且最终输出的HTML内容总字符数必须小于等于{char_limit}字符。模板如下：\n{format_template}"
        else:
            return f"{current_date}\n{role_desc}\n请帮我撰写一篇关于《{title}》的微信公众号文章。请严格遵循您将在下方接收到的HTML排版结构和样式风格进行输出（请直接输出完整的HTML代码，不包含其他说明文字）。\n\n---\n**重要：微信公众号文章内容输出规范**\n1.  **HTML格式：** 必须使用标准的HTML标签和内联`style`属性。\n2.  **禁止JavaScript：** 禁止使用任何JavaScript代码，包括`<script>`标签、`javascript:`协议的链接以及所有HTML元素的`on`事件属性（如`onclick`, `onload`等）。\n4.  **字符数限制：** 最终输出的HTML内容总字符数必须小于等于{char_limit}字符，且可见文本字数约为{word_count_str}。请注意HTML标签和样式本身会占用字符，请在保证排版效果的前提下尽量简洁。\n5.  **禁止外部CSS/内嵌<style>：** 禁止使用外部CSS文件或在HTML中嵌入`<style>`标签，所有样式必须通过元素的`style=""`属性以内联形式声明。\n6.  **`backdrop-filter` 兼容性：** 如果样式定义中包含`backdrop-filter`属性，请注意其在微信Webview中的兼容性可能不稳定，建议作为可选效果，或考虑使用半透明背景替代。\n\nHTML标签使用规范：\n- <h2>、<h3> 用于段落标题\n- <p> 用于正文段落\n- <ul>、<li> 用于要点列表\n- <blockquote> 用于引用或重要观点\n- <strong> 用于强调重要内容\n\n请直接输出HTML格式的文章内容，不要包含其他说明文字或代码块之外的任何文本："
    

    # 摘要生成提示词（通用）
    @staticmethod
    def digest_prompt(title, content_preview, role_prompt=None):
        role_desc = role_prompt if role_prompt else PromptManager.ROLE_PROMPT
        return f"""{role_desc}\n请为以下文章生成一个简洁的摘要：\n\n标题：{title}\n内容预览：{content_preview}\n\n要求：\n1. 摘要长度不超过100字\n2. 概括文章的核心内容和价值\n3. 语言吸引人，能激发读者的阅读兴趣\n4. 不要包含HTML标签，纯文本即可\n5. 使用中文表达\n\n请直接输出摘要内容，不要包含任何其他说明文字："""

    # 生图生成提示词（Gemini/海报风格）
    # @staticmethod
    # def image_prompt(title, description="", user_custom=""):
    #     if user_custom:
    #         base_prompt = f"{PromptManager.ROLE_PROMPT}\n{user_custom}"
    #     else:
    #         base_prompt = f"{PromptManager.ROLE_PROMPT}\n为文章《{title}》生成一张高质量的海报风格配图。\n\n要求：\n1. 图片风格现代、简洁、专业，具有海报感\n2. 色调温和，适合微信公众号\n3. 构图美观，有设计感\n4. 与文章主题相关\n5. 图片中不要包含过多文字，最好无文字，仅以视觉元素表达主题\n6. 尺寸比例适合作为文章封面\n7. 使用中国读者喜欢的视觉元素\n"
    #     if description:
    #         base_prompt += f"\n\n文章描述：{description}\n请根据文章内容生成相关的视觉元素。"
    #     return base_prompt

    # 生图生成提示词（带风格）
    @staticmethod
    def image_prompt_with_style(title, description="", user_style=""):
        # user_style 动态替换风格/景别/运镜部分
        base_prompt = f"为文章《{title}》生成一张高质量的配图。"
        if user_style:
            # 用户输入替换默认风格
            style_line = f"图片风格：{user_style}。"
        else:
            style_line = "图片风格现代、简洁、专业，具有海报感。"
        base_prompt += f"\n要求：\n1. {style_line}\n2. 色调温和，适合微信公众号\n3. 构图美观，有设计感\n4. 与文章主题相关\n5. 图片中不要包含过多文字，最好无文字，仅以视觉元素表达主题\n6. 尺寸比例适合作为文章封面\n7. 使用中国读者喜欢的视觉元素"
        if description:
            base_prompt += f"\n\n文章描述：{description}\n请根据文章内容生成相关的视觉元素。"
        # 追加英文提示
        base_prompt += "\n\n请用英文输出提示词。"
        return base_prompt

    # Pexels图片搜索AI提示词
    @staticmethod
    def pexels_search_prompt(analysis_text, image_index=1, total_images=1):
        return f"""{PromptManager.ROLE_PROMPT}\n请根据以下文章信息，生成适合在Pexels图片库中搜索相关图片的英文关键词。\n\n文章信息：\n{analysis_text}\n\n图片信息：\n- 这是第{image_index}张图片，总共需要{total_images}张图片\n- 每张图片应该有不同的视觉风格和内容重点\n- 请为这张图片生成独特的关键词组合\n\n要求：\n1. 生成2-4个英文关键词，用空格分隔\n2. 关键词要准确反映文章的主题和内容\n3. 关键词要适合图片搜索，避免抽象概念\n4. 优先使用具体的、可视化的词汇\n5. 考虑文章的情感色彩和风格\n6. 关键词要简洁明了，适合搜索引擎\n7. 根据图片位置生成不同的关键词组合，避免重复\n\n关键词变化建议：\n- 第1张图片：关注文章的核心主题和主要概念\n- 第2张图片：关注具体的应用场景或案例\n- 第3张图片：关注技术细节或方法\n- 第4张图片：关注结果或效果\n- 第5张图片：关注未来趋势或展望\n\n示例：\n- 如果文章关于\"人工智能在医疗领域的应用\"：\n  - 第1张图片：\"medical technology artificial intelligence\"\n  - 第2张图片：\"hospital doctor patient care\"\n  - 第3张图片：\"medical diagnosis treatment\"\n  - 第4张图片：\"healthcare innovation research\"\n  - 第5张图片：\"future medicine technology\"\n\n请直接输出关键词，不要包含任何其他说明文字：""" 

    # 抖音热点markdown→大模型标题生成提示词
    @staticmethod
    def douyin_hotspot_title_prompt(markdown, industry=None):
        logger = logging.getLogger(__name__)
        logger.info(f"生成抖音热点标题prompt，industry={industry}, markdown内容前100字={markdown[:100]}")
        industry_str = f"（行业：{industry}）" if industry else ""
        prompt = f"""
{PromptManager.ROLE_PROMPT}
你将获得一份抖音平台{industry_str}的最新热点榜单（markdown格式），请基于这些热点内容，分析趋势和用户关注点，输出一个最适合用来写微信公众号文章的标题，要求：\n1. 标题要新颖、有吸引力，能引发读者兴趣\n2. 结合榜单内容，体现行业热点或趋势\n3. 语言简洁有力，适合公众号推文\n4. 只输出标题本身，不要包含任何说明或格式化内容\n\n抖音热点榜单如下：\n{markdown}\n\n请直接输出建议标题："""
        logger.info(f"生成的prompt内容前200字：{prompt[:200]}")
        return prompt 