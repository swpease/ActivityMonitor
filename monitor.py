#!/usr/bin/env python3.8

import subprocess
import signal
import sys
import sqlite3
import logging
import collections
import functools
from typing import List, Tuple


def handle_shutdown(_signo, _stack_frame, conn: sqlite3.Connection):
    # https://sqlite.org/lang_transaction.html:
    # But a transaction will also ROLLBACK if the database is closed
    # or if an error occurs and the ROLLBACK conflict resolution algorithm is specified.
    conn.close()
    sys.exit()


def parse_output(output: str) -> List[Tuple[str, str, float, int]]:
    """
    Converts the stdout of the shell command `top -l<int> -stats command,cpu,mem` into data suitable for db input.

    Processes with identical command names are summed together (cpu, mem).
    :param output: `top -l<int> -stats command,cpu,mem`'s output.
    :return: Parsed data: List of (datetime, command, cpu, mem) tuples
    """
    latest_measure = output[(output.rfind("\nProcesses: ") + 1):].splitlines()
    dt = latest_measure[1]
    # 12 is the number of header lines (pre-data)
    readings = [" ".join(line.split()) for line in latest_measure[12:]]  # Replaces whitespace sequences with " "
    readings = [line.rsplit(" ", 2) for line in readings]  # `rsplit` to hedge against multi-word `command`s

    # Add Datetimes
    for r in readings:
        r.insert(0, dt)

    # Convert CPU
    for r in readings:
        try:
            r[2] = float(r[2])
        except ValueError as e:
            logging.error("%s :: %s", e, r)
    readings = [r for r in readings if isinstance(r[2], float)]

    # Convert mem
    suffix_map = {
        "K": "",
        "M": "000",
        "G": "000000",
    }
    for r in readings:
        r[3] = r[3].rstrip("+-")  # e.g. 104M+ -> 104M
        try:
            r[3] = r[3].replace(r[3][-1], suffix_map[r[3][-1]])  # e.g. 104M -> 104000
            r[3] = int(r[3])
        except (KeyError, ValueError) as e:
            logging.error("%s :: %s", e, r)
    readings = [r for r in readings if isinstance(r[3], int)]

    # Combine duplicate Command names
    combined_cpu = collections.defaultdict(float)
    for r in readings:
        combined_cpu[r[1]] += r[2]
    combined_mem = collections.defaultdict(int)
    for r in readings:
        combined_mem[r[1]] += r[3]
    for r in readings:
        r[2] = round(combined_cpu[r[1]], 1)
        r[3] = combined_mem[r[1]]

    # Transform and deduplicate
    readings = [tuple(reading) for reading in readings]
    readings = list(set(readings))

    return readings  # TODO: sort?


def main():
    logging.basicConfig(filename="errors.log",
                        level=logging.ERROR,
                        format='%(levelname)s :: %(message)s')

    conn = sqlite3.connect("cpu_usage_data.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS CPUReadings
                    (Datetime TEXT NOT NULL, 
                     Command TEXT NOT NULL, 
                     CPU REAL NOT NULL,
                     Memory_kB INTEGER NOT NULL,
                     UNIQUE(datetime, command))""")

    signal.signal(signal.SIGTERM, functools.partial(handle_shutdown, conn=conn))
    signal.signal(signal.SIGINT, functools.partial(handle_shutdown, conn=conn))

    while True:
        done_proc = subprocess.run("top -n 10 -l 3 -s 5 -o cpu -stats command,cpu,mem".split(), capture_output=True, text=True)
        readings = parse_output(done_proc.stdout)
        try:
            # context manager auto-commits and in case of sql error auto-rollsback
            with conn:
                conn.executemany("INSERT INTO CPUReadings VALUES (?,?,?,?)", readings)
        except sqlite3.Error as e:
            logging.error("%s :: %s", e, readings)


if __name__ == "__main__":
    main()
