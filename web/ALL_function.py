import binascii
import hashlib
import secrets
import ast
import csv
import re
import smtplib
import random
from email.mime.text import MIMEText
from email.header import Header
from openai import OpenAI

# 添加MySQL支持
import pymysql

# MySQL数据库配置
MYSQL_CONFIG = {}


# 邮箱验证相关配置
EMAIL_CONFIG = {}

# 存储验证码的全局变量（实际应用中应该使用缓存或数据库）
verification_codes = {}


def connect_db(database='smsf'):
    # 连接到MySQL数据库
    try:
        config = MYSQL_CONFIG.copy()
        config['database'] = database
        conn = pymysql.connect(**config)
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        # 尝试重新连接
        try:
            config = MYSQL_CONFIG.copy()
            config['database'] = database
            conn = pymysql.connect(**config)
            return conn
        except Exception as e2:
            print(f"数据库重连失败: {e2}")
            raise e2


def read_study_resources(conn):
    """读取学习资源数据"""
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查询res表中的所有资源
        cursor.execute('''
            SELECT type, id, name, introduce, subject
            FROM res
            ORDER BY id DESC
        ''')
        
        resources = cursor.fetchall()
        
        # 获取学科映射信息
        subject_mapping = {}
        try:
            # noinspection SqlResolve
            cursor.execute('''
                SELECT id_s, subject 
                FROM sub
            ''')
            subjects = cursor.fetchall()
            subject_mapping = {str(row['id_s']): row['subject'] for row in subjects}
        except Exception as e:
            print(f"读取学科映射失败: {e}")
            # 如果sub表不存在，使用默认映射
            subject_mapping = {}
        
        # 转换数据格式以匹配前端需求
        formatted_resources = []
        type_mapping = {
            'v': '视频教程',
            't': '练习题库',
            'o': '其他资源'
        }
        
        category_mapping = {
            'v': 'video',
            't': 'exercise',
            'o': 'other'
        }
        
        icon_mapping = {
            'v': 'fas fa-video',
            't': 'fas fa-tasks',
            'o': 'fas fa-file-alt'
        }
        
        for resource in resources:
            resource_type = resource['type']
            # 获取学科名称，如果subject字段存在且能映射到学科名称
            subject_name = '未分类'
            if resource['subject'] and str(resource['subject']) in subject_mapping:
                subject_name = subject_mapping[str(resource['subject'])]
            
            formatted_resource = {
                'id': resource['id'],
                'title': resource['name'],
                'description': resource['introduce'],
                'type': type_mapping.get(resource_type, '其他资源'),
                'category': category_mapping.get(resource_type, 'other'),
                'icon': icon_mapping.get(resource_type, 'fas fa-file-alt'),
                'tags': [subject_name],
                'subject_id': resource['subject'],  # 保留原始学科ID用于筛选
                'downloads': random.randint(1000, 20000),  # 模拟下载量
                'rating': round(random.uniform(4.0, 5.0), 1),  # 模拟评分
                'date': '2026-01-15'  # 模拟发布日期
            }
            formatted_resources.append(formatted_resource)
        
        return formatted_resources
        
    except Exception as e:
        print(f"读取学习资源失败: {e}")
        return []

def read_all_subjects(conn):
    """读取所有学科信息"""
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查询sub表中的所有学科
        cursor.execute('''
            SELECT id_s, subject
            FROM sub
            ORDER BY subject
        ''')
        
        subjects = cursor.fetchall()
        # 返回兼容前端期望的数据结构
        return [{'id_s': row['id_s'], 'subject': row['subject']} for row in subjects]
        
    except Exception as e:
        print(f"读取学科信息失败: {e}")
        return []

def check_user_account_type(account):
    """
    检查用户账户类型，在free_account库的acc表和smsf库的teachers表中进行匹配
    
    参数:
    account: 账户名
    
    返回:
    str: "student" 如果在acc表中匹配到，"teacher" 如果在teachers表中匹配到，None 如果都未匹配到
    """
    try:
        # 首先检查free_account库的acc表
        free_conn = connect_db('free_account')
        cursor = free_conn.cursor()
        
        # 查询acc表中是否存在该账户
        cursor.execute('''
            SELECT `account` FROM `acc` WHERE `account` = %s
        ''', (account,))
        
        result = cursor.fetchone()
        free_conn.close()
        
        if result:
            print(f"在free_account.acc表中找到账户: {account}")
            return "student"
        
        # 如果在acc表中未找到，则检查smsf库的teachers表
        smsf_conn = connect_db('smsf')
        cursor = smsf_conn.cursor()
        
        # 查询teachers表中是否存在该账户
        cursor.execute('''
            SELECT `账户` FROM `teachers` WHERE `账户` = %s
        ''', (account,))
        
        result = cursor.fetchone()
        smsf_conn.close()
        
        if result:
            print(f"在smsf.teachers表中找到账户: {account}")
            return "teacher"
        
        print(f"未在任何表中找到账户: {account}")
        return None
        
    except Exception as e:
        print(f"检查用户账户类型时发生错误: {e}")
        return None


def add_free_account(name, account, password, email=None):
    """添加自由账户"""
    conn = None
    try:
        conn = connect_db("free_account")
        cursor = conn.cursor()

        # 对密码进行哈希处理，使用固定盐值确保验证一致性
        fixed_salt = '0' * 32  # 使用32个0作为固定盐值
        pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), fixed_salt.encode('ascii'), 100000)
        hashed_password = binascii.hexlify(pwdhash).decode('ascii')

        # 插入账户信息，包含邮箱字段
        cursor.execute('''
            INSERT INTO `acc` (`name`, `account`, `password`, `email`, `rank`, `exp`, `info`, `friend`,`study_time`)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (name, account, hashed_password, email or '', 1, 0, '{}', '{}',0))

        cursor.execute('''
        INSERT INTO `vo_book` (`account`, `uf_word_book`, `pass_w_b`)
        VALUES (%s, %s, %s)
        ''',(account,'{}', '{}'))

        conn.commit()
        print(f"✅ 自由账户 {account} 创建成功")
        return True
    except pymysql.IntegrityError as e:
        print(f"❌ 账户创建失败（账户已存在）: {e}")
        return False
    except Exception as e:
        print(f"❌ 添加自由账户时发生错误: {e}")
        return False
    finally:
        if conn:
            conn.close()


def authenticate_free_account(account, password):
    """验证自由账户登录"""
    conn = None
    try:
        conn = connect_db("free_account")
        cursor = conn.cursor()
        cursor.execute('''
            SELECT `password` FROM `acc` WHERE `account` = %s
        ''', (account,))

        result = cursor.fetchone()
        if result is None:
            return False

        stored_hash = result[0]
        # 使用固定的32个0作为盐值进行验证
        fixed_salt = '0' * 32
        pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), fixed_salt.encode('ascii'), 100000)
        input_hash = binascii.hexlify(pwdhash).decode('ascii')

        return input_hash == stored_hash
    except Exception as e:
        print(f"❌ 验证自由账户时发生错误: {e}")
        return False
    finally:
        if conn:
            conn.close()

def read_free_account_info(conn, account):
    """读取free_account表中的学生信息"""
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查询指定账户的学生信息，包含邮箱字段
        # 注意：表名为'acc'而不是'free_account'
        cursor.execute('''
            SELECT `name`, `account`, `email`, `rank`, `exp`, `info`, `friend`
            FROM `acc` 
            WHERE `account` = %s
        ''', (account,))
        
        student_info = cursor.fetchone()
        
        if not student_info:
            return None
        
        # 处理info和friend字段，默认为空字典{}
        try:
            info_data = ast.literal_eval(student_info['info']) if student_info['info'] else {}
        except:
            info_data = {}
            
        try:
            friend_data = ast.literal_eval(student_info['friend']) if student_info['friend'] else {}
        except:
            friend_data = {}
        
        # 返回格式化的学生信息
        return {
            'name': student_info['name'],
            'account': student_info['account'],
            'email': student_info.get('email', ''),  # 添加邮箱信息
            'rank': student_info['rank'] or 1,  # 默认等级1
            'exp': student_info['exp'] or 0,    # 默认经验0
            'info': info_data,
            'friend': friend_data
        }
        
    except Exception as e:
        print(f"读取学生信息失败: {e}")
        return None

def read_video_detail(conn, video_id):
    """读取单个视频的详细信息"""
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查询指定视频的基本信息
        cursor.execute('''
            SELECT r.type, r.id, r.name, r.introduce, r.subject
            FROM res r
            WHERE r.id = %s AND r.type = 'v'
        ''', (video_id,))
        
        video = cursor.fetchone()
        
        if not video:
            return None
        
        # 获取学科名称
        subject_name = '未分类'
        if video['subject']:
            try:
                cursor.execute('''
                    SELECT subject 
                    FROM sub 
                    WHERE id_s = %s
                ''', (video['subject'],))
                subject_result = cursor.fetchone()
                if subject_result:
                    subject_name = subject_result['subject']
            except Exception as e:
                print(f"获取学科名称失败: {e}")
        
        # 从pathh表获取视频路径
        video_path = ''
        try:
            cursor.execute('''
                SELECT path 
                FROM pathh 
                WHERE id = %s
            ''', (video_id,))
            path_result = cursor.fetchone()
            if path_result:
                video_path = path_result['path'] or ''
        except Exception as e:
            print(f"获取视频路径失败: {e}")
            video_path = ''
        
        # 处理视频路径 - 确保路径格式正确
        if video_path:
            # 移除Windows盘符和绝对路径前缀
            video_path = re.sub(r'^[A-Za-z]:\\', '', video_path)
            video_path = re.sub(r'^\\', '', video_path)
            
            # 将所有反斜杠转换为正斜杠（符合Web标准）
            video_path = re.sub(r'\\', '/', video_path)
            
            # 如果是相对路径，添加基础URL
            if not re.match(r'^https?://', video_path) and not video_path.startswith('/'):
                video_path = f'/video-files/{video_path}'
            # 确保路径以斜杠开头（相对路径）
            elif not video_path.startswith('/') and not re.match(r'^https?://', video_path):
                video_path = f'/{video_path}'
        
        # 构建视频详情数据
        video_detail = {
            'id': video['id'],
            'title': video['name'],
            'description': video['introduce'] or '暂无视频介绍',
            'subject': subject_name,
            'subject_id': video['subject'],
            'url': video_path,  # 视频文件路径
            'thumbnail': '',  # 缩略图路径，可根据需要添加
            'date': '2026-01-15',  # 模拟发布日期
            'views': random.randint(1000, 50000),  # 模拟观看次数
            'likes': random.randint(100, 5000),   # 模拟点赞数
            'favorites': random.randint(50, 2000),  # 模拟收藏数
            'rating': round(random.uniform(4.0, 5.0), 1),  # 模拟评分
            'duration': '00:00'  # 视频时长，需要根据实际文件计算
        }
        
        return video_detail
        
    except Exception as e:
        print(f"读取视频详情失败: {e}")
        return None

def read_related_videos(conn, video_id, subject_id=None, limit=6):
    """读取相关推荐视频"""
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 根据相同学科或其他条件推荐相关视频
        if subject_id:
            # 优先推荐相同学科的视频
            cursor.execute('''
                SELECT r.id, r.name, r.subject
                FROM res r
                WHERE r.type = 'v' AND r.id != %s AND r.subject = %s
                ORDER BY RAND()
                LIMIT %s
            ''', (video_id, subject_id, limit))
        else:
            # 如果没有学科信息，则随机推荐视频
            cursor.execute('''
                SELECT r.id, r.name, r.subject
                FROM res r
                WHERE r.type = 'v' AND r.id != %s
                ORDER BY RAND()
                LIMIT %s
            ''', (video_id, limit))
        
        videos = cursor.fetchall()
        
        # 获取学科映射
        subject_mapping = {}
        try:
            cursor.execute('SELECT id_s, subject FROM sub')
            subjects = cursor.fetchall()
            subject_mapping = {str(row['id_s']): row['subject'] for row in subjects}
        except Exception as e:
            print(f"读取学科映射失败: {e}")
        
        # 格式化相关视频数据
        related_videos = []
        for video in videos:
            subject_name = '未分类'
            if video['subject'] and str(video['subject']) in subject_mapping:
                subject_name = subject_mapping[str(video['subject'])]
            
            related_videos.append({
                'id': video['id'],
                'title': video['name'],
                'subject': subject_name,
                'subject_id': video['subject'],
                'views': random.randint(500, 30000),
                'thumbnail': ''
            })
        
        return related_videos
        
    except Exception as e:
        print(f"读取相关视频失败: {e}")
        return []

def read_english_articles(conn, limit=20, offset=0, search_keyword=None):
    """读取英语文章数据从english_vocabulary库的passage表，包含难度等级信息、分页支持和搜索功能"""
    try:
        # 连接到english_vocabulary数据库
        english_conn = connect_db('english_vocabulary')
        cursor = english_conn.cursor(pymysql.cursors.DictCursor)
        
        # 构建查询条件
        base_query = "SELECT id, title, reading_number, cover_picture_url FROM passage"
        count_query = "SELECT COUNT(*) as total FROM passage"
        params = []
        count_params = []
        
        # 如果有搜索关键词，添加WHERE条件
        if search_keyword:
            search_condition = " WHERE title LIKE %s"
            search_param = f"%{search_keyword}%"
            base_query += search_condition
            count_query += search_condition
            params.append(search_param)
            count_params.append(search_param)
        
        # 获取文章总数
        cursor.execute(count_query, count_params)
        total_result = cursor.fetchone()
        total_count = total_result['total'] if total_result else 0
        
        # 获取指定范围的文章基本信息
        base_query += " ORDER BY id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(base_query, params)
        articles = cursor.fetchall()
        
        # 获取所有难度等级信息
        cursor.execute("SELECT id, level FROM passage_level")
        level_data = cursor.fetchall()
        
        # 创建难度映射字典
        level_mapping = {}
        for row in level_data:
            level_value = row['level']
            # 将level值转换为整数以确保类型匹配
            try:
                level_int = int(level_value)
                level_mapping[row['id']] = level_int
            except (ValueError, TypeError):
                level_mapping[row['id']] = 2  # 默认中级
        
        english_conn.close()
        
        # 难度等级映射
        difficulty_mapping = {
            1: 'beginner',      # 初级
            2: 'intermediate',  # 中级
            3: 'advanced'       # 高级
        }
        
        # 图片文件名映射（根据实际文件名调整）
        cover_image_mapping = {
            'Can you rewire your brain_.jpg': '/static/article_covers/Can you rewire your brain_.jpg',
            'Compost modernity!.jpg': '/static/article_covers/Compost modernity!.jpg'
        }
        
        # 格式化文章数据
        formatted_articles = []
        for article in articles:
            # 获取文章ID
            article_id = article.get('id', 0)
            
            # 从映射中获取难度等级，如果没有则默认为中级
            level_id = level_mapping.get(article_id, 2)  # 默认中级
            
            difficulty = difficulty_mapping.get(level_id, 'intermediate')
            
            # 获取难度中文名称
            difficulty_chinese = {
                'beginner': '初级',
                'intermediate': '中级',
                'advanced': '高级'
            }.get(difficulty, '未知')
            
            # 处理封面图片URL
            original_cover_url = article.get('cover_picture_url', '')
            web_cover_url = ''
            if original_cover_url:
                # 提取文件名
                import os
                filename = os.path.basename(original_cover_url)
                # 映射到Web路径
                web_cover_url = '/static/article_covers/'+ filename
            
            formatted_article = {
                'id': article_id,
                'title': article.get('title') or '无标题',
                'readingNumber': article.get('reading_number') or 0,
                'coverPictureUrl': web_cover_url,  # 使用Web服务器路径
                'tags': ['英语', '阅读'],
                'difficulty': difficulty,  # 英文难度标识
                'difficultyChinese': difficulty_chinese,  # 中文难度显示
                'levelId': level_id  # 原始等级ID
            }
            formatted_articles.append(formatted_article)
        
        # 返回分页结果
        result = {
            'articles': formatted_articles,
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_count
        }
        
        return result
        
    except Exception as e:
        print(f"读取英语文章失败: {e}")
        import traceback
        traceback.print_exc()
        return {'articles': [], 'total': 0, 'limit': limit, 'offset': offset, 'has_more': False}

def update_passage_reading_count(conn, passage_id):
    """
    更新文章阅读次数
    
    参数:
    conn: 数据库连接对象
    passage_id: 文章ID
    
    返回:
    bool: 是否更新成功
    """
    try:
        cursor = conn.cursor()
        
        # 更新reading_number字段，使其自增1
        cursor.execute('''
            UPDATE passage 
            SET reading_number = reading_number + 1 
            WHERE id = %s
        ''', (passage_id,))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f'更新文章阅读次数时出现错误: {str(e)}')
        conn.rollback()
        return False

def update_user_exp(account, reading_minutes, unknown_words_count):
    """
    更新用户的经验值
    
    参数:
    account: 用户账户名
    reading_minutes: 阅读分钟数
    unknown_words_count: 生词数量
    
    返回:
    bool: 是否更新成功
    """
    conn = None
    try:
        # 连接到free_account数据库
        conn = connect_db('free_account')
        cursor = conn.cursor()
        
        # 计算获得的经验值：阅读分钟数*30 + 生词数*5
        exp_gained = reading_minutes * 30 + unknown_words_count * 5
        
        # 更新用户的exp字段，增加获得的经验值
        cursor.execute('''
            UPDATE acc 
            SET exp = exp + %s 
            WHERE account = %s
        ''', (exp_gained, account))
        
        conn.commit()
        
        # 检查是否更新成功
        if cursor.rowcount > 0:
            print(f"✅ 用户 {account} 经验值更新成功，获得 {exp_gained} 点经验")
            return True
        else:
            print(f"⚠️  用户 {account} 不存在或更新失败")
            return False
            
    except Exception as e:
        print(f'更新用户经验值时出现错误: {str(e)}')
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def update_user_study_time(account, reading_minutes):
    """
    更新用户的学习时间(分钟)

    参数:
    account: 用户账户名
    reading_minutes: 阅读分钟数
    unknown_words_count: 生词数量

    返回:
    bool: 是否更新成功
    """
    conn = None
    try:
        # 连接到free_account数据库
        conn = connect_db('free_account')
        cursor = conn.cursor()

        # 更新用户的exp字段，增加获得的经验值
        cursor.execute('''
            UPDATE acc 
            SET study_time = study_time + %s 
            WHERE account = %s
        ''', (reading_minutes, account))

        conn.commit()
        return  True

    except Exception as e:
        print(f'更新用户学习时常时出现错误: {str(e)}')
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def save_new_word_ids_to_vo_book(account, word_ids):
    """
    将生词ID保存到free_account库vo_book表的un_word_book字段中
    
    参数:
    account: 用户账户名
    word_ids: 单词ID列表
    
    返回:
    bool: 是否保存成功
    """
    conn = None
    try:
        # 连接到free_account数据库
        conn = connect_db('free_account')
        cursor = conn.cursor()
        
        # 查询当前的un_word_book数据
        cursor.execute('''
            SELECT uf_word_book FROM vo_book WHERE account = %s
        ''', (account,))
        
        result = cursor.fetchone()
        
        if result:
            # 如果存在记录，获取现有数据
            current_data = result[0]
            try:
                import json
                if current_data and current_data.strip():
                    un_word_book = json.loads(current_data)
                else:
                    un_word_book = {}
            except:
                un_word_book = {}
        else:
            # 如果不存在记录，创建空字典
            un_word_book = {}
            # 插入新记录
            cursor.execute('''
                INSERT INTO vo_book (account, uf_word_book, pass_w_b) 
                VALUES (%s, %s, %s)
            ''', (account, '{}', '{}'))
        
        # 将新的单词ID添加到字典中，格式为 {单词ID: 0}
        for word_id in word_ids:
            un_word_book[str(word_id)] = 0
        
        # 更新数据库
        cursor.execute('''
            UPDATE vo_book 
            SET uf_word_book = %s 
            WHERE account = %s
        ''', (json.dumps(un_word_book, ensure_ascii=False), account))
        
        conn.commit()
        print(f"✅ 成功保存 {len(word_ids)} 个生词ID到用户 {account} 的vo_book表")
        return True
        
    except Exception as e:
        print(f'保存生词ID到vo_book表时出现错误: {str(e)}')
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def cheek_user_rank(account):
    """
    更新用户的等级

    参数:
    account: 用户账户名

    返回:
    bool: 是否更新成功
    """
    # 输入校验
    if not account or not isinstance(account, str):
        return False

    try:
        # 连接到free_account数据库
        conn = connect_db('free_account')
        cursor = conn.cursor()

        # 合并查询和更新操作，减少数据库交互
        EXP_TO_RANK_FACTOR = 500  # 经验值转等级因子
        sql = '''
            UPDATE acc 
            SET `rank` = (
                SELECT new_rank 
                FROM (
                    SELECT FLOOR(exp / %s) + 1 AS new_rank 
                    FROM acc 
                    WHERE account = %s 
                    LIMIT 1
                ) AS tmp
            )
            WHERE account = %s
        '''


        cursor.execute(sql, (EXP_TO_RANK_FACTOR, account, account))

        # 提交事务
        conn.commit()
        print(f"✅ 用户 {account} 等级更新成功")
        return True

    except Exception as e:
        # 回滚事务
        if conn:
            conn.rollback()
            print(f"⚠️  用户 {account} 等级更新失败: {str(e)}")
        return False

    finally:
        # 关闭数据库连接
        if conn:
            conn.close()


def read_vocabulary(word):
    """
    从数据库中调取对应单词信息
    """
    conn = connect_db('english_vocabulary')
    cursor = None
    try:
        # 使用字典游标以方便访问列名
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # 优化后的SQL语句，使用参数化查询避免硬编码
       # ... existing code ...
        sql_query = """
                SELECT * FROM new_word WHERE word = %s;
            """
# ... existing code ...

        # 执行查询并传入参数
        cursor.execute(sql_query, (word,))
        result = cursor.fetchall()
        return result
    except Exception as e:
        # 记录异常信息以便调试
        # logging.error(f"查询单词 '{word}' 时发生错误: {e}")
        raise  # 抛出异常供上层处理
    finally:
        # 确保游标资源被正确释放
        if cursor:
            cursor.close()


def read_some_word_form_certain_level(level=6):
    """
    从数据库中调取对应单词信息
    """
    conn = connect_db('english_vocabulary')
    cursor = None
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)

       # 执行SQL查询：获取指定等级的随机单词
        sql_query = """
                     SELECT w.word, w.`Chinese Definition`
                     FROM word_level_ref ref
                     JOIN words w ON ref.word_id = w.id
                     WHERE ref.level_id = %s
                     ORDER BY RAND()
                     LIMIT %s
                    """

        cursor.execute(sql_query, (level, 10))
        results = cursor.fetchall()

        # 格式化返回数据
        word_list = []
        for row in results:
            word_info = {
                'word': row['word'],
                'chinese_definition': row['Chinese Definition'],
                'phonetic':read_vocabulary(row['word'])[0]['phonetic']
           }
            word_list.append(word_info)

        return word_list
    except Exception as e:
        # 记录异常信息以便调试
        # logging.error(f"查询单词 '{word}' 时发生错误: {e}")
        raise  # 抛出异常供上层处理
    finally:
        # 确保游标资源被正确释放
        if cursor:
            cursor.close()





def read_english_passage(conn, passage_id):
    """
    读取单个英语文章的详细信息
    
    参数:
    conn: 数据库连接对象
    passage_id: 文章ID
    
    返回:
    dict: 文章详细信息
    """
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查询单个文章的详细信息（移除不存在的word_count字段）
        cursor.execute("""
            SELECT p.id, p.title, p.content, p.cover_picture_url, p.translation, 
                   pl.level
            FROM passage p
            LEFT JOIN passage_level pl ON p.id = pl.id
            WHERE p.id = %s
        """, (passage_id,))
        
        article = cursor.fetchone()
        
        if not article:
            return None
            
        # 难度等级映射
        difficulty_mapping = {
            1: 'beginner',      # 初级
            2: 'intermediate',  # 中级
            3: 'advanced'       # 高级
        }
        
        # 获取难度等级
        level_id = article.get('level', 2)  # 默认中级
        difficulty = difficulty_mapping.get(level_id, 'intermediate')
        
        # 处理封面图片URL
        original_cover_url = article.get('cover_picture_url', '')
        web_cover_url = ''
        print(f"DEBUG: 原始封面URL: '{original_cover_url}'")
        
        if original_cover_url and original_cover_url.strip():
            # 如果已经是完整路径，直接使用
            if original_cover_url.startswith('/static/'):
                web_cover_url = original_cover_url
            else:
                # 否则构造完整路径
                import os
                filename = os.path.basename(original_cover_url)
                web_cover_url = '/static/article_covers/' + filename
            print(f"DEBUG: 处理后的Web封面URL: '{web_cover_url}'")
        else:
            print("DEBUG: 没有封面图片URL")
        
        # 计算词数（如果没有存储的话）
        content = article['content'] or ''
        word_count = len(content.split()) if content else 0
        
        # 处理段落级别翻译数据
        paragraph_translations = []
        original_content = article['content'] or ''
        translation_content = article['translation'] or ''
        
        if original_content and translation_content:
            # 按换行符分割原文和翻译
            original_paragraphs = [p.strip() for p in original_content.split('\n\n') if p.strip()]
            translated_paragraphs = [p.strip() for p in translation_content.split('\n\n') if p.strip()]
            
            # 确保两个数组长度一致
            min_length = min(len(original_paragraphs), len(translated_paragraphs))
            
            # 构建段落翻译映射
            for i in range(min_length):
                paragraph_translations.append({
                    'index': i,
                    'original': original_paragraphs[i],
                    'translation': translated_paragraphs[i]
                })
        
        # 构建返回数据
        formatted_article = {
            'id': article['id'],
            'title': article['title'] or '无标题',
            'content': article['content'] or '',
            'cover_picture_url': web_cover_url,
            'translation': article['translation'] or '',
            'word_count': word_count,
            'difficulty': difficulty,
            'topic': '英语文章',  # 默认主题
            'paragraph_translations': paragraph_translations  # 新增段落翻译数据
        }
        
        return formatted_article
        
    except Exception as e:
        print(f"读取英语文章详情失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """
    对密码进行哈希处理

    Args:
        password: 原始密码
        salt: 盐值，如果未提供则自动生成

    Returns:
        tuple: (哈希值, 盐值)
    """
    if salt is None:
        # 生成随机盐值
        salt = secrets.token_hex(16)

    # 使用SHA-256和盐值对密码进行哈希
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return hashed.hex(), salt

def verify_password(password: str, hashed: str, salt: str) -> bool:
    """
    验证密码是否正确

    Args:
        password: 待验证的密码
        hashed: 存储的哈希值
        salt: 盐值

    Returns:
        bool: 密码是否正确
    """
    new_hashed, _ = hash_password(password, salt)
    return new_hashed == hashed

def create_teacher_table(conn):
    """创建教师表"""
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS `teachers` (
	`账户`	VARCHAR(255) NOT NULL UNIQUE,
	`密码`	TEXT NOT NULL,
	`盐值`	TEXT NOT NULL,
	`邮箱`	TEXT NOT NULL,
	`分组`	TEXT,
	`模板`	TEXT,
	PRIMARY KEY(`账户`)
)
    ''')
    conn.commit()

def create_student_table(conn, teacher_account):
    """为指定教师创建学生表"""
    cursor = conn.cursor()
    # 验证teacher_account只包含字母数字和下划线
    if not re.match(r'^[a-zA-Z0-9_]+$', teacher_account):
        raise ValueError("Invalid teacher account name")
    
    table_name = f"student_{teacher_account}"
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS `{table_name}` (
	`账号`	VARCHAR(255) NOT NULL UNIQUE,
	`密码`	TEXT NOT NULL,
	`名称`	TEXT NOT NULL,
	`班级`	TEXT NOT NULL,
	`考试`	TEXT,
	`序号`	INT AUTO_INCREMENT,
	PRIMARY KEY(`序号`)
        )
    ''')
    conn.commit()






#添加学生用的，参数是：名字，班级，考试字典（正常情况不用填）
def add_student(conn, teacher_account, name, class_name, exam="{}"):
    """添加学生记录"""
    cursor = conn.cursor()

    # 验证teacher_account只包含字母数字和下划线
    if not re.match(r'^[a-zA-Z0-9_]+$', teacher_account):
        raise ValueError("Invalid teacher account name")
    
    table_name = f"student_{teacher_account}"

    # 先查询该表中的记录数量，用于生成账号
    cursor.execute(f'SELECT COUNT(*) FROM `{table_name}`')
    count = cursor.fetchone()[0]
    student_id = count + 1

    # 构造账号和密码
    account = f"{teacher_account}@{student_id}"
    password = account  # 密码默认为账号

    # # 对密码进行哈希处理
    # hashed_password, salt = hash_password(password)

    # 插入完整记录
    cursor.execute(f'''
        INSERT INTO `{table_name}` (`账号`, `密码`, `名称`, `班级`, `考试`)
        VALUES (%s, %s, %s, %s, %s)
    ''', (account, password, name, class_name, exam))

    conn.commit()
    return student_id


def send_verification_email(email: str) -> str:
    """
    发送邮箱验证码
    
    Args:
        email: 接收验证码的邮箱地址
    
    Returns:
        str: 生成的验证码
    """
    # 生成6位随机验证码
    key = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # 邮件主题
    subject = "【SMSF】账户注册验证码 - 请及时验证"
    
    # 邮件HTML内容
    content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            border-bottom: 3px solid #2c3e50;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .content {{
            padding: 20px 0;
        }}
        .verification-code {{
            display: inline-block;
            padding: 15px 25px;
            background-color: #f8f9fa;
            border: 1px dashed #3498db;
            color: #e74c3c;
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 5px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 10px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #7f8c8d;
        }}
        .signature {{
            font-style: italic;
            color: #2c3e50;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">SMSF 智慧教育</div>
    </div>
    <div class="content">
        <p>尊敬的用户，您好：</p>
        <p>感谢您选择 SMSF 智慧教育软件服务，我们致力于为您提供可靠的智慧教育解决方案。</p>
        <p>您的账户注册验证码如下：</p>
        <div class="verification-code">{key}</div>
        <p>验证码有效期为 <strong>10分钟</strong>，请尽快完成验证以确保账户安全。</p>
        <p>如非本人操作，请立即联系我们的客服团队或忽略此邮件。</p>
    </div>
    <div class="footer">
        <p>此致</p>
        <p class="signature">SMSF 智慧教育服务团队</p>
        <p>© 2026 SMSF. 版权所有</p>
        <p>本邮件由系统自动发送，请勿直接回复。</p>
    </div>
</body>
</html>"""

    # 创建邮件对象
    msg = MIMEText(content, 'html', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = EMAIL_CONFIG['sender']
    msg['To'] = email

    try:
        # 连接SMTP服务器
        smtp = smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        
        # HELO向服务器标志用户身份
        smtp.helo(EMAIL_CONFIG['smtp_server'])
        
        # 服务器返回结果确认
        smtp.ehlo(EMAIL_CONFIG['smtp_server'])
        
        # 登录邮箱
        smtp.login(EMAIL_CONFIG['user'], EMAIL_CONFIG['password'])
        
        # 发送邮件
        smtp.sendmail(EMAIL_CONFIG['sender'], email, msg.as_string())
        smtp.quit()
        
        # 存储验证码（实际应用中应该使用带过期时间的缓存）
        import time
        verification_codes[email] = {'code': key, 'timestamp': time.time()}
        
        print(f"验证码已发送至 {email}")
        return key
        
    except Exception as e:
        print(f"发送邮件失败: {e}")
        raise e


def verify_email_code(email: str, code: str) -> bool:
    """
    验证邮箱验证码
    
    Args:
        email: 邮箱地址
        code: 验证码
    
    Returns:
        bool: 验证是否成功
    """
    import time
    
    # 检查验证码是否存在
    if email not in verification_codes:
        print("邮箱未发送验证码或验证码已过期")
        return False
    
    # 检查验证码是否过期（10分钟有效期）
    stored_time = verification_codes[email]['timestamp']
    if time.time() - stored_time > 600:  # 10分钟 = 600秒
        print("验证码已过期")
        del verification_codes[email]
        return False
    
    # 检查验证码是否正确
    stored_code = verification_codes[email]['code']
    if code == stored_code:
        # 验证成功后删除验证码
        del verification_codes[email]
        return True
    else:
        print("验证码错误")
        return False


def add_teacher(conn, account, password, email, group="{}", modle="{}"):
    """
    添加教师记录

    参数:
    conn: 数据库连接对象
    account: 教师账户
    password: 教师密码
    email: 教师邮箱
    group: 教师分组（可选）

    返回:
    新插入记录的rowid或者None（如果插入失败）
    """
    try:
        cursor = conn.cursor()
        # 对密码进行哈希处理
        hashed_password, salt = hash_password(password)

        cursor.execute('''
            INSERT INTO `teachers` (`账户`, `密码`, `盐值`, `邮箱`, `分组`, `模板`)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (account, hashed_password, salt, email, group, modle))
        
        conn.commit()
        
        # 创建对应的学生表（在提交后创建，避免事务问题）
        create_student_table(conn, account)
        
        print("添加教师成功")
        return True
    except pymysql.IntegrityError as e:
        # 处理唯一性约束违反（账户或邮箱重复）
        print(f"注册教师失败: {e}")
        try:
            conn.rollback()
        except:
            pass  # 忽略回滚过程中的错误
        return None
    except ValueError as e:  # 捕获账户名验证错误
        # 处理账户名验证错误
        print(f"账户名验证失败: {e}")
        try:
            conn.rollback()
        except:
            pass  # 忽略回滚过程中的错误
        return None
    except Exception as e:
        # 处理其他异常
        print(f"添加教师时发生错误: {e}")
        try:
            conn.rollback()
        except:
            pass  # 忽略回滚过程中的错误
        return None


def register_teacher_with_verification(conn, account, password, email, verification_code, group="{}", modle="{}"):
    """
    带邮箱验证的教师注册流程

    参数:
    conn: 数据库连接对象
    account: 教师账户
    password: 教师密码
    email: 教师邮箱
    verification_code: 验证码
    group: 教师分组（可选）
    modle: 教师模板（可选）

    返回:
    bool: 注册是否成功
    """
    # 首先验证邮箱验证码
    if not verify_email_code(email, verification_code):
        print("邮箱验证失败")
        return False
    
    # 验证通过后，执行完整的教师注册流程
    try:
        # 不显式开始事务，让MySQL自动处理
        
        # 添加教师账户
        result = add_teacher(conn, account, password, email, group, modle)
        if not result:
            # 如果教师账户创建失败，直接返回
            return False
        
        # 提交事务
        conn.commit()
        return True
        
    except Exception as e:
        # 发生任何错误时回滚事务
        print(f"完整注册流程失败: {e}")
        try:
            conn.rollback()
        except:
            pass  # 忽略回滚过程中的错误
        return False


def authenticate_teacher(conn, account, password):
    """
    验证教师登录

    参数:
    conn: 数据库连接对象
    account: 教师账户
    password: 输入的密码

    返回:
    bool: 验证是否成功
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT `密码`, `盐值` FROM `teachers` WHERE `账户` = %s
    ''', (account,))

    result = cursor.fetchone()
    if result is None:
        return False

    stored_hash, salt = result
    return verify_password(password, stored_hash, salt)



def read_student(conn,student_id):
    result = student_id.split("@")
    """
    读取学生信息

    参数:
    conn: 数据库连接对象
    student_id: 学生ID

    返回:
    tuple: (名称, 班级, 考试)
    """
    cursor = conn.cursor()
    # 验证teacher_account只包含字母数字和下划线
    if not re.match(r'^[a-zA-Z0-9_]+$', result[0]):
        raise ValueError("Invalid teacher account name")
    table_name = f"student_{result[0]}"
    cursor.execute(f'''
        SELECT `名称`, `班级`, `考试` FROM `{table_name}` WHERE `账号` = %s
    ''', (student_id,))
    result = cursor.fetchone()
    return result



def read_class(conn,teacher_account):
    """
    读取班级信息

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户

    返回:
    list: 班级列表
    """
    try:
        cursor = conn.cursor()
        # 验证teacher_account只包含字母数字和下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', teacher_account):
            raise ValueError("Invalid teacher account name")
        table_name = f"student_{teacher_account}"
        cursor.execute(f'''
            SELECT DISTINCT `班级` FROM `{table_name}`
        ''')
        result = cursor.fetchall()
        return [row[0] for row in result]
    except Exception as e:
        # 如果连接断开或序列号错误，尝试重新连接
        if "Lost connection" in str(e) or "2013" in str(e) or "Packet sequence number wrong" in str(e):
            fresh_conn = connect_db()
            cursor = fresh_conn.cursor()
            if not re.match(r'^[a-zA-Z0-9_]+$', teacher_account):
                fresh_conn.close()
                raise ValueError("Invalid teacher account name")
            table_name = f"student_{teacher_account}"
            cursor.execute(f'''
                SELECT DISTINCT `班级` FROM `{table_name}`
            ''')
            result = cursor.fetchall()
            fresh_conn.close()
            return [row[0] for row in result]
        else:
            raise e



def read_single_class(conn,teacher_account,class_name):
    """
    读取指定班级的学生信息

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户
    class_name: 班级名称

    返回:
    list: 学生列表
    """
    try:
        cursor = conn.cursor()
        # 验证teacher_account只包含字母数字和下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', teacher_account):
            raise ValueError("Invalid teacher account name")
        table_name = f"student_{teacher_account}"
        cursor.execute(f'''
            SELECT `账号`, `名称`, `考试` FROM `{table_name}` WHERE `班级` = %s
        ''', (class_name,))
        result = cursor.fetchall()
        return [{"账号": row[0],"名称": row[1], "考试": row[2]} for row in result]
    except Exception as e:
        # 如果连接断开或序列号错误，尝试重新连接
        if "Lost connection" in str(e) or "2013" in str(e) or "Packet sequence number wrong" in str(e):
            fresh_conn = connect_db()
            cursor = fresh_conn.cursor()
            if not re.match(r'^[a-zA-Z0-9_]+$', teacher_account):
                fresh_conn.close()
                raise ValueError("Invalid teacher account name")
            table_name = f"student_{teacher_account}"
            cursor.execute(f'''
                SELECT `账号`, `名称`, `考试` FROM `{table_name}` WHERE `班级` = %s
            ''', (class_name,))
            result = cursor.fetchall()
            fresh_conn.close()
            return [{"账号": row[0],"名称": row[1], "考试": row[2]} for row in result]
        else:
            raise e



def student_class_change(conn,teacher_account,student_id,class_name):
    """
    修改学生班级

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户
    student_id: 学生ID
    class_name: 新的班级名称

    返回:
    bool: 修改成功与否
    """
    cursor = conn.cursor()
    # 验证teacher_account只包含字母数字和下划线
    if not re.match(r'^[a-zA-Z0-9_]+$', teacher_account):
        raise ValueError("Invalid teacher account name")
    table_name = f"student_{teacher_account}"
    cursor.execute(f'''
        UPDATE `{table_name}` SET `班级` = %s WHERE `账号` = %s
    ''', (class_name, student_id))
    conn.commit()
    return cursor.rowcount > 0


##读取学生考试信息，输出字典
def read_student_exam(conn,student_id):
    """
    读取学生考试信息

    参数:
    conn: 数据库连接对象
    student_id: 学生ID

    返回:
    tuple: 考试成绩字典

    """
    student_parts = student_id.split("@")
    try:
        cursor = conn.cursor()
        # 验证teacher_account只包含字母数字和下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', student_parts[0]):
            raise ValueError("Invalid teacher account name")
        table_name = f"student_{student_parts[0]}"
        cursor.execute(f'''
            SELECT `考试` FROM `{table_name}` WHERE `账号` = %s
        ''', (student_id,))
        result = cursor.fetchone()
        if result is None or result[0] is None:
            return {}
        score_dict = ast.literal_eval(result[0])

        return score_dict
    except Exception as e:
        # 如果连接断开或序列号错误，尝试重新连接
        if "Lost connection" in str(e) or "2013" in str(e) or "Packet sequence number wrong" in str(e):
            fresh_conn = connect_db()
            cursor = fresh_conn.cursor()
            if not re.match(r'^[a-zA-Z0-9_]+$', student_parts[0]):
                fresh_conn.close()
                raise ValueError("Invalid teacher account name")
            table_name = f"student_{student_parts[0]}"
            cursor.execute(f'''
                SELECT `考试` FROM `{table_name}` WHERE `账号` = %s
            ''', (student_id,))
            result = cursor.fetchone()
            fresh_conn.close()
            if result is None or result[0] is None:
                return {}
            score_dict = ast.literal_eval(result[0])
            return score_dict
        else:
            raise e


def subject_calculate(score_dict):
    """
    计算学生的综合成绩、各科目平均分和方差

    参数:
    conn: 数据库连接对象
    score_dict: 包含学生历次考试成绩的字典

    返回:
    dict: 包含综合成绩、各科目平均分和方差的字典
    """
    import statistics

    # 初始化结果字典
    result = {}

    # 收集所有科目名称
    all_subjects = set()
    for exam_data in score_dict.values():
        all_subjects.update(exam_data.keys())

    # 计算每次考试的总分
    total_scores = []
    subject_scores = {subject: [] for subject in all_subjects}

    # 遍历每次考试
    for exam_name, exam_data in score_dict.items():
        # 计算本次考试总分
        exam_total = 0
        for subject, scores in exam_data.items():
            # scores[0] 是实际得分，scores[1] 是满分
            actual_score = scores[0]
            full_score = scores[1]

            # 累计总分
            exam_total += actual_score

            # 收集各科目分数
            subject_scores[subject].append(actual_score)

        total_scores.append(exam_total)

    # 计算综合成绩（各次考试总分的平均分）
    result["综合成绩"] = sum(total_scores) / len(total_scores) if total_scores else 0

    # 计算各科目平均分
    for subject, scores in subject_scores.items():
        result[f"{subject}均分"] = sum(scores) / len(scores) if scores else 0

    # 计算方差（基于历次考试总分）
    if len(total_scores) > 1:
        result["方差"] = statistics.variance(total_scores)
    else:
        result["方差"] = 0

    return result


#更新教师分组数据，注意是覆盖原来的数据，所以如果是原数据的基础上添加新数据，记得处理好再用这个函数，否则会被覆盖
def update_teacher_group(conn, teacher_account, group_data):
    """
    更新教师的分组信息

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户
    group_data: 分组数据

    返回:
    bool: 更新是否成功
    """
    try:
        cursor = conn.cursor()
        # 确保group_data是字符串类型
        group_str = str(group_data) if group_data is not None else None
        cursor.execute('''
            UPDATE `teachers` 
            SET `分组` = %s 
            WHERE `账户` = %s
        ''', (group_str, teacher_account))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"更新教师分组时发生错误: {e}")
        return False


##读取教师已创建的分组信息
def read_teacher_group(conn, teacher_account):
    """
    读取教师的分组信息

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户

    返回:
    dict: 分组信息
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT `分组` FROM `teachers` 
        WHERE `账户` = %s
    ''', (teacher_account,))
    result = cursor.fetchone()
    if result and result[0]:
        return ast.literal_eval(result[0])
    else:
        return {}


##返回单个学生参加过的考试列表，参数为该学生的成绩字典
def student_joined_exam_list(score_dict):
    result = []
    for i in score_dict.keys():
        result.append(i)
    return result


## 读取该教师账号下已创建但未分组的考试，返回列表
def not_group_exam(conn, teacher_account):
    """
    读取未分组的考试信息

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户

    返回:
    list: 未分组的考试信息列表
    """
    # 先读取老师账户下的所有班级
    class_list = read_class(conn, teacher_account)
    # 创建一个空字典存储结果
    dicct = {}
    # 遍历所有班级
    for class_name in class_list:
        student_list = read_single_class(conn, teacher_account, class_name)
        for student in student_list:
            dicct[student["名称"]] = student["账号"]

    created_exam_set = set()
    for i in dicct.values():
        dict = read_student_exam(conn, i)
        for i in student_joined_exam_list(dict):
            created_exam_set.add(i)


    already_group_dict = read_teacher_group(conn, teacher_account)
    result = []
    noww_have = []
    if already_group_dict != {}:
        for i in already_group_dict.values():
            for aa in i:
               noww_have.append(aa)
        for end in created_exam_set:
            if end not in noww_have:
                result.append(end)

    else:
        for a in created_exam_set:
            result.append(a)

    return result


##删除学生信息，输入学生ID
def remove_student(conn,student_id):
    """
    删除学生信息

    参数:
    conn: 数据库连接对象
    student_id: 学生ID

    返回:
    bool: 删除是否成功
    """
    result = student_id.split("@")
    cursor = conn.cursor()
    # 验证teacher_account只包含字母数字和下划线
    if not re.match(r'^[a-zA-Z0-9_]+$', result[0]):
        raise ValueError("Invalid teacher account name")
    table_name = f"student_{result[0]}"
    cursor.execute(f'''
        DELETE FROM `{table_name}` WHERE `账号` = %s
    ''', (student_id,))
    conn.commit()
    return cursor.rowcount > 0


#修改学生考试成绩字典，参数（原字典，考试名， 学科名，分数）
def change_student_score(score_dict, exam_name, subject, score):
    """
    修改学生的考试成绩

    参数:
    score_dict: 考试成绩字典
    exam_name: 考试名称
    subject: 科目名称
    score: 成绩

    返回:
    dict: 修改后的考试成绩字典
    """

    ##先确定考试字典中是否存在该次考试以及科目
    result = score_dict

    j_exam_name = student_joined_exam_list(score_dict)
    if exam_name in j_exam_name:
        subjecct = score_dict[exam_name]
        if subject in subjecct.keys():
            result[exam_name][subject] = [score, subjecct[subject][1]]

    return result


#更新学生考试成绩，覆盖数据库
def update_student_score(conn, student_id,score_dict):
    """
    更新学生的考试成绩

    参数:
    conn: 数据库连接对象
    student_id: 学生ID
    score_dict: 考试成绩字典

    返回:
    bool: 更新是否成功
    """
    try:
        cursor = conn.cursor()
        student_parts = student_id.split('@')
        # 验证teacher_account只包含字母数字和下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', student_parts[0]):
            raise ValueError("Invalid teacher account name")
        table_name = f"student_{student_parts[0]}"
        cursor.execute(f'''
            UPDATE `{table_name}` 
            SET `考试` = %s 
            WHERE `账号` = %s
        ''', (str(score_dict), student_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"更新学生成绩时发生错误: {e}")
        return False


#创建新考试，参数（教师账号， 参与班级， 考试名称， 科目信息），其中科目信息为字典，格式{科目：满分}， 创建完后默认0分
def add_new_exam(conn, teacher_account, join_class, exam_name, subject_info):
    """
    添加新的考试信息

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户
    join_class: 参与的班级
    exam_name: 考试名称
    subject_info: 考试科目信息 {学科：满分}


    返回:
    bool: 添加是否成功
    """
    # 先读取老师账户符合参考班级下的所有学生账号
    stu_lis =[]
    student_a = read_single_class(conn, teacher_account, join_class)
    for i in student_a:
        stu_lis.append(i["账号"])
    for i in stu_lis:

        score_d = read_student_exam(conn, i)
        new_e_d ={}
        for k in subject_info.keys():
            fenshu = [0, subject_info[k]]
            new_e_d[k] = fenshu
        score_d[exam_name] = new_e_d
        update_student_score(conn, i, score_d)


def subject_compare_rate(conn, student_id, exam_name):
    """
    比较学生单次考试科目的得分率百分比

    参数:
    student_id: 学生ID
    exam_name: 考试名称

    返回:
    float: 比例
    """
    single_score_d = read_student_exam(conn, student_id)[exam_name]
    result = {}
    for i in single_score_d.keys():
        result[i] =float( single_score_d[i][0]/single_score_d[i][1])
    return result


def export_student_account_and_password_to_csv(conn, teacher_account, class_name, file_path):
    """
    导出班级学生账号和密码到CSV文件

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户
    class_name: 班级名称
    file_path: CSV文件路径

    返回:
    bool: 导出是否成功
    """
    try:
        
        # 获取指定班级的学生信息
        student_list = read_single_class(conn, teacher_account, class_name)
        
        # 准备CSV文件数据
        csv_data = []
        csv_data.append(['姓名', '账号', '密码'])  # 表头
        
        # 获取每个学生的账号和密码
        # 验证teacher_account只包含字母数字和下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', teacher_account):
            raise ValueError("Invalid teacher account name")
        table_name = f"student_{teacher_account}"
        cursor = conn.cursor()
        
        for student in student_list:
            student_account = student["账号"]
            # 查询该学生的密码
            cursor.execute(f'''
                SELECT `密码` FROM `{table_name}` WHERE `账号` = %s
            ''', (student_account,))
            result = cursor.fetchone()
            if result:
                password = result[0]
                csv_data.append([student["名称"], student_account, password])
        
        # 写入CSV文件
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(csv_data)
        
        return True
    except Exception as e:
        print(f"导出学生账号密码时发生错误: {e}")
        return False


def add_new_exam_group(conn, teacher_account, exam_name, group):
    """
    添加新的考试分组

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户
    exam_name: 考试名称
    group: 分组名

    返回:
    bool: 添加是否成功
    """
    now_group = read_teacher_group(conn, teacher_account)
    if now_group != {}:
        try:
            now_group[group].append(exam_name)
        except:
            now_group[group] = [exam_name]


        update_teacher_group(conn, teacher_account, now_group)
    else:
        update_teacher_group(conn, teacher_account, {group: [exam_name]})


#AI分析
def ALLexam_AI_analysis(conn, student_id):

    ddict = read_student_exam(conn, student_id)


    # for backward compatibility, you can still use `https://api.deepseek.com/v1` as `base_url`.
    client = OpenAI(api_key="", base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system",
             "content": "你是一个专业的学生成绩分析助手,用五句话分析用户成绩并给出建议建议（纯文本格式）"},
            {"role": "user",
             "content": str(ddict)},
        ],
        max_tokens=1024,
        temperature=1.0,
        stream=False
    )

    return response.choices[0].message.content


def single_exam_AI_analysis(conn, student_id, exam_name):
    """
    对单次考试进行AI分析
    """
    ddict = read_student_exam(conn, student_id)
    
    # 只获取指定考试的数据
    if exam_name in ddict:
        exam_data = {exam_name: ddict[exam_name]}
    else:
        return f"未找到考试 '{exam_name}' 的数据"
    
    # for backward compatibility, you can still use `https://api.deepseek.com/v1` as `base_url`.
    client = OpenAI(api_key="", base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system",
             "content": "你是一个专业的学生成绩分析助手,用五句话分析用户单次考试成绩并给出建议建议（纯文本格式）"},
            {"role": "user",
             "content": str(exam_data)},
        ],
        max_tokens=1024,
        temperature=1.0,
        stream=False
    )

    return response.choices[0].message.content


#考试分组修改
def exam_group_change(conn, teacher_account, exam_name, group):
    """
    修改考试分组

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户
    exam_name: 考试名称
    group: 分组名

    返回:
    none
    """
    now_group = read_teacher_group(conn, teacher_account)
    for o in now_group.keys():
        if exam_name in now_group[o]:
            now_group[o].remove(exam_name)
    update_teacher_group(conn, teacher_account, now_group)
    add_new_exam_group(conn, teacher_account, exam_name, group)


def single_exam_score_show(conn, teacher_account, exam_name):

    student_listt = []
    class_tea_con = read_class(conn, teacher_account)
    #读取参加考试的学生账号
    for i in class_tea_con:
        stu_l = read_single_class(conn, teacher_account, i)
        for j in stu_l:
            dicccct = read_student_exam(conn, j["账号"])
            if exam_name in dicccct.keys():
                student_listt.append(j["账号"])


    scoore_dic = {}
    for i in student_listt:
        scoore_dic[read_student(conn, i)[0]] = read_student_exam(conn, i)[exam_name]
    return scoore_dic


def new_student_exam_return_attach_allscore(conn, student_id):
    """
    获取学生考试成绩并附加总分

    参数:
    conn: 数据库连接对象
    student_id: 学生ID
    exam_name: 考试名称
{exname:{sub_n:[scoe, all], sub_n2:[scoe, all]},....}
    返回:
    dict: 包含考试成绩和所有科目的总分
    """
    student_dic_ori = read_student_exam(conn, student_id)
    print(student_dic_ori)
    
    for i in list(student_dic_ori.keys()):  # 使用list()复制键列表，避免在迭代时修改字典
        all_s = 0  # 每个考试单独计算总分
        alll_a = 0
        print(student_dic_ori[i].keys())
        for a in list(student_dic_ori[i].keys()):  # 使用list()复制键列表，避免在迭代时修改字典
            if a == "total":  # 跳过已有的total字段
                continue
            print(a)
            all_s += int(student_dic_ori[i][a][0])
            alll_a += int(student_dic_ori[i][a][1])
        student_dic_ori[i]["total"] = [all_s, alll_a]

    return student_dic_ori


##读取教师已创建的分组信息
def read_teacher_model(conn, teacher_account):
    """
    读取教师的模板信息

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户

    返回:
    dict: 模板信息
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT `模板` FROM `teachers` 
        WHERE `账户` = %s
    ''', (teacher_account,))
    result = cursor.fetchone()
    if result and result[0]:
        return ast.literal_eval(result[0])
    else:
        return {}


def create_new_model_exam(conn, teacher_account, model_name,exam_subjects):
    """

        更新教师的模板信息
        {"model_1":{"subject_1":"满分", "subject_2":"", ....},....}

    """
    cursor = conn.cursor()
    model_info = read_teacher_model(conn, teacher_account)
    model_info[model_name] = exam_subjects
    try:
        cursor.execute('''
                   UPDATE `teachers` 
                   SET `模板` = %s 
                   WHERE `账户` = %s
               ''', (str(model_info), teacher_account))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"更新教师模板时发生错误: {e}")
        return False


def delete_model_exam(conn, teacher_account, model_name):
    """
    删除教师模板
    """
    cursor = conn.cursor()
    model_info = read_teacher_model(conn, teacher_account)
    if model_name in model_info:
        del model_info[model_name]
        try:
            cursor.execute('''
                   UPDATE `teachers` 
                   SET `模板` = %s 
                   WHERE `账户` = %s
               ''', (str(model_info), teacher_account))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"更新教师模板时发生错误: {e}")
            return False


def cre_new_exam_bymodel(conn, teacher_account, class_name, exam_name, model_name):
    """
    使用模板创建考试
    
    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户
    class_name: 班级名称
    exam_name: 考试名称
    model_name: 模板名称
    
    返回:
    bool: 操作是否成功
    """
    try:
        model_info = read_teacher_model(conn, teacher_account)
        if model_name not in model_info:
            print(f"模板 {model_name} 不存在")
            return False
        
        stu = read_single_class(conn, teacher_account, class_name)
        moddel = model_info[model_name]

        all_success = True
        for i in stu:
            student_id = i["账号"]
            data = read_student_exam(conn, student_id)
            data[exam_name] = {}
            for subject_name, max_score in moddel.items():
                data[exam_name][subject_name] = [0, int(max_score)]
            
            success = update_student_score(conn, student_id, data)
            if not success:
                all_success = False
                
        return all_success
    except Exception as e:
        print(f"使用模板创建考试时发生错误: {e}")
        return False


def exam_exist_cheek(conn, teacher_account, exam_name):
    """
    检查考试是否存在

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户
    exam_name: 考试名称

    返回:
    bool: 考试是否存在
    """
    class_list = read_class(conn, teacher_account)
    for i in class_list:
        stu_data = read_single_class(conn, teacher_account, i)
        for j in stu_data:
            if exam_name in read_student_exam(conn, j["账号"]):
                return True
    return False


def refreash_exam_groupp(conn, teacher_account, exam_name):
    """
    删除已经失效的考试分组信息

    参数:
    conn: 数据库连接对象
    teacher_account: 教师账户
    exam_name: 考试名称

    返回:
    无返回值
    """
    llist = read_teacher_group(conn, teacher_account)
    for i in llist.keys():
        if exam_name in llist[i]:
            llist[i].remove(exam_name)  # 从列表中移除元素，而不是从字典中删除键
    update_teacher_group(conn, teacher_account, llist)


def account_cheek(conn, account, password):
    """
    检查账户类型（教师或学生）

    参数:
    conn: 数据库连接对象
    account: 账户名
    password: 密码

    返回:
    str: "teacher" 如果是教师账户，"student" 如果是学生账户，None 如果验证失败
    """
    # 首先尝试验证教师账户
    if authenticate_teacher(conn, account, password):
        return "teacher"
    
    # 检查是否为学生账户格式 (teacher@id)
    if "@" in account:
        teacher_part = account.split("@")[0]
        
        # 尝试找到对应的教师数据库表
        cursor = conn.cursor()
        # 验证teacher_part只包含字母数字和下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', teacher_part):
            raise ValueError("Invalid teacher account name")
        table_name = f"student_{teacher_part}"
        
        try:
            # 检查是否存在该学生账户
            cursor.execute(f'SELECT `账号`, `密码` FROM `{table_name}` WHERE `账号` = %s', (account,))
            result = cursor.fetchone()
            
            if result and result[1] == password:  # 简单密码验证，实际应用中应使用哈希验证
                return "student"
        except Exception:
            # 表不存在，说明不是有效的教师账户
            pass
    
    return None  # 验证失败



def update_teacher_password(conn, account, old_password, new_password):
    """
    更新教师密码

    参数:
    conn: 数据库连接对象
    account: 教师账户
    old_password: 旧密码
    new_password: 新密码

    返回:
    bool: 更新是否成功
    """
    # 首先验证旧密码
    if not authenticate_teacher(conn, account, old_password):
        return False
    
    # 生成新密码的哈希值和盐
    hashed_password, salt = hash_password(new_password)
    
    # 更新数据库中的密码
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE `teachers` 
            SET `密码` = %s, `盐值` = %s 
            WHERE `账户` = %s
        ''', (hashed_password, salt, account))
        conn.commit()
        return True
    except Exception as e:
        print(f"更新密码时发生错误: {e}")
        return False



def update_student_password(conn, student_id, old_password, new_password):
    """
    更新学生密码

    参数:
    conn: 数据库连接对象
    student_id: 学生ID
    old_password: 旧密码
    new_password: 新密码

    返回:
    bool: 更新是否成功
    """
    # 首先验证旧密码
    student_info = read_student(conn, student_id)
    if not student_info or student_info[1] != old_password:  # 简单密码验证，实际应用中应使用哈希验证
        # 对于学生账户，密码通常直接存储，这里简单验证
        result = student_id.split("@")
        table_name = f"student_{result[0]}"
        cursor = conn.cursor()
        cursor.execute(f'SELECT 密码 FROM "{table_name}" WHERE 账号 = ?', (student_id,))
        stored_password = cursor.fetchone()
        if not stored_password or stored_password[0] != old_password:
            return False
    
    # 更新数据库中的密码
    result = student_id.split("@")
    table_name = f"student_{result[0]}"
    cursor = conn.cursor()
    try:
        cursor.execute(f'''
            UPDATE "{table_name}" 
            SET 密码 = ? 
            WHERE 账号 = ?
        ''', (new_password, student_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"更新学生密码时发生错误: {e}")
        return False



def read_csv_and_update_scores(csv_file_path, conn, student_id, exam_name, full_scores=None):
    """
    从CSV文件中读取表头科目，并使用change_student_score函数更新学生成绩

    参数:
    csv_file_path: CSV文件路径
    conn: 数据库连接对象
    student_id: 学生ID
    exam_name: 考试名称
    full_scores: 满分字典，格式为{"科目1": 满分值, ...}
    """
    # 自动从学生ID获取学生姓名
    stu_name = read_student(conn, student_id)[0]
    # 读取CSV文件
    with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
        # 使用DictReader读取CSV，第一行作为表头
        reader = csv.DictReader(csvfile)

        # 获取CSV文件的表头（列名）
        headers = reader.fieldnames
        print(f"CSV文件表头: {headers}")

        # 标记是否找到目标学生
        student_found = False
        
        # 遍历CSV行查找指定学生
        for row in reader:
            # 查找包含学生姓名的列（可能是"姓名"、"学生姓名"等）
            student_col = None
            for col in headers:
                if col in ["姓名", "学生姓名", "Name", "student_name"]:
                    student_col = col
                    break
            
            # 如果找到学生姓名列，检查是否匹配目标学生
            if student_col and row[student_col] == stu_name:
                # 获取学生的成绩字典
                score_dict = read_student_exam(conn, student_id)
                
                # 检查考试是否已存在
                exam_exists = exam_name in score_dict
                
                # 如果考试不存在，需要为该学生创建考试
                if not exam_exists:
                    # 创建新的考试数据结构
                    score_dict[exam_name] = {}
                    
                    # 使用传入的满分字典或从CSV表头提取科目信息
                    if full_scores is not None:
                        # 使用传入的满分字典
                        for subject, full_score in full_scores.items():
                            # 从CSV中获取该科目的成绩
                            if subject in row and row[subject] and row[subject].strip() != "":
                                try:
                                    score_value = float(row[subject])
                                    score_dict[exam_name][subject] = [score_value, full_score]
                                except ValueError:
                                    print(f"科目 {subject} 的成绩 '{row[subject]}' 不是有效数字，设置为0分")
                                    score_dict[exam_name][subject] = [0, full_score]
                            else:
                                # 如果CSV中没有该科目的成绩，设置为0分
                                score_dict[exam_name][subject] = [0, full_score]
                    else:
                        # 如果没有提供满分字典，从表头中提取科目信息并设置默认满分100
                        for header in headers:
                            if header not in ["姓名", "学号", "ID", "学生姓名", "账号", "Name", "ID", "student_name", "student_id"]:  # 非科目列
                                if header in row and row[header] and row[header].strip() != "":
                                    try:
                                        score_value = float(row[header])
                                        score_dict[exam_name][header] = [score_value, 100]  # 默认满分为100
                                    except ValueError:
                                        print(f"科目 {header} 的成绩 '{row[header]}' 不是有效数字，设置为0分")
                                        score_dict[exam_name][header] = [0, 100]
                                else:
                                    # 如果CSV中没有该科目的成绩，设置为0分
                                    score_dict[exam_name][header] = [0, 100]
                
                # 更新数据库中的成绩
                update_student_score(conn, student_id, score_dict)
                print(f"已为学生 {stu_name} 创建新考试: {exam_name}")

                # 对于已存在的考试，使用change_student_score函数更新各科成绩
                if exam_exists:
                    # 遍历表头，更新各科成绩
                    for header in headers:
                        # 跳过标识列（如姓名、学号等）
                        if header not in ["姓名", "学号", "ID", "学生姓名", "账号", "Name", "ID", "student_name", "student_id"]:  # 可以根据实际表头调整
                            # 获取该科目的成绩
                            score = row[header]

                            # 检查成绩是否为空
                            if score and score.strip() != "":
                                try:
                                    # 将成绩转换为数字
                                    score_value = float(score)

                                    # 使用change_student_score函数更新成绩
                                    updated_score_dict = change_student_score(
                                        score_dict=score_dict,
                                        exam_name=exam_name,
                                        subject=header,
                                        score=score_value
                                    )

                                    # 更新数据库中的成绩
                                    update_student_score(conn, student_id, updated_score_dict)

                                    print(f"已更新 {student_id} ({stu_name}) 在 {exam_name} 中 {header} 的成绩为 {score_value}")

                                    # 更新score_dict用于下一次循环
                                    score_dict = updated_score_dict
                                except ValueError:
                                    print(f"科目 {header} 的成绩 '{score}' 不是有效数字，跳过更新")
                            else:
                                print(f"科目 {header} 的成绩为空，跳过更新")
                
                student_found = True
                break  # 找到目标学生后退出循环
        
        if not student_found:
            print(f"在CSV文件中未找到学生 '{stu_name}' 的记录")
        else:
            print(f"已成功更新学生 '{stu_name}' 的成绩")

# 使用示例
# def example_usage():
#     """
#     使用示例
#     假设CSV文件格式如下：
#     姓名,学号,语文,数学,英语
#     张三,001,85,92,78
#     李四,002,90,87,85
#     """
#     csv_file_path = "student_scores.csv"  # CSV文件路径
#     conn = connect_db()  # 获取数据库连接
#     student_id = "teacher1@1"  # 学生ID
#     exam_name = "期中考试"  # 考试名称
# 
#     # 不指定学生姓名，处理CSV第一行
#     read_csv_and_update_scores(csv_file_path, conn, student_id, exam_name)
#     
#     # 指定学生姓名，查找对应行并更新成绩
#     read_csv_and_update_scores(csv_file_path, conn, student_id, exam_name, stu_name="张三")

def csv_updata(conn, csv_file_path, class_name, teacher_account, exam_name, full_scores=None):
    """
    从CSV文件更新学生考试数据
    
    参数:
    conn: 数据库连接对象
    csv_file_path: CSV文件路径
    class_name: 班级名称
    teacher_account: 教师账号
    exam_name: 考试名称
    full_scores: 满分字典，格式为{"科目1": 满分值, ...}
    """
    import csv

    # 读取CSV文件，获取考生名单
    with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        headers = reader.fieldnames

        # 查找包含学生姓名的列（可能是"姓名"、"学生姓名"等）
        student_col = None
        for col in headers:
            if col in ["姓名", "学生姓名", "Name", "student_name"]:
                student_col = col
                break

        if not student_col:
            print("错误：CSV文件中未找到学生姓名列")
            return False

        # 读取该班级下所有学生信息
        class_students = read_single_class(conn, teacher_account, class_name)
        # 创建学生姓名到ID的映射
        student_name_to_id = {}
        for student in class_students:
            student_name = read_student(conn, student["账号"])[0]  # 获取学生姓名
            student_name_to_id[student_name] = student["账号"]

        # 遍历CSV中的每个考生
        for row in reader:
            csv_student_name = row[student_col]

            if csv_student_name in student_name_to_id:
                # 学生已存在，更新其考试数据
                student_id = student_name_to_id[csv_student_name]
                print(f"正在更新学生 {csv_student_name} 的考试数据...")
                read_csv_and_update_scores(csv_file_path, conn, student_id, exam_name, full_scores)
            else:
                # 学生不存在，先创建学生
                print(f"学生 {csv_student_name} 不存在，正在创建...")
                student_id = add_student(conn, teacher_account, csv_student_name, class_name)
                new_student_id = f"{teacher_account}@{student_id}"
                print(f"已创建学生 {csv_student_name}，ID: {new_student_id}")

                # 更新该学生的考试数据
                read_csv_and_update_scores(csv_file_path, conn, new_student_id, exam_name, full_scores)

    print("CSV数据更新完成")
    return True


def detect_csv_subjects(csv_file_path):
    """
    检测CSV文件的科目信息并返回科目列表
    
    参数:
    csv_file_path: CSV文件路径
    
    返回:
    list: 科目名称列表
    """
    import csv
    
    with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        headers = reader.fieldnames
        
        # 定义标识列（非科目列）
        identifier_columns = ["姓名", "学号", "ID", "学生姓名", "账号", "Name", "student_name", "student_id"]
        
        # 过滤出科目列
        subjects = []
        for header in headers:
            if header not in identifier_columns:
                subjects.append(header)
    
    return subjects
