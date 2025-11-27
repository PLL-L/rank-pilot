# gunicorn_config.py
import multiprocessing

bind = "0.0.0.0:8085"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
max_requests = 1000
max_requests_jitter = 100
timeout = 30
preload_app = True

