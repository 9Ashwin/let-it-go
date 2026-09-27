#!/usr/bin/env python3
"""Validate every skill the way the DeepSeek Harness loads it.

This set is DSH-only: one host to satisfy, one manifest to keep in sync.

Layout: `skills/<bucket>/<name>/SKILL.md`, with `<bucket>` one of `flow`, `bonus` or
`vendor`. DSH discovers a skill at `<root>/<name>/SKILL.md`
— exactly one level below a configured root — so `cordis.patch.yml` lists every
bucket as its own root. That makes two mistakes invisible until someone notices
a skill is gone:

  * an invalid frontmatter (for example an unquoted `left: foo`, or a `name` that is not
    kebab-case) makes DSH drop the skill with only a logger warning;
  * a description longer than `catalogDescriptionMaxLength` (default 500) is **truncated**
    in the catalog rather than dropped — silent, and it weakens triggering, so it is
    worth failing on our own skills.

This script fails loudly on both, on any bucket it does not know, on a root missing from
the bundle patch, on a `/name` in prose that names a skill that no longer exists —
that last one is how a rename quietly leaves dead routes behind — and on an installer
manifest that has drifted away from the buckets.

Vendored skills are upstream's to shape, so this repo's own conventions (name matching
the directory, description inside the cap) are reported as warnings for them, while
anything that would stop DSH loading the skill stays fatal.

Usage: python3 scripts/check_skills.py [skills_root]
Exit code 1 when anything fails.
"""

from __future__ import annotations

import json
import os
import re
import sys

DESCRIPTION_CAP = 500
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BUCKETS = ("flow", "bonus", "vendor")
# Third-party copies live in this bucket. Upstream is theirs to shape, so this repo's own
# conventions (name matching the directory, description inside the catalog cap) only warn.
VENDOR_BUCKET = "vendor"
# A skill reference in prose: the DSH prefix `/` followed by a kebab-case name. The trailing
# lookahead keeps paths out — `/usr/bin` and `https://host/path` are not skill references.
SKILL_REF = re.compile(r"(?:^|[\s(\[`'\"*>])(/)([a-z0-9]+(?:-[a-z0-9]+)*)(?![a-z0-9/_.-])")
# Things that look like a skill reference but are not skills: host commands the guides
# legitimately name.
HOST_COMMANDS = frozenset(
    {"goal", "new", "cancel", "stop", "status", "help", "clear", "compact", "resume"}
)


def _prose_refs(text: str):
    """Yield (name, prefix, offset) for skill-looking references written in prose.

    Two rules keep this from crying wolf, and both were added after the first version
    flagged five non-skills: fenced code blocks are skipped outright, and a reference only
    counts when it sits inside an inline code span. That is how this repo writes them —
    `` `/prd` ``, `` `/graph` `` — while a filesystem path (`/tmp`) or a UI route
    (`/tasks`) is written bare.
    """
    fenced = False
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fenced = not fenced
            offset += len(line)
            continue
        if not fenced:
            for match in SKILL_REF.finditer(line):
                if line[: match.start(2)].count("`") % 2 == 1:
                    yield match.group(2), match.group(1), offset + match.start(2)
        offset += len(line)


def check_skill_references(repo_root: str, skills: list[tuple[str, str, str]]) -> list[str]:
    """Every `/name` or `$name` in prose must name a skill that actually exists.

    This is the cheapest rot to ship and the hardest to notice: a skill gets renamed or
    merged, its old name survives in a neighbour's prose, and the agent follows a route to
    nowhere. Manual cleanup does not scale — it was done by hand once in this repo and six
    dead references had already accumulated across four merged or deleted skills.

    The mechanical half of the loop lives here; the prose half (which problems deserve a
    durable rule, and which rules have gone stale) stays judgement, per the retrospective
    step the guides describe.
    """
    known = {name for _, name, _ in skills} | HOST_COMMANDS
    targets: list[tuple[str, str]] = [
        (os.path.join(repo_root, name), name) for name in ("README.md", "README_EN.md")
    ]
    targets += [(path, f"{bucket}/{name}") for bucket, name, path in skills if bucket != VENDOR_BUCKET]

    problems: list[str] = []
    for path, label in targets:
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        for name, prefix, offset in _prose_refs(text):
            if name in known:
                continue
            line = text.count("\n", 0, offset) + 1
            problems.append(
                f"{label}:{line}: references `{prefix}{name}`, which is not a skill — "
                f"renamed, merged or deleted? Update the reference or restore the skill"
            )
    return problems


def load_frontmatter(path: str) -> dict | str:
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---"):
        return "file does not start with a YAML frontmatter fence"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "frontmatter fence is not closed"
    try:
        import yaml
    except ImportError:  # pragma: no cover - dependency is optional
        return "PyYAML is not installed — run `python3 -m pip install -r requirements.txt`"
    try:
        data = yaml.safe_load(parts[1])
    except Exception as exc:  # noqa: BLE001 - report whatever the parser said
        return f"YAML error: {exc.__class__.__name__}: {exc}"
    if not isinstance(data, dict):
        return "frontmatter is not a mapping"
    return data


def strip_code_fences(body: str) -> str:
    """去掉围栏代码块。

    围栏里的是**内容**，不是引用。模板类技能把"要写进别处"的 markdown 放在围栏里，那些相对
    链接在目标工作区才解析得到——扫它们会把一份正确的模板报成死链（`start` 就是这么撞上的）。
    注意只有链接检查该跳过围栏：脚本引用恰恰常常写在围栏里（`python3 <SKILL_DIR>/scripts/x.py`）。
    """
    kept, inside = [], False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
            continue
        if not inside:
            kept.append(line)
    return "\n".join(kept)


def check_reference_links(repo_root: str, skills: list[tuple[str, str, str]]) -> list[str]:
    """Every `references/x.md` a skill links to must exist.

    A rename leaves these behind, and the failure is quiet in the worst way: the model follows a
    link into nothing, then improvises around the missing guidance. `check_skill_references`
    covers `/skill-name` routes; this covers the files beside the skill.
    """
    problems = []
    for _, name, path in skills:
        directory = os.path.dirname(path)
        for root, _, files in os.walk(directory):
            for entry in files:
                if not entry.endswith(".md"):
                    continue
                source = os.path.join(root, entry)
                body = strip_code_fences(open(source, encoding="utf-8").read())
                for target in re.findall(r"\]\(([^)#:]+\.md)\)", body):
                    if target.startswith(("http://", "https://")):
                        continue
                    if not os.path.exists(os.path.normpath(os.path.join(root, target))):
                        rel = os.path.relpath(source, repo_root)
                        problems.append(f"{rel} links to {target}, which does not exist")
    return problems


def check_script_references(repo_root: str, skills: list[tuple[str, str, str]]) -> list[str]:
    """Every `scripts/<name>` a skill mentions must exist somewhere in the set.

    Same failure as a dead `references/` link, and just as quiet: the model runs a command that
    is not there, gets "No such file", and improvises. It happened for real — `review-it`
    described a `<SKILL_DIR>/scripts/review-it` runner in ~40 lines, with `--parallel-tests`,
    `--help` and `--agent auto`, long after the DSH-only refactor deleted the script. Its own
    runtime reference said DSH has no runner, so the skill contradicted itself and nothing
    mechanical noticed: `check_reference_links` only follows `.md` links, and this was inline
    code in prose.

    Any skill's `scripts/` counts, so a genuine cross-skill reference is fine, and so does the
    repo's own top-level `scripts/`. The vendor bucket is skipped: those are verbatim upstream
    copies and their prose is upstream's to shape.
    """
    known = set(os.listdir(os.path.join(repo_root, "scripts")))
    for bucket, _, path in skills:
        if bucket == VENDOR_BUCKET:
            continue
        script_dir = os.path.join(os.path.dirname(path), "scripts")
        if os.path.isdir(script_dir):
            known.update(os.listdir(script_dir))

    problems = []
    for bucket, _, path in skills:
        if bucket == VENDOR_BUCKET:
            continue
        directory = os.path.dirname(path)
        for root, _, files in os.walk(directory):
            for entry in files:
                if not entry.endswith((".md", ".json")):
                    continue
                source = os.path.join(root, entry)
                body = open(source, encoding="utf-8").read()
                for target in re.findall(r"scripts/([A-Za-z0-9_.-]+)", body):
                    if target in known:
                        continue
                    rel = os.path.relpath(source, repo_root)
                    problems.append(
                        f"{rel} mentions scripts/{target}, which exists in no skill — "
                        f"the command the reader would run is not there"
                    )
    return sorted(set(problems))


def _skills_in(root: str, label: str, problems: list[str]) -> list[tuple[str, str, str]]:
    """Collect `<root>/<name>/SKILL.md` triples, one level deep."""
    found: list[tuple[str, str, str]] = []
    for name in sorted(os.listdir(root)):
        if name.startswith("."):
            continue  # dotfiles are manifests and caches, not skills
        skill_dir = os.path.join(root, name)
        if not os.path.isdir(skill_dir):
            continue
        path = os.path.join(skill_dir, "SKILL.md")
        if os.path.isfile(path):
            found.append((label, name, path))
        else:
            problems.append(f"{label}/{name}: no SKILL.md (skills are one level below a root)")
    return found


def discover(skills_root: str) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Return (bucket, name, path) triples plus layout problems.

    Every bucket is scanned exactly one level deep, because that is how DSH resolves a
    skill root: `skills/<bucket>/<name>/SKILL.md`. `vendor` is a bucket like any other —
    it holds third-party copies instead of skills this repo owns, which is what makes
    provenance obvious and a sync safe.
    """
    found: list[tuple[str, str, str]] = []
    problems: list[str] = []

    for entry in sorted(os.listdir(skills_root)):
        full = os.path.join(skills_root, entry)
        if not os.path.isdir(full):
            continue
        if os.path.isfile(os.path.join(full, "SKILL.md")):
            problems.append(
                f"{entry}: sits at the top level of skills/ — move it into a bucket "
                f"({'/'.join(BUCKETS)}), or the bundle patch will not serve it"
            )
            continue
        if entry not in BUCKETS:
            problems.append(f"{entry}: unknown bucket (expected one of {', '.join(BUCKETS)})")
            continue
        found.extend(_skills_in(full, entry, problems))
    return found, problems


def check_bundle_patch(repo_root: str, buckets: set[str]) -> list[str]:
    """Every bucket must appear as its own customSkillDirs root in the bundle patch."""
    path = os.path.join(repo_root, "cordis.patch.yml")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        return [f"cordis.patch.yml is unreadable: {exc}"]
    problems = []
    for bucket in sorted(buckets):
        # The root expression ends in `..., 'skills', '<bucket>'`.
        if f"'skills', '{bucket}'" not in text:
            problems.append(
                f"cordis.patch.yml does not list '{bucket}' as a customSkillDirs root — "
                f"the bundle install would serve none of the skills under skills/{bucket}"
            )
    return problems


def check_installer_manifest(repo_root: str, skills: list[tuple[str, str, str]]) -> list[str]:
    """The bucket layout and the installer picker must agree.

    `npx skills add` reads the root `.claude-plugin/marketplace.json` to label each skill
    with a group, and it reads nothing else: the picker falls back to one flat list of
    names the moment that file is absent or short a skill. That flat list is not an error
    the installer reports — it just stops showing which bucket a skill belongs to, which is
    how the three buckets silently stopped being visible once already.

    So the manifest is a second copy of the layout, and a second copy rots: it is checked
    rather than trusted. Vendored skills are included — they are listed like any other, and
    a vendor sync that adds or drops one has to move this file too.
    """
    path = os.path.join(repo_root, ".claude-plugin", "marketplace.json")
    try:
        manifest = json.load(open(path, encoding="utf-8"))
    except OSError:
        return [
            ".claude-plugin/marketplace.json is missing — the installer picker would show "
            "one flat list instead of the buckets"
        ]
    except json.JSONDecodeError as exc:
        return [f".claude-plugin/marketplace.json is not valid JSON: {exc}"]

    problems: list[str] = []
    listed: dict[str, set[str]] = {}
    for plugin in manifest.get("plugins", []):
        source = plugin.get("source")
        if not isinstance(source, str) or not source.startswith("./"):
            problems.append(
                f"marketplace.json: plugin {plugin.get('name')!r} has source {source!r}, "
                f"expected a './skills/<bucket>' path"
            )
            continue
        rel = os.path.relpath(os.path.normpath(os.path.join(repo_root, source)), repo_root)
        parts = rel.split(os.sep)
        if len(parts) != 2 or parts[0] != "skills":
            problems.append(
                f"marketplace.json: plugin {plugin.get('name')!r} has source {source!r}, "
                f"expected a './skills/<bucket>' path"
            )
            continue
        bucket = parts[1]
        names: set[str] = set()
        for entry in plugin.get("skills", []):
            if not isinstance(entry, str) or not entry.startswith("./"):
                problems.append(
                    f"marketplace.json: {bucket} lists {entry!r}, expected a './<name>' path"
                )
                continue
            names.add(os.path.basename(entry.rstrip("/")))
        listed[bucket] = names

    actual: dict[str, set[str]] = {}
    for bucket, name, _ in skills:
        actual.setdefault(bucket, set()).add(name)

    for bucket in sorted(set(listed) | set(actual)):
        want, have = listed.get(bucket, set()), actual.get(bucket, set())
        for name in sorted(have - want):
            problems.append(
                f"marketplace.json: skills/{bucket}/{name} is not listed — it would show up "
                f"ungrouped in the installer picker"
            )
        for name in sorted(want - have):
            problems.append(
                f"marketplace.json: lists {bucket}/{name}, which is not a skill any more"
            )
    return problems


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills"
    )
    repo_root = os.path.dirname(root)
    skills, failures = discover(root)
    if not skills and not failures:
        print(f"no skills found under {root}", file=sys.stderr)
        return 1
    failures.extend(check_bundle_patch(repo_root, {b for b, _, _ in skills}))
    failures.extend(check_skill_references(repo_root, skills))
    failures.extend(check_reference_links(repo_root, skills))
    failures.extend(check_script_references(repo_root, skills))
    failures.extend(check_installer_manifest(repo_root, skills))

    warnings: list[str] = []
    for bucket, name, path in skills:
        # A vendored skill is upstream's to shape. DSH still has to be able to load it, so
        # the frontmatter rules stay fatal; this repo's own conventions only warn, because
        # fixing them would mean editing a verbatim copy.
        report = warnings.append if bucket == VENDOR_BUCKET else failures.append

        fm = load_frontmatter(path)
        if isinstance(fm, str):
            failures.append(f"{bucket}/{name}: {fm}")
            continue
        if fm.get("name") != name:
            report(f"{bucket}/{name}: frontmatter name {fm.get('name')!r} != directory name")
        if not KEBAB.match(str(fm.get("name", ""))):
            failures.append(f"{bucket}/{name}: name is not kebab-case")
        description = fm.get("description")
        if not isinstance(description, str) or not description.strip():
            failures.append(f"{bucket}/{name}: description is missing or empty")
            continue
        if len(description) > DESCRIPTION_CAP:
            report(
                f"{bucket}/{name}: description is {len(description)} chars, over the "
                f"{DESCRIPTION_CAP} catalog cap — DSH truncates the tail in the model catalog"
            )

    if warnings:
        print(f"{len(warnings)} warning(s) — vendored skills are upstream's to shape:")
        for line in warnings:
            print(f"  - {line}")

    if failures:
        print(f"{len(failures)} problem(s) across {len(skills)} skills:")
        for line in failures:
            print(f"  - {line}")
        return 1

    per_bucket = ", ".join(
        f"{bucket}: {sum(1 for b, _, _ in skills if b == bucket)}" for bucket in BUCKETS
    )
    print(f"ok: {len(skills)} skills valid ({per_bucket}; frontmatter parses, names match, "
          f"descriptions <= {DESCRIPTION_CAP} chars, every /reference resolves, "
          f"every bucket served by the bundle patch and listed in the installer manifest)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
