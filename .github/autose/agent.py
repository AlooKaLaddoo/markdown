"""Run one agent as a headless Claude Code session (`claude -p`).

Each role gets its own model, tool list, pre-approved permissions, turn and budget limits
(config.json), and a scrubbed environment. The full event stream is saved as the transcript.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text())

# Only these variables reach the agent process. Everything else (GITHUB_TOKEN, ACTIONS_* ...) is dropped.
PASS_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "VIRTUAL_ENV", "pythonLocation", "PYTHONPATH",
            "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")


@dataclass
class AgentResult:
    role: str
    ok: bool
    text: str = ""
    structured: dict | None = None
    error: str = ""
    usage: dict = field(default_factory=dict)
    cost_usd: float = 0.0
    turns: int = 0
    seconds: float = 0.0
    transcript: str = ""

    def summary(self) -> dict:
        return {"role": self.role, "ok": self.ok, "error": self.error, "turns": self.turns,
                "seconds": round(self.seconds, 1), "cost_usd_nominal": round(self.cost_usd, 4),
                "input_tokens": self.usage.get("input_tokens", 0)
                + self.usage.get("cache_creation_input_tokens", 0)
                + self.usage.get("cache_read_input_tokens", 0),
                "output_tokens": self.usage.get("output_tokens", 0), "transcript": self.transcript}


def claude_bin() -> str:
    return os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "claude"


def run_agent(role: str, prompt: str, cwd: Path, transcript: Path, *, system_files: list[Path],
              model: str | None = None, json_schema: dict | None = None) -> AgentResult:
    cfg = CONFIG["roles"][role]
    transcript.parent.mkdir(parents=True, exist_ok=True)
    # Join the role's system prompt files into one file passed with --append-system-prompt-file.
    sys_file = transcript.with_suffix(".system.md")
    sys_file.write_text("\n\n".join(p.read_text() for p in system_files))
    cmd = [claude_bin(), "-p", "--output-format", "stream-json", "--verbose",
           "--model", model or cfg["model"],
           "--permission-mode", "dontAsk",
           "--strict-mcp-config", "--no-session-persistence",
           # Only user settings: a .claude/ directory or CLAUDE.md inside a PR cannot configure the agent.
           "--setting-sources", "user",
           "--max-turns", str(cfg["max_turns"]),
           "--max-budget-usd", str(cfg["budget_usd"]),
           "--append-system-prompt-file", str(sys_file),
           "--tools", ",".join(cfg["tools"])]
    if json_schema:
        cmd += ["--json-schema", json.dumps(json_schema)]
    if cfg["allowed"]:
        cmd += ["--allowedTools", *cfg["allowed"]]
    env = {k: v for k, v in os.environ.items() if k in PASS_ENV}
    env.update({"CLAUDE_CODE_SUBPROCESS_ENV_SCRUB": "1",
                "CLAUDE_CODE_EFFORT_LEVEL": cfg["effort"],
                "DISABLE_AUTOUPDATER": "1", "DISABLE_TELEMETRY": "1",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"})
    start = time.time()
    res = AgentResult(role=role, ok=False, transcript=transcript.name)
    try:
        with transcript.open("w") as out:
            proc = subprocess.run(cmd, input=prompt, text=True, cwd=cwd, env=env, stdout=out,
                                  stderr=subprocess.PIPE, timeout=CONFIG["budgets"]["agent_timeout_seconds"])
        stderr = proc.stderr[-2000:]
    except subprocess.TimeoutExpired:
        res.error = f"timeout after {CONFIG['budgets']['agent_timeout_seconds']} s"
        stderr = ""
    res.seconds = time.time() - start
    # A session can emit several result events: a background-task notification can start an extra turn after the
    # agent has finished (run 45423758931: the implementer finished in 16 turns, then an extra turn hit the plan
    # limit). Use the first successful result, and add up usage over all result events.
    results = []
    for line in transcript.read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            results.append(ev)
    if results:
        good = [r for r in results if r.get("subtype") == "success" and not r.get("is_error")]
        final = good[0] if good else results[-1]
        for r in results:
            for k, v in (r.get("usage") or {}).items():
                if isinstance(v, (int, float)):
                    res.usage[k] = res.usage.get(k, 0) + v
        res.cost_usd = max(r.get("total_cost_usd") or 0.0 for r in results)  # cumulative per session
        res.turns = sum(r.get("num_turns") or 0 for r in results)
        res.text = final.get("result") or ""
        res.structured = final.get("structured_output")
        if good:
            res.ok = True
        else:
            res.error = res.error or f"agent stopped: {final.get('subtype')} {str(final.get('result', ''))[:300]}"
    elif not res.error:
        res.error = f"no result event (exit {proc.returncode}): {stderr}"
    return res
