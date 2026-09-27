#!/usr/bin/env python3
"""扫一个工作区，把「铺约定需要的事实」读出来。

技能正文写判断，这里只做算术：门禁是什么、有没有既有约定、测试基线在哪、
下一个需求序号是几——这些都能从文件系统读出来，不该让模型靠猜。

用法：
    python3 scan_workspace.py [--root DIR] [--json]
    python3 scan_workspace.py --self-test

只读，不写任何东西。
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

# 会写产物的技能按这些目录找作用域根；顺序即优先级（先命中先用）。
SCOPE_ROOT_CANDIDATES = ["requirements", "specs", "spec", "docs/requirements", "tasks"]

# 一个工作区"铺过约定"的标志文件。
CONVENTION_FILES = ["AGENTS.md", "CONSTRAINTS.md", "RULES.md", "requirements/README.md"]

# 认得出是测试的文件名形状（各语言常见的那几种）。
TEST_PATTERNS = [
    re.compile(r"_test\.go$"),
    re.compile(r"(^|/)test_.*\.py$"),
    re.compile(r"_test\.py$"),
    re.compile(r"\.(test|spec)\.[jt]sx?$"),
    re.compile(r"(^|/)tests?/"),
]

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "__pycache__"}

# Makefile 里算门禁的目标名。
GATE_TARGETS = {"check", "test", "lint", "verify", "ci"}
# package.json 里算门禁的脚本名。
GATE_SCRIPTS = {"check", "test", "lint", "typecheck", "verify"}


def read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def git(root: str, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def find_gate(root: str) -> dict:
    """找出这个仓库的门禁候选。返回 {candidates, evidence}。"""
    candidates: list[str] = []
    evidence: list[str] = []

    makefile = os.path.join(root, "Makefile")
    if os.path.exists(makefile):
        targets = set(re.findall(r"^([A-Za-z0-9_-]+)\s*:", read(makefile), re.M))
        hit = sorted(targets & GATE_TARGETS)
        evidence.append("Makefile targets: " + (", ".join(sorted(targets)) or "（无）"))
        for name in hit:
            candidates.append(f"make {name}")

    package = os.path.join(root, "package.json")
    if os.path.exists(package):
        try:
            scripts = json.loads(read(package)).get("scripts") or {}
        except json.JSONDecodeError:
            scripts = {}
        hit = sorted(set(scripts) & GATE_SCRIPTS)
        evidence.append("package.json scripts: " + (", ".join(sorted(scripts)) or "（无）"))
        for name in hit:
            candidates.append(f"npm run {name}")

    if os.path.exists(os.path.join(root, "go.mod")):
        evidence.append("go.mod 存在")
        candidates.append("go build ./... && go test ./...")

    workflows = os.path.join(root, ".github", "workflows")
    if os.path.isdir(workflows):
        names = sorted(f for f in os.listdir(workflows) if f.endswith((".yml", ".yaml")))
        if names:
            evidence.append("CI workflows: " + ", ".join(names))

    # 去重但保持顺序
    seen, ordered = set(), []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return {"candidates": ordered, "evidence": evidence}


def find_tests(root: str, limit: int = 200) -> dict:
    found: list[str] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in files:
            rel = os.path.relpath(os.path.join(base, name), root)
            if any(pattern.search(rel) for pattern in TEST_PATTERNS):
                found.append(rel)
                if len(found) >= limit:
                    break
        if len(found) >= limit:
            break
    return {"count": len(found), "sample": sorted(found)[:8]}


def find_scope_root(root: str) -> dict:
    for candidate in SCOPE_ROOT_CANDIDATES:
        if os.path.isdir(os.path.join(root, candidate)):
            return {"path": candidate, "exists": True}
    return {"path": None, "exists": False, "default": "tasks/<feature>/"}


def next_requirement_number(root: str, scope_root: str | None) -> dict:
    """需求目录按 <NN>_<名> 编号；返回下一个可用序号。"""
    if not scope_root:
        return {"next": 1, "existing": []}
    base = os.path.join(root, scope_root)
    existing = sorted(
        d for d in (os.listdir(base) if os.path.isdir(base) else [])
        if os.path.isdir(os.path.join(base, d))
    )
    numbers = [int(m.group(1)) for d in existing if (m := re.match(r"^(\d+)[_-]", d))]
    return {"next": (max(numbers) + 1) if numbers else 1, "existing": existing}


def scan(root: str) -> dict:
    root = os.path.abspath(root)
    scope_root = find_scope_root(root)
    conventions = {rel: os.path.exists(os.path.join(root, rel)) for rel in CONVENTION_FILES}
    return {
        "root": root,
        "is_git": bool(git(root, "rev-parse", "--is-inside-work-tree")),
        "default_branch": git(root, "branch", "--show-current"),
        "has_remote": bool(git(root, "remote")),
        "gate": find_gate(root),
        "conventions": conventions,
        "already_initialised": all(conventions.values()),
        "tests": find_tests(root),
        "scope_root": scope_root,
        "requirements": next_requirement_number(root, scope_root["path"]),
        "top_level": sorted(
            e for e in os.listdir(root) if not e.startswith(".") and e not in SKIP_DIRS
        )[:20],
    }


# 体检项：(编号, 说明, 该满足什么)。查的是**结构性空洞**，不是文风。
# 每项都对应一条真实的失败：缺了它，流程会按不存在的约定走，或者干脆退回默认。
AUDIT_CHECKS = [
    ("instructions", "有 AGENTS.md（流程读它才知道作用域根与门禁）", "exists:AGENTS.md"),
    ("precedence", "AGENTS.md 给了冲突裁决顺序（红线 > 用户指令 > 项目约定 > 模块决策 > 建议）",
     "text:AGENTS.md:红线"),
    ("startup", "AGENTS.md 有开工清单：先确认基线是绿的，再动新范围",
     "text:AGENTS.md:开工"),
    ("scope-root", "AGENTS.md 声明了作用域根", "text:AGENTS.md:作用域根"),
    ("gate", "AGENTS.md 声明了门禁命令", "text:AGENTS.md:门禁"),
    ("constraints", "有 CONSTRAINTS.md（边界与资料归属）", "exists:CONSTRAINTS.md"),
    ("rules", "有 RULES.md 且是登记表形状（编号 / 来源 / 优先级 / 适用 / 过期 / 状态）",
     "text:RULES.md:过期条件"),
    ("requirements", "有 requirements/README.md（目录索引与资料约定）", "exists:requirements/README.md"),
    ("closeout", "AGENTS.md 有收尾固定动作（做完自查什么）", "text:AGENTS.md:收尾"),
]


def audit(root: str) -> list[dict]:
    """体检一个已有约定的工作区，报结构性空洞。

    与 `scan` 的分工：`scan` 回答「铺之前需要知道什么」，`audit` 回答「已经铺的缺什么」。
    已经铺过约定的仓库不该重铺（那会覆盖掉人家写的红线），但**该体检**。
    """
    root = os.path.abspath(root)
    findings = []
    for key, description, rule in AUDIT_CHECKS:
        kind, _, rest = rule.partition(":")
        if kind == "exists":
            ok = os.path.exists(os.path.join(root, rest))
            evidence = rest if ok else f"缺 {rest}"
        else:  # text:<file>:<needle>
            target, _, needle = rest.partition(":")
            body = read(os.path.join(root, target))
            ok = needle in body
            evidence = f"{target} 里有「{needle}」" if ok else f"{target} 里找不到「{needle}」"
        findings.append({"check": key, "description": description, "passed": ok, "evidence": evidence})
    return findings


def self_test() -> int:
    import tempfile

    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "requirements", "01_REQ-alpha"))
        os.makedirs(os.path.join(tmp, "requirements", "02_REQ-beta"))
        os.makedirs(os.path.join(tmp, "pkg"))
        with open(os.path.join(tmp, "go.mod"), "w", encoding="utf-8") as handle:
            handle.write("module example.com/x\n")
        with open(os.path.join(tmp, "Makefile"), "w", encoding="utf-8") as handle:
            handle.write("check:\n\ttrue\nlint:\n\ttrue\n")
        with open(os.path.join(tmp, "pkg", "a_test.go"), "w", encoding="utf-8") as handle:
            handle.write("package pkg\n")

        got = scan(tmp)

        def expect(condition: bool, message: str) -> None:
            if not condition:
                failures.append(message)

        expect(got["gate"]["candidates"] == ["make check", "make lint", "go build ./... && go test ./..."],
               f"门禁候选不对: {got['gate']['candidates']}")
        expect(got["requirements"]["next"] == 3, f"下一个序号应为 3，得到 {got['requirements']['next']}")
        expect(got["scope_root"]["path"] == "requirements", f"作用域根应为 requirements，得到 {got['scope_root']}")
        expect(got["tests"]["count"] == 1, f"应找到 1 个测试文件，得到 {got['tests']['count']}")
        expect(got["already_initialised"] is False, "还没铺约定，不该报已初始化")
        expect(got["conventions"]["AGENTS.md"] is False, "AGENTS.md 不该存在")

        # audit：没铺过约定的仓库应该大部分不满足；铺好之后应该全满足
        before = audit(tmp)
        expect(sum(1 for f in before if f["passed"]) < len(before) // 2,
               f"空仓库不该通过大半体检：{sum(1 for f in before if f['passed'])}/{len(before)}")
        (pathlib.Path(tmp) / "AGENTS.md").write_text(
            "# x 协作入口\n\n## 底线\n\n红线：暂无\n\n## 开工\n\n先跑门禁看基线。\n\n"
            "作用域根是 requirements/<scope>/，门禁是 make check。\n\n## 收尾\n\n自查。\n",
            encoding="utf-8")
        (pathlib.Path(tmp) / "CONSTRAINTS.md").write_text("# 约束\n", encoding="utf-8")
        (pathlib.Path(tmp) / "RULES.md").write_text(
            "| 编号 | 规则 | 来源 | 优先级 | 适用条件 | 过期条件 | 状态 |\n", encoding="utf-8")
        (pathlib.Path(tmp) / "requirements" / "README.md").write_text("# 需求目录\n", encoding="utf-8")
        after = audit(tmp)
        expect(all(f["passed"] for f in after),
               "铺好之后体检应全过：" + str([f["check"] for f in after if not f["passed"]]))

    if failures:
        for message in failures:
            print("FAIL:", message, file=sys.stderr)
        return 1
    print("ok: scan_workspace 自测通过")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="扫工作区，给出铺约定需要的事实")
    parser.add_argument("--root", default=".", help="工作区根（默认当前目录）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--self-test", action="store_true", help="跑自测")
    parser.add_argument("--audit", action="store_true", help="体检一个已有约定的工作区")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if args.audit:
        findings = audit(args.root)
        passed = sum(1 for f in findings if f["passed"])
        for f in findings:
            print(f"  {'✓' if f['passed'] else '✗'} {f['description']}")
            if not f["passed"]:
                print(f"      {f['evidence']}")
        print(f"\n  {passed}/{len(findings)} 项满足")
        return 0 if passed == len(findings) else 1

    result = scan(args.root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"根: {result['root']}")
    print(f"git: {result['is_git']}  默认分支: {result['default_branch'] or '（无）'}  远端: {result['has_remote']}")
    print(f"门禁候选: {', '.join(result['gate']['candidates']) or '（没找到——问用户）'}")
    for line in result["gate"]["evidence"]:
        print(f"  依据: {line}")
    print(f"已有约定: {', '.join(k for k, v in result['conventions'].items() if v) or '（无）'}")
    print(f"作用域根: {result['scope_root']['path'] or '（没有——默认 ' + result['scope_root']['default'] + '）'}")
    print(f"下一个需求序号: {result['requirements']['next']}")
    print(f"测试文件: {result['tests']['count']} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
