# -*- coding: utf-8 -*-
"""
文章段落数据库导入工具
Professional Article Paragraph Database Importer
"""

import pymysql
import os
import re
from typing import List, Dict


# MySQL数据库配置
MYSQL_CONFIG = {}

class ArticleDatabaseImporter:
    """文章段落数据库导入器"""
    
    def __init__(self):
        """
        初始化数据库导入器，使用MySQL配置
        """
        self.mysql_config = MYSQL_CONFIG
        self.init_database()
    
    def init_database(self):
        """验证数据库连接和表结构"""
        try:
            conn = pymysql.connect(**self.mysql_config)
            cursor = conn.cursor()
            
            # 验证passage表是否存在
            cursor.execute("SHOW TABLES LIKE 'passage'")
            result = cursor.fetchone()
            
            if result:
                print("✅ passage表已存在")
                # 验证表结构
                cursor.execute("DESCRIBE passage")
                columns = cursor.fetchall()
                print("📋 passage表结构:")
                for col in columns:
                    print(f"   {col[0]} ({col[1]}) - {'主键' if col[3] == 'PRI' else '普通字段'}")
            else:
                print("❌ passage表不存在，请先创建表")
                raise Exception("passage表不存在")
            
            conn.close()
            print("✅ MySQL数据库连接验证成功")
            
        except Exception as e:
            print(f"❌ 数据库连接验证失败: {str(e)}")
            raise
    
    def parse_txt_file(self, file_path: str) -> Dict:
        """
        解析TXT文件，提取标题、作者、日期和段落内容
        
        Args:
            file_path (str): TXT文件路径
            
        Returns:
            dict: 包含文章信息的字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 分割文件内容
            lines = content.strip().split('\n')
            
            # 提取头部信息
            title = ""
            author = ""
            date = ""
            paragraphs = []
            
            # 解析头部信息
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith("标题: "):
                    title = line.replace("标题: ", "").strip()
                elif line.startswith("作者: "):
                    author = line.replace("作者: ", "").strip()
                elif line.startswith("日期: "):
                    date = line.replace("日期: ", "").strip()
                elif line.startswith("=================================================="):
                    header_end = i + 1
                    break
            
            # 提取段落内容
            for line in lines[header_end:]:
                line = line.strip()
                if line and re.match(r'^\d+\.\s', line):  # 匹配段落编号格式
                    # 提取段落内容（去掉编号）
                    paragraph_content = re.sub(r'^\d+\.\s*', '', line)
                    if paragraph_content:
                        paragraphs.append(paragraph_content)
            
            return {
                "title": title,
                "author": author,
                "date": date,
                "paragraphs": paragraphs
            }
            
        except Exception as e:
            print(f"❌ 文件解析失败 {file_path}: {str(e)}")
            return {}
    
    def format_paragraph_content(self, paragraph: str) -> str:
        """
        格式化段落内容，清理多余空白
        
        Args:
            paragraph (str): 原始段落内容
            
        Returns:
            str: 格式化后的段落内容
        """
        # 清理多余的空白字符
        return re.sub(r'\s+', ' ', paragraph.strip())
    
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
    
    def import_article_to_db(self, article_data: Dict) -> int:
        """
        将文章数据导入MySQL数据库，将所有段落拼接成一个记录
        
        Args:
            article_data (dict): 文章数据字典
            
        Returns:
            int: 成功插入的记录数（应该为1）
        """
        if not article_data or not article_data.get('paragraphs'):
            print("❌ 文章数据为空或无段落内容")
            return 0
        
        try:
            conn = pymysql.connect(**self.mysql_config)
            cursor = conn.cursor()
            
            title = article_data['title']
            paragraphs = article_data['paragraphs']
            
            # 生成封面图片路径
            cover_picture_url = self.generate_cover_picture_url(title)
            
            # 将所有段落拼接，每段之间用两个换行符分隔
            combined_content = '\n\n'.join([
                self.format_paragraph_content(paragraph) 
                for paragraph in paragraphs
            ])
            
            # 插入单条记录，包含封面图片路径
            sql = '''
                INSERT INTO passage (title, content, reading_number, cover_picture_url, translation)
                VALUES (%s, %s, %s, %s, %s)
            '''
            cursor.execute(sql, (title, combined_content, 0, cover_picture_url, ''))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 成功导入文章记录")
            print(f"📚 文章标题: {title}")
            print(f"📝 段落数量: {len(paragraphs)}")
            print(f"📄 合并后内容长度: {len(combined_content)} 字符")
            print(f"🖼️  封面图片路径: {cover_picture_url}")
            
            return 1
            
        except Exception as e:
            print(f"❌ 数据库插入失败: {str(e)}")
            return 0
    
    def import_txt_file(self, file_path: str) -> int:
        """
        导入单个TXT文件
        
        Args:
            file_path (str): TXT文件路径
            
        Returns:
            int: 成功导入的记录数
        """
        print(f"📥 开始导入文件: {os.path.basename(file_path)}")
        
        # 解析文件
        article_data = self.parse_txt_file(file_path)
        if not article_data:
            return 0
        
        # 导入数据库
        return self.import_article_to_db(article_data)
    
    def import_multiple_files(self, file_paths: List[str]) -> Dict:
        """
        批量导入多个文件
        
        Args:
            file_paths (list): 文件路径列表
            
        Returns:
            dict: 导入统计信息
        """
        stats = {
            "total_files": len(file_paths),
            "successful_files": 0,
            "failed_files": 0,
            "total_paragraphs": 0
        }
        
        print(f"📥 开始批量导入 {len(file_paths)} 个文件")
        print("=" * 50)
        
        for i, file_path in enumerate(file_paths, 1):
            print(f"\n[{i}/{len(file_paths)}] 处理文件: {os.path.basename(file_path)}")
            
            try:
                inserted_count = self.import_txt_file(file_path)
                if inserted_count > 0:
                    stats["successful_files"] += 1
                    stats["total_paragraphs"] += inserted_count
                else:
                    stats["failed_files"] += 1
                    
            except Exception as e:
                print(f"❌ 文件处理失败: {str(e)}")
                stats["failed_files"] += 1
        
        print("\n" + "=" * 50)
        print("📊 导入统计:")
        print(f"   总文件数: {stats['total_files']}")
        print(f"   成功文件: {stats['successful_files']}")
        print(f"   失败文件: {stats['failed_files']}")
        print(f"   总段落数: {stats['total_paragraphs']}")
        
        return stats
    
    def get_database_stats(self) -> Dict:
        """
        获取MySQL数据库统计信息
        
        Returns:
            dict: 数据库统计信息
        """
        try:
            conn = pymysql.connect(**self.mysql_config)
            cursor = conn.cursor()
            
            # 获取总记录数
            cursor.execute("SELECT COUNT(*) FROM passage")
            total_records = cursor.fetchone()[0]
            
            # 获取不同文章标题数
            cursor.execute("SELECT COUNT(DISTINCT title) FROM passage")
            unique_titles = cursor.fetchone()[0]
            
            # 获取阅读次数统计
            cursor.execute("SELECT COALESCE(SUM(reading_number), 0) FROM passage")
            total_readings = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_records": total_records,
                "unique_titles": unique_titles,
                "total_readings": total_readings
            }
            
        except Exception as e:
            print(f"❌ 获取数据库统计失败: {str(e)}")
            return {}

def demo_usage():
    """使用示例"""
    print("📚 文章段落数据库导入工具演示")
    print("=" * 50)
    
    # 初始化导入器
    try:
        importer = ArticleDatabaseImporter()
    except Exception as e:
        print(f"❌ 导入器初始化失败: {str(e)}")
        return
    
        # 获取当前目录下的所有TXT文件（排除特定文件）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    exclude_files = {'all_res.txt', 'data.txt'}  # 要排除的文件名集合
    txt_files = [f for f in os.listdir(current_dir)
                 if f.endswith('.txt') and f not in exclude_files]

    if txt_files:
        print(f"📁 发现 {len(txt_files)} 个TXT文件:")
        for txt_file in txt_files:
            print(f"   - {txt_file}")

        # 导入文件
        file_paths = [os.path.join(current_dir, f) for f in txt_files]
        stats = importer.import_multiple_files(file_paths)

        # 显示数据库统计
        print("\n📊 数据库当前状态:")
        db_stats = importer.get_database_stats()
        for key, value in db_stats.items():
            print(f"   {key}: {value}")

    else:
        print("❌ 当前目录下未发现可导入的TXT文件")

#
# if __name__ == "__main__":
#     demo_usage()