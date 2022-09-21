import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
bind = ["127.0.0.1:8001"]
