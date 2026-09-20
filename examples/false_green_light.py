#!/usr/bin/env python3
"""
假绿灯最小可复现示例 (False Green Light — minimal reproduction)

运行方式：
    python examples/false_green_light.py

运行后你会看到：同一个任务，两种判据给出**相反**的结论——
    日志显示"任务执行成功"、退出码为 0
    但任务应该产生的文件根本不存在

这就是「假绿灯」：监控说是绿的，实际什么都没发生。

说明：
- 运行后会在本目录下生成 state/ 痕迹文件（这是演示证据，可随时删除）
- 可重复运行，每次都会自动重置现场
"""

import os
import shutil
import sys
from datetime import datetime

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(WORK_DIR, "state")          # 存在（演示框架自己创建）
RUN_DIR = os.path.join(STATE_DIR, "run")             # ⚠️ 故意不存在：模拟"清理脚本/重新部署后子目录被删"
STATE_FILE = os.path.join(RUN_DIR, "last_run.txt")   # 任务产物应该出现在这里
TMP_FILE = os.path.join(STATE_DIR, "tmp_write.txt")
LOG_FILE = os.path.join(STATE_DIR, "task.log")


# ============================================================
# 场景一：AI 常见的写法 —— 看起来很对，实际上有问题
# ============================================================

def ai_typical_task():
    """一个典型的 AI 生成风格的每日任务。

    想做的事：把今天的运行时间写入 state/run/last_run.txt
    实际的事：state/run/ 目录不存在 → 移动失败 → 异常被吞 → 什么都没发生

    两个高发问题，都是 AI 生成代码里的真实模式：
      1. 没有 os.makedirs —— AI 默认"目录应该已经在了"
      2. except Exception: pass —— AI 的舒适区："出错不该让主流程崩"
         （结果：错误彻底消失，连日志里都没有）
    """
    try:
        # 第 1 步：写临时文件（这步会成功，state/ 存在）
        with open(TMP_FILE, "w", encoding="utf-8") as f:
            f.write(datetime.now().isoformat())

        # 第 2 步：移动到位（这步会失败 —— state/run/ 不存在）
        # ⚠️ 注意：没有 makedirs，也没有对失败的任何处理
        os.replace(TMP_FILE, STATE_FILE)

    except Exception:
        # ⚠️ 异常被吞掉。不是打印，不是上报，是彻底消失。
        pass

    return 0  # "没崩溃 = 成功"


def shell_wrapper_bug():
    """模拟 shell 包装脚本的经典陷阱。

    AI 生成的 crontab / 定时任务包装脚本，常常这样结尾：

        python task.py
        rm -f /tmp/task.lock     # ← 清理锁文件

    因为 rm -f 几乎永远成功（-f 连"文件不存在"都不报错），
    所以整个脚本的退出码永远是 0 —— 无论 task.py 成功还是失败。
    """
    return 0  # 假装这是 rm -f 的返回码，它覆盖了前面所有命令的结果


# ============================================================
# 场景二：正确的写法 —— 对照组
# ============================================================

def correct_task():
    """正确写法：目录自己建、异常不吞、产物必须验证。"""
    # 1. 不假设目录存在 —— 自己创建
    os.makedirs(RUN_DIR, exist_ok=True)

    with open(TMP_FILE, "w", encoding="utf-8") as f:
        f.write(datetime.now().isoformat())
    os.replace(TMP_FILE, STATE_FILE)

    # 2. 验证痕迹 —— 不看返回值，看产物
    if not os.path.exists(STATE_FILE):
        raise RuntimeError("任务声称成功，但产物不存在")
    if os.path.getsize(STATE_FILE) == 0:
        raise RuntimeError("产物存在但内容为空（同样是失效）")

    return 0


def verify_by_trace():
    """判据 B：不看退出码，看它应该产生的痕迹。"""
    if not os.path.exists(STATE_FILE):
        return False, "产物文件不存在 —— 任务实际上没有执行"
    mtime = os.path.getmtime(STATE_FILE)
    return True, f"产物存在，最后写入时间：{datetime.fromtimestamp(mtime).strftime('%H:%M:%S')}"


# ============================================================
# 演示主流程
# ============================================================

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    os.makedirs(STATE_DIR, exist_ok=True)

    print("=" * 62)
    print("假绿灯最小复现示例")
    print("=" * 62)
    print()

    # ---------- 场景一：AI 写法 ----------
    print("【场景一】AI 典型写法（吞异常 + rm -f 收尾）")
    print("-" * 62)

    # 重置现场：删掉 run/ 子目录，模拟"环境不完整"
    # （真实世界里：清理脚本、重新部署、磁盘迁移都干得出这种事）
    shutil.rmtree(RUN_DIR, ignore_errors=True)

    rc_inner = ai_typical_task()
    rc_outer = shell_wrapper_bug()

    # AI 风格的乐观日志：只记录"调用过"，不验证结果
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("任务开始\n")
        f.write("任务执行成功\n")

    ok_by_rc = (rc_outer == 0)
    ok_by_trace, msg = verify_by_trace()

    print(f"  日志最后一行 : 任务执行成功")
    print(f"  退出码       : {rc_outer}")
    print()
    print(f"  判据 A：看退出码  →  rc = {rc_outer}  →  判定：{'成功 ✅' if ok_by_rc else '失败 ❌'}")
    print(f"  判据 B：看痕迹    →  {msg}")
    print(f"                                  →  判定：{'成功 ✅' if ok_by_trace else '失败 ❌'}")
    print()
    print("  >>> 两个判据结论相反。真相是：任务根本没执行。")
    print("  >>> 如果你的监控只看退出码，它现在正对着绿灯微笑。")
    print()

    # ---------- 场景二：正确写法 ----------
    print("=" * 62)
    print("【场景二】正确写法（对照）")
    print("-" * 62)

    try:
        correct_task()
        ok, msg2 = verify_by_trace()
        print(f"  执行结果 : 未抛异常")
        print(f"  痕迹检查 : {msg2}  →  判定：{'成功 ✅' if ok else '失败 ❌'}")
    except Exception as e:
        print(f"  执行结果 : 抛出异常 —— {e}")
        print(f"  判定     : 失败 ❌（但这一次，你看得见）")
    print()

    # ---------- 结论 ----------
    print("=" * 62)
    print("结论")
    print("=" * 62)
    print()
    print("  1. 「日志显示成功」和「任务真的执行了」是两回事。")
    print("  2. 判据不要看退出码，要看它应该产生的痕迹：")
    print("     文件有没有更新？时间戳变了吗？数据库里有没有新行？")
    print("  3. except: pass 和 rm -f 结尾，是假绿灯的两大制造机。")
    print("     它们单独看都无害，组合起来让整个监控失效。")
    print()
    print(f"  演示痕迹保存在: {os.path.relpath(STATE_DIR, WORK_DIR)}{os.sep} （可随时删除）")
    print()


if __name__ == "__main__":
    main()
