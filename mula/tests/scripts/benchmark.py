import argparse
import logging
import subprocess
import threading
import time

import psutil
import requests

SCHEDULER_API = "http://localhost:8004"

logger = logging.getLogger(__name__)

def are_tasks_done():
    response = requests.get(
        url=f"{SCHEDULER_API}/tasks/stats",
    )

    try:
        resp_tasks_stats.raise_for_status()
    except requests.exceptions.HTTPError:
        logger.error("Error getting tasks")
        raise

    tasks_stats = resp_tasks_stats.json()
    if not tasks_stats:
        logger.debug("No tasks found")
        return False

    return all(tasks_stats[hour].get("queued") <= 0 for hour in tasks_stats)


def parse_stats():
    resp_tasks_stats = requests.get(
        url=f"{SCHEDULER_API}/tasks/stats",
    )

    try:
        resp_tasks_stats.raise_for_status()
    except requests.exceptions.HTTPError:
        logger.error("Error getting tasks")
        raise

    tasks_stats = resp_tasks_stats.json()
    for hour in tasks_stats:
        queued = tasks_stats[hour].get("queued")
        running = tasks_stats[hour].get("running")
        failed = tasks_stats[hour].get("failed")
        completed = tasks_stats[hour].get("completed")
        logger.info(f"HOUR {hour}, QUEUED {queued}, RUNNING {running}, FAILED {failed}, COMPLETED {completed}")


def capture_logs(pid: int, output_file: str):
    try:
        with open(output_file, 'a') as file:
            process = subprocess.Popen(['tail', '-f', f'/proc/{pid}/fd/1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            while process.poll() is None:
                output_line = process.stdout.readline().strip()
                error_line = process.stderr.readline().strip()

                if output_line:
                    file.write(f"STDOUT: {output_line}\n")
                if error_line:
                    file.write(f"STDERR: {error_line}\n")
    except Exception as e:
        logger.error(f"Error capturing logs: {e}")
        raise


def parse_logs(path: str):
    # Check if there were any errors in the logs
    count = 0
    with open(path, encoding="utf-8") as file:
        for line in file:
            if "ERROR" in line:
                count += 1
                logger.info(line)
            if "Traceback" in line:
                count += 1
                logger.info(line)

    if count > 0:
        logger.error(f"Found {count} errors in the logs")


def collect_cpu(pid: int):
    process = psutil.Process(pid)
    return process.cpu_percent()


def collect_memory(pid: int):
    process = psutil.Process(pid)
    return process.memory_info().rss / 1024 / 1024


def run(pid: int):
    # Start capturing logs
    th_capture_logs = threading.Thread(target=capture_logs, args=(pid, "logs.txt"))
    th_capture_logs.start()

    # Wait for tasks to finish
    while not are_tasks_done():
        logger.debug("Tasks are not done yet")

        cpu = collect_cpu(pid)
        memory = collect_memory(pid)
        logger.info(f"CPU {cpu}, MEM {memory:.2f}")

        # Parse stats
        parse_stats()

        time.sleep(10)
        continue

    logger.debug("Tasks are done")

    # Stop capturing logs
    th_capture_logs.join(timeout=TIMEOUT_FOR_LOG_CAPTURE)

    # Parse stats
    parse_stats()

    # Parse logs
    parse_logs("logs.txt")


if __name__ == "__main__":
    TIMEOUT_FOR_LOG_CAPTURE = 5

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
        format="%(asctime)s %(name)-10s %(levelname)-8s %(message)s",
    )

    run(args.pid)
