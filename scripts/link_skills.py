#!/usr/bin/env python3
"""把仓库里的技能**软链**进本机的技能目录，而不是拷贝。

为什么是软链：拷贝式安装咬过两次。

  * `star` 这个技能从仓库里删掉之后，`~/.agents/skills/star` 还留着——`npx skills add`
    只加不删，安装目录里的副本与仓库之间没有任何东西在维持一致；
  * `CONTRACT.md` 曾经放在 `skills/flow/` 下（**不是技能**），而拍平只复制
    `<root>/<name>/` 这一层，于是它在安装目录里根本不存在——八份 flow `SKILL.md` 那句
    「见 `../CONTRACT.md`」指向一个空文件。T1 eval 第一轮就是这么发现的：臂 `read` 它得到
    `not found`，然后花好几个工具调用到处找。**那个文件现在住在 `skills/flow/loop-it/`
    里**，跟着 loop-it 一起被复制，于是不需要任何特判。

软链一次解决两个：`git pull` 就更新；技能删掉之后链接变成悬空的，下次跑本脚本被清掉。

    python3 scripts/link_skills.py                 # 链进 ~/.agents/skills
    python3 scripts/link_skills.py --dest DIR      # 换一个目标目录
    python3 scripts/link_skills.py --check         # 只报告，不改动（退出码 1 表示有漂移）

不认识的条目**不动**：`~/.agents/skills` 可能同时住着别的来源的技能（`teach`、`sticker`
之类）。只有「指向本仓库的悬空链接」会被清掉，其余只列出来给人看。
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUCKETS = ("flow", "bonus", "vendor")
DEFAULT_DEST = os.path.join(os.path.expanduser("~"), ".agents", "skills")


def repo_skills() -> dict[str, str]:
    """仓库里的技能：名字 → 目录的绝对路径。技能是 `<bucket>/<name>/SKILL.md` 一层。"""
    found: dict[str, str] = {}
    for bucket in BUCKETS:
        root = os.path.join(REPO, "skills", bucket)
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            skill_dir = os.path.join(root, name)
            if os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
                found[name] = skill_dir
    return found


def points_into_repo(path: str) -> bool:
    """这个路径（跟着软链走）是不是落在本仓库里。"""
    if not os.path.islink(path):
        return False
    target = os.path.realpath(path)
    return target == REPO or target.startswith(REPO + os.sep)


def main() -> int:
    parser = argparse.ArgumentParser(description="把仓库技能软链进本机技能目录")
    parser.add_argument("--dest", default=DEFAULT_DEST, help=f"目标目录（默认 {DEFAULT_DEST}）")
    parser.add_argument("--check", action="store_true", help="只报告漂移，不改动")
    args = parser.parse_args()

    skills = repo_skills()
    if not skills:
        print(f"读不到任何技能：{os.path.join(REPO, 'skills')}/<桶>/<技能>/SKILL.md", file=sys.stderr)
        return 1

    dest = os.path.abspath(os.path.expanduser(args.dest))
    if os.path.islink(dest):
        print(f"error: {dest} 本身是一个软链；删掉它再跑，本脚本会把它建成真目录", file=sys.stderr)
        return 1

    problems: list[str] = []
    linked: list[str] = []
    pruned: list[str] = []
    unknown: list[str] = []

    existing = sorted(os.listdir(dest)) if os.path.isdir(dest) else []
    if not args.check:
        os.makedirs(dest, exist_ok=True)

    # 1) 仓库里的每个技能：目标必须是指向它的软链。
    for name, src in skills.items():
        target = os.path.join(dest, name)
        if os.path.islink(target):
            if os.path.realpath(target) == src:
                linked.append(name)
                continue
            problems.append(f"{name}: 软链指向 {os.path.realpath(target)}，应该是 {src}")
        elif os.path.exists(target):
            # 拷贝式安装留下的真目录——正是「删技能不留尸体」治不了的那种。
            problems.append(f"{name}: 是拷贝而不是软链，要替换成 -> {src}")
        else:
            problems.append(f"{name}: 没有链接，应该是 -> {src}")
        if not args.check:
            if os.path.isdir(target) and not os.path.islink(target):
                shutil.rmtree(target)
            elif os.path.exists(target):
                os.remove(target)
            os.symlink(src, target)
            linked.append(name)

    # 2) 指向本仓库、但目标已经不在的悬空链接：技能被删了，尸体要清掉。
    for name in existing:
        target = os.path.join(dest, name)
        if name in skills:
            continue
        if os.path.islink(target) and not os.path.exists(target):
            if points_into_repo(target):
                problems.append(f"{name}: 悬空软链（技能已删），清掉")
                if not args.check:
                    os.remove(target)
                    pruned.append(name)
        elif os.path.islink(target) and points_into_repo(target):
            problems.append(f"{name}: 指向本仓库但已不是技能，清掉")
            if not args.check:
                os.remove(target)
                pruned.append(name)
        elif not os.path.islink(target):
            unknown.append(name)

    if args.check:
        if problems:
            print(f"{dest} 有 {len(problems)} 处漂移：")
            for problem in problems:
                print(f"  - {problem}")
            return 1
        print(f"ok: {len(linked)} 个技能都软链到本仓库（{dest}）")
        return 0

    for problem in problems:
        print(f"  {problem}")
    print(f"ok: 软链 {len(linked)} 个技能 -> {dest}" + (f"；清掉 {len(pruned)} 个" if pruned else ""))
    if unknown:
        print(f"  ℹ️  不认识的条目（别的来源，没动）：{'、'.join(unknown)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
