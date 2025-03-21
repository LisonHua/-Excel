import multiprocessing

# 工作进程数
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = 'sync'

# 绑定的地址和端口
bind = '127.0.0.1:8000'

# 超时时间
timeout = 120

# 日志配置
accesslog = 'logs/access.log'
errorlog = 'logs/error.log'
loglevel = 'info'

# 进程名称
proc_name = 'excel_merger'

# 守护进程模式
daemon = False

# 优雅重启
graceful_timeout = 30 