import argparse
import logging
import time

import psutil
import requests

SCHEDULER_API = "http://localhost:8004"


def are_tasks_done():
    resp_tasks_stats = requests.get(
        url=f"{SCHEDULER_API}/tasks/stats",
    )

    try:
        resp_tasks_stats.raise_for_status()
    except requests.exceptions.HTTPError:
        print("Error getting tasks")
        raise

    tasks_stats = resp_tasks_stats.json()
    if not tasks_stats:
        print("No tasks found")
        return False

    return all(tasks_stats[hour].get("queued") <= 0 for hour in tasks_stats)


def parse_stats():
    resp_tasks_stats = requests.get(
        url=f"{SCHEDULER_API}/tasks/stats",
    )

    try:
        resp_tasks_stats.raise_for_status()
    except requests.exceptions.HTTPError:
        print("Error getting tasks")
        raise

    tasks_stats = resp_tasks_stats.json()
    for hour in tasks_stats:
        print(hour)


def parse_logs():
    pass


def collect_cpu(pid: int):
    process = psutil.Process(pid)
    return process.cpu_percent()

def collect_memory(pid: int):
    process = psutil.Process(pid)
    return process.memory_info().rss / 1024 / 1024


def run(pid: int):
    while not are_tasks_done():
        print("Tasks are not done yet")

        memory = collect_memory(pid)
        print(f"Memory usage: {memory:.2f} MB")

        cpu = collect_cpu(pid)
        print(f"CPU usage: {cpu:.2f} %")

        time.sleep(10)
        continue

    print("Tasks are done")

    parse_logs()

    parse_stats()


if __name__ == "__main__":
    # Setup command line interface
    parser = argparse.ArgumentParser(description="Check")

    # Add arguments
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Set to enable verbose logging.")

    parser.add_argument(
        "--pid",
        "-p",
        type=int,
        required=True,
        help="The pid of the process to monitor.",
    )

    # Parse arguments
    args = parser.parse_args()

    # Configure logging level, if the -v (verbose) flag was given this will
    # set the log-level to DEBUG (printing all debug messages and higher),
    # if -v was not given it defaults to printing level warning and higher.
    default_loglevel = logging.INFO
    if args.verbose:
        default_loglevel = logging.DEBUG

    logging.basicConfig(
        level=default_loglevel,
        format="%(asctime)s %(name)-52s %(levelname)-8s %(message)s",
    )

    run(args.pid)
