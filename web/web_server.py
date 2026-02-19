import binascii

import pymysql
from flask import Flask,redirect, url_for, session
from ALL_function import (
    connect_db,
    read_english_passage,
    read_vocabulary,
    add_free_account,
    create_teacher_table,
    add_teacher,
    authenticate_teacher,
    read_class,
    read_teacher_group,
    not_group_exam,
    read_student,
    read_single_class,
    read_student_exam,
    student_class_change,
    change_student_score,
    update_student_score,
    read_study_resources,
    read_all_subjects,
    read_video_detail,
    read_related_videos,
    read_english_articles,
    MYSQL_CONFIG,
    read_free_account_info,
    check_user_account_type,
    authenticate_free_account,
    update_user_exp,
    update_user_study_time,
    cheek_user_rank,
    save_new_word_ids_to_vo_book,
    read_some_word_form_certain_level
)

import os
import time
import hashlib
import smtplib
import random
import sys
from email.mime.text import MIMEText
from email.header import Header

# 导入 Redis 会话管理器
try:
    from redis_manager import (
        redis_session_manager,
        create_user_session,
        get_user_session,
        delete_user_session,
        force_logout_user,
        extend_user_session
    )
    REDIS_ENABLED = True
    print("✅ Redis 会话管理已启用")
except ImportError as e:
    REDIS_ENABLED = False
    print(f"⚠️  Redis 会话管理未启用: {e}")

# 检测运行环境
def is_development_mode():
    """检测是否为开发模式"""
    return os.environ.get('FLASK_ENV') == 'development' or \
           os.environ.get('ENVIRONMENT') == 'development' or \
           'debug' in sys.argv

# Flask应用初始化
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 设置密钥用于session

# 添加CORS支持
@app.after_request
def after_request(response):
    """添加CORS头以支持跨域请求"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# 生产环境优化配置
if not is_development_mode():
    # 生产环境配置
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # 安全配置增强
    app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS环境下启用
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # 性能优化
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 3600  # 静态文件缓存1小时
    
    print("生产环境配置已启用")
else:
    print("开发环境配置已启用")

# 用于存储验证码（在实际生产环境中应使用Redis等缓存服务）
verification_storage = {}

# 邮箱配置
EMAIL_CONFIG = {}

def send_verification_email_directly(email: str, code: str):
    """
    直接发送邮箱验证码（不依赖全局变量）
    
    Args:
        email: 接收验证码的邮箱地址
        code: 验证码
    """
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
        <div class="verification-code">{code}</div>
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
        
        print(f"验证码已发送至 {email}")
        
    except Exception as e:
        print(f"发送邮件失败: {e}")
        raise e

def verify_email_code_locally(email: str, code: str) -> bool:
    """
    本地验证邮箱验证码（使用应用级存储）
    
    Args:
        email: 邮箱地址
        code: 验证码
    
    Returns:
        bool: 验证是否成功
    """
    # 检查验证码是否存在
    if email not in verification_storage:
        print("邮箱未发送验证码或验证码已过期")
        return False
    
    # 检查验证码是否过期（10分钟有效期）
    stored_time = verification_storage[email]['timestamp']
    if time.time() - stored_time > 600:  # 10分钟 = 600秒
        print("验证码已过期")
        del verification_storage[email]
        return False
    
    # 检查验证码是否正确
    stored_code = verification_storage[email]['code']
    if code == stored_code:
        # 验证成功后删除验证码
        del verification_storage[email]
        return True
    else:
        print("验证码错误")
        return False

@app.route('/resource_web/<path:filename>')
def serve_resource_web(filename):
    """提供resource_web目录下的静态资源文件"""
    return send_from_directory('static/OKComputer_企业化网页重设/resource_web', filename)

@app.route('/video-files/<path:filename>')
def serve_video_files(filename):
    """提供视频文件服务"""
    try:
        # 尝试从不同可能的位置提供视频文件
        possible_paths = [
            f'static/videos/{filename}',
            f'videos/{filename}',
            filename  # 如果是完整路径
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return send_from_directory(os.path.dirname(path), os.path.basename(path))
        
        # 如果文件不存在，返回404
        return jsonify({
            'success': False,
            'message': f'视频文件不存在: {filename}'
        }), 404
        
    except Exception as e:
        print(f"提供视频文件时出错: {e}")
        return jsonify({
            'success': False,
            'message': f'文件服务错误: {str(e)}'
        }), 500

# 添加静态文件服务路由
@app.route('/static/<path:filename>')
def serve_static_files(filename):
    """提供静态文件服务（包括JS、CSS等）"""
    print(f"DEBUG: 请求静态文件: {filename}")
    try:
        # 检查文件是否存在
        full_path = os.path.join('static', filename)
        print(f"DEBUG: 完整路径: {full_path}")
        print(f"DEBUG: 文件存在: {os.path.exists(full_path)}")
        
        response = send_from_directory('static', filename)
        
        # 对于图片文件，禁用缓存以确保每次都重新加载
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            print(f"DEBUG: 为图片文件禁用缓存: {filename}")
        
        print(f"DEBUG: 静态文件服务成功: {filename}")
        return response
    except Exception as e:
        print(f"DEBUG: 提供静态文件时出错: {e}")
        print(f"DEBUG: 文件名: {filename}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'静态文件不存在: {filename}',
            'error': str(e)
        }), 404

@app.route('/api/send_verification_code', methods=['POST'])
def api_send_verification_code():
    """发送邮箱验证码"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({
                'success': False, 
                'message': '邮箱不能为空'
            }), 400
        
        # 验证邮箱格式
        import re
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return jsonify({
                'success': False, 
                'message': '邮箱格式不正确'
            }), 400
        
        # 生成6位随机验证码
        import random
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # 发送验证码到邮箱
        try:
            send_verification_email_directly(email, verification_code)
        except Exception as e:
            print(f"发送邮件失败: {e}")
            return jsonify({
                'success': False, 
                'message': '验证码发送失败，请稍后重试'
            }), 500
        
        # 存储验证码到应用级别存储（带时间戳）
        verification_storage[email] = {
            'code': verification_code,
            'timestamp': time.time()
        }
        
        print(f"验证码已发送至 {email}")
        return jsonify({
            'success': True, 
            'message': '验证码已发送至您的邮箱'
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'发送验证码过程中出现错误: {str(e)}'
        }), 500



@app.route('/api/register', methods=['POST'])
@app.route('/api/register_with_verification', methods=['POST'])
def api_register():
    """处理新的注册请求（包含姓名和邮箱验证码验证）"""
    try:
        data = request.get_json()
        name = data.get('name')
        account = data.get('account')
        password = data.get('password')
        email = data.get('email')
        verification_code = data.get('verification_code')
        
        # 验证必需字段
        if not name or not account or not password or not email or not verification_code:
            return jsonify({
                'success': False, 
                'message': '姓名、账号、密码、邮箱和验证码不能为空'
            }), 400
            
        # 验证邮箱验证码
        if not verify_email_code_locally(email, verification_code):
            return jsonify({
                'success': False, 
                'message': '邮箱验证码错误或已过期'
            }), 400
        
        # 执行注册逻辑
        conn = connect_db()
        success = add_teacher(conn, account, password, email, "{}", "{}")
        conn.close()
        
        if success:
            return jsonify({
                'success': True, 
                'message': '注册成功！'
            })
        else:
            return jsonify({
                'success': False, 
                'message': '注册失败，账号可能已存在'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'注册过程中出现错误: {str(e)}'
        }), 500

# 重复的app实例定义已删除，保留文件开头的app实例

# 初始化数据库连接 - 仅用于首次创建表
initial_conn = connect_db()
create_teacher_table(initial_conn)
initial_conn.close()  # 关闭初始连接

@app.route('/')
def index_root():
    """根路径重定向到学习平台页面"""
    return redirect(url_for('learning_platform_page'))

@app.route('/index')
def index():
    """智慧管理首页"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/index.html')

@app.route('/learning-platform')
def learning_platform_page():
    """在线学习平台页面"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/learning_platform.html')

@app.route('/login')
def login():
    """登录页面"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/login.html')

@app.route('/register')
def register():
    """学习账户注册登录页面"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/register_login.html')

@app.route('/register_login.html')
def register_login_html():
    """直接访问注册登录页面HTML文件"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/register_login.html')

@app.route('/leaderboard')
def leaderboard_page():
    """排行榜页面"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/leaderboard.html')

@app.route('/profile')
def profile_page():
    """个人主页页面"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/profile.html')

@app.route('/friends')
def friends_page():
    """个人好友页面"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/friends.html')

@app.route('/api/free_register', methods=['POST'])
def api_free_register():
    """处理免费账户注册请求"""
    try:
        data = request.get_json()
        name = data.get('name')
        account = data.get('account')
        password = data.get('password')
        email = data.get('email')
        verification_code = data.get('verification_code')
        
        # 验证必需字段
        if not name or not account or not password or not email or not verification_code:
            return jsonify({
                'success': False, 
                'message': '姓名、账号、密码、邮箱和验证码不能为空'
            }), 400
            
        # 验证邮箱验证码
        if not verify_email_code_locally(email, verification_code):
            return jsonify({
                'success': False, 
                'message': '邮箱验证码错误或已过期'
            }), 400
        
        # 创建免费账户，包含邮箱信息
        success = add_free_account(name, account, password, email)
        
        if success:
            return jsonify({
                'success': True, 
                'message': '免费账户注册成功！'
            })
        else:
            return jsonify({
                'success': False, 
                'message': '注册失败，账号可能已存在'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'注册过程中出现错误: {str(e)}'
        }), 500

@app.route('/api/update-spelling-exp', methods=['POST'])
def api_update_spelling_exp():
    """处理拼写训练完成后的经验值更新"""
    try:
        # 添加调试日志
        print("=== 拼写训练经验值更新请求 ===")
        print(f"请求Headers: {dict(request.headers)}")
        print(f"请求数据: {request.get_data()}"), 400
        
        data = request.get_json()
        print(f"解析后的JSON数据: {data}")
        
        account = data.get('account')
        correct_count = data.get('correct_count', 0)
        wrong_count = data.get('wrong_count', 0)
        streak_count = data.get('streak_count', 0)
        
        print(f"提取的参数: account={account}, correct_count={correct_count}, wrong_count={wrong_count}, streak_count={streak_count}")
        
        # 验证必需字段
        if not account:
            print("❌ 账户名为空")
            return jsonify({
                'success': False, 
                'message': '账户名不能为空'
            }), 400
        
        # 验证数据类型
        try:
            correct_count = int(correct_count)
            wrong_count = int(wrong_count)
            streak_count = int(streak_count)
        except (ValueError, TypeError):
            return jsonify({
                'success': False, 
                'message': '统计数据必须是数字'
            }), 400
        
        # 计算经验值: 正确词数*4 + 错误词数*2 + 连对*2
        exp_gained = correct_count * 4 + wrong_count * 2 + streak_count * 2
        
        # 直接连接数据库更新经验值
        conn = connect_db('free_account')
        cursor = conn.cursor()
        
        try:
            # 首先检查用户是否存在
            cursor.execute('SELECT account FROM acc WHERE account = %s', (account,))
            user_exists = cursor.fetchone()
            
            if not user_exists:
                conn.close()
                return jsonify({
                    'success': False, 
                    'message': f'用户账户 {account} 不存在'
                }), 404
            
            # 更新用户的总经验值
            cursor.execute('''
                UPDATE acc SET exp = exp + %s WHERE account = %s
            ''', (exp_gained, account))
            
            # 更新学习时间（这里设为0，因为拼写训练不计入学习时间）
            cursor.execute('''
                UPDATE acc SET study_time = study_time + %s WHERE account = %s
            ''', (0, account))
            
            conn.commit()
            conn.close()
            
            # 更新用户等级
            cheek_user_rank(account)
            
            return jsonify({
                'success': True, 
                'message': f'经验值更新成功！获得 {exp_gained} 点经验',
                'exp_gained': exp_gained,
                'correct_count': correct_count,
                'wrong_count': wrong_count,
                'streak_count': streak_count
            })
            
        except Exception as db_error:
            conn.rollback()
            conn.close()
            print(f'数据库更新失败: {db_error}')
            return jsonify({
                'success': False, 
                'message': f'数据库更新失败: {str(db_error)}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'更新拼写训练经验值过程中出现错误: {str(e)}'
        }), 500

@app.route('/api/update-reading-exp', methods=['POST'])
def api_update_reading_exp():
    """处理阅读完成后的经验值更新"""
    try:
        data = request.get_json()
        account = data.get('account')
        reading_minutes = data.get('reading_minutes', 0)
        unknown_words_count = data.get('unknown_words_count', 0)
        
        # 验证必需字段
        if not account:
            return jsonify({
                'success': False, 
                'message': '账户名不能为空'
            }), 400
        
        # 验证数据类型
        try:
            reading_minutes = int(reading_minutes)
            unknown_words_count = int(unknown_words_count)
        except (ValueError, TypeError):
            return jsonify({
                'success': False, 
                'message': '阅读时间和生词数必须是数字'
            }), 400
        
        # 调用数据库更新函数
        success = update_user_exp(account, reading_minutes, unknown_words_count)
        update_user_study_time(account, reading_minutes)
        cheek_user_rank( account)
        
        if success:
            # 计算获得的经验值
            exp_gained = reading_minutes * 30 + unknown_words_count * 5
            return jsonify({
                'success': True, 
                'message': f'经验值更新成功！获得 {exp_gained} 点经验',
                'exp_gained': exp_gained,
                'total_reading_minutes': reading_minutes,
                'unknown_words_count': unknown_words_count
            })
        else:
            return jsonify({
                'success': False, 
                'message': '经验值更新失败，请稍后重试'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'更新经验值过程中出现错误: {str(e)}'
        }), 500

@app.route('/api/update-learning-exp', methods=['POST'])
def api_update_learning_exp():
    """处理学习活动完成后的经验值更新（如生词学习等）"""
    try:
        data = request.get_json()
        account = data.get('account')
        exp_gained = data.get('exp_gained', 0)
        activity_type = data.get('activity_type', 'learning')
        description = data.get('description', '')
        
        # 验证必需字段
        if not account:
            return jsonify({
                'success': False, 
                'message': '账户名不能为空'
            }), 400
        
        # 验证经验值
        try:
            exp_gained = int(exp_gained)
            if exp_gained <= 0:
                return jsonify({
                    'success': False, 
                    'message': '获得的经验值必须大于0'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False, 
                'message': '经验值必须是正整数'
            }), 400
        
        # 直接连接数据库验证并更新用户经验值
        conn = connect_db('free_account')
        cursor = conn.cursor()
        
        try:
            # 首先检查用户是否存在
            cursor.execute('SELECT account FROM acc WHERE account = %s', (account,))
            user_exists = cursor.fetchone()
            
            if not user_exists:
                conn.close()
                return jsonify({
                    'success': False, 
                    'message': f'用户账户 {account} 不存在'
                }), 404
            
            # 更新用户的总经验值
            cursor.execute('''
                UPDATE acc SET exp = exp + %s WHERE account = %s
            ''', (exp_gained, account))
            
            # 更新学习时间（这里设为0，因为我们只关注经验值）
            cursor.execute('''
                UPDATE acc SET study_time = study_time + %s WHERE account = %s
            ''', (0, account))
            
            conn.commit()
            conn.close()
            
            # 更新用户等级
            cheek_user_rank(account)
            
            return jsonify({
                'success': True, 
                'message': f'经验值更新成功！获得 {exp_gained} 点经验',
                'exp_gained': exp_gained,
                'activity_type': activity_type,
                'description': description
            })
            
        except Exception as db_error:
            conn.rollback()
            conn.close()
            print(f'数据库更新失败: {db_error}')
            return jsonify({
                'success': False, 
                'message': f'数据库更新失败: {str(db_error)}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'更新学习经验值过程中出现错误: {str(e)}'
        }), 500

@app.route('/api/save-new-word-ids', methods=['POST'])
def api_save_new_word_ids():
    """处理保存生词ID到vo_book表的请求"""
    try:
        data = request.get_json()
        account = data.get('account')
        word_ids = data.get('word_ids', [])
        
        # 验证必需字段
        if not account:
            return jsonify({
                'success': False, 
                'message': '账户名不能为空'
            }), 400
        
        if not word_ids or not isinstance(word_ids, list):
            return jsonify({
                'success': False, 
                'message': '生词ID列表不能为空且必须是数组'
            }), 400
        
        # 验证ID都是数字
        try:
            word_ids = [int(word_id) for word_id in word_ids]
        except (ValueError, TypeError):
            return jsonify({
                'success': False, 
                'message': '所有生词ID必须是数字'
            }), 400
        
        # 调用数据库保存函数
        success = save_new_word_ids_to_vo_book(account, word_ids)
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'成功保存 {len(word_ids)} 个生词ID',
                'saved_count': len(word_ids)
            })
        else:
            return jsonify({
                'success': False, 
                'message': '保存生词ID失败，请稍后重试'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'保存生词ID过程中出现错误: {str(e)}'
        }), 500

@app.route('/api/free_login', methods=['POST'])
def api_free_login():
    """处理免费账户登录请求"""
    try:
        data = request.get_json()
        account = data.get('account')
        password = data.get('password')
        
        if not account or not password:
            return jsonify({
                'success': False, 
                'message': '账号和密码不能为空'
            }), 400
            
        # 验证用户凭据
        authenticated = authenticate_free_account(account, password)
        
        if authenticated:
            # 创建会话
            session_id = None
            if REDIS_ENABLED and redis_session_manager.is_connected():
                # 使用 Redis 创建会话
                session_id = create_user_session(account, expires_in_hours=24)
                if session_id:
                    response_data = {
                        'success': True, 
                        'message': f'登录成功！欢迎您，{account}',
                        'user': {'account': account, 'type': 'free'},
                        'session_id': session_id
                    }
                    # 设置 Cookie
                    response = jsonify(response_data)
                    response.set_cookie(
                        'session_id', 
                        session_id, 
                        max_age=24*3600,  # 24小时
                        httponly=True,    # 防止 XSS
                        secure=False,     # 开发环境设为 False，生产环境应设为 True
                        samesite='Lax'
                    )
                    return response
                else:
                    # Redis 失败回退到 Flask session
                    print("⚠️  Redis 会话创建失败，回退到 Flask session")
                    session['user_account'] = account
                    session['user_type'] = 'free'
                    # 生成临时session_id用于cookie
                    import uuid
                    temp_session_id = str(uuid.uuid4())
                    response_data = {
                        'success': True, 
                        'message': f'登录成功！欢迎您，{account}',
                        'user': {'account': account, 'type': 'free'},
                        'session_id': temp_session_id
                    }
                    response = jsonify(response_data)
                    response.set_cookie(
                        'session_id', 
                        temp_session_id, 
                        max_age=24*3600,  # 24小时
                        httponly=True,    # 防止 XSS
                        secure=False,     # 开发环境设为 False，生产环境应设为 True
                        samesite='Lax'
                    )
                    return response
            else:
                # Redis 不可用，使用 Flask session
                session['user_account'] = account
                session['user_type'] = 'free'
                # 生成临时session_id用于cookie
                import uuid
                temp_session_id = str(uuid.uuid4())
                response_data = {
                    'success': True, 
                    'message': f'登录成功！欢迎您，{account}',
                    'user': {'account': account, 'type': 'free'},
                    'session_id': temp_session_id
                }
                response = jsonify(response_data)
                response.set_cookie(
                    'session_id', 
                    temp_session_id, 
                    max_age=24*3600,  # 24小时
                    httponly=True,    # 防止 XSS
                    secure=False,     # 开发环境设为 False，生产环境应设为 True
                    samesite='Lax'
                )
                return response
        else:
            return jsonify({
                'success': False, 
                'message': '账号或密码错误'
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'登录过程中出现错误: {str(e)}'
        }), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    """处理登录请求 - 支持 Redis 会话"""
    conn = None
    try:
        conn = connect_db()  # 为每个请求创建新连接
        data = request.get_json()
        account = data.get('account')
        password = data.get('password')
        
        if not account or not password:
            return jsonify({
                'success': False, 
                'message': '账号和密码不能为空'
            }), 400
            
        # 验证用户凭据
        authenticated = authenticate_teacher(conn, account, password)
        
        if authenticated:
            # 创建会话
            session_id = None
            if REDIS_ENABLED and redis_session_manager.is_connected():
                # 使用 Redis 创建会话
                session_id = create_user_session(account, expires_in_hours=24)
                if session_id:
                    response_data = {
                        'success': True, 
                        'message': f'登录成功！欢迎您，{account}',
                        'user': {'account': account},
                        'session_id': session_id
                    }
                    # 设置 Cookie
                    response = jsonify(response_data)
                    response.set_cookie(
                        'session_id', 
                        session_id, 
                        max_age=24*3600,  # 24小时
                        httponly=True,    # 防止 XSS
                        secure=False,     # 开发环境设为 False，生产环境应设为 True
                        samesite='Lax'
                    )
                    return response
                else:
                    # Redis 失败回退到 Flask session
                    print("⚠️  Redis 会话创建失败，回退到 Flask session")
                    session['user_account'] = account
                    # 生成临时session_id用于cookie
                    import uuid
                    temp_session_id = str(uuid.uuid4())
                    response_data = {
                        'success': True, 
                        'message': f'登录成功！欢迎您，{account}',
                        'user': {'account': account},
                        'session_id': temp_session_id
                    }
                    response = jsonify(response_data)
                    response.set_cookie(
                        'session_id', 
                        temp_session_id, 
                        max_age=24*3600,  # 24小时
                        httponly=True,    # 防止 XSS
                        secure=False,     # 开发环境设为 False，生产环境应设为 True
                        samesite='Lax'
                    )
                    return response
            else:
                # Redis 不可用，使用 Flask session
                session['user_account'] = account
                # 生成临时session_id用于cookie
                import uuid
                temp_session_id = str(uuid.uuid4())
                response_data = {
                    'success': True, 
                    'message': f'登录成功！欢迎您，{account}',
                    'user': {'account': account},
                    'session_id': temp_session_id
                }
                response = jsonify(response_data)
                response.set_cookie(
                    'session_id', 
                    temp_session_id, 
                    max_age=24*3600,  # 24小时
                    httponly=True,    # 防止 XSS
                    secure=False,     # 开发环境设为 False，生产环境应设为 True
                    samesite='Lax'
                )
                return response
        else:
            return jsonify({
                'success': False, 
                'message': '账号或密码错误'
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'登录过程中出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()  # 确保连接被关闭

@app.route('/api/current_user', methods=['GET'])
def get_current_user():
    """获取当前登录用户信息 - 支持 Redis 会话"""
    print(f"DEBUG: /api/current_user 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    user_account = None
    user_type = None
    session_id = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
                user_type = 'free'  # Redis会话通常用于免费账户
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        user_type = session.get('user_type', 'teacher')
        print(f"DEBUG: 使用 Flask session，用户: {user_account}, 类型: {user_type}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")
    
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 成功获取用户信息，用户: {user_account}, 类型: {user_type}")
    
    return jsonify({
        'success': True,
        'user': {
            'account': user_account,
            'type': user_type
        }
    })

@app.route('/api/check-user-type', methods=['GET'])
def check_user_type():
    """检查用户类型并返回相应的页面跳转信息 - 支持 Redis 会话"""
    print(f"DEBUG: /api/check-user-type 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    user_account = None
    session_id = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")
    
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 开始检查用户类型，用户: {user_account}")
    
    # 检查用户类型
    user_type = check_user_account_type(user_account)
    
    if user_type:
        print(f"DEBUG: 用户类型检查成功: {user_type}")
        return jsonify({
            'success': True,
            'userType': user_type,
            'user': {'account': user_account}
        })
    else:
        print(f"DEBUG: 无法确定用户类型")
        return jsonify({
            'success': False,
            'message': '无法确定用户类型'
        }), 400






@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """获取统计信息 - 支持 Redis 会话"""
    print(f"DEBUG: /api/statistics 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问统计API，用户: {user_account}")
    conn = None
    try:
        conn = connect_db()
        
        # 获取班级数量
        classes = read_class(conn, user_account)
        class_count = len(classes) if classes else 0
        
        # 获取学生数量
        student_count = 0
        if classes:
            for class_name in classes:
                students = read_single_class(conn, user_account, class_name)
                student_count += len(students) if students else 0
        
        # 获取考试数量
        grouped_exams = read_teacher_group(conn, user_account)
        ungrouped_exams = not_group_exam(conn, user_account)
        exam_count = len(grouped_exams) + len(ungrouped_exams)
        
        # 计算平均及格率（模拟数据，实际应用中需要根据具体逻辑计算）
        avg_pass_rate = "96%"  # 这里使用模拟数据，实际应用中需要复杂计算
        
        statistics = {
            'classCount': class_count,
            'studentCount': student_count,
            'examCount': exam_count,
            'avgPassRate': avg_pass_rate
        }
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取统计数据时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/leaderboard/<leaderboard_type>')
def get_leaderboard(leaderboard_type):
    """获取排行榜数据 - 支持 Redis 会话"""
    print(f"DEBUG: /api/leaderboard/{leaderboard_type} 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问排行榜API，用户: {user_account}")
    
    # 获取查询参数
    time_range = request.args.get('range', 'all')
    
    try:
        # 生成模拟排行榜数据
        leaderboard_data = generate_mock_leaderboard(leaderboard_type, time_range)
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard_data,
            'totalCount': len(leaderboard_data)
        })
        
    except Exception as e:
        print(f"获取排行榜数据时出错: {e}")
        return jsonify({
            'success': False,
            'message': f'获取排行榜数据时出现错误: {str(e)}'
        }), 500

@app.route('/api/class-distribution', methods=['GET'])
def get_class_distribution():
    """获取班级分布数据用于饼图 - 支持 Redis 会话"""
    print(f"DEBUG: /api/class-distribution 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问班级分布API，用户: {user_account}")
    conn = None
    try:
        conn = connect_db()
        
        # 获取所有班级
        classes = read_class(conn, user_account)
        
        if not classes:
            return jsonify({
                'success': True,
                'distribution': {
                    'classNames': ['暂无班级'],
                    'studentCounts': [0]
                }
            })
        
        # 获取每个班级的学生数量
        classNames = []
        studentCounts = []
        
        for class_name in classes:
            students = read_single_class(conn, user_account, class_name)
            student_count = len(students) if students else 0
            classNames.append(class_name)
            studentCounts.append(student_count)
        
        return jsonify({
            'success': True,
            'distribution': {
                'classNames': classNames,
                'studentCounts': studentCounts
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取班级分布数据时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/subject-comparison', methods=['GET'])
def get_subject_comparison():
    """获取科目对比数据用于柱状图 - 支持 Redis 会话"""
    print(f"DEBUG: /api/subject-comparison 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问科目对比API，用户: {user_account}")
    conn = None
    try:
        conn = connect_db()
        
        # 获取所有班级
        classes = read_class(conn, user_account)
        
        if not classes:
            return jsonify({
                'success': True,
                'comparison': {
                    'subjects': ['暂无数据'],
                    'datasets': []
                }
            })
        
        # 为了生成科目对比图，我们需要获取每个班级的主要科目及其平均分
        # 获取第一个班级的几个学生及其成绩，以确定科目列表
        subjects = set()
        class_averages = {}  # 存储每个班级的科目平均分
        
        for class_name in classes:
            students = read_single_class(conn, user_account, class_name)
            class_subject_totals = {}  # 存储每个科目的总分
            class_subject_counts = {}  # 存储每个科目的计数
            
            if students:
                for student in students:
                    student_id = student["账号"]
                    student_exams = read_student_exam(conn, student_id)
                    
                    for exam_data in student_exams.values():
                        for subject, (score, total) in exam_data.items():
                            subjects.add(subject)
                            
                            if subject not in class_subject_totals:
                                class_subject_totals[subject] = 0
                                class_subject_counts[subject] = 0
                            
                            class_subject_totals[subject] += score
                            class_subject_counts[subject] += 1
            
            # 计算平均分
            class_averages[class_name] = {}
            for subject in subjects:
                if subject in class_subject_totals and class_subject_counts[subject] > 0:
                    avg_score = class_subject_totals[subject] / class_subject_counts[subject]
                    class_averages[class_name][subject] = round(avg_score, 2)
                else:
                    class_averages[class_name][subject] = 0
        
        # 限制最多显示3个主要科目
        top_subjects = list(subjects)[:3] if subjects else ['暂无科目']
        
        # 为每个班级创建数据集
        datasets = []
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
        
        for i, class_name in enumerate(classes):
            dataset = {
                'label': class_name,
                'data': [],
                'backgroundColor': colors[i % len(colors)],
                'borderColor': colors[i % len(colors)],
                'borderWidth': 1
            }
            
            for subject in top_subjects:
                avg_score = class_averages.get(class_name, {}).get(subject, 0)
                dataset['data'].append(avg_score)
            
            datasets.append(dataset)
        
        return jsonify({
            'success': True,
            'comparison': {
                'subjects': top_subjects,
                'datasets': datasets
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取科目对比数据时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/classes', methods=['GET'])
def get_classes():
    """获取班级列表用于班级管理页面 - 支持 Redis 会话"""
    print(f"DEBUG: /api/classes 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问班级列表API，用户: {user_account}")
    conn = None
    try:
        conn = connect_db()
        
        # 获取所有班级
        classes = read_class(conn, user_account)
        
        if not classes:
            return jsonify({
                'success': True,
                'classes': []
            })
        
        # 为每个班级准备详细信息
        class_list = []
        
        for class_name in classes:
            students = read_single_class(conn, user_account, class_name)
            student_count = len(students) if students else 0
            
            # 计算班级平均分
            total_score = 0
            total_count = 0
            
            if students:
                for student in students:
                    student_id = student["账号"]
                    student_exams = read_student_exam(conn, student_id)
                    
                    for exam_data in student_exams.values():
                        for subject, (score, total) in exam_data.items():
                            total_score += score
                            total_count += 1
            
            avg_score = total_score / total_count if total_count > 0 else 0
            
            # 计算考试数量（这里简化为统计学生考试记录数）
            exam_count = 0
            if students:
                for student in students:
                    student_id = student["账号"]
                    student_exams = read_student_exam(conn, student_id)
                    exam_count = max(exam_count, len(student_exams))
            
            class_info = {
                'name': class_name,
                'studentCount': student_count,
                'avgScore': avg_score,
                'examCount': exam_count
            }
            
            class_list.append(class_info)
        
        return jsonify({
            'success': True,
            'classes': class_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取班级列表时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/class-detail/<class_name>', methods=['GET'])
def get_class_detail(class_name):
    """获取班级详细信息 - 支持 Redis 会话"""
    print(f"DEBUG: /api/class-detail/{class_name} 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问班级详情API，用户: {user_account}")
    conn = None
    try:
        conn = connect_db()
        
        # 获取指定班级的学生列表
        students = read_single_class(conn, user_account, class_name)
        
        if not students:
            return jsonify({
                'success': False,
                'message': '班级不存在或无学生数据'
            })
        
        # 计算班级整体信息
        student_count = len(students)
        total_score = 0
        total_count = 0
        exam_count = 0
        passed_count = 0  # 及格人数（假设60分为及格线）
        
        # 存储学生详细信息
        student_list = []
        subject_totals = {}  # 存储各科目的总分
        subject_counts = {}  # 存储各科目的计数
        
        for student in students:
            student_id = student["账号"]
            student_name = student["名称"]
            student_exams = read_student_exam(conn, student_id)
            
            # 计算学生的平均分和考试次数
            student_total_score = 0
            student_score_count = 0
            student_passed_count = 0
            
            for exam_data in student_exams.values():
                for subject, (score, total) in exam_data.items():
                    student_total_score += score
                    student_score_count += 1
                    total_score += score
                    total_count += 1
                    
                    # 统计科目总分
                    if subject not in subject_totals:
                        subject_totals[subject] = 0
                        subject_counts[subject] = 0
                    subject_totals[subject] += score
                    subject_counts[subject] += 1
                    
                    # 统计及格情况
                    if score >= 60:
                        student_passed_count += 1
                        passed_count += 1
            
            # 存储学生信息
            student_info = {
                'name': student_name,
                'account': student_id,
                'avgScore': student_total_score / student_score_count if student_score_count > 0 else 0,
                'examCount': len(student_exams),
                'passedRate': (student_passed_count / student_score_count * 100) if student_score_count > 0 else 0
            }
            student_list.append(student_info)
            
            # 更新考试数量
            exam_count = max(exam_count, len(student_exams))
        
        # 计算班级平均分和及格率
        class_avg_score = total_score / total_count if total_count > 0 else 0
        class_pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0
        
        # 计算各科目平均分
        subject_averages = {}
        for subject in subject_totals:
            subject_averages[subject] = subject_totals[subject] / subject_counts[subject]
        
        # 准备返回数据
        class_detail = {
            'className': class_name,
            'studentCount': student_count,
            'avgScore': round(class_avg_score, 2),
            'passRate': round(class_pass_rate, 2),
            'examCount': exam_count,
            'students': student_list,
            'subjectAverages': subject_averages
        }
        
        return jsonify({
            'success': True,
            'classDetail': class_detail
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取班级详情时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/class-detail')
def class_detail():
    """班级详情页面 - 支持 Redis 会话"""
    print(f"DEBUG: /class-detail 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，重定向到登录页面
    if not user_account:
        print(f"DEBUG: 未找到有效会话，重定向到登录页面")
        return redirect(url_for('login'))
    
    print(f"DEBUG: 允许访问 class-detail 页面，用户: {user_account}")
    return send_from_directory('static', 'OKComputer_企业化网页重设/class_detail.html')

@app.route('/video-player')
def video_player():
    """视频播放页面"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/video_player.html')

@app.route('/api/video-detail/<int:video_id>')
def get_video_detail(video_id):
    """获取视频详情信息"""
    conn = None
    try:
        # 连接study_resource数据库
        conn = connect_db('study_resource')
        
        # 获取指定视频的详细信息
        video_detail = read_video_detail(conn, video_id)
        
        if not video_detail:
            return jsonify({
                'success': False,
                'message': '视频不存在'
            }), 404
        
        # 获取相关推荐视频
        related_videos = read_related_videos(conn, video_id, video_detail.get('subject_id'))
        
        return jsonify({
            'success': True,
            'video': video_detail,
            'related_videos': related_videos
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取视频详情时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/student-detail')
def student_detail():
    """学生详情页面 - 支持 Redis 会话"""
    print(f"DEBUG: /student-detail 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，重定向到登录页面
    if not user_account:
        print(f"DEBUG: 未找到有效会话，重定向到登录页面")
        return redirect(url_for('login'))
    
    print(f"DEBUG: 允许访问 student-detail 页面，用户: {user_account}")
    return send_from_directory('static', 'OKComputer_企业化网页重设/student_detail.html')


@app.route('/modify-score')
def modify_score():
    """修改成绩页面 - 支持 Redis 会话"""
    print(f"DEBUG: /modify-score 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，重定向到登录页面
    if not user_account:
        print(f"DEBUG: 未找到有效会话，重定向到登录页面")
        return redirect(url_for('login'))
    
    print(f"DEBUG: 允许访问 modify-score 页面，用户: {user_account}")
    return send_from_directory('static', 'OKComputer_企业化网页重设/modify_score.html')


@app.route('/api/student-exam-data/<student_account>')
def get_student_exam_data(student_account):
    """获取学生的考试数据"""
    if 'user_account' not in session:
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    user_account = session['user_account']
    conn = None
    try:
        conn = connect_db()
        
        # 获取学生考试数据
        student_exams = read_student_exam(conn, student_account)
        
        return jsonify({
            'success': True,
            'examData': student_exams
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取学生考试数据时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/student-detail/<student_account>', methods=['GET'])
def get_student_detail(student_account):
    """获取学生详细信息 - 支持 Redis 会话"""
    print(f"DEBUG: /api/student-detail/{student_account} 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问学生详情API，用户: {user_account}")
    conn = None
    try:
        conn = connect_db()
        
        # 获取学生基本信息
        student_info = read_student(conn, student_account)
        
        if not student_info:
            return jsonify({
                'success': False,
                'message': '学生不存在或无数据'
            })
        
        # 确保返回正确的数据结构
        if len(student_info) < 2:
            return jsonify({
                'success': False,
                'message': '学生信息数据不完整'
            })
        
        # 获取学生考试数据
        student_exams = read_student_exam(conn, student_account)
        
        # 初始化各项指标
        total_exams = len(student_exams)
        total_score = 0
        total_count = 0
        highest_score = 0
        lowest_score = float('inf')  # 初始化为无穷大
        passed_count = 0  # 及格考试次数
        subject_totals = {}  # 各科目总分
        subject_counts = {}  # 各科目考试次数
        exam_records = []  # 考试记录详情
        exam_trend_labels = []  # 考试趋势标签
        exam_trend_data = []  # 考试趋势数据
        
        # 遍历考试数据并计算各项指标
        for exam_name, exam_data in student_exams.items():
            # 计算本次考试总分
            exam_total = 0
            exam_max = 0
            
            for subject, (score, max_score) in exam_data.items():
                if subject != 'total':  # 跳过total字段
                    exam_total += score
                    exam_max += max_score
                    total_score += score
                    total_count += 1
                    
                    # 记录最高分和最低分
                    if score > highest_score:
                        highest_score = score
                    if score < lowest_score:
                        lowest_score = score
                    
                    # 统计科目数据
                    if subject not in subject_totals:
                        subject_totals[subject] = 0
                        subject_counts[subject] = 0
                    subject_totals[subject] += score
                    subject_counts[subject] += 1
                    
                    # 统计及格情况
                    if score >= 60:
                        passed_count += 1
            
            # 添加考试记录
            exam_record = {
                'examName': exam_name,
                'date': '2024-01-01',  # 实际应用中应从数据库获取
                'subjects': exam_data,
                'total': [exam_total, exam_max]
            }
            exam_records.append(exam_record)
            
            # 添加考试趋势数据
            exam_trend_labels.append(exam_name)
            exam_trend_data.append(exam_total)
        
        # 处理没有考试数据的情况
        if total_count == 0:
            avg_score = 0
            pass_rate = '0%'
            lowest_score = 0  # 如果没有考试数据，最低分设为0
        else:
            avg_score = total_score / total_count
            pass_rate = f"{(passed_count / total_count * 100):.1f}%"
        
        # 计算各科目平均分
        subject_averages = {}
        for subject in subject_totals:
            subject_averages[subject] = subject_totals[subject] / subject_counts[subject]
        
        # 找出最强和最弱科目
        strongest_subject = ""
        strongest_score = 0
        weakest_subject = ""
        weakest_score = float('inf')
        
        for subject, avg in subject_averages.items():
            if avg > strongest_score:
                strongest_score = avg
                strongest_subject = subject
            if avg < weakest_score:
                weakest_score = avg
                weakest_subject = subject
        
        # 如果没有科目数据，设置默认值
        if not subject_averages:
            strongest_subject = "暂无数据"
            strongest_score = 0
            weakest_subject = "暂无数据"
            weakest_score = 0
        else:
            # 如果没找到最弱科目（例如所有科目分数相同），使用任意一个科目
            if weakest_subject == "":
                weakest_subject = list(subject_averages.keys())[0]
                weakest_score = subject_averages[weakest_subject]
        
        # 模拟AI分析（实际应用中应调用AI分析函数）
        ai_analysis = "该学生在较强科目表现优异，但在部分科目仍需加强练习。建议重点关注薄弱环节，制定个性化学习计划。" if total_count > 0 else "暂无考试数据，无法进行分析。"
        
        # 模拟变化数据
        avg_score_change = "+2.5" if total_count > 0 else "0.0"  # 模拟数据
        pass_rate_change = "+5.0%" if total_count > 0 else "0.0%"  # 模拟数据
        
        result = {
            'success': True,
            'studentInfo': {
                'name': student_info[0],
                'account': student_account,
                'className': student_info[1],
                'avgScore': avg_score,
                'examCount': total_exams,
                'highestScore': highest_score,
                'lowestScore': lowest_score,  # 添加最低分
                'passRate': pass_rate,
                'avgScoreChange': avg_score_change,
                'passRateChange': pass_rate_change
            },
            'examRecords': exam_records,
            'examTrendData': {
                'labels': exam_trend_labels,
                'data': exam_trend_data
            },
            'subjectAverages': subject_averages,
            'strongestSubject': strongest_subject,
            'strongestScore': strongest_score,
            'weakestSubject': weakest_subject,
            'weakestScore': weakest_score,
            'aiAnalysis': ai_analysis
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f'获取学生详情时出现错误: {str(e)}')  # 添加错误日志
        return jsonify({
            'success': False,
            'message': f'获取学生详情时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()



@app.route('/dashboard')
def dashboard():
    """仪表板页面 - 登录成功后跳转的页面"""
    print(f"DEBUG: 请求到达 /dashboard 路由")
    print(f"DEBUG: Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，重定向到登录页面
    if not user_account:
        print(f"DEBUG: 未找到有效会话，重定向到登录页面")
        return redirect(url_for('login'))
    
    print(f"DEBUG: 允许访问 dashboard，用户: {user_account}")
    # 传递用户名给前端
    return send_from_directory('static', 'OKComputer_企业化网页重设/dashboard.html')

@app.route('/classes')
def classes():
    """班级管理页面"""
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        if session_id:
            session_data = get_user_session(session_id)
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
    
    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
    
    # 如果都没有找到有效的会话，重定向到登录页面
    if not user_account:
        return redirect(url_for('login'))
        
    return send_from_directory('static', 'OKComputer_企业化网页重设/classes.html')

@app.route('/exams')
def exams():
    """考试管理页面"""
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        if session_id:
            session_data = get_user_session(session_id)
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
    
    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
    
    # 如果都没有找到有效的会话，重定向到登录页面
    if not user_account:
        return redirect(url_for('login'))
        
    return send_from_directory('static', 'OKComputer_企业化网页重设/exams.html')

@app.route('/exam-detail')
def exam_detail():
    """考试详情页面"""
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        if session_id:
            session_data = get_user_session(session_id)
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
    
    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
    
    # 如果都没有找到有效的会话，重定向到登录页面
    if not user_account:
        return redirect(url_for('login'))
        
    return send_from_directory('static', 'OKComputer_企业化网页重设/exam_detail.html')


@app.route('/api/exam-detail/<exam_name>', methods=['GET'])
def get_exam_detail(exam_name):
    """获取考试详细信息 - 支持 Redis 会话"""
    print(f"DEBUG: /api/exam-detail/{exam_name} 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问考试详情API，用户: {user_account}")
    conn = None
    try:
        conn = connect_db()
        
        # 获取所有班级
        classes = read_class(conn, user_account)
        
        if not classes:
            return jsonify({
                'success': True,
                'examDetail': {
                    'name': exam_name,
                    'date': '2024-01-01',
                    'participants': 0,
                    'avgScore': 0,
                    'subjectMaxScores': {},
                    'allSubjects': []
                },
                'students': []
            })
        
        # 收集参加此考试的所有学生信息
        all_students = []
        total_score = 0
        score_count = 0
        participant_count = 0
        subject_max_scores = {}  # 存储各科目的满分
        all_subjects = set()  # 收集所有科目名称
        
        for class_name in classes:
            students = read_single_class(conn, user_account, class_name)
            
            if students:
                for student in students:
                    student_id = student["账号"]
                    try:
                        student_exams = read_student_exam(conn, student_id)
                        
                        # 检查学生是否参加了此次考试
                        if exam_name in student_exams:
                            exam_data = student_exams[exam_name]
                            
                            # 获取学生基本信息
                            student_info = read_student(conn, student_id)
                            student_name = student_info[0] if student_info else "未知学生"
                            
                            # 计算该学生的总分
                            student_total = sum([score[0] for score in exam_data.values()])
                            
                            # 统计总分和科目数
                            for subject, (score, max_score) in exam_data.items():
                                total_score += score
                                score_count += 1
                                all_subjects.add(subject)
                                
                                # 记录各科目的满分（取最大值）
                                if subject not in subject_max_scores or max_score > subject_max_scores[subject]:
                                    subject_max_scores[subject] = max_score
                            
                            # 添加学生信息到列表
                            student_detail = {
                                'name': student_name,
                                'account': student_id,
                                'className': class_name,
                                'scores': {subject: data[0] for subject, data in exam_data.items()},  # 只保留得分，不包含满分
                                'totalScore': student_total
                            }
                            all_students.append(student_detail)
                            participant_count += 1
                    except Exception as e:
                        print(f"读取学生 {student_id} 考试数据时出错: {str(e)}")
                        continue  # 继续处理下一个学生
        
        if score_count == 0:
            avg_score = 0
        else:
            avg_score = total_score / score_count
        
        # 构建考试详情
        exam_detail = {
            'name': exam_name,
            'date': '2024-01-01',  # 实际应用中应从数据库获取
            'participants': participant_count,
            'avgScore': avg_score,
            'subjectMaxScores': subject_max_scores,
            'allSubjects': list(all_subjects)
        }
        
        return jsonify({
            'success': True,
            'examDetail': exam_detail,
            'students': all_students
        })
        
    except Exception as e:
        print(f'获取考试详情时出现错误: {str(e)}')  # 添加错误日志
        import traceback
        traceback.print_exc()  # 打印详细错误堆栈
        return jsonify({
            'success': False,
            'message': f'获取考试详情时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/exam-details/<int:exam_id>')
def get_exam_details(exam_id):
    """获取考试详情 - 为兼容现有功能保留 - 支持 Redis 会话"""
    print(f"DEBUG: /api/exam-details/{exam_id} 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({'success': False, 'message': '用户未登录'}), 401
    
    print(f"DEBUG: 允许访问考试详情API (by ID)，用户: {user_account}")
    
    # 这里需要根据exam_id获取实际的考试名称
    # 由于目前的实现中没有直接的方法从ID获取考试名称，我们需要通过其他方式实现
    # 在实际应用中，您可能需要一个方法来根据ID获取考试名称
    # 为了兼容性，这里返回一个通用的错误信息
    return jsonify({
        'success': False,
        'message': '请使用考试名称而非ID来获取考试详情'
    })


@app.route('/reports')
def reports():
    """报表统计页面"""
    if 'user_account' not in session:
        return redirect(url_for('login'))
    return '<h1>报表统计</h1><p>这里是报表统计页面</p><a href="/dashboard">返回仪表板</a>'

# 考试管理相关API
@app.route('/api/exams', methods=['GET'])
def get_exams():
    """获取考试列表 - 支持 Redis 会话"""
    print(f"DEBUG: /api/exams 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问考试列表API，用户: {user_account}")
    conn = None
    try:
        conn = connect_db()
        
        # 获取所有班级
        classes = read_class(conn, user_account)
        
        if not classes:
            return jsonify({
                'success': True,
                'exams': []
            })
        
        # 收集所有考试数据
        all_exams = {}
        
        for class_name in classes:
            students = read_single_class(conn, user_account, class_name)
            
            if students:
                for student in students:
                    student_id = student["账号"]
                    student_exams = read_student_exam(conn, student_id)
                    
                    for exam_name, exam_data in student_exams.items():
                        if exam_name not in all_exams:
                            # 初始化考试信息
                            all_exams[exam_name] = {
                                'name': exam_name,
                                'subject': '',  # 我们可以尝试从科目名推断
                                'className': class_name,
                                'date': '2024-01-01',  # 默认日期，实际应用中应从数据库获取
                                'participants': 0,
                                'total_score': 0,
                                'score_count': 0,
                                'highest_score': float('-inf'),  # 最高分
                                'lowest_score': float('inf'),      # 最低分
                                'subjects': set()  # 记录该考试涉及的所有科目
                            }
                        
                        # 更新参与者数量和分数统计
                        all_exams[exam_name]['participants'] += 1
                        for subject, (score, total) in exam_data.items():
                            all_exams[exam_name]['total_score'] += score
                            all_exams[exam_name]['score_count'] += 1
                            all_exams[exam_name]['subjects'].add(subject)
                            
                            # 更新最高分和最低分
                            if score > all_exams[exam_name]['highest_score']:
                                all_exams[exam_name]['highest_score'] = score
                            if score < all_exams[exam_name]['lowest_score']:
                                all_exams[exam_name]['lowest_score'] = score
                            
                            # 使用第一个遇到的科目作为考试科目
                            if not all_exams[exam_name]['subject']:
                                all_exams[exam_name]['subject'] = subject
        
        # 格式化考试列表
        exam_list = []
        for exam_name, exam_data in all_exams.items():
            avg_score = exam_data['total_score'] / exam_data['score_count'] if exam_data['score_count'] > 0 else 0
            
            # 如果最高分还是初始值，说明没有有效分数
            highest_score = exam_data['highest_score'] if exam_data['highest_score'] != float('-inf') else 0
            lowest_score = exam_data['lowest_score'] if exam_data['lowest_score'] != float('inf') else 0
            
            # 确定考试状态 (可以根据日期或其他逻辑来判断)
            status = 'completed'  # 默认为已完成
            
            exam_info = {
                'id': len(exam_list) + 1,
                'name': exam_data['name'],
                'subject': exam_data['subject'],
                'className': exam_data['className'],
                'date': exam_data['date'],
                'status': status,
                'participants': exam_data['participants'],
                'avgScore': round(avg_score, 1),
                'highestScore': highest_score,
                'lowestScore': lowest_score
            }
            exam_list.append(exam_info)
        
        return jsonify({
            'success': True,
            'exams': exam_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取考试列表时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/exam-statistics', methods=['GET'])
def get_exam_statistics():
    """获取考试统计信息 - 支持 Redis 会话"""
    print(f"DEBUG: /api/exam-statistics 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问考试统计API，用户: {user_account}")
    conn = None
    try:
        conn = connect_db()
        
        # 获取所有班级
        classes = read_class(conn, user_account)
        
        if not classes:
            return jsonify({
                'success': True,
                'statistics': {
                    'examCount': 0,
                    'avgScore': 0,
                    'passRate': '0%',
                    'studentCount': 0
                }
            })
        
        # 统计数据
        exam_count = 0
        total_score = 0
        score_count = 0
        total_students = 0
        passed_students = 0  # 假设是基于学生平均分的及格率
        
        for class_name in classes:
            students = read_single_class(conn, user_account, class_name)
            total_students += len(students) if students else 0
            
            if students:
                for student in students:
                    student_id = student["账号"]
                    student_exams = read_student_exam(conn, student_id)
                    exam_count = max(exam_count, len(student_exams))
                    
                    # 计算学生平均分
                    student_total = 0
                    student_count = 0
                    for exam_data in student_exams.values():
                        for subject, (score, total) in exam_data.items():
                            total_score += score
                            score_count += 1
                            student_total += score
                            student_count += 1
                    
                    if student_count > 0:
                        student_avg = student_total / student_count
                        if student_avg >= 60:  # 假设60分为及格线
                            passed_students += 1
        
        avg_score = total_score / score_count if score_count > 0 else 0
        pass_rate = f'{(passed_students / total_students * 100):.1f}%' if total_students > 0 else '0%'
        
        return jsonify({
            'success': True,
            'statistics': {
                'examCount': exam_count,
                'avgScore': round(avg_score, 1),
                'passRate': pass_rate,
                'studentCount': total_students
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取考试统计时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/exam-groups', methods=['GET'])
def get_exam_groups():
    """获取考试分组信息 - 支持 Redis 会话"""
    print(f"DEBUG: /api/exam-groups 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")

    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问考试分组API，用户: {user_account}")
    conn = None
    try:
        conn = connect_db()
        
        # 获取教师的分组信息
        grouped_exams = read_teacher_group(conn, user_account)
        ungrouped_exams = not_group_exam(conn, user_account)
        
        # 构建分组列表，包括"未分组"选项
        groups = [{"name": "未分组", "exams": ungrouped_exams}]
        
        for group_name, exam_list in grouped_exams.items():
            groups.append({
                "name": group_name,
                "exams": exam_list
            })
        
        return jsonify({
            'success': True,
            'groups': groups
        })
        
    except Exception as e:
        print(f'获取考试分组时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取考试分组时出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/change-student-class', methods=['POST'])
def change_student_class():
    """更改学生班级"""
    if 'user_account' not in session:
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    user_account = session['user_account']
    conn = None
    try:
        conn = connect_db()
        data = request.get_json()
        student_account = data.get('student_account')
        new_class_name = data.get('new_class_name')
        
        if not student_account or not new_class_name:
            return jsonify({
                'success': False,
                'message': '学生账号和新班级名称不能为空'
            }), 400
        
        # 执行换班操作
        result = student_class_change(conn, user_account, student_account, new_class_name)
        
        if result:
            return jsonify({
                'success': True,
                'message': '换班成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '换班失败，可能是学生不存在或权限不足'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'换班过程中出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/update-student-score', methods=['POST'])
def update_student_score_api():
    """更新学生成绩"""
    if 'user_account' not in session:
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    user_account = session['user_account']
    conn = None
    try:
        conn = connect_db()
        data = request.get_json()
        student_account = data.get('student_account')
        exam_name = data.get('exam_name')
        subject = data.get('subject')
        new_score = data.get('new_score')
        
        if not student_account or not exam_name or not subject or new_score is None:
            return jsonify({
                'success': False,
                'message': '学生账号、考试名称、科目和分数不能为空'
            }), 400
        
        # 读取当前学生成绩数据
        current_score_dict = read_student_exam(conn, student_account)
        
        # 修改指定科目的成绩
        updated_score_dict = change_student_score(current_score_dict, exam_name, subject, new_score)
        
        # 更新数据库中的成绩
        success = update_student_score(conn, student_account, updated_score_dict)
        
        if success:
            return jsonify({
                'success': True,
                'message': '成绩修改成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '成绩修改失败'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'修改成绩过程中出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()




def connect_db(database='smsf'):
    """连接到指定数据库，默认连接smsf数据库"""
    config = MYSQL_CONFIG.copy()
    config['database'] = database
    try:
        conn = pymysql.connect(**config)
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        raise e

def read_student_score(conn, student_account):
    """读取指定学生的成绩"""
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT `exam_name`, `subject`, `score`
            FROM `scores`
            WHERE `account` = %s
        ''', (student_account,))
        result = cursor.fetchall()
        score_dict = {}
        for row in result:
            exam_name, subject, score = row
            if exam_name not in score_dict:
                score_dict[exam_name] = {}
            score_dict[exam_name][subject] = score
        return score_dict
    except Exception as e:
        print(f"读取成绩时发生错误: {e}")
        return {}

def change_student_score(current_score_dict, exam_name, subject, new_score):
    """修改指定考试和科目的成绩"""
    if exam_name not in current_score_dict:
        current_score_dict[exam_name] = {}
    current_score_dict[exam_name][subject] = new_score
    return current_score_dict

def update_student_score(conn, student_account, updated_score_dict):
    """更新数据库中的成绩"""
    try:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM `scores`
            WHERE `account` = %s
        ''', (student_account,))
        for exam_name, subjects in updated_score_dict.items():
            for subject, score in subjects.items():
                cursor.execute('''
                    INSERT INTO `scores` (`account`, `exam_name`, `subject`, `score`)
                    VALUES (%s, %s, %s, %s)
                ''', (student_account, exam_name, subject, score))
        conn.commit()
        return True
    except Exception as e:
        print(f"更新成绩时发生错误: {e}")
        return False

# 使用 ALL_function.py 中定义的 read_study_resources 和 read_all_subjects 函数
# 避免重复定义造成冲突

# 初始化免费账户表

if __name__ == '__main__':
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=True)


def hash_password(password):
    """对密码进行哈希处理"""
    salt = hashlib.sha256(os.urandom(16)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (pwdhash.decode('ascii'), salt.decode('ascii'))

def verify_password(password, stored_hash, salt):
    """验证密码"""
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt.encode('ascii'), 100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == stored_hash

from flask import Flask, request, jsonify, send_from_directory

@app.route('/api/scores', methods=['GET'])
def get_scores():
    """获取成绩数据"""
    student_account = request.args.get('account')
    conn = None
    try:
        # 连接到scores数据库
        conn = connect_db('scores')
        
        # 读取成绩
        score_dict = read_student_score(conn, student_account)
        
        return jsonify({
            'success': True,
            'scores': score_dict
        })
        
    except Exception as e:
        print(f'获取成绩时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取成绩失败: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/scores', methods=['POST'])
def update_scores():
    """更新成绩数据"""
    student_account = request.args.get('account')
    exam_name = request.form.get('exam_name')
    subject = request.form.get('subject')
    new_score = request.form.get('score')
    conn = None
    try:
        # 连接到scores数据库
        conn = connect_db('scores')
        
        # 读取当前成绩
        current_score_dict = read_student_score(conn, student_account)
        
        # 修改指定考试和科目的成绩
        updated_score_dict = change_student_score(current_score_dict, exam_name, subject, new_score)
        
        # 更新数据库
        result = update_student_score(conn, student_account, updated_score_dict)
        
        if result:
            return jsonify({
                'success': True,
                'message': '成绩更新成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '成绩更新失败'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'成绩更新过程中出现错误: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/test-route')
def test_route():
    """测试路由"""
    return "测试路由工作正常"

@app.route('/learning-resources')
def learning_resources():
    """学习资源页面"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/learning_resources.html')

@app.route('/student-learning')
def student_learning():
    """学生学习中心页面"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/student_learning.html')

@app.route('/video-frontend-demo')
def video_frontend_demo():
    """纯前端视频播放器演示页面"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/video_frontend_demo.html')

@app.route('/test-video-integration')
def test_video_integration():
    """视频播放功能集成测试页面"""
    return send_from_directory('.', 'test_video_integration.html')

@app.route('/api/study-resources', methods=['GET'])
def get_study_resources():
    """获取学习资源数据"""
    conn = None
    try:
        # 连接到study_resource数据库
        conn = connect_db('study_resource')
        
        # 读取学习资源
        resources = read_study_resources(conn)
        
        return jsonify({
            'success': True,
            'resources': resources
        })
        
    except Exception as e:
        print(f'获取学习资源时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取学习资源失败: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/student-info', methods=['GET'])
def get_student_info():
    """获取学生信息 - 从free_account表中读取"""
    print(f"DEBUG: /api/student-info 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 检查用户是否已登录（支持 Redis 和 Flask session）
    user_account = None
    
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
        if session_id:
            session_data = get_user_session(session_id)
            print(f"DEBUG: Redis 会话数据: {session_data}")
            if session_data:
                user_account = session_data['user_account']
                # 延长会话有效期
                extend_user_session(session_id, 24)
                print(f"DEBUG: Redis 验证通过，用户: {user_account}")
            else:
                print(f"DEBUG: Redis 会话不存在或已过期")
        else:
            print(f"DEBUG: 未找到 session_id Cookie")
    else:
        print(f"DEBUG: Redis 不可用或未启用")

    # 如果 Redis 不可用或没有找到会话，则检查 Flask session
    if not user_account and 'user_account' in session:
        user_account = session['user_account']
        print(f"DEBUG: 使用 Flask session，用户: {user_account}")
    else:
        print(f"DEBUG: Flask session 中未找到 user_account")
    
    # 如果都没有找到有效的会话，返回未授权
    if not user_account:
        print(f"DEBUG: 未找到有效会话，返回 401")
        return jsonify({
            'success': False,
            'message': '用户未登录'
        }), 401
    
    print(f"DEBUG: 允许访问学生信息API，用户: {user_account}")
    conn = None
    try:
        conn = connect_db('free_account')  # 连接到smsf数据库
        
        # 读取学生信息
        student_info = read_free_account_info(conn, user_account)
        
        if not student_info:
            return jsonify({
                'success': False,
                'message': '未找到学生信息'
            }), 404
        
        return jsonify({
            'success': True,
            'student': student_info
        })
        
    except Exception as e:
        print(f'获取学生信息时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取学生信息失败: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/subjects', methods=['GET'])
def get_all_subjects():
    """获取所有学科信息"""
    conn = None
    try:
        # 连接到study_resource数据库
        conn = connect_db('study_resource')
        
        # 读取所有学科
        subjects = read_all_subjects(conn)
        
        return jsonify({
            'success': True,
            'subjects': subjects
        })
        
    except Exception as e:
        print(f'获取学科信息时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取学科信息失败: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/english-articles', methods=['GET'])
def get_english_articles():
    """获取英语文章列表（支持分页和搜索）"""
    conn = None
    try:
        conn = connect_db("english_vocabulary")
        
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)  # 默认每页5个
        search_keyword = request.args.get('search', '').strip()  # 搜索关键词
        
        # 计算偏移量
        offset = (page - 1) * per_page
        
        # 获取英语文章数据（分页+搜索）
        result = read_english_articles(conn, limit=per_page, offset=offset, search_keyword=search_keyword)
        
        return jsonify({
            'success': True,
            'articles': result['articles'],
            'pagination': {
                'total': result['total'],
                'page': page,
                'per_page': per_page,
                'total_pages': (result['total'] + per_page - 1) // per_page,
                'has_more': result['has_more']
            }
        })
        
    except Exception as e:
        print(f'获取英语文章时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取英语文章失败: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/english-passage/<int:passage_id>', methods=['GET'])
def get_english_passage(passage_id):
    """获取单个英语文章详情"""
    conn = None
    try:
        conn = connect_db("english_vocabulary")
        
        # 先更新阅读次数
        from ALL_function import update_passage_reading_count
        update_success = update_passage_reading_count(conn, passage_id)
        if not update_success:
            print(f'警告: 更新文章 {passage_id} 的阅读次数失败')
        
        # 获取英语文章详情
        article = read_english_passage(conn, passage_id)
        
        if article:
            return jsonify({
                'success': True,
                'article': article
            })
        else:
            return jsonify({
                'success': False,
                'message': f'未找到ID为 {passage_id} 的文章'
            }), 404
            
    except Exception as e:
        print(f'获取英语文章详情时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取文章详情失败: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/vocabulary/<word>', methods=['GET'])
def get_vocabulary_definition(word):
    """获取单词的详细定义信息"""
    try:
        # 调用ALL_function中的read_vocabulary函数
        vocabulary_data = read_vocabulary(word)
        
        if vocabulary_data and len(vocabulary_data) > 0:
            # 获取第一个匹配的结果
            raw_data = vocabulary_data[0]
            
            # 转换为前端期望的格式
            formatted_word = {
                'word': raw_data.get('word', word),
                'translation': raw_data.get('translation', ''),
                'tag': raw_data.get('tag', ''),
                'exchange': raw_data.get('exchange', ''),
                'frq': raw_data.get('frq', ''),
                'id': raw_data.get('id', 0),
                'phonetic': raw_data.get('phonetic', ''),
                # 兼容旧字段名
                'pho_symbol': raw_data.get('phonetic', ''),
                'Chinese Definition': raw_data.get('translation', '')
            }
            
            # 处理标签显示
            if formatted_word['tag']:
                # 将标签转换为可读格式
                tag_mapping = {
                    'zk': '中考',
                    'gk': '高考',
                    'cet4': '四级',
                    'cet6': '六级',
                    'toefl': '托福',
                    'ielts': '雅思',
                    'ky':'考研',
                    'gre': 'GRE'
                }
                tags = formatted_word['tag'].split()
                readable_tags = [tag_mapping.get(tag, tag) for tag in tags]
                formatted_word['levels'] = ', '.join(readable_tags)
            else:
                formatted_word['levels'] = ''
            
            return jsonify({
                'success': True,
                'word': formatted_word
            })
        else:
            return jsonify({
                'success': False,
                'message': f'未找到单词 "{word}" 的定义'
            }), 404
            
    except Exception as e:
        print(f'获取单词定义时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取单词定义失败: {str(e)}'
        }), 500

# ==================== 单词训练相关API接口 ====================

@app.route('/api/vocabulary/get-mode-status', methods=['GET'])
def get_mode_status():
    """获取用户的生词模式状态"""
    try:
        # 检查用户登录状态
        user_account = get_current_user_account()
        if not user_account:
            return jsonify({
                'success': False,
                'message': '用户未登录'
            }), 401
        
        # 获取用户的生词本数据
        conn = connect_db('free_account')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT uf_word_book FROM vo_book WHERE account = %s
        ''', (user_account,))
        
        result = cursor.fetchone()
        
        if not result or not result[0]:
            conn.close()
            return jsonify({
                'success': True,
                'mode_status': {}
            })
        
        # 解析生词本JSON数据
        try:
            import json
            word_book_data = json.loads(result[0])
            mode_status = word_book_data  # 包含每个单词的学习模式状态
        except:
            mode_status = {}
        
        conn.close()
        
        return jsonify({
            'success': True,
            'mode_status': mode_status
        })
        
    except Exception as e:
        print(f'获取模式状态时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取模式状态失败: {str(e)}'
        }), 500

@app.route('/api/vocabulary/new-words', methods=['GET'])
def get_new_words():
    """获取用户的生词列表（支持学习模式）"""
    try:
        # 检查用户登录状态
        user_account = get_current_user_account()
        if not user_account:
            return jsonify({
                'success': False,
                'message': '用户未登录'
            }), 401
        
        # 获取用户的生词本数据
        conn = connect_db('free_account')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT uf_word_book FROM vo_book WHERE account = %s
        ''', (user_account,))
        
        result = cursor.fetchone()
        
        if not result or not result[0]:
            conn.close()
            return jsonify({
                'success': True,
                'words': [],
                'mode_status': {}
            })
        
        # 解析生词本JSON数据
        try:
            import json
            word_book_data = json.loads(result[0])
            # 获取所有单词ID及其学习模式状态
            word_ids = list(word_book_data.keys())[:15]  # 限制返回15个单词用于三轮学习
            mode_status = word_book_data  # 包含每个单词的学习模式状态
        except:
            word_ids = []
            mode_status = {}
        
        if not word_ids:
            conn.close()
            return jsonify({
                'success': True,
                'words': [],
                'mode_status': {}
            })
        
        # 获取单词详细信息
        vocab_conn = connect_db('english_vocabulary')
        vocab_cursor = vocab_conn.cursor(pymysql.cursors.DictCursor)
        
        # 构建IN查询
        placeholders = ','.join(['%s'] * len(word_ids))
        vocab_cursor.execute(f'''
            SELECT id, word, translation, phonetic, tag 
            FROM new_word 
            WHERE id IN ({placeholders})
            ORDER BY FIELD(id, {placeholders})
        ''', word_ids + word_ids)
        
        words_data = vocab_cursor.fetchall()
        
        # 格式化返回数据
        formatted_words = []
        for word_data in words_data:
            formatted_word = {
                'id': word_data['id'],
                'word': word_data['word'],
                'translation': word_data['translation'] or '暂无释义',
                'phonetic': word_data['phonetic'] or '',
                'tag': word_data['tag'] or ''
            }
            formatted_words.append(formatted_word)
        
        conn.close()
        vocab_conn.close()
        
        return jsonify({
            'success': True,
            'words': formatted_words,
            'mode_status': mode_status
        })
        
    except Exception as e:
        print(f'获取生词列表时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取生词列表失败: {str(e)}'
        }), 500

@app.route('/api/vocabulary/word-books', methods=['GET'])
def get_word_books():
    """获取词书列表和单词"""
    try:
        # 获取词书分类
        conn = connect_db('english_vocabulary')
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 获取不同等级的单词（模拟词书分类）
        cursor.execute('''
            SELECT DISTINCT level_id FROM word_level_ref 
            ORDER BY level_id
        ''')
        
        levels = cursor.fetchall()
        
        # 获取每个等级的部分单词作为示例
        word_books = []
        for level in levels[:4]:  # 限制4个等级
            level_id = level['level_id']
            
            cursor.execute('''
                SELECT w.id, w.word, w.translation, w.phonetic, w.tag
                FROM words w
                JOIN word_level_ref wlr ON w.id = wlr.word_id
                WHERE wlr.level_id = %s
                ORDER BY RAND()
                LIMIT 15
            ''', (level_id,))
            
            words = cursor.fetchall()
            
            # 格式化单词数据
            formatted_words = []
            for word in words:
                formatted_word = {
                    'id': word['id'],
                    'word': word['word'],
                    'translation': word['translation'] or '暂无释义',
                    'phonetic': word['phonetic'] or '',
                    'tag': word['tag'] or ''
                }
                formatted_words.append(formatted_word)
            
            level_names = {
                1: '初级词汇',
                2: '中级词汇',
                3: '高级词汇',
                4: '托福雅思'
            }
            
            word_books.append({
                'id': level_id,
                'name': level_names.get(level_id, f'词汇等级{level_id}'),
                'word_count': len(formatted_words),
                'words': formatted_words
            })
        
        conn.close()
        
        # 返回第一个词书的单词作为默认数据
        if word_books:
            return jsonify({
                'success': True,
                'words': word_books[0]['words'],
                'books': word_books
            })
        else:
            return jsonify({
                'success': True,
                'words': [],
                'books': []
            })
            
    except Exception as e:
        print(f'获取词书数据时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取词书数据失败: {str(e)}'
        }), 500

@app.route('/api/vocabulary/spelling-challenges', methods=['GET'])
def get_spelling_challenges():
    """获取拼写挑战单词"""
    try:
        conn = connect_db('english_vocabulary')
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 随机获取24个单词用于拼写挑战
        cursor.execute('''
            SELECT id, word, translation, phonetic, tag
            FROM words
            WHERE LENGTH(word) BETWEEN 4 AND 12
            ORDER BY RAND()
            LIMIT 24
        ''')
        
        words = cursor.fetchall()
        
        # 格式化数据
        formatted_words = []
        for word in words:
            formatted_word = {
                'id': word['id'],
                'word': word['word'],
                'translation': word['translation'] or '根据释义拼写单词',
                'phonetic': word['phonetic'] or '',
                'tag': word['tag'] or ''
            }
            formatted_words.append(formatted_word)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'words': formatted_words
        })
        
    except Exception as e:
        print(f'获取拼写挑战单词时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取拼写挑战单词失败: {str(e)}'
        }), 500

@app.route('/api/read_some_word_form_certain_level', methods=['GET'])
def get_some_word_form_certain_level():
    """获取指定等级的单词"""
    try:
        formatted_words = read_some_word_form_certain_level()
        return jsonify({
            'success': True,
            'words': formatted_words
        })
    except Exception as e:
        print(f'获取指定等级单词时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取指定等级单词失败: {str(e)}'
        }), 500



@app.route('/spelling_training')
def spelling_training_page():
    """拼写训练页面路由"""
    return send_from_directory('static/OKComputer_企业化网页重设', 'spelling_training.html')

# 保留原始 get_spelling_challenges 函数（第3382行）
# 已删除重复定义以避免路由冲突

@app.route('/api/vocabulary/pk-words', methods=['GET'])
def get_pk_words():
    """获取PK对战单词"""
    try:
        conn = connect_db('english_vocabulary')
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 获取适合PK的单词（常见但有一定难度）
        cursor.execute('''
            SELECT id, word, translation, phonetic, tag
            FROM words
            WHERE LENGTH(word) BETWEEN 5 AND 10
            AND frq > 1000
            ORDER BY RAND()
            LIMIT 20
        ''')
        
        words = cursor.fetchall()
        
        # 格式化数据
        formatted_words = []
        for word in words:
            formatted_word = {
                'id': word['id'],
                'word': word['word'],
                'translation': word['translation'] or '快速拼写这个单词',
                'phonetic': word['phonetic'] or '',
                'tag': word['tag'] or ''
            }
            formatted_words.append(formatted_word)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'words': formatted_words
        })
        
    except Exception as e:
        print(f'获取PK单词时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取PK单词失败: {str(e)}'
        }), 500

@app.route('/api/vocabulary/add-to-book', methods=['POST'])
def add_word_to_book():
    """将单词添加到生词本"""
    try:
        data = request.get_json()
        word_id = data.get('word_id')
        user_account = data.get('account') or get_current_user_account()
        
        if not word_id or not user_account:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        # 调用ALL_function中的保存函数
        from ALL_function import save_new_word_ids_to_vo_book
        result = save_new_word_ids_to_vo_book(user_account, [word_id])
        
        if result:
            return jsonify({
                'success': True,
                'message': '单词已添加到生词本'
            })
        else:
            return jsonify({
                'success': False,
                'message': '添加单词失败'
            }), 500
            
    except Exception as e:
        print(f'添加单词到生词本时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'添加单词失败: {str(e)}'
        }), 500

@app.route('/api/vocabulary/batch-update-mode-status', methods=['POST'])
def batch_update_mode_status():
    """批量更新生词本中多个单词的学习模式状态"""
    try:
        user_account = get_current_user_account()
        if not user_account:
            return jsonify({
                'success': False,
                'message': '用户未登录'
            }), 401
        
        data = request.get_json()
        updates = data.get('updates', [])
        
        if not updates:
            return jsonify({
                'success': False,
                'message': '缺少更新数据'
            }), 400
        
        conn = connect_db('free_account')
        cursor = conn.cursor()
        
        # 获取当前生词本数据
        cursor.execute('''
            SELECT uf_word_book FROM vo_book WHERE account = %s
        ''', (user_account,))
        
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return jsonify({
                'success': False,
                'message': '生词本不存在'
            }), 404
        
        try:
            import json
            word_book_data = json.loads(result[0])
            
            # 批量更新模式状态
            updated_count = 0
            for update_item in updates:
                word_id = str(update_item.get('wordId'))
                new_mode = update_item.get('newMode')
                
                if word_id in word_book_data and new_mode is not None:
                    word_book_data[word_id] = new_mode
                    # 确保模式不超过3
                    if word_book_data[word_id] > 3:
                        word_book_data[word_id] = 3
                    updated_count += 1
                
            updated_word_book = json.dumps(word_book_data, ensure_ascii=False)
            
            # 更新数据库
            cursor.execute('''
                UPDATE vo_book SET uf_word_book = %s WHERE account = %s
            ''', (updated_word_book, user_account))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'成功更新 {updated_count} 个单词的模式状态',
                'updated_count': updated_count
            })
            
        except json.JSONDecodeError:
            conn.close()
            return jsonify({
                'success': False,
                'message': '生词本数据格式错误'
            }), 500
        
    except Exception as e:
        print(f'批量更新模式状态时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500

@app.route('/api/vocabulary/update-mode-status', methods=['POST'])
def update_mode_status():
    """更新生词本中单词的学习模式状态"""
    try:
        user_account = get_current_user_account()
        if not user_account:
            return jsonify({
                'success': False,
                'message': '用户未登录'
            }), 401
        
        data = request.get_json()
        word_id = data.get('word_id')
        mode = data.get('mode')
        is_correct = data.get('is_correct', True)
        
        if not word_id or mode is None:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        conn = connect_db('free_account')
        cursor = conn.cursor()
        
        # 获取当前生词本数据
        cursor.execute('''
            SELECT uf_word_book FROM vo_book WHERE account = %s
        ''', (user_account,))
        
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return jsonify({
                'success': False,
                'message': '生词本不存在'
            }), 404
        
        try:
            import json
            word_book_data = json.loads(result[0])
            word_id_str = str(word_id)
            
            if word_id_str not in word_book_data:
                return jsonify({
                    'success': False,
                    'message': '单词不在生词本中'
                }), 404
            
            # 更新模式状态
            if is_correct:
                # 回答正确，升级到下一模式
                word_book_data[word_id_str] = mode + 1
                # 如果达到模式3，表示完全掌握
                if word_book_data[word_id_str] >= 3:
                    word_book_data[word_id_str] = 3  # 标记为完全掌握
            else:
                # 回答错误，保持当前模式或降级
                if word_book_data[word_id_str] > 0:
                    word_book_data[word_id_str] = mode  # 保持在当前模式
                
            updated_word_book = json.dumps(word_book_data, ensure_ascii=False)
            
            # 更新数据库
            cursor.execute('''
                UPDATE vo_book SET uf_word_book = %s WHERE account = %s
            ''', (updated_word_book, user_account))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': '模式状态更新成功',
                'new_mode': word_book_data[word_id_str]
            })
            
        except json.JSONDecodeError:
            conn.close()
            return jsonify({
                'success': False,
                'message': '生词本数据格式错误'
            }), 500
        
    except Exception as e:
        print(f'更新模式状态时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500

@app.route('/api/vocabulary/search', methods=['GET'])
def search_vocabulary():
    """搜索单词"""
    try:
        keyword = request.args.get('keyword', '').strip()
        if not keyword:
            return jsonify({
                'success': False,
                'message': '请输入搜索关键词'
            }), 400
        
        conn = connect_db('english_vocabulary')
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 模糊搜索单词
        cursor.execute('''
            SELECT id, word, translation, phonetic, tag
            FROM words
            WHERE word LIKE %s OR translation LIKE %s
            ORDER BY word
            LIMIT 20
        ''', (f'%{keyword}%', f'%{keyword}%'))
        
        words = cursor.fetchall()
        
        # 格式化数据
        formatted_words = []
        for word in words:
            formatted_word = {
                'id': word['id'],
                'word': word['word'],
                'translation': word['translation'] or '暂无释义',
                'phonetic': word['phonetic'] or '',
                'tag': word['tag'] or ''
            }
            formatted_words.append(formatted_word)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'words': formatted_words,
            'count': len(formatted_words)
        })
        
    except Exception as e:
        print(f'搜索单词时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'搜索失败: {str(e)}'
        }), 500

# ==================== 辅助函数 ====================

def get_current_user_account():
    """获取当前登录用户的账户名"""
    # 首先检查 Redis 会话
    if REDIS_ENABLED and redis_session_manager.is_connected():
        session_id = request.cookies.get('session_id')
        if session_id:
            session_data = get_user_session(session_id)
            if session_data:
                return session_data['user_account']
    
    # 检查 Flask session
    if 'user_account' in session:
        return session['user_account']
    
    return None

@app.route('/api/english-passage/<int:passage_id>/paragraph-translation', methods=['POST'])
def get_paragraph_translation(passage_id):
    """获取指定段落的翻译"""
    conn = None
    try:
        conn = connect_db("english_vocabulary")
        
        # 获取请求数据
        data = request.get_json()
        paragraph_index = data.get('paragraph_index')
        selected_text = data.get('selected_text', '').strip()
        
        if paragraph_index is None:
            return jsonify({
                'success': False,
                'message': '缺少段落索引参数'
            }), 400
        
        # 获取文章详情
        article = read_english_passage(conn, passage_id)
        
        if not article:
            return jsonify({
                'success': False,
                'message': f'未找到ID为 {passage_id} 的文章'
            }), 404
        
        # 获取段落翻译数据
        paragraph_translations = article.get('paragraph_translations', [])
        
        # 查找匹配的段落翻译
        translation_result = None
        for paragraph_data in paragraph_translations:
            if paragraph_data['index'] == paragraph_index:
                translation_result = {
                    'original': paragraph_data['original'],
                    'translation': paragraph_data['translation'],
                    'index': paragraph_index
                }
                break
            
            # 如果提供了选中文本，也可以模糊匹配
            if selected_text and selected_text in paragraph_data['original']:
                translation_result = {
                    'original': paragraph_data['original'],
                    'translation': paragraph_data['translation'],
                    'index': paragraph_data['index']
                }
                break
        
        if translation_result:
            return jsonify({
                'success': True,
                'translation': translation_result
            })
        else:
            return jsonify({
                'success': False,
                'message': f'未找到第 {paragraph_index} 段的翻译'
            }), 404
            
    except Exception as e:
        print(f'获取段落翻译时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取段落翻译失败: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/downloads')
def downloads():
    """下载页面"""
    return send_from_directory('static', 'OKComputer_企业化网页重设/downloads.html')

@app.route('/api/versions', methods=['GET'])
def get_versions():
    """获取可用版本信息"""
    conn = None
    try:
        # 尝试连接到version_base数据库
        version_db_config = MYSQL_CONFIG.copy()
        version_db_config['database'] = 'version_base'
        
        try:
            conn = pymysql.connect(**version_db_config)
            cursor = conn.cursor()
            
            # 查询vers表中的版本信息（适应实际表结构）
            cursor.execute('''
                SELECT version,path
                FROM vers 
            ''')
            
            versions = cursor.fetchall()
            version_list = []
            
            for i, version in enumerate(versions):
                version_list.append({
                    'id': i + 1,  # 使用索引作为ID
                    'version': version[0],
                    'platform': 'Windows',  # 默认平台
                    'file_path': version[1],
                    'file_size': '未知大小',
                    'description': 'Windows安装包',
                    'release_date': '2026-01-01'
                })
            
            conn.close()
            
            return jsonify({
                'success': True,
                'versions': version_list
            })
            
        except Exception as e:
            print(f"连接version_base数据库失败: {e}")
            # 如果无法连接到version_base数据库，返回默认版本信息
            default_versions = [
                {
                    'id': 1,
                    'version': '1.0.0',
                    'platform': 'Windows',
                    'file_path': '/static/downloads/smsf_installer_v1.0.0.exe',
                    'file_size': '50MB',
                    'description': '适用于Windows 10/11操作系统的完整安装包',
                    'release_date': '2026-01-01'
                }
            ]
            
            return jsonify({
                'success': True,
                'versions': default_versions,
                'message': '使用默认版本信息'
            })
            
    except Exception as e:
        print(f'获取版本信息时出现错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'获取版本信息失败: {str(e)}'
        }), 500


@app.route('/api/download/<int:version_id>')
def download_file(version_id):
    """下载指定版本的文件 - 流式传输优化"""
    conn = None
    try:
        print(f"开始处理版本 {version_id} 的下载请求")

        # 连接到version_base数据库获取文件路径
        version_db_config = MYSQL_CONFIG.copy()
        version_db_config['database'] = 'version_base'

        try:
            print("尝试连接数据库...")
            conn = pymysql.connect(**version_db_config)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT version, path
                FROM vers 
                LIMIT 1 OFFSET %s
            ''', (version_id - 1,))

            result = cursor.fetchone()

            # 及时关闭数据库连接
            if conn and conn.open:
                conn.close()
                conn = None


            if not result:
                return jsonify({
                    'success': False,
                    'message': f'版本ID {version_id} 不存在'
                }), 404

            version = result[0]
            file_path = result[1]

            print(f"找到版本: {version}, 文件路径: {file_path}")

            # 验证文件路径
            if not file_path or not isinstance(file_path, str):
                return jsonify({
                    'success': False,
                    'message': '文件路径无效'
                }), 400

            # 规范化路径
            file_path = os.path.normpath(file_path)

            # 检查文件是否存在
            if not os.path.exists(file_path):
                # 尝试相对路径
                relative_path = os.path.join(os.getcwd(), file_path)
                if os.path.exists(relative_path):
                    file_path = relative_path
                else:
                    return jsonify({
                        'success': False,
                        'message': f'文件不存在: {file_path}'
                    }), 404

            # 检查文件是否可读
            if not os.access(file_path, os.R_OK):
                return jsonify({
                    'success': False,
                    'message': '文件无读取权限'
                }), 403

            # 获取文件信息
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)

            print(f"文件大小: {file_size} bytes, 文件名: {file_name}")

            # 启用流式传输
            print(f"开始流式传输文件: {file_path}")

            def generate_file_chunks():
                """生成文件块的生成器函数"""
                chunk_size = 8192  # 8KB chunks
                try:
                    with open(file_path, 'rb') as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk
                except Exception as e:
                    print(f"文件读取错误: {str(e)}")
                    # 这里不能抛出异常，因为生成器已经在响应中使用
                    # 可以记录日志或采取其他措施

            # 创建流式响应
            from flask import Response
            response = Response(
                generate_file_chunks(),
                mimetype='application/octet-stream',
                headers={
                    'Content-Disposition': f'attachment; filename="smsf_{version}_{file_name}"',
                    'Content-Length': str(file_size),
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0',
                    'Accept-Ranges': 'bytes',  # 支持断点续传
                    'Connection': 'keep-alive'
                }
            )

            print("流式传输响应已构建")
            return response

        except pymysql.Error as db_error:
            # 确保连接被关闭
            if conn and conn.open:
                conn.close()
                conn = None

            # 尝试默认文件 - 也使用流式传输
            default_path = 'static/downloads/smsf_installer_v1.0.0.exe'
            if os.path.exists(default_path):
                file_size = os.path.getsize(default_path)

                def generate_default_chunks():
                    chunk_size = 8192
                    try:
                        with open(default_path, 'rb') as f:
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk:
                                    break
                                yield chunk
                    except Exception as e:
                        print(f"默认文件读取错误: {str(e)}")

                return Response(
                    generate_default_chunks(),
                    mimetype='application/octet-stream',
                    headers={
                        'Content-Disposition': 'attachment; filename="smsf_installer_v1.0.0.exe"',
                        'Content-Length': str(file_size),
                        'Cache-Control': 'no-cache, no-store, must-revalidate'
                    }
                )

            return jsonify({
                'success': False,
                'message': f'数据库连接失败: {str(db_error)}'
            }), 500

        except Exception as e:
            # 确保连接被关闭
            if conn and conn.open:
                conn.close()
                conn = None

            print(f"处理下载请求时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'处理下载请求时发生错误: {str(e)}'
            }), 500

    except Exception as e:
        # 确保连接被关闭
        if conn and conn.open:
            conn.close()
            conn = None

        print(f'下载过程中出现严重错误: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'下载失败: {str(e)}'
        }), 500
    finally:
        # 安全关闭连接
        if conn and conn.open:
            try:
                conn.close()
            except:
                pass


@app.route('/logout')
def logout():
    """退出登录"""
    session.pop('user_account', None)  # 清除session
    return redirect(url_for('index'))

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """处理用户退出登录请求 - 清理 Redis 会话和 Cookie"""
    print(f"DEBUG: /api/logout 被调用")
    print(f"DEBUG: 请求 Headers: {dict(request.headers)}")
    print(f"DEBUG: 请求 Cookies: {request.cookies}")
    
    # 获取 session_id
    session_id = request.cookies.get('session_id')
    user_account = None
    print(f"DEBUG: 从 Cookie 获取 session_id: {session_id}")
    
    # 先从Redis获取用户信息用于日志记录
    if session_id and REDIS_ENABLED and redis_session_manager.is_connected():
        try:
            session_data = get_user_session(session_id)
            if session_data:
                user_account = session_data.get('user_account')
                print(f"DEBUG: 获取到用户信息: {user_account}")
        except Exception as e:
            print(f"DEBUG: 获取用户信息时出错: {e}")
    
    # 清理 Redis 会话
    if session_id and REDIS_ENABLED and redis_session_manager.is_connected():
        try:
            # 从 Redis 删除会话
            if delete_user_session(session_id):
                print(f"✅ Redis 会话 {session_id} 已删除")
            else:
                print(f"⚠️  Redis 会话 {session_id} 删除失败或不存在")
        except Exception as e:
            print(f"❌ 删除 Redis 会话时出错: {e}")
    
    # 清理 Flask session
    session.clear()
    print(f"✅ Flask session 已清空")
    
    # 创建响应并清除 Cookie
    response = jsonify({
        'success': True,
        'message': '已成功退出登录'
    })
    
    # 更彻底地清除 session_id Cookie
    response.set_cookie(
        'session_id',
        '',
        max_age=0,
        expires=0,  # 立即过期
        httponly=True,
        secure=False,
        samesite='Lax',
        path='/'
    )
    
    # 添加额外的安全头部
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    print(f"✅ session_id Cookie 已清除")
    if user_account:
        print(f"✅ 用户 {user_account} 已成功退出登录")
    print(f"DEBUG: 退出登录处理完成")
    
    return response

def generate_mock_leaderboard(leaderboard_type, time_range):
    """生成模拟排行榜数据"""
    # 模拟学生数据
    mock_students = [
        {'name': '张三', 'class_name': '高三(1)班'},
        {'name': '李四', 'class_name': '高三(2)班'},
        {'name': '王五', 'class_name': '高三(1)班'},
        {'name': '赵六', 'class_name': '高三(3)班'},
        {'name': '钱七', 'class_name': '高三(2)班'},
        {'name': '孙八', 'class_name': '高三(1)班'},
        {'name': '周九', 'class_name': '高三(3)班'},
        {'name': '吴十', 'class_name': '高三(2)班'},
        {'name': '郑十一', 'class_name': '高三(1)班'},
        {'name': '王十二', 'class_name': '高三(3)班'}
    ]
    
    # 生成随机成绩数据
    leaderboard_data = []
    
    for i, student in enumerate(mock_students):
        # 生成各科成绩
        subject_scores = {
            'chinese': random.randint(80, 150),
            'math': random.randint(80, 150),
            'english': random.randint(80, 150),
            'physics': random.randint(60, 100),
            'chemistry': random.randint(60, 100),
            'biology': random.randint(60, 100)
        }
        
        # 根据排行榜类型计算总分
        if leaderboard_type == 'overall':
            total_score = sum(subject_scores.values())
        elif leaderboard_type in subject_scores:
            total_score = subject_scores[leaderboard_type]
        else:
            total_score = sum(subject_scores.values())
        
        # 模拟排名趋势
        trends = ['up', 'down', 'same']
        trend = random.choice(trends)
        
        leaderboard_data.append({
            'name': student['name'],
            'class_name': student['class_name'],
            'total_score': total_score,
            'subject_scores': subject_scores,
            'trend': trend
        })
    
    # 按总分排序
    leaderboard_data.sort(key=lambda x: x['total_score'], reverse=True)
    
    return leaderboard_data


if __name__ == '__main__':
    # 检查运行环境
    if is_development_mode():
        # 开发环境使用Flask内置服务器
        print("⚠️  警告: 当前使用开发服务器，不适用于生产环境")
        print("💡 建议使用生产服务器: python production_server.py")
        
        # 检查并创建静态文件目录
        static_dir = 'static'
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
        
        # 如果html目录不在static下，则创建符号链接或复制文件
        import shutil
        import errno
        
        html_src = os.path.join(os.getcwd(), 'html')
        html_dst = os.path.join(static_dir, 'html')
        
        if os.path.exists(html_src) and not os.path.exists(html_dst):
            try:
                shutil.copytree(html_src, html_dst)
            except FileExistsError:
                pass  # 如果目标目录已存在，则忽略
            except OSError as e:
                if e.errno == errno.EXDEV:  # Cross-device link 错误
                    # 尝试使用复制而非硬链接
                    import distutils.dir_util
                    distutils.dir_util.copy_tree(html_src, html_dst)
                else:
                    print(f"复制HTML文件时出错: {e}")
        
        print("服务器启动中...")
        print("访问 http://localhost:5000 开始使用系统")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        # 生产环境提示
        print("❌ 错误: 请使用生产服务器启动")
        print("💡 运行命令:")
        print("   Windows: start_production.bat")
        print("   Linux/macOS: ./start_production.sh")
        print("   或直接运行: python production_server.py")
        sys.exit(1)