#!/bin/bash

# 创建必要的目录
mkdir -p logs
mkdir -p uploads
mkdir -p static

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export FLASK_ENV=production
export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')

# 启动Gunicorn
gunicorn -c gunicorn.conf.py web_excel_merger:app 