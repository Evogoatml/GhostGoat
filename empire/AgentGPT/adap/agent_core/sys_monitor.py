# adap/plugins/sys_monitor.py

"""
Monitor system resources
@jarviscmd: Monitors CPU and RAM usage.
"""
def run():
    import psutil
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    print(f"CPU Usage: {cpu}% | RAM Usage: {ram}%")
