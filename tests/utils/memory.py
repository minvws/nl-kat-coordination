import os
import time

import psutil


def get_process_memory():
    """Returns the memory usage of the current process in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def profile_memory(func, *args, **kwargs):
    """Profiles the given function and returns the memory usage in MB."""

    def wrapper(*args, **kwargs):
        memory_before = get_process_memory()
        start_time = time.time()

        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time

        memory_after = get_process_memory()

        print(
            f"{func.__name__}: memory before: {memory_before:.2f} MB, after: {memory_after:.2f} MB, consumed: {memory_after - memory_before:.2f} MB; exec time: {elapsed_time}"
        )

        return result

    return wrapper
