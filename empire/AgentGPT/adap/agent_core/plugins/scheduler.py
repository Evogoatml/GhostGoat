"""
Basic scheduler for reminders and jobs
@jarviscmd: Schedule a reminder or shell command.
"""

import time, threading, os

def run():
    t = input("Minutes from now: ")
    cmd = input("Command to run (or text for reminder): ")

    def do_job():
        if os.path.exists(cmd):
            os.system(cmd)
        else:
            print(f"[Reminder] {cmd}")
    print(f"Scheduled in {t} minutes.")
    threading.Timer(float(t)*60, do_job).start()
