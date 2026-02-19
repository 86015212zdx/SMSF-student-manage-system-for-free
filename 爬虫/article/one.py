import requests
import re
import os
import html
from datetime import datetime


def extract_og_image_url(html_text):
    """
    精准提取<meta property="og:image">标签中的图片URL
    :param html_text: 包含该meta标签的HTML文本
    :return: 提取到的图片URL（无则返回空字符串）
    """
    # 核心正则：精准匹配og:image的meta标签，提取content里的URL
    pattern = r'<meta property="og:image" content="([^"]+)"'
    match = re.search(pattern, html_text)
    if match:
        return match.group(1)
    return ""

class ArticleDataCleaner:
    def __init__(self):
        # 定义各种需要清洗的模式
        self.patterns = {
            'html_tags': r'<[^>]+>',  # HTML标签
            'empty_strong': r'<strong>\s*</strong>',  # 空的strong标签
            'multiple_spaces': r'\s+',  # 多个空格
            'nbsp': r'&nbsp;',  # 不间断空格
            'special_chars': r'[\xa0\u200b\u200c\u200d]',  # 特殊空白字符
            'copyright_patterns': [  # 版权相关信息模式
                r'©.*?\d{4}.*?(?:Privacy Policy|Terms of Use).*',
                r'Aeon is published by.*?charity.*?',
                r'Registered charity.*?\d+\(c\)\(\d+\).*?charity',
                r'Media Group Ltd.*?\d{4}.*?\d{4}',
            ],
            'footer_patterns': [  # 页脚无关信息
                r'Privacy Policy.*?Terms of Use',
                r'All rights reserved',
                r'Published by.*?(?:association|partnership)',
            ]
        }

    def clean_html_content(self, content):
        """清洗HTML内容"""
        if not content:
            return ""

        # 解码HTML实体
        content = html.unescape(content)

        # 移除HTML标签
        content = re.sub(self.patterns['html_tags'], '', content)

        # 移除空的strong标签
        content = re.sub(self.patterns['empty_strong'], '', content)

        # 清理特殊字符
        content = re.sub(self.patterns['special_chars'], ' ', content)

        # 清理不间断空格
        content = re.sub(self.patterns['nbsp'], ' ', content)

        # 规范化空白字符
        content = re.sub(self.patterns['multiple_spaces'], ' ', content)

        # 去除首尾空白
        content = content.strip()

        return content

    def clean_article_data(self, title, author, date, content_list):
        """清洗完整文章数据"""
        cleaned_data = {
            'title': self.clean_html_content(title) if title else "",
            'author': self.clean_html_content(author) if author else "",
            'date': self.clean_date(date) if date else "",
            'content': []
        }

        # 清洗每个段落并过滤无关内容
        for paragraph in content_list:
            cleaned_paragraph = self.clean_html_content(paragraph)
            if (cleaned_paragraph and
                not self.is_footer_content(cleaned_paragraph) and
                len(cleaned_paragraph.strip()) > 10):  # 过滤过短的内容
                cleaned_data['content'].append(cleaned_paragraph)

        return cleaned_data

    def is_footer_content(self, content):
        """判断是否为页脚无关内容"""
        content_lower = content.lower().strip()

        # 检查版权模式
        for pattern in self.patterns['copyright_patterns']:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        # 检查页脚模式
        for pattern in self.patterns['footer_patterns']:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        # 检查特定关键词
        footer_keywords = [
            'privacy policy', 'terms of use', 'all rights reserved',
            'registered charity', 'media group', 'published by'
        ]

        keyword_count = sum(1 for keyword in footer_keywords
                          if keyword in content_lower)

        # 如果包含多个页脚关键词，则认为是页脚内容
        return keyword_count >= 2

    def clean_date(self, date_string):
        """清洗和标准化日期格式"""
        if not date_string:
            return ""

        try:
            # 尝试解析日期
            date_obj = datetime.strptime(date_string.strip(), '%d %B %Y')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            # 如果解析失败，返回原始字符串
            return date_string.strip()

    def save_cleaned_data(self, cleaned_data, filename=None):
        """保存清洗后的数据"""
        if not filename:
            # 基于标题生成文件名
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', cleaned_data['title'][:50])
            filename = f"{safe_title}_{cleaned_data['date']}.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            # 写入文章头部信息
            f.write(f"标题: {cleaned_data['title']}\n")
            f.write(f"作者: {cleaned_data['author']}\n")
            f.write(f"日期: {cleaned_data['date']}\n")
            f.write("=" * 50 + "\n\n")

            # 写入正文内容
            for i, paragraph in enumerate(cleaned_data['content'], 1):
                f.write(f"{i}. {paragraph}\n\n")

        return filename

def sanitize_filename(filename):
    """
    清理文件名，移除非法字符

    Args:
        filename (str): 原始文件名

    Returns:
        str: 清理后的安全文件名
    """
    # 移除或替换Windows非法字符
    illegal_chars = '<>:"/\|?*'
    for char in illegal_chars:
        filename = filename.replace(char, '_')

    # 限制文件名长度
    if len(filename) > 100:
        filename = filename[:100]

    # 移除首尾空格和点
    filename = filename.strip('. ')

    # 如果文件名为空，使用默认名称
    if not filename:
        filename = "cover_image"

    return filename + ".jpg"


def one_main(url):
    cookies = {}

    headers = {}

    response = requests.get(
        url,
        cookies=cookies,
        headers=headers,
    )
    if response.status_code == 200:
        print("INFO--抓取成功")
    tit_pattern = r"article_name=(.*?)&amp;author=(.*)&amp;date=(.*?)\""
    smal_tit = r"<meta name=\"description\" content=\"(.*?)\"/>"
    cont_p = r"<p>(.*?)</p>"

    pict_url = extract_og_image_url(response.text)
    print("INFO--解析到图像地址" + pict_url)

    cleaner = ArticleDataCleaner()

    # 提取基本信息
    title_match = re.findall(tit_pattern, response.text)
    meta_match = re.findall(smal_tit, response.text)
    content_matches = re.findall(cont_p, response.text)

    if title_match:
        title, author, date = title_match[0]
        print(f"标题: {cleaner.clean_html_content(title)}")
        print(f"作者: {cleaner.clean_html_content(author)}")
        print(f"日期: {cleaner.clean_date(date)}")

    if meta_match:
        description = cleaner.clean_html_content(meta_match[0])
        print(f"描述: {description}")

    cleaned_content = []
    for paragraph in content_matches:
        cleaned_para = cleaner.clean_html_content(paragraph)
        if cleaned_para:  # 只保留非空段落
            cleaned_content.append(cleaned_para)

    # 使用专业清洗器处理完整数据
    cleaned_data = cleaner.clean_article_data(
        title=title if title_match else "",
        author=author if title_match else "",
        date=date if title_match else "",
        content_list=content_matches
    )

    # 保存清洗后的数据
    output_file = cleaner.save_cleaned_data(cleaned_data)
    print(f"\n✅ 数据清洗完成，已保存至: {output_file}")
    print(f"📊 清洗统计: 原始段落数 {len(content_matches)}, 清洗后段落数 {len(cleaned_data['content'])}")

    print("INFO--爬取封面中")
    headers = {
        'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://aeon.co/',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'image',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-storage-access': 'active',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    }

    params = {
        'width': '1920',
        'quality': '75',
        'format': 'auto',
    }
    response = requests.get(
        re.sub(r"\?width=1200&amp;quality=75&amp;format=jpg", "", pict_url),
        params=params,
        headers=headers,
    )
    print("INFO--保存封面中")
    # 使用清理后的安全文件名
    safe_filename = sanitize_filename(title_match[0][0])

    # 1. 获取当前脚本所在的文件夹
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. 从脚本目录出发，构建目标目录的绝对路径
    # 这里的 ".." 表示从脚本目录（例如 article 文件夹）向上走一级
    target_dir = os.path.join(script_dir, "..","..", "web", "static", "article_covers")

    # 3. 确保目录存在
    os.makedirs(target_dir, exist_ok=True)

    safe_filename = sanitize_filename(title_match[0][0])

    file_path = os.path.join(target_dir, safe_filename)

    with open(file_path, 'wb') as f:
        f.write(response.content)
    print(f"✅ 封面已保存为: {safe_filename}")
    print("✅ 文件已保存到:", os.path.abspath(file_path))
