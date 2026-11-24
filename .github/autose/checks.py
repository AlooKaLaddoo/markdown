"""Deterministic stage checks. The orchestrator, not an agent, decides pass/fail from these."""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

AC_ID = re.compile(r"^AC-FR-(\d{3})-(\d{2})$")


@dataclass
class Check:
    ok: bool
    problems: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def text(self) -> str:
        return "PASS" if self.ok else "FAIL\n" + "\n".join(f"- {p}" for p in self.problems)


# ---------- stage 1: spec.md ----------

def parse_spec(spec: str) -> tuple[list[dict], list[str]]:
    """Return (functional requirements, parse problems) from the ```yaml blocks of spec.md."""
    frs, problems = [], []
    for i, block in enumerate(re.findall(r"```ya?ml\n(.*?)```", spec, re.S)):
        try:
            doc = yaml.safe_load(block)
        except yaml.YAMLError as e:
            problems.append(f"yaml block {i + 1} does not parse: {str(e).splitlines()[0]}")
            continue
        docs = doc if isinstance(doc, list) else [doc]
        for d in docs:
            if isinstance(d, dict) and str(d.get("id", "")).startswith("FR-"):
                frs.append(d)
    return frs, problems


def acceptance_criteria(frs: list[dict]) -> list[dict]:
    return [ac for fr in frs for ac in (fr.get("acceptance_criteria") or []) if isinstance(ac, dict)]


def check_spec(spec: str) -> Check:
    frs, problems = parse_spec(spec)
    if not frs:
        problems.append("no functional requirement (yaml block with id FR-xxx) found")
    for fr in frs:
        fid = fr.get("id")
        acs = fr.get("acceptance_criteria") or []
        if fr.get("readiness_status") == "BLOCKED_ON_CLARIFICATION":
            problems.append(f"{fid} is BLOCKED_ON_CLARIFICATION")
        if not acs:
            problems.append(f"{fid} has no acceptance criteria")
        for ac in acs:
            aid = str(ac.get("id", ""))
            if not AC_ID.match(aid):
                problems.append(f"{fid}: acceptance criterion id {aid!r} does not match AC-FR-xxx-yy")
            elif aid[3:9] != fid:
                problems.append(f"{aid} is listed under {fid}")
            for key in ("given", "when", "then"):
                if not str(ac.get(key, "")).strip():
                    problems.append(f"{aid}: empty '{key}'")
    ids = [str(ac.get("id")) for ac in acceptance_criteria(frs)]
    dups = {i for i in ids if ids.count(i) > 1}
    if dups:
        problems.append(f"duplicate acceptance criterion ids: {sorted(dups)}")
    blocked = "BLOCKED_ON_CLARIFICATION" in spec and not frs
    return Check(not problems, problems, {"frs": len(frs), "acs": ids, "blocked": blocked})


def test_name_for(ac_id: str) -> str:
    """AC-FR-001-02 -> test_ac_fr_001_02"""
    return "test_" + ac_id.lower().replace("-", "_")


# ---------- stage 2: design.md ----------

def parse_change_plan(design: str) -> list[dict]:
    m = re.search(r"^##+\s*Change plan\s*$(.*?)(?=^##\s|\Z)", design, re.S | re.M | re.I)
    if not m:
        return []
    rows = []
    for line in m.group(1).splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or set(cells[0]) <= set("-: ") or cells[0].lower() == "file":
            continue
        rows.append({"file": cells[0], "symbol": cells[1], "change": cells[2]})
    return rows


def _symbols(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names: set[str] = set()

    def visit(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(prefix + child.name)
                visit(child, prefix + child.name + ".")
            elif isinstance(child, (ast.Assign, ast.AnnAssign)) and not prefix:
                for t in getattr(child, "targets", [getattr(child, "target", None)]):
                    if isinstance(t, ast.Name):
                        names.add(t.id)
    visit(tree)
    return names


def check_design(design: str, repo: Path) -> Check:
    rows = parse_change_plan(design)
    problems = []
    if not rows:
        problems.append("no '## Change plan' table with rows `| file | symbol | change |` found")
    for r in rows:
        f, sym, change = r["file"], r["symbol"], r["change"].lower()
        is_new = change.startswith("new") or "(new)" in sym.lower() or change.startswith("add")
        path = repo / f
        if not path.exists():
            if not (change.startswith("new") or "(new)" in sym.lower()):
                problems.append(f"{f}: file does not exist and is not marked new")
            continue
        if f.startswith(".github/"):
            problems.append(f"{f}: the workflow may not change .github/")
        if not sym or sym in ("-", "n/a", "(module)") or not f.endswith(".py"):
            continue
        name = re.sub(r"\(new\)|\(\)", "", sym, flags=re.I).strip()
        try:
            known = _symbols(path)
        except SyntaxError:
            continue
        if name not in known and not is_new:
            problems.append(f"{f}: symbol {name!r} not found (mark it 'new' if it is to be created)")
    return Check(not problems, problems, {"rows": rows})


# ---------- stage 3: build ----------

def run(cmd: list[str] | str, cwd: Path, timeout: int = 900) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout, shell=isinstance(cmd, str))
    return p.returncode, (p.stdout + p.stderr)


# Claude Code's Bash sandbox (bubblewrap) creates empty placeholder files for sensitive paths in the working
# directory and leaves them behind (seen in run 45420334361, PR #11). They are never part of a change.
SANDBOX_STUBS = {".env", ".env.local", ".env.development", ".env.development.local", ".env.production",
                 ".env.production.local", ".env.test", ".env.test.local", ".gitmodules", ".npmrc", ".yarnrc",
                 ".yarnrc.yml", "bunfig.toml", "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
                 ".mcp.json", ".bashrc", ".profile", ".gitconfig"}


def changed_files(worktree: Path, base: str) -> list[str]:
    run(["git", "add", "-A"], worktree)
    _, out = run(["git", "diff", "--cached", "--name-only", "--diff-filter=A", base], worktree)
    for f in out.splitlines():
        p = worktree / f
        if "/" not in f and (f in SANDBOX_STUBS or f.startswith(".env")) and p.is_file() and p.stat().st_size == 0:
            run(["git", "rm", "-q", "-f", "--cached", f], worktree)
            p.unlink(missing_ok=True)
    _, out = run(["git", "diff", "--cached", "--name-only", base], worktree)
    return [l for l in out.splitlines() if l]


def enforce_allowlist(worktree: Path, base: str, allowed, forbidden) -> list[str]:
    """Revert every changed path that is not allowed. Returns the reverted paths."""
    reverted = []
    for f in changed_files(worktree, base):
        if forbidden(f) or not allowed(f):
            reverted.append(f)
            exists = run(["git", "cat-file", "-e", f"{base}:{f}"], worktree)[0] == 0
            if exists:
                run(["git", "checkout", base, "--", f], worktree)
            else:
                run(["git", "rm", "-q", "-f", "--cached", f], worktree)
                (worktree / f).unlink(missing_ok=True)
    run(["git", "add", "-A"], worktree)
    return reverted


def check_build(worktree: Path, base: str) -> Check:
    problems = []
    files = changed_files(worktree, base)
    src = [f for f in files if not f.startswith("tests/")]
    if not src:
        problems.append("the diff changes no source file")
    steps = [
        ([sys.executable, "-m", "pip", "install", "-q", "-e", ".[testing]"], "pip install -e ."),
        ([sys.executable, "-m", "compileall", "-q", "markdown"], "python -m compileall markdown"),
        ([sys.executable, "-c", "import markdown; markdown.markdown('# ok')"], "import markdown"),
    ]
    log = []
    for cmd, label in steps:
        code, out = run(cmd, worktree)
        log.append(f"$ {label}\n{out.strip()[-1500:]}\n(exit {code})")
        if code:
            problems.append(f"`{label}` failed")
            break
    return Check(not problems, problems, {"files": files, "log": "\n".join(log)})


# ---------- stage 4: tests ----------

def run_suite(worktree: Path, pattern: str = "test*.py") -> dict:
    code, out = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-p", pattern],
                    worktree, timeout=600)
    ran = re.search(r"Ran (\d+) tests?", out)
    status = re.findall(r"^(OK.*|FAILED.*)$", out, re.M)
    return {"exit": code, "ran": int(ran.group(1)) if ran else 0, "status": status[-1] if status else "no result",
            "output": out}


def check_acceptance_tests(test_file: Path, ac_ids: list[str]) -> Check:
    problems = []
    if not test_file.exists():
        return Check(False, [f"{test_file.name} was not written"])
    src = test_file.read_text()
    try:
        ast.parse(src)
    except SyntaxError as e:
        return Check(False, [f"{test_file.name} has a syntax error: {e}"])
    names = re.findall(r"def (test_\w+)", src)
    mapping = {}
    for ac in ac_ids:
        prefix = test_name_for(ac)
        hits = [n for n in names if n.startswith(prefix)]
        mapping[ac] = hits
        if not hits:
            problems.append(f"no test named {prefix}* for {ac}")
    return Check(not problems, problems, {"mapping": mapping, "tests": names})
