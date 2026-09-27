#!/usr/bin/env python3
"""Sync the skills under `skills/vendor/` from their upstream repositories.

`skills/vendor/` holds third-party skills copied **verbatim**: this repo never edits them in
place, which is what makes a one-command update safe. Anything this repo owns or adapts
lives under `skills/` instead, so a sync can never clobber local work.

`skills/vendor/vendor.json` pins every skill to a commit, so a sync is reproducible and the
resulting diff is reviewable. Adding a skill mirrors the `npx skills add` shape:

  python3 scripts/sync_vendor.py --add https://github.com/anthropics/skills.git --skill pptx

which resolves the source's default branch, finds where `pptx` lives in the checkout,
records it, and copies it in. `--update` re-resolves every pin; `--check` reports pins
that are behind without writing anything.

Usage:
  python3 scripts/sync_vendor.py                 # sync to the pinned commits
  python3 scripts/sync_vendor.py --add URL --skill NAME [--skill NAME ...]
  python3 scripts/sync_vendor.py --update        # re-pin to upstream HEAD, then sync
  python3 scripts/sync_vendor.py --check         # report pins that are behind
  python3 scripts/sync_vendor.py --only NAME     # one skill
  python3 scripts/sync_vendor.py --list          # what is vendored, and at which commit

Exit code 1 when anything fails; `--check` also exits 1 when drift is found.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO_ROOT, "skills", "vendor", "vendor.json")
VENDOR_DIR = os.path.join(REPO_ROOT, "skills", "vendor")
# Never copy these out of an upstream checkout: VCS metadata and Python bytecode are not
# part of the skill, and a nested .git would make the vendored tree a repo itself.
COPY_IGNORE = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".DS_Store")
# Directories that never contain a skill worth discovering.
SKIP_DIRS = {".git", "node_modules", "__pycache__", "dist", "build", ".venv"}


def git(*args: str, cwd: str | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def resolve_head(source_url: str) -> str:
    """The commit a source's default branch points at right now."""
    out = git("ls-remote", "--symref", source_url, "HEAD")
    for line in out.splitlines():
        if line.startswith("ref:"):
            continue  # the symref line names the default branch, not a commit
        parts = line.split()
        if len(parts) == 2 and parts[1] == "HEAD":
            return parts[0]
    raise RuntimeError(f"could not resolve HEAD of {source_url}")


def ensure_checkout(source_url: str, ref: str, cache: str) -> str:
    """A working tree at `ref`, cloned once per source and reused across its skills."""
    slug = source_url.rstrip("/").removesuffix(".git").split("//")[-1].split("/", 1)[-1].replace("/", "__")
    dest = os.path.join(cache, slug)
    if not os.path.isdir(os.path.join(dest, ".git")):
        # A blobless clone fetches history and trees but not file contents; the checkout
        # then pulls only the blobs this path needs. For a repo like anthropics/skills
        # that is the difference between a few hundred kilobytes and the whole history.
        git("clone", "--filter=blob:none", "--no-checkout", "--quiet", source_url, dest)
    git("fetch", "--quiet", "--depth", "1", "origin", ref, cwd=dest)
    git("checkout", "--quiet", "--detach", "FETCH_HEAD", cwd=dest)
    return dest


def find_skill_path(checkout: str, name: str) -> str:
    """Where `<name>` lives in a checkout — the discovery half of `npx skills add`.

    A skill is a directory named after it that contains a `SKILL.md`. When a repo has
    several (a `skills/` copy and a mirror under `plugins/`, say), the shallowest wins,
    because that is the one a human browsing the repo would call canonical.
    """
    matches: list[str] = []
    for root, dirs, files in os.walk(checkout):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if os.path.basename(root) == name and "SKILL.md" in files:
            matches.append(os.path.relpath(root, checkout))
    if matches:
        matches.sort(key=lambda rel: (rel.count(os.sep), len(rel)))
        return matches[0]
    if os.path.isfile(os.path.join(checkout, "SKILL.md")):
        # Some repositories *are* the skill, with SKILL.md at the root and no directory
        # named after it (op7418/humanizer-zh, Tencent/WeChatReading).
        return "."
    raise RuntimeError(f"no directory named {name} containing SKILL.md in {checkout}")


def find_license(checkout: str, rel_path: str) -> str | None:
    """The upstream license text governing a skill, if the checkout ships one.

    A skill directory often has no LICENSE of its own — the repo root does. Copying the
    root one in is the difference between a vendored tree that can be attributed and one
    that cannot, so it is worth the one non-verbatim file.
    """
    candidates = []
    skill_dir = os.path.normpath(os.path.join(checkout, rel_path))
    for base in (skill_dir, checkout):
        if not os.path.isdir(base):
            continue
        for entry in sorted(os.listdir(base)):
            if entry.lower().startswith(("license", "licence", "copying")):
                candidates.append(os.path.join(base, entry))
    return candidates[0] if candidates else None


def write_notice(dst: str, name: str, entry: dict, license_file: str | None) -> None:
    """Record provenance next to the copy, so the tree explains itself."""
    if license_file:
        license_note = (
            f"Upstream license text copied in as `{os.path.basename(license_file)}`"
            if os.path.dirname(license_file) == dst
            else f"Upstream license text copied in from the repository root as `LICENSE`"
        )
    else:
        license_note = "No license file was found upstream — verify before redistributing."
    text = f"""# NOTICE — vendored third-party skill

This directory is a **verbatim copy** of a third-party skill. Do not edit it here:
change `skills/vendor/vendor.json` and re-run `python3 scripts/sync_vendor.py`. A skill this
repo adapts belongs under `skills/` instead.

| | |
|---|---|
| Skill | `{name}` |
| Upstream | {entry["source"]} |
| Source | {entry["sourceUrl"]} |
| Path in source | `{entry["path"]}` |
| Commit | `{entry["ref"]}` |
| License | {entry.get("license", "unknown")} |
| Synced | {time.strftime("%Y-%m-%d")} |

{license_note} The authoritative version of every file here is upstream.
"""
    with open(os.path.join(dst, "NOTICE.md"), "w", encoding="utf-8") as handle:
        handle.write(text)


def copy_skill(src: str, dst: str) -> None:
    """Replace `dst` with a fresh copy of `src` — a sync is not a merge."""
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copytree(src, dst, ignore=COPY_IGNORE, symlinks=True)


def load_manifest() -> dict:
    with open(MANIFEST, encoding="utf-8") as handle:
        return json.load(handle)


def save_manifest(data: dict) -> None:
    with open(MANIFEST, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def verify() -> int:
    """Re-run the repo's own invariant check, so a bad sync fails here and not later."""
    result = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "scripts", "check_skills.py")],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def add_skills(source_url: str, names: list[str], manifest: dict, cache: str) -> list[str]:
    """Record new skills from one source — the `npx skills add` equivalent.

    Returns the problems and the names that were recorded, so the caller can sync just those
    instead of re-fetching every other source in the manifest.
    """
    problems: list[str] = []
    added: list[str] = []
    try:
        ref = resolve_head(source_url)
        checkout = ensure_checkout(source_url, ref, cache)
    except RuntimeError as exc:
        return [f"{source_url}: {exc}"], []

    slug = source_url.rstrip("/").removesuffix(".git").split("//")[-1].split("/", 1)[-1]
    for name in names:
        try:
            rel = find_skill_path(checkout, name)
        except RuntimeError as exc:
            problems.append(f"{name}: {exc}")
            continue
        manifest["skills"][name] = {
            "source": slug,
            "sourceUrl": source_url,
            "path": rel,
            "ref": ref,
            "license": "unknown",
        }
        added.append(name)
        print(f"added {name} -> {rel} @ {ref[:12]}  ({slug})")
    return problems, added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--add", metavar="SOURCE_URL", help="vendor new skills from this source")
    parser.add_argument("--skill", action="append", default=[], metavar="NAME", help="skill name to add (repeatable, with --add)")
    parser.add_argument("--update", action="store_true", help="re-pin each skill to its source's default branch, then sync")
    parser.add_argument("--check", action="store_true", help="report pins that are behind upstream; write nothing")
    parser.add_argument("--only", metavar="NAME", help="sync a single vendored skill")
    parser.add_argument("--list", action="store_true", help="list what is vendored and at which commit")
    parser.add_argument("--no-verify", action="store_true", help="skip check_skills.py after syncing")
    args = parser.parse_args()

    if args.add and not args.skill:
        print("--add needs at least one --skill NAME", file=sys.stderr)
        return 1
    if args.skill and not args.add:
        print("--skill only makes sense together with --add SOURCE_URL", file=sys.stderr)
        return 1

    manifest = load_manifest()
    manifest.setdefault("skills", {})

    problems: list[str] = []
    drift: list[str] = []
    license_warnings: list[str] = []

    with tempfile.TemporaryDirectory(prefix="sync-vendor-") as cache:
        added_set: set[str] = set()
        if args.add:
            problems, added = add_skills(args.add, args.skill, manifest, cache)
            save_manifest(manifest)
            if problems:
                for line in problems:
                    print(f"  ! {line}", file=sys.stderr)
                return 1
            # Sync only what was just added. Re-fetching every other source here would make a
            # one-skill addition depend on the network health of all of them.
            added_set = set(added)

        skills: dict = manifest["skills"]
        if not skills:
            print("skills/vendor/vendor.json lists no skills", file=sys.stderr)
            return 1

        if args.list:
            width = max(len(name) for name in skills)
            for name, entry in sorted(skills.items()):
                print(f"{name:<{width}}  {entry['ref'][:12]}  {entry['source']}  ({entry['path']})")
            return 0

        if args.only and args.only not in skills:
            print(f"{args.only} is not in skills/vendor/vendor.json", file=sys.stderr)
            return 1
        if args.only:
            selected = {args.only: skills[args.only]}
        elif added_set:
            selected = {name: skills[name] for name in sorted(added_set)}
        else:
            selected = skills

        for name, entry in sorted(selected.items()):
            try:
                head = resolve_head(entry["sourceUrl"])
            except RuntimeError as exc:
                problems.append(f"{name}: {exc}")
                continue

            if args.check:
                if head != entry["ref"]:
                    drift.append(
                        f"{name}: pinned {entry['ref'][:12]}, upstream {head[:12]} ({entry['source']})"
                    )
                continue

            if args.update and head != entry["ref"]:
                entry["ref"] = head

            try:
                checkout = ensure_checkout(entry["sourceUrl"], entry["ref"], cache)
            except RuntimeError as exc:
                problems.append(f"{name}: {exc}")
                continue

            src = os.path.normpath(os.path.join(checkout, entry["path"]))
            if not os.path.isdir(src):
                problems.append(f"{name}: {entry['path']} does not exist at {entry['ref'][:12]}")
                continue

            dst = os.path.join(VENDOR_DIR, name)
            copy_skill(src, dst)

            license_file = find_license(checkout, entry["path"])
            if license_file and os.path.dirname(license_file) != dst:
                shutil.copy2(license_file, os.path.join(dst, "LICENSE"))
            write_notice(dst, name, entry, license_file)
            if not license_file:
                # Not fatal: plenty of skills ship no license text, and that is upstream's
                # call. It is worth saying out loud before anyone redistributes the copy.
                license_warnings.append(
                    f"{name}: no license file upstream — confirm {entry.get('license')} by hand"
                )
            print(f"synced {name} @ {entry['ref'][:12]}  ({entry['source']})")

    if args.check:
        if drift:
            print("drift detected — run `python3 scripts/sync_vendor.py --update`:")
            for line in drift:
                print(f"  - {line}")
            return 1
        print(f"ok: all {len(selected)} vendored skills match their pinned commits")
        return 0

    if args.update and not problems:
        save_manifest(manifest)

    for line in license_warnings:
        print(f"  ? {line}")
    for line in problems:
        print(f"  ! {line}", file=sys.stderr)
    if problems:
        return 1

    if not args.no_verify:
        print()
        return verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
