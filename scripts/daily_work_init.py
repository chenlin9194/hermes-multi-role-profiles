#!/usr/bin/env python3
"""
每日工作目录初始化脚本
运行时间：每天 6:00 AM
功能：创建当天 YYYY-MM-DD 目录及 shared/ 文件骨架
"""

import os
from datetime import date
from pathlib import Path

# D: drive root
WORK_ROOT = Path("/mnt/d/Work")
TODAY = date.today()
DATE_STR = TODAY.isoformat()  # 2026-04-27
TODAY_DIR = WORK_ROOT / DATE_STR

# 子目录
SUBDIRS = ["shared", "assistant", "se", "writer", "reviewer"]

# 公共区文件内容
SHARED_TASKS = """# 📋 今日待办 ({date})

> 来源：全员可登记 | 更新频率：实时

| # | 事项 | 截止时间 | 责任人 | 状态 | 来源角色 |
|---|------|---------|--------|------|---------|
| - | 暂无待办 | - | - | - | - |
"""

SHARED_RISKS = """# ⚠️ 风险登记簿 ({date})

> 来源：全员可登记 | 更新频率：实时

| # | 风险描述 | 等级 | 影响范围 | 提出人 | 状态 |
|---|---------|------|---------|-------|------|
| - | 暂无风险 | - | - | - | - |
"""

SHARED_DECISIONS = """# 📌 关键决议记录 ({date})

> 来源：全员可登记 | 更新频率：实时

| 时间 | 决议内容 | 提出人 | 参与角色 |
|------|---------|-------|---------|
| - | 暂无新决议 | - | - |
"""


def main():
    if TODAY_DIR.exists():
        print(f"[SKIP] {TODAY_DIR} 已存在，跳过创建")
        return

    # 创建目录
    for sub in SUBDIRS:
        (TODAY_DIR / sub).mkdir(parents=True, exist_ok=True)

    # 创建 shared 文件
    files = {
        "shared/tasks.md": SHARED_TASKS.format(date=DATE_STR),
        "shared/risks.md": SHARED_RISKS.format(date=DATE_STR),
        "shared/decisions.md": SHARED_DECISIONS.format(date=DATE_STR),
    }
    for rel_path, content in files.items():
        (TODAY_DIR / rel_path).write_text(content, encoding="utf-8")

    print(f"[CREATED] {TODAY_DIR}")
    print(f"  子目录: {', '.join(SUBDIRS)}")
    print(f"  公共文件: {', '.join(files.keys())}")


if __name__ == "__main__":
    main()
