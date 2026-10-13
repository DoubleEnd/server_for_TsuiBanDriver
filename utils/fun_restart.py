# 后端重启：重新启动当前程序（新进程）并退出旧进程
import logging
import os
import subprocess
import sys
import threading

from utils.fun_logger import archive_log

logger = logging.getLogger(__name__)

# 先让接口把响应返回给前端，再退出进程
_RESTART_DELAY = 0.5


def _launch_command():
    """返回重启用的 (启动参数, 工作目录)"""
    if getattr(sys, "frozen", False):
        # 打包运行：用当前 exe 路径重新启动
        exe = sys.executable
        return [exe], os.path.dirname(exe)
    # 源码运行：用同一个解释器重新执行当前命令
    return [sys.executable, *sys.argv], os.getcwd()


def restart_process():
    args, cwd = _launch_command()
    logger.info(f"[restart] 启动新进程: {args}（工作目录: {cwd}）")
    # 启动失败会抛异常，此时不退出，避免后端直接挂掉
    subprocess.Popen(args, cwd=cwd)
    # os._exit 不触发 atexit，这里手动归档日志
    archive_log()
    os._exit(0)


def schedule_restart():
    """延时重启，保证当前 HTTP 响应先返回给前端"""
    threading.Timer(_RESTART_DELAY, restart_process).start()
