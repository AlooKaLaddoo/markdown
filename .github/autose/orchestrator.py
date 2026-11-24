#!/usr/bin/env python3
"""AutoSE orchestrator: a deterministic state machine around the agents.

Subcommands (one per workflow job that needs logic):
  build    stages 1-4 (requirements, design, implementation, testing)   - no GitHub token
  release  stage 5 (push branch, open PR, run CI)                        - GitHub token, no agent
  review   stage 6 (independent reviewer)                                - no GitHub token
  route    post the review, update the state comment, dispatch the next round - GitHub token, no agent
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import checks  # noqa: E402
from agent import CONFIG, AgentResult, run_agent  # noqa: E402

PROMPTS = HERE / "prompts"
SKILL = HERE / "skills" / "requirements" / "SKILL.md"
BUDGET = CONFIG["budgets"]
STATE_MARKER = "<!-- autose-state -->"


# ----------------------------------------------------------------------------- helpers

def sh(cmd, cwd=None, check=True, **kw) -> str:
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, shell=isinstance(cmd, str), **kw)
    if check and p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {cmd}\n{p.stdout}\n{p.stderr}")
    return p.stdout.strip()


def variant_cfg(name: str) -> dict:
    return CONFIG["variants"].get(name or "main", {})


def untrusted_issue(issue: dict) -> str:
    body = {"number": issue.get("number"), "title": issue.get("title"), "author": (issue.get("author") or {}).get("login"),
            "body": issue.get("body")}
    return ("<untrusted_issue>\n" + json.dumps(body, indent=2, ensure_ascii=False) + "\n</untrusted_issue>")


def strip_fence(text: str) -> str:
    t = text.strip()
    m = re.match(r"^```(?:markdown|md)?\n(.*)\n```$", t, re.S)
    return (m.group(1) if m else t).strip() + "\n"


def tail(text: str, n: int = 6000) -> str:
    return text if len(text) <= n else "...(truncated)...\n" + text[-n:]


def prompt_files(*names: str) -> list[Path]:
    return [PROMPTS / "common.md", *[PROMPTS / n for n in names]]


class Run:
    """Per-run bookkeeping: artifacts, agent usage, stage history."""

    def __init__(self, out: Path, meta: dict):
        self.out = out
        (out / "transcripts").mkdir(parents=True, exist_ok=True)
        self.state = {**meta, "status": "running", "stages": {}, "agents": [], "history": []}

    def log(self, stage: str, event: str, detail: str = ""):
        entry = {"t": time.strftime("%H:%M:%S"), "stage": stage, "event": event, "detail": detail[:500]}
        self.state["history"].append(entry)
        print(f"[{entry['t']}] {stage}: {event} {detail[:200]}", flush=True)
        self.save()

    def agent(self, stage: str, res: AgentResult):
        self.state["agents"].append({"stage": stage, **res.summary()})
        self.log(stage, f"agent {res.role} {'ok' if res.ok else 'FAILED'}",
                 f"{res.turns} turns, {res.seconds:.0f}s {res.error}")

    def write(self, name: str, text: str):
        (self.out / name).write_text(text)

    def save(self):
        (self.out / "state.json").write_text(json.dumps(self.state, indent=2))

    def finish(self, status: str, reason: str = ""):
        self.state["status"] = status
        self.state["reason"] = reason
        self.log("run", status, reason)


# ----------------------------------------------------------------------------- stage 1

JUDGE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["criteria"],
                "properties": {"criteria": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False, "required": ["id", "testable", "reason"],
                    "properties": {"id": {"type": "string"}, "testable": {"type": "boolean"},
                                   "reason": {"type": "string"}}}}}}


def stage_requirements(run: Run, issue: dict, cwd: Path) -> str | None:
    feedback = ""
    for attempt in range(1 + BUDGET["stage_retries"]):
        prompt = (f"Write spec.md for the GitHub issue below. Follow the output contract in your instructions.\n\n"
                  f"{untrusted_issue(issue)}\n")
        if feedback:
            prompt += f"\nYour previous spec.md failed the orchestrator's check. Fix exactly these problems:\n{feedback}\n"
        res = run_agent("analyst", prompt, cwd, run.out / "transcripts" / f"1-requirements-a{attempt + 1}.jsonl",
                        system_files=prompt_files("analyst_spec.md", ) + [SKILL])
        run.agent("requirements", res)
        spec = strip_fence(res.text) if res.text else ""
        chk = checks.check_spec(spec) if spec else checks.Check(False, [res.error or "agent returned no text"])
        if chk.ok:
            acs = checks.acceptance_criteria(checks.parse_spec(spec)[0])
            jprompt = ("Classify each acceptance criterion below as testable or not.\n\n"
                       + json.dumps([{k: ac.get(k) for k in ("id", "given", "when", "then")} for ac in acs], indent=2))
            jr = run_agent("judge", jprompt, cwd, run.out / "transcripts" / f"1-judge-a{attempt + 1}.jsonl",
                           system_files=[PROMPTS / "judge.md"], json_schema=JUDGE_SCHEMA)
            run.agent("requirements-judge", jr)
            verdicts = (jr.structured or {}).get("criteria", [])
            if not jr.ok or not verdicts:
                chk = checks.Check(False, [f"testability judge gave no verdict ({jr.error})"])
            else:
                bad = [f"{v['id']} is not testable: {v['reason']}" for v in verdicts if not v.get("testable")]
                missing = set(chk.data["acs"]) - {v["id"] for v in verdicts}
                bad += [f"{m} was not judged" for m in sorted(missing)]
                chk = checks.Check(not bad, bad, chk.data | {"judge": verdicts})
        run.state["stages"]["requirements"] = {"ok": chk.ok, "attempts": attempt + 1, "problems": chk.problems,
                                               "acceptance_criteria": chk.data.get("acs", [])}
        report = (f"\n\n---\n## Stage 1 check (orchestrator, attempt {attempt + 1})\n\n"
                  f"Result: **{'PASS' if chk.ok else 'FAIL'}**\n\n"
                  + "".join(f"- {p}\n" for p in chk.problems)
                  + "".join(f"- {v['id']}: testable={v['testable']} ({v['reason']})\n" for v in chk.data.get("judge", [])))
        run.write("spec.md", (spec or "# spec.md\n\n(no spec produced)\n") + report)
        if chk.ok:
            run.log("requirements", "check passed", f"{len(chk.data['acs'])} acceptance criteria")
            return spec
        feedback = "\n".join(f"- {p}" for p in chk.problems)
        run.log("requirements", "check failed", feedback)
    return None


# ----------------------------------------------------------------------------- stage 2

def stage_design(run: Run, spec: str, cwd: Path, extra: str = "", label: str = "") -> str | None:
    feedback = ""
    for attempt in range(1 + BUDGET["stage_retries"]):
        prompt = ("Write design.md for the specification below. Read ARCHITECTURE.md first. "
                  "Follow the output contract in your instructions.\n\n<spec>\n" + spec + "\n</spec>\n" + extra)
        if feedback:
            prompt += f"\nYour previous design.md failed the orchestrator's check. Fix exactly these problems:\n{feedback}\n"
        res = run_agent("analyst", prompt, cwd, run.out / "transcripts" / f"2-design{label}-a{attempt + 1}.jsonl",
                        system_files=prompt_files("analyst_design.md"))
        run.agent("design", res)
        design = strip_fence(res.text) if res.text else ""
        chk = checks.check_design(design, cwd) if design else checks.Check(False, [res.error or "agent returned no text"])
        run.state["stages"]["design"] = {"ok": chk.ok, "attempts": attempt + 1, "problems": chk.problems,
                                         "files": [r["file"] for r in chk.data.get("rows", [])]}
        report = (f"\n\n---\n## Stage 2 check (orchestrator, attempt {attempt + 1})\n\n"
                  f"Result: **{'PASS' if chk.ok else 'FAIL'}**\n\n" + "".join(f"- {p}\n" for p in chk.problems)
                  + "".join(f"- `{r['file']}` / `{r['symbol']}`: ok\n" for r in chk.data.get("rows", []) if chk.ok))
        run.write("design.md", (design or "# design.md\n\n(no design produced)\n") + report)
        if chk.ok:
            run.log("design", "check passed", ", ".join(run.state["stages"]["design"]["files"]))
            return design
        feedback = "\n".join(f"- {p}" for p in chk.problems)
        run.log("design", "check failed", feedback)
    return None


# ----------------------------------------------------------------------------- stages 3 + 4

def acceptance_test_path(issue_no: int) -> str:
    return f"tests/test_autose_issue_{issue_no}.py"


def stage_implement(run: Run, spec: str, design: str, impl: Path, base: str, feedback: str, attempt: int,
                    issue_no: int, writes_tests: bool, review_md: str, start: str) -> checks.Check:
    test_path = acceptance_test_path(issue_no)
    prompt = ("Implement the change described by the specification and the design below, in this repository.\n\n"
              f"<spec>\n{spec}\n</spec>\n\n<design>\n{design}\n</design>\n")
    if writes_tests:
        prompt += (f"\nAlso write the acceptance tests yourself in `{test_path}`: one or more unittest test methods per "
                   "acceptance criterion, named `test_ac_fr_xxx_yy_<what>` after the criterion id (AC-FR-001-02 -> "
                   "test_ac_fr_001_02_...).\n")
    else:
        prompt += (f"\nDo not create or edit `{test_path}`: a separate tester writes the acceptance tests from the spec. "
                   "You may add or update other tests.\n")
    if review_md:
        prompt += "\nAn independent reviewer requested changes on the previous round. Address its findings:\n" \
                  f"<review>\n{review_md}\n</review>\n"
    if feedback:
        prompt += f"\nThe previous attempt failed. Output of the failing check:\n<failure>\n{tail(feedback)}\n</failure>\n"
    res = run_agent("implementer", prompt, impl, run.out / "transcripts" / f"3-implementation-a{attempt}.jsonl",
                    system_files=prompt_files("implementer.md"))
    run.agent("implementation", res)
    def forbidden(f: str) -> bool:
        protected = f.startswith((".github/", ".claude/")) or f == "CLAUDE.md"
        return protected or (not writes_tests and f == test_path)
    # Compare with the round's starting commit: in round 2+ the acceptance tests already exist on the branch.
    reverted = checks.enforce_allowlist(impl, start, allowed=lambda f: True, forbidden=forbidden)
    checks.changed_files(impl, base)  # also drops sandbox placeholder files relative to the base
    if reverted:
        run.log("implementation", "reverted out-of-scope changes", ", ".join(reverted))
    chk = checks.check_build(impl, base)
    chk.data["reverted"] = reverted
    chk.data["agent_error"] = res.error
    return chk


def stage_write_tests(run: Run, spec: str, clean: Path, base: str, issue_no: int, ac_ids: list[str]) -> checks.Check:
    test_path = acceptance_test_path(issue_no)
    feedback = ""
    chk = checks.Check(False, ["tester did not run"])
    for attempt in range(1 + BUDGET["stage_retries"]):
        prompt = (f"Write the acceptance tests for the specification below into `{test_path}`.\n\n<spec>\n{spec}\n</spec>\n"
                  f"\nAcceptance criteria to cover: {', '.join(ac_ids)}\n")
        if feedback:
            prompt += f"\nYour previous test file failed the orchestrator's check:\n{feedback}\n"
        res = run_agent("tester", prompt, clean, run.out / "transcripts" / f"4-tests-a{attempt + 1}.jsonl",
                        system_files=prompt_files("tester.md"))
        run.agent("testing", res)
        reverted = checks.enforce_allowlist(clean, base, allowed=lambda f: f == test_path, forbidden=lambda f: False)
        if reverted:
            run.log("testing", "reverted out-of-scope changes by tester", ", ".join(reverted))
        chk = checks.check_acceptance_tests(clean / test_path, ac_ids)
        if chk.ok:
            return chk
        feedback = "\n".join(f"- {p}" for p in chk.problems)
        run.log("testing", "acceptance test check failed", feedback)
    return chk


def write_test_report(run: Run, issue_no: int, ac_chk: checks.Check | None, on_base: dict | None, attempts: list[dict],
                      final: dict | None, baseline: dict):
    lines = [f"# test_report.md (issue #{issue_no}, round {run.state['round']})", "",
             f"Existing suite on the base commit: **{baseline['status']}** ({baseline['ran']} tests)", ""]
    if ac_chk:
        lines += ["## Acceptance criteria → tests", "", "| Acceptance criterion | Tests |", "|---|---|"]
        lines += [f"| {ac} | {', '.join(t) or '**none**'} |" for ac, t in ac_chk.data.get("mapping", {}).items()]
        lines.append("")
    if on_base:
        lines += [f"New acceptance tests on the *base* commit (they should fail for a bug/feature): "
                  f"**{on_base['status']}** ({on_base['ran']} tests)", ""]
    lines += ["## Attempts", "", "| # | Build | Full suite | Note |", "|---|---|---|---|"]
    for a in attempts:
        lines.append(f"| {a['n']} | {'pass' if a['build'] else 'FAIL'} | {a.get('suite', '-')} | {a.get('note', '')} |")
    lines.append("")
    if final:
        lines += [f"## Final full run: **{final['status']}** ({final['ran']} tests)", "",
                  "```", tail(final["output"], 3000), "```"]
    run.write("test_report.md", "\n".join(lines) + "\n")


def build(args):
    out = Path(args.out)
    issue = json.loads(Path(args.issue_json).read_text())
    issue_no = int(args.issue)
    var = variant_cfg(args.variant)
    run = Run(out, {"issue": issue_no, "round": int(args.round), "from_stage": args.from_stage,
                    "variant": args.variant or "main", "base_sha": args.base_sha, "start_sha": args.start_sha or args.base_sha})
    work = Path(args.work)
    impl, clean = work / "impl", work / "clean"
    repo = Path(args.repo)
    for wt, ref in ((impl, args.start_sha or args.base_sha), (clean, args.base_sha)):
        if wt.exists():
            sh(["git", "worktree", "remove", "--force", str(wt)], cwd=repo, check=False)
        sh(["git", "worktree", "prune"], cwd=repo, check=False)  # idempotent on re-runs
        sh(["git", "worktree", "add", "-f", "--detach", str(wt), ref], cwd=repo)
    # The orchestrator's own code lives on master; agents must never see or edit it in the worktrees.
    base = args.base_sha
    prev = Path(args.prev_dir) if args.prev_dir else None
    review_md = (prev / "review.md").read_text() if prev and (prev / "review.md").exists() else ""

    baseline = checks.run_suite(clean)
    run.state["baseline"] = {k: baseline[k] for k in ("status", "ran")}
    run.log("setup", "baseline suite", baseline["status"])

    # ---- stage 1
    if args.from_stage == "requirements":
        spec = stage_requirements(run, issue, clean)
        if spec is None:
            run.finish("failed", "stage 1 (requirements) check failed; see spec.md")
            return
    else:
        spec = (prev / "spec.md").read_text().split("\n---\n## Stage 1 check")[0]
        run.write("spec.md", (prev / "spec.md").read_text())
        run.log("requirements", "reused from previous round")
    ac_ids = checks.acceptance_criteria(checks.parse_spec(spec)[0])
    ac_ids = [str(a.get("id")) for a in ac_ids]

    # ---- stage 2
    design_extra = ""
    if review_md and args.from_stage == "design":
        design_extra = ("\nAn independent reviewer rejected the previous approach. Revise the design to address it:\n"
                        f"<review>\n{review_md}\n</review>\n")
    if args.from_stage in ("requirements", "design"):
        design = stage_design(run, spec, impl, design_extra)
        if design is None:
            run.finish("failed", "stage 2 (design) check failed; see design.md")
            return
    else:
        design = (prev / "design.md").read_text().split("\n---\n## Stage 2 check")[0]
        run.write("design.md", (prev / "design.md").read_text())
        run.log("design", "reused from previous round")

    # ---- stages 3 + 4 with retries
    writes_tests = bool(var.get("skip_tester"))
    test_path = acceptance_test_path(issue_no)
    # Reuse the branch's acceptance tests only when the spec is reused too (a new spec has new AC ids).
    tests_exist_on_branch = (impl / test_path).exists() and args.from_stage != "requirements"
    ac_chk, on_base, attempts, final = None, None, [], None
    impl_review = review_md if args.from_stage == "implementation" else ""
    feedback, n, revisions = "", 0, 0
    while True:
        for _ in range(BUDGET["impl_attempts_per_design"]):
            n += 1
            bchk = stage_implement(run, spec, design, impl, base, feedback, n, issue_no, writes_tests, impl_review,
                                   args.start_sha or base)
            agent_error = bchk.data.get("agent_error") or ""
            if "limit" in agent_error.lower() or "budget" in agent_error.lower():
                # ADR-009: an implementer that never produced a successful result because a usage/budget limit
                # stopped it ends the run, instead of letting the previous round's code pass the checks again.
                run.state["stages"]["implementation"] = {"ok": False, "attempts": n, "problems": [agent_error]}
                write_test_report(run, issue_no, ac_chk, on_base, attempts, None, baseline)
                run.finish("failed", f"stage 3: implementer stopped by a limit: {agent_error[:200]}")
                return
            attempt = {"n": n, "build": bchk.ok, "note": "; ".join(bchk.problems)}
            attempts.append(attempt)
            run.state["stages"]["implementation"] = {"ok": bchk.ok, "attempts": n, "problems": bchk.problems,
                                                     "files": bchk.data.get("files", [])}
            if not bchk.ok:
                feedback = "Build check failed:\n" + "\n".join(bchk.problems) + "\n" + bchk.data.get("log", "")
                run.log("implementation", "build check failed", "; ".join(bchk.problems))
                continue
            run.log("implementation", "build check passed", ", ".join(bchk.data["files"]))
            # stage 4a: acceptance tests (written once, blind to the implementation)
            if ac_chk is None:
                if writes_tests:
                    ac_chk = checks.check_acceptance_tests(impl / test_path, ac_ids)
                elif tests_exist_on_branch:
                    ac_chk = checks.check_acceptance_tests(impl / test_path, ac_ids)
                    run.log("testing", "reusing acceptance tests already on the branch")
                else:
                    ac_chk = stage_write_tests(run, spec, clean, base, issue_no, ac_ids)
                    if (clean / test_path).exists():
                        on_base = checks.run_suite(clean, pattern=Path(test_path).name)
                        run.log("testing", "new tests on base commit", on_base["status"])
                        shutil.copy(clean / test_path, impl / test_path)
                if not ac_chk.ok:
                    run.state["stages"]["testing"] = {"ok": False, "problems": ac_chk.problems}
                    if writes_tests:  # in this variant the implementer owns the test file: retry it
                        feedback = "Acceptance test check failed:\n" + "\n".join(ac_chk.problems)
                        attempt["note"] = "acceptance tests missing"
                        ac_chk = None
                        continue
                    write_test_report(run, issue_no, ac_chk, on_base, attempts, None, baseline)
                    run.finish("failed", "stage 4: the tester could not produce acceptance tests for every criterion")
                    return
            # stage 4b: full suite (old + new)
            suite = checks.run_suite(impl)
            attempt["suite"] = suite["status"]
            if suite["exit"] == 0:
                final = suite
                break
            feedback = "Full test suite failed (existing + acceptance tests):\n" + suite["output"]
            run.log("testing", "suite failed", suite["status"])
            if writes_tests:
                ac_chk = None  # re-check the implementer-owned tests after the next attempt
        if final:
            break
        if revisions < BUDGET["design_revisions_from_tests"] and attempts and attempts[-1]["build"]:
            revisions += 1
            run.log("design", "returning to design after failed implementation attempts")
            extra = ("\nThe previous design was implemented twice and the tests still failed. Revise the plan. "
                     f"Last failure:\n<failure>\n{tail(feedback, 3000)}\n</failure>\n")
            design = stage_design(run, spec, impl, extra, label=f"-rev{revisions}")
            if design is None:
                break
            continue
        break

    run.state["stages"]["testing"] = {"ok": bool(final), "attempts": n,
                                      "suite": final["status"] if final else attempts[-1].get("suite", "not run")}
    write_test_report(run, issue_no, ac_chk, on_base, attempts, final or (checks.run_suite(impl) if attempts and attempts[-1]["build"] else None), baseline)
    sh(["git", "add", "-A"], cwd=impl)
    run.write("diff.patch", sh(["git", "diff", "--cached", "--binary", "--src-prefix=a/", "--dst-prefix=b/", base], cwd=impl) + "\n")
    if not final:
        run.finish("failed", f"stage 3/4: no passing implementation after {n} attempts and {revisions} design revision(s)")
        return
    run.finish("passed")


# ----------------------------------------------------------------------------- stage 6

VERDICT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["issue_asks", "checklist", "findings", "commands_run", "verdict", "route", "summary"],
    "properties": {
        "issue_asks": {"type": "array", "items": {"type": "string"}},
        "checklist": {"type": "object", "additionalProperties": False,
                      "required": ["addresses_every_issue_point", "existing_tests_pass", "own_probe_done",
                                   "no_regression_found", "fits_codebase_design", "no_out_of_scope_changes"],
                      "properties": {k: {"type": "boolean"} for k in
                                     ["addresses_every_issue_point", "existing_tests_pass", "own_probe_done",
                                      "no_regression_found", "fits_codebase_design", "no_out_of_scope_changes"]}},
        "findings": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["severity", "file", "line", "problem", "evidence"],
            "properties": {"severity": {"type": "string", "enum": ["blocker", "major", "minor"]},
                           "file": {"type": "string"}, "line": {"type": "integer"},
                           "problem": {"type": "string"}, "evidence": {"type": "string"}}}},
        "commands_run": {"type": "array", "items": {"type": "string"}},
        "verdict": {"type": "string", "enum": ["approve", "request_changes"]},
        "route": {"type": "string", "enum": ["none", "design", "implementation"]},
        "summary": {"type": "string"}}}


def validate_verdict(v: dict | None) -> dict:
    """The route decision is made here, in code, from the reviewer's structured output."""
    if not v:
        return {"final": "inconclusive", "route": "none", "why": "reviewer returned no valid verdict"}
    blocking = [f for f in v["findings"] if f["severity"] in ("blocker", "major") and f["evidence"].strip()]
    failed_items = [k for k, ok in v["checklist"].items() if not ok]
    if blocking:
        route = v["route"] if v["route"] != "none" else "implementation"
        return {"final": "request_changes", "route": route,
                "why": f"{len(blocking)} blocker/major finding(s) with evidence"}
    if not failed_items:
        why = "every checklist item is true and there is no blocker/major finding"
        if v["verdict"] != "approve":
            why += " (the reviewer asked for changes, but only with minor findings)"
        return {"final": "approve", "route": "none", "why": why}
    # No evidence-backed problem, but the reviewer could not confirm the change: never turn that into an approval.
    return {"final": "inconclusive", "route": "none",
            "why": f"no blocker/major finding with evidence, but checklist items are false: {failed_items}"}


def render_review(v: dict | None, decision: dict, res: AgentResult, meta: dict) -> str:
    icon = {"approve": "✅ APPROVE", "request_changes": "❌ REQUEST CHANGES", "inconclusive": "⚠️ INCONCLUSIVE"}
    lines = [f"## AutoSE independent review: {icon[decision['final']]}", "",
             f"Reviewer: `{meta['model']}` (variant `{meta['variant']}`), fresh context: issue + diff + repository at "
             f"`{meta['head_sha'][:10]}`; no access to the spec, design, test report or implementer transcript.", ""]
    if v:
        lines += [f"**Summary.** {v['summary']}", "", "**What the issue asks for** (listed before reading the diff):"]
        lines += [f"- {a}" for a in v["issue_asks"]] + ["", "**Checklist**", ""]
        lines += [f"- [{'x' if ok else ' '}] {k.replace('_', ' ')}" for k, ok in v["checklist"].items()]
        lines += ["", "**Findings**", ""]
        if v["findings"]:
            lines += ["| Severity | Location | Problem | Evidence |", "|---|---|---|---|"]
            for f in v["findings"]:
                esc = lambda s: s.replace("|", "\\|").replace("\n", " ")  # noqa: E731
                lines.append(f"| {f['severity']} | `{f['file']}:{f['line']}` | {esc(f['problem'])} | {esc(f['evidence'])} |")
        else:
            lines.append("None.")
        lines += ["", "**Commands the reviewer ran**", ""] + [f"- `{c}`" for c in v["commands_run"][:30]]
        lines += ["", f"Reviewer's own verdict: `{v['verdict']}`, proposed route: `{v['route']}`."]
    else:
        lines.append(f"The reviewer did not return a valid verdict: {res.error}")
    lines += ["", f"**Orchestrator decision:** `{decision['final']}` → route `{decision['route']}` ({decision['why']}).",
              "", "_A human maintainer decides whether to merge. The workflow never merges._"]
    return "\n".join(lines) + "\n"


def review(args):
    out = Path(args.out)
    (out / "transcripts").mkdir(parents=True, exist_ok=True)
    var = variant_cfg(args.variant)
    model = var.get("reviewer_model") or CONFIG["roles"]["reviewer"]["model"]
    prompt_name = var.get("reviewer_prompt", "reviewer.md")
    issue = json.loads(Path(args.issue_json).read_text())
    diff = Path(args.diff).read_text()
    pr_dir = Path(args.pr_dir)
    head = sh(["git", "rev-parse", "HEAD"], cwd=pr_dir)
    prompt = ("Review this pull request. The issue it claims to resolve and its diff (against the base branch) are "
              "below. The repository at the pull request's head commit is your working directory.\n\n"
              f"{untrusted_issue(issue)}\n\n<untrusted_diff>\n{tail(diff, 60000)}\n</untrusted_diff>\n")
    if var.get("reviewer_sees_pr_description") and args.pr_body and Path(args.pr_body).exists():
        prompt += f"\n<pr_description>\n{Path(args.pr_body).read_text()}\n</pr_description>\n"
    res = run_agent("reviewer", prompt, pr_dir, out / "transcripts" / "6-review.jsonl",
                    system_files=prompt_files(prompt_name), model=model, json_schema=VERDICT_SCHEMA)
    v = res.structured if res.ok else None
    decision = validate_verdict(v)
    meta = {"model": model, "variant": args.variant or "main", "head_sha": head}
    (out / "review.md").write_text(render_review(v, decision, res, meta))
    (out / "verdict.json").write_text(json.dumps({"reviewer": v, "decision": decision, "agent": res.summary(),
                                                  **meta}, indent=2))
    print(json.dumps(decision))


# ----------------------------------------------------------------------------- stage 5

def gh(*a, check=True) -> str:
    return sh(["gh", *a], check=check)


def pr_body(art: Path, issue_no: int, run_url: str, round_no: int) -> str:
    spec = (art / "spec.md").read_text().split("\n---\n## Stage 1 check")[0]
    frs = checks.parse_spec(spec)[0]
    design = (art / "design.md").read_text().split("\n---\n## Stage 2 check")[0]
    rows = checks.parse_change_plan(design)
    tr = (art / "test_report.md").read_text()
    final = re.search(r"## Final full run: \*\*(.*?)\*\* \((\d+) tests\)", tr)
    lines = [f"Closes #{issue_no}", "", f"_Opened by the AutoSE workflow (round {round_no}). "
             f"All stage artifacts (spec.md, design.md, diff.patch, test_report.md, agent transcripts) are on the "
             f"[workflow run]({run_url})._", "", "### Requirements (from spec.md)", ""]
    for fr in frs:
        lines.append(f"- **{fr.get('id')}** {fr.get('title', '')}: {fr.get('statement', '')}")
        for ac in fr.get("acceptance_criteria") or []:
            lines.append(f"  - `{ac.get('id')}` given {ac.get('given')}, when {ac.get('when')}, then {ac.get('then')}")
    lines += ["", "### Change plan (from design.md)", "", "| File | Symbol | Change |", "|---|---|---|"]
    lines += [f"| `{r['file']}` | `{r['symbol']}` | {r['change']} |" for r in rows]
    lines += ["", "### Tests (from test_report.md)", "",
              f"Full suite with the new acceptance tests: **{final.group(1)}** ({final.group(2)} tests)" if final else tr[:500]]
    return "\n".join(lines) + "\n"


def release(args):
    art = Path(args.art)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    issue_no = int(args.issue)
    variant = args.variant or "main"
    # Experiment variants get their own branch and PR so they never mix with the main design's PR.
    branch = f"autose/issue-{issue_no}" + ("" if variant == "main" else f"-{variant}")
    info = {"branch": branch, "variant": variant, "ok": False}
    try:
        exists = sh(["git", "ls-remote", "--heads", "origin", branch])
        if exists:
            sh(["git", "fetch", "-q", "origin", branch])
            parent = sh(["git", "rev-parse", "FETCH_HEAD"])
        else:
            parent = args.base_sha
        sh(["git", "checkout", "-q", "--detach", parent])
        sh(["git", "read-tree", "--reset", "-u", args.base_sha])
        sh(["git", "apply", "--index", "--binary", str(art / "diff.patch")])
        title = json.loads(Path(args.issue_json).read_text())["title"]
        sh(["git", "-c", "user.name=autose-bot", "-c", "user.email=autose-bot@users.noreply.github.com", "commit",
            "-q", "-m", f"autose: {title} (#{issue_no}, round {args.round})"])
        head = sh(["git", "rev-parse", "HEAD"])
        sh(["git", "push", "-q", "origin", f"HEAD:refs/heads/{branch}"])
        info["head_sha"] = head
        body = pr_body(art, issue_no, args.run_url, int(args.round))
        (out / "pr.md").write_text(body)
        prs = json.loads(gh("pr", "list", "--head", branch, "--state", "open", "--json", "number,url"))
        if prs:
            info["pr"], info["url"] = prs[0]["number"], prs[0]["url"]
            gh("pr", "edit", str(info["pr"]), "--body-file", str(out / "pr.md"))
        else:
            url = gh("pr", "create", "--base", args.base_branch, "--head", branch,
                     "--title", f"autose: {title} (#{issue_no})" + ("" if variant == "main" else f" [{variant}]"),
                     "--body-file", str(out / "pr.md"))
            info["url"] = url
            info["pr"] = int(url.rstrip("/").split("/")[-1])
        # Pushes made with GITHUB_TOKEN do not trigger other workflows, so CI is dispatched explicitly.
        t0 = time.time()
        gh("workflow", "run", "ci.yml", "--ref", branch)
        run_id = None
        for _ in range(40):
            time.sleep(6)
            runs = json.loads(gh("run", "list", "--workflow", "ci.yml", "--branch", branch, "--event",
                                 "workflow_dispatch", "--json", "databaseId,headSha,url", "-L", "10"))
            match = [r for r in runs if r["headSha"] == head]
            if match:
                run_id, info["ci_url"] = match[0]["databaseId"], match[0]["url"]
                break
        if run_id is None:
            raise RuntimeError("CI run for the pushed commit did not start")
        subprocess.run(["gh", "run", "watch", str(run_id), "--exit-status", "--interval", "10"],
                       capture_output=True, timeout=1200)
        info["ci"] = json.loads(gh("run", "view", str(run_id), "--json", "conclusion"))["conclusion"]
        state = json.loads(gh("pr", "view", str(info["pr"]), "--json", "state"))["state"]
        info["pr_state"] = state
        info["ci_seconds"] = round(time.time() - t0)
        info["ok"] = state == "OPEN" and info["ci"] == "success"
        if not info["ok"]:
            info["reason"] = f"stage 5 check failed: PR state {state}, CI {info['ci']}"
    except Exception as e:  # noqa: BLE001 - every failure is reported in pr.md and stops the run
        info["reason"] = f"stage 5 failed: {e}"
    with (out / "pr.md").open("a") as f:
        f.write(f"\n---\n## Stage 5 check (orchestrator)\n\n- PR: {info.get('url', 'not opened')}\n"
                f"- PR state: {info.get('pr_state', '?')}\n- CI (`ci.yml` on `{branch}`): {info.get('ci', 'not run')} "
                f"{info.get('ci_url', '')}\n- Result: **{'PASS' if info['ok'] else 'FAIL'}** {info.get('reason', '')}\n")
    (out / "release.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info))
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"ok={'true' if info['ok'] else 'false'}\npr={info.get('pr', '')}\nhead_sha={info.get('head_sha', '')}\n")


# ----------------------------------------------------------------------------- routing

def upsert_state_comment(repo: str, issue_no: int, entry: dict):
    comments = json.loads(gh("api", f"repos/{repo}/issues/{issue_no}/comments", "--paginate"))
    mine = [c for c in comments if STATE_MARKER in c["body"]]
    state = {"issue": issue_no, "rounds": []}
    if mine:
        m = re.search(r"```json\n(.*?)\n```", mine[-1]["body"], re.S)
        if m:
            state = json.loads(m.group(1))
    state["rounds"] = [r for r in state["rounds"] if r.get("run_id") != entry["run_id"]] + [entry]
    rows = ["| Round | Run | From stage | Build | PR | CI | Review | Next |", "|---|---|---|---|---|---|---|---|"]
    for r in state["rounds"]:
        rows.append(f"| {r['round']} | [{r['run_id']}]({r['run_url']}) | {r['from_stage']}{'' if r.get('variant', 'main') == 'main' else ' (' + r['variant'] + ')'} | {r['build']} | "
                    f"{('#' + str(r['pr'])) if r.get('pr') else '-'} | {r.get('ci', '-')} | {r.get('review', '-')} | "
                    f"{r['next']} |")
    body = (f"{STATE_MARKER}\n### AutoSE status for #{issue_no}\n\n" + "\n".join(rows) + "\n\n"
            "<details><summary>machine-readable state</summary>\n\n```json\n" + json.dumps(state, indent=2)
            + "\n```\n</details>\n")
    tmp = Path("state_comment.md")
    tmp.write_text(body)
    if mine:
        gh("api", "-X", "PATCH", f"repos/{repo}/issues/comments/{mine[-1]['id']}", "-F", f"body=@{tmp}")
    else:
        gh("issue", "comment", str(issue_no), "--body-file", str(tmp))


def route(args):
    repo = os.environ["GITHUB_REPOSITORY"]
    build_dir, rel_dir, rev_dir = Path(args.build_dir), Path(args.release_dir), Path(args.review_dir)
    bstate = json.loads((build_dir / "state.json").read_text()) if (build_dir / "state.json").exists() else {}
    rel = json.loads((rel_dir / "release.json").read_text()) if (rel_dir / "release.json").exists() else {}
    verdict = json.loads((rev_dir / "verdict.json").read_text()) if (rev_dir / "verdict.json").exists() else {}
    rnd = int(args.round)
    pr = rel.get("pr") or (int(args.pr) if args.pr else None)
    entry = {"round": rnd, "run_id": args.run_id, "run_url": args.run_url, "from_stage": args.from_stage,
             "variant": args.variant or "main", "build": bstate.get("status", "skipped" if args.mode == "review" else "not run"),
             "pr": pr, "ci": rel.get("ci", "-"), "review": verdict.get("decision", {}).get("final", "-"), "next": "stop"}
    decision = verdict.get("decision")
    if decision and pr:
        gh("pr", "review", str(pr), "--comment", "--body-file", str(rev_dir / "review.md"))
    if args.mode != "full":
        entry["next"] = "stop (review-only run)"
    elif bstate.get("status") == "failed":
        entry["next"] = "stop: " + bstate.get("reason", "")
        msg = (f"AutoSE stopped in round {rnd}: {bstate.get('reason', '')}\n\nSee the artifacts of "
               f"[run {args.run_id}]({args.run_url}).")
        spec_file = build_dir / "spec.md"
        if spec_file.exists():
            qs = re.findall(r"^\s*[-*|]?\s*\**(Q-\d{3})\**[:|]?\s*(.+)$", spec_file.read_text(), re.M)
            if qs:
                msg += "\n\nOpen questions from the requirements stage:\n" + "\n".join(f"- **{q}** {t}" for q, t in qs[:10])
        Path("stop.md").write_text(msg)
        gh("issue", "comment", args.issue, "--body-file", "stop.md")
    elif rel and not rel.get("ok"):
        entry["next"] = "stop: " + rel.get("reason", "release failed")
    elif decision and decision["final"] == "request_changes":
        if rnd <= BUDGET["max_review_sendbacks"]:
            nxt = rnd + 1
            entry["next"] = f"round {nxt} from {decision['route']}"
            gh("workflow", "run", "autose.yml", "--ref", args.default_branch, "-f", f"issue={args.issue}",
               "-f", f"round={nxt}", "-f", f"from_stage={decision['route']}", "-f", f"prev_run_id={args.run_id}",
               "-f", f"variant={args.variant or 'main'}", "-f", "mode=full")
        else:
            entry["next"] = "stop: review rounds used up; a human decides"
    elif decision and decision["final"] == "approve":
        entry["next"] = "stop: approved; a human decides whether to merge"
    elif decision:
        entry["next"] = "stop: review inconclusive; a human decides"
    if args.mode == "full":
        upsert_state_comment(repo, int(args.issue), entry)
    print(json.dumps(entry))


# ----------------------------------------------------------------------------- CLI

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    for a in ("issue", "issue-json", "round", "from-stage", "base-sha", "out", "work", "repo"):
        b.add_argument(f"--{a}", required=True)
    b.add_argument("--start-sha", default="")
    b.add_argument("--prev-dir", default="")
    b.add_argument("--variant", default="main")
    r = sub.add_parser("review")
    for a in ("issue-json", "pr-dir", "diff", "out"):
        r.add_argument(f"--{a}", required=True)
    r.add_argument("--variant", default="main")
    r.add_argument("--pr-body", default="")
    rl = sub.add_parser("release")
    for a in ("art", "out", "issue", "issue-json", "round", "base-sha", "base-branch", "run-url"):
        rl.add_argument(f"--{a}", required=True)
    rl.add_argument("--variant", default="main")
    ro = sub.add_parser("route")
    for a in ("issue", "round", "from-stage", "mode", "run-id", "run-url", "default-branch"):
        ro.add_argument(f"--{a}", required=True)
    for a in ("build-dir", "release-dir", "review-dir", "pr", "variant"):
        ro.add_argument(f"--{a}", default="")
    args = p.parse_args()
    {"build": build, "review": review, "release": release, "route": route}[args.cmd](args)


if __name__ == "__main__":
    main()
