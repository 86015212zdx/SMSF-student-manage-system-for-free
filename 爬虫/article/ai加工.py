import os
import json
import re
import time

import pymysql
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models

# 腾讯云API密钥
SECRET_ID = ""  # 替换为您的SecretId
SECRET_KEY = ""

# MySQL数据库配置
MYSQL_CONFIG = {}

class TencentTranslator:
    """腾讯云翻译API封装类"""

    def __init__(self, secret_id=None, secret_key=None, region="ap-guangzhou"):
        """
        初始化翻译器

        Args:
            secret_id (str): 腾讯云SecretId
            secret_key (str): 腾讯云SecretKey
            region (str): 区域，默认广州
        """
        # 从环境变量获取密钥（推荐方式）
        self.secret_id = secret_id or os.getenv("TENCENTCLOUD_SECRET_ID")
        self.secret_key = secret_key or os.getenv("TENCENTCLOUD_SECRET_KEY")
        self.region = region

        if not self.secret_id or not self.secret_key:
            raise ValueError("请设置腾讯云密钥：TENCENTCLOUD_SECRET_ID 和 TENCENTCLOUD_SECRET_KEY")

        # 初始化客户端
        self._init_client()

    def _init_client(self):
        """初始化API客户端"""
        try:
            # 实例化认证对象
            cred = credential.Credential(self.secret_id, self.secret_key)

            # HTTP配置
            httpProfile = HttpProfile()
            httpProfile.endpoint = "tmt.tencentcloudapi.com"

            # 客户端配置
            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile

            # 创建客户端
            self.client = tmt_client.TmtClient(cred, self.region, clientProfile)

        except Exception as e:
            raise TencentCloudSDKException(f"客户端初始化失败: {str(e)}")

    def translate_text(self, source_text, source_lang="auto", target_lang="zh",
                       project_id=0, untranslated_text=""):
        """
        文本翻译

        Args:
            source_text (str): 源文本
            source_lang (str): 源语言，如 'auto', 'en', 'zh', 'ja' 等
            target_lang (str): 目标语言，如 'zh', 'en', 'ja' 等
            project_id (int): 项目ID，默认0
            untranslated_text (str): 不翻译的词，多个词用分号分隔

        Returns:
            dict: 翻译结果
        """
        try:
            # 创建请求对象
            req = models.TextTranslateRequest()

            # 设置参数
            params = {
                "SourceText": source_text,
                "Source": source_lang,
                "Target": target_lang,
                "ProjectId": project_id
            }

            if untranslated_text:
                params["UntranslatedText"] = untranslated_text

            req.from_json_string(json.dumps(params))

            # 发送请求
            resp = self.client.TextTranslate(req)

            # 解析响应
            result = {
                "target_text": resp.TargetText,
                "source": resp.Source,
                "target": resp.Target,
                "request_id": resp.RequestId
            }

            return result

        except TencentCloudSDKException as e:
            raise TencentCloudSDKException(f"翻译请求失败: {str(e)}")

    def batch_translate(self, text_list, source_lang="auto", target_lang="zh",
                        project_id=0):
        """
        批量文本翻译

        Args:
            text_list (list): 待翻译文本列表
            source_lang (str): 源语言
            target_lang (str): 目标语言
            project_id (int): 项目ID

        Returns:
            list: 翻译结果列表
        """
        results = []
        for text in text_list:
            try:
                result = self.translate_text(text, source_lang, target_lang, project_id)
                results.append(result)
            except Exception as e:
                results.append({
                    "error": str(e),
                    "source_text": text
                })
        return results

    def get_supported_languages(self):
        """
        获取支持的语言列表
        注意：腾讯云API没有直接的语言列表接口，这里提供常用语言代码
        """
        return {
            "auto": "自动识别",
            "zh": "中文",
            "en": "英语",
            "ja": "日语",
            "ko": "韩语",
            "fr": "法语",
            "es": "西班牙语",
            "ru": "俄语",
            "ar": "阿拉伯语",
            "th": "泰语",
            "vi": "越南语"
        }


class TranslationProcessor:
    """翻译处理器，整合翻译和数据库操作"""
    
    def __init__(self):
        """初始化翻译处理器"""
        self.translator = TencentTranslator(SECRET_ID, SECRET_KEY)
        self.mysql_config = MYSQL_CONFIG
        
    def parse_txt_file(self, file_path: str) -> dict:
        """
        解析TXT文件，提取段落内容
        
        Args:
            file_path (str): TXT文件路径
            
        Returns:
            dict: 包含标题和段落的字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.strip().split('\n')
            title = ""
            paragraphs = []
            
            # 提取标题
            for line in lines:
                if line.startswith("标题: "):
                    title = line.replace("标题: ", "").strip()
                    break
            
            # 提取段落内容
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith("=================================================="):
                    header_end = i + 1
                    break
            
            # 提取段落
            for line in lines[header_end:]:
                line = line.strip()
                if line and re.match(r'^\d+\.\s', line):
                    paragraph_content = re.sub(r'^\d+\.\s*', '', line)
                    if paragraph_content:
                        paragraphs.append(paragraph_content)
            
            return {
                "title": title,
                "paragraphs": paragraphs
            }
            
        except Exception as e:
            print(f"❌ 文件解析失败 {file_path}: {str(e)}")
            return {}
    
    def translate_paragraphs(self, paragraphs: list) -> list:
        """
        翻译段落列表
        
        Args:
            paragraphs (list): 英文段落列表
            
        Returns:
            list: 翻译后的中文段落列表
        """
        print(f"🔄 开始翻译 {len(paragraphs)} 个段落...")
        translated_paragraphs = []
        
        for i, paragraph in enumerate(paragraphs, 1):
            try:
                print(f"   翻译第 {i}/{len(paragraphs)} 段...")
                result = self.translator.translate_text(
                    source_text=paragraph,
                    source_lang="en",
                    target_lang="zh"
                )
                translated_paragraphs.append(result['target_text'])
                time.sleep(0.5)
            except Exception as e:
                print(f"   ❌ 第 {i} 段翻译失败: {str(e)}")
                translated_paragraphs.append(f"[翻译失败: {str(e)}]")
        
        return translated_paragraphs
    
    def generate_cover_picture_url(self, title: str) -> str:
        """
        生成封面图片URL路径（不带时间戳，确保与实际文件名一致）
        
        Args:
            title (str): 文章标题
            
        Returns:
            str: 封面图片路径
        """
        # 清理标题中的非法字符
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title.strip())
        # 限制长度
        if len(safe_title) > 50:
            safe_title = safe_title[:50]
        # 不添加时间戳，使用统一的文件名
        filename = f"{safe_title}.jpg"
        
        # 返回指定路径格式
        return f"/static/article_covers/{filename}"
    
    def update_translation_in_db(self, title: str, translated_content: str):
        """
        更新数据库中的翻译内容和封面图片路径
        
        Args:
            title (str): 文章标题
            translated_content (str): 翻译后的内容
        """
        try:
            conn = pymysql.connect(**self.mysql_config)
            cursor = conn.cursor()
            
            # 生成封面图片路径
            cover_picture_url = self.generate_cover_picture_url(title)
            
            # 同时更新translation和cover_picture_url字段
            sql = "UPDATE passage SET translation = %s, cover_picture_url = %s WHERE title = %s"
            cursor.execute(sql, (translated_content, cover_picture_url, title))
            
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            if affected_rows > 0:
                print(f"✅ 成功更新 {affected_rows} 条记录的翻译内容和封面路径")
                print(f"🖼️  封面图片路径: {cover_picture_url}")
            else:
                print(f"⚠️  未找到标题为 '{title}' 的记录")
                
        except Exception as e:
            print(f"❌ 数据库更新失败: {str(e)}")
    
    def process_txt_file(self, file_path: str):
        """
        处理TXT文件：读取段落→翻译→更新数据库
        
        Args:
            file_path (str): TXT文件路径
        """
        print(f"🚀 开始处理文件: {os.path.basename(file_path)}")
        print("=" * 50)
        
        # 1. 解析文件
        article_data = self.parse_txt_file(file_path)
        if not article_data or not article_data.get('paragraphs'):
            print("❌ 无法解析文件或无段落内容")
            return
        
        title = article_data['title']
        paragraphs = article_data['paragraphs']
        
        print(f"📚 文章标题: {title}")
        print(f"📝 段落数量: {len(paragraphs)}")
        
        # 2. 翻译段落
        translated_paragraphs = self.translate_paragraphs(paragraphs)
        
        # 3. 拼接翻译后的内容（段落间用两个换行符分隔）
        combined_translation = '\n\n'.join(translated_paragraphs)
        print(f"📄 翻译后内容长度: {len(combined_translation)} 字符")
        
        # 4. 更新数据库
        self.update_translation_in_db(title, combined_translation)
        
        print("=" * 50)
        print("🎉 文件处理完成!")


def tra(con):
    """保持向后兼容的简单翻译函数"""
    translator = TencentTranslator(SECRET_ID, SECRET_KEY)
    result = translator.translate_text(
        source_text=con,
        source_lang="en",
        target_lang="zh"
    )
    return result['target_text']


def process_file(filepath):
    """处理单个文件的便捷函数"""
    processor = TranslationProcessor()
    processor.process_txt_file(filepath)


def demo_usage_ai():
    """使用示例"""
    # 获取当前目录下的所有TXT文件（排除特定文件）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    exclude_files = {'all_res.txt', 'data.txt'}  # 要排除的文件名集合
    txt_files = [f for f in os.listdir(current_dir)
                 if f.endswith('.txt') and f not in exclude_files]

    if txt_files:
        print(f"📁 发现 {len(txt_files)} 个TXT文件:")
        for txt_file in txt_files:
            print(f"   - {txt_file}")

        # 处理第一个文件作为示例
        if txt_files:
            first_file = os.path.join(current_dir, txt_files[0])
            process_file(first_file)
    else:
        print("❌ 当前目录下未发现可处理的TXT文件")


#
# if __name__ == "__main__":
#     demo_usage_ai()

