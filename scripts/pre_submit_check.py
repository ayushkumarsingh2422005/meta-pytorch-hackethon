#!/usr/bin/env python3
"""
Local pre-submission checks (mirrors hackathon checklist items you can run without Scaler).

From repo root:
    pip install -e ".[dev]"   # or: pip install openenv-core pyyaml
    python scripts/pre_submit_check.py
    python scripts/pre_submit_check.py --space-url https://your-space.hf.space

Checks:
  1. openenv.yaml parses and has >= 3 tasks, each with a non-empty grader string
  2. Imports root graders module and runs each canonical grader; scores in [0, 1]
  3. Optional: HTTP GET /tasks and POST /reset on --space-url (needs urllib)
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def check_openenv_yaml(root: Path) -> list[dict]:
    try:
        import yaml
    except ImportError:
        _fail("Install PyYAML: pip install pyyaml")

    path = root / "openenv.yaml"
    if not path.is_file():
        _fail(f"Missing {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        _fail("openenv.yaml must be a mapping")

    tasks = data.get("tasks") or []
    if not isinstance(tasks, list) or len(tasks) < 3:
        _fail(f"Need at least 3 tasks in openenv.yaml, got {len(tasks)}")

    with_grader: list[dict] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        gid = t.get("id")
        g = t.get("grader")
        if gid and g and isinstance(g, str) and ":" in g:
            with_grader.append(t)

    if len(with_grader) < 3:
        _fail(
            f"Need >= 3 tasks with string grader 'module:function', found {len(with_grader)}"
        )

    _ok(f"openenv.yaml: {len(tasks)} tasks, {len(with_grader)} with grader strings")
    for t in with_grader[:6]:
        print(f"       - id={t.get('id')!r} grader={t.get('grader')!r}")
    return with_grader


def check_graders_run(root: Path) -> None:
    sys.path.insert(0, str(root))
    try:
        mod = importlib.import_module("graders")
    except Exception as e:
        _fail(f"import graders failed: {e}")

    ids = getattr(mod, "PRIMARY_GRADER_TASK_IDS", None)
    if not ids or len(ids) < 3:
        _fail("graders.PRIMARY_GRADER_TASK_IDS must have 3 entries")

    reg = getattr(mod, "GRADERS", {})
    for tid in ids:
        if tid not in reg:
            _fail(f"graders.GRADERS missing key {tid!r}")
        fn = reg[tid]
        try:
            score = float(fn())
        except Exception as e:
            _fail(f"grader {tid}() raised: {e}")
        if not (0.0 <= score <= 1.0):
            _fail(f"grader {tid}() returned {score}, expected in [0, 1]")
        _ok(f"grader {tid}() -> {score:.4f} (in [0,1])")

    print("[OK]   All primary graders run and scores in [0.0, 1.0]")


def check_space_url(url: str) -> None:
    import urllib.error
    import urllib.request

    base = url.rstrip("/")
    for path, method, body in (
        ("/health", "GET", None),
        ("/reset", "POST", b"{}"),
        ("/tasks", "GET", None),
    ):
        req = urllib.request.Request(
            f"{base}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body else {},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                code = resp.status
                payload = resp.read().decode("utf-8", errors="replace")[:500]
        except urllib.error.HTTPError as e:
            _fail(f"{method} {path} -> HTTP {e.code}")
        except Exception as e:
            _fail(f"{method} {path} -> {e}")

        if code != 200:
            _fail(f"{method} {path} -> HTTP {code}")
        _ok(f"{method} {base}{path} -> 200")
        if path == "/tasks" and payload:
            try:
                j = json.loads(payload)
                twg = j.get("tasks_with_graders")
                if isinstance(twg, list):
                    n = len(twg)
                else:
                    n = twg if isinstance(twg, int) else j.get("count", 0)
                print(f"       /tasks tasks_with_graders (len)={n!r}")
            except json.JSONDecodeError:
                pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Local hackathon pre-submit checks")
    ap.add_argument(
        "--space-url",
        default="",
        help="HF Space base URL (e.g. https://user-space.hf.space) for /health /reset /tasks",
    )
    args = ap.parse_args()

    root = _repo_root()
    print(f"Repo: {root}\n")

    check_openenv_yaml(root)
    print()
    check_graders_run(root)
    print()

    if args.space_url.strip():
        print("Remote Space checks:")
        check_space_url(args.space_url.strip())
    else:
        print("(Skip remote: pass --space-url https://....hf.space to ping your Space)")

    print("\n[PASS] Local grader + openenv.yaml checks completed.")
    print("Also run: openenv validate")
    print("Also run: docker build -t corporate-expense-openenv:test .")


if __name__ == "__main__":
    main()
