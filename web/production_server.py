#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMSF 生产环境服务器启动脚本
支持Windows和Linux平台的生产级部署
"""

import os
import sys
import platform
from web_server import app

def start_production_server():
    """启动生产环境服务器"""
    
    # 获取系统平台
    system = platform.system().lower()
    
    # 服务器配置
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 80))
    WORKERS = int(os.getenv('WORKERS', 4))  # 工作进程数
    
    print("=" * 50)
    print("SMSF 智慧教育系统 - 生产环境服务器")
    print("=" * 50)
    print(f"系统平台: {system}")
    print(f"监听地址: {HOST}:{PORT}")
    print(f"工作进程: {WORKERS}")
    print(f"启动时间: {platform.node()}")
    print("=" * 50)
    
    if system == 'windows':
        # Windows平台使用Waitress
        try:
            from waitress import serve
            print("使用 Waitress 服务器启动...")
            serve(app, host=HOST, port=PORT, threads=WORKERS*4)
        except ImportError:
            print("错误: 请先安装 waitress")
            print("运行命令: pip install waitress")
            sys.exit(1)
    else:
        # Linux/macOS平台使用Gunicorn
        try:
            import gunicorn.app.base
            
            class StandaloneApplication(gunicorn.app.base.BaseApplication):
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()

                def load_config(self):
                    config = {key: value for key, value in self.options.items()
                              if key in self.cfg.settings and value is not None}
                    for key, value in config.items():
                        self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application

            # Gunicorn配置
            options = {
                'bind': f'{HOST}:{PORT}',
                'workers': WORKERS,
                'worker_class': 'sync',
                'timeout': 30,
                'keepalive': 2,
                'max_requests': 1000,
                'max_requests_jitter': 100,
                'preload_app': True,
                'worker_tmp_dir': '/dev/shm' if system == 'linux' else None,
            }
            
            print("使用 Gunicorn 服务器启动...")
            StandaloneApplication(app, options).run()
            
        except ImportError:
            print("错误: 请先安装 gunicorn")
            print("运行命令: pip install gunicorn")
            sys.exit(1)

if __name__ == '__main__':
    start_production_server()