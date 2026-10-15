#!/usr/bin/env python3
"""Hand prompts to Freebuff Desktop sessions through a gpt-6-luna Computer Use controller.

Freebuff has no headless mode, so a Codex model (Luna) drives the Freebuff Desktop window:
this script puts one prompt on the clipboard, asks Luna (via `codex app-server`) to open a new
Freebuff session with the requested model/effort, paste and send, and repeats per prompt.
Each prompt gets a header telling the Freebuff agent to write a `started/` marker first and a
`done/` marker last; `wait` blocks (no model tokens) until every `done/` marker exists.

Usage (from the workspace root):
    python tools/freebuff-dispatch/dispatch.py run    --run-dir evidence/freebuff-dispatch/<id>
    python tools/freebuff-dispatch/dispatch.py wait   --run-dir evidence/freebuff-dispatch/<id>
    python tools/freebuff-dispatch/dispatch.py status --run-dir evidence/freebuff-dispatch/<id>

`run` reads every `prompts/*.md` in the run dir (the file stem is the slot name).
Standard library only. Needs the Codex desktop app running (it owns the Computer Use pipe).
"""
from __future__ import annotations

import argparse
import json
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

VERSION = "1.1.0"
WORKSPACE = Path(__file__).resolve().parents[2]
# Apps the controller may be granted through the Computer Use approval prompt. Nothing else.
APPROVED_APPS = ("freebuff",)


def rel(path: Path) -> str:
    return path.resolve().relative_to(WORKSPACE).as_posix()


def slots(run_dir: Path) -> list[str]:
    return sorted(p.stem for p in (run_dir / "prompts").glob("*.md"))


def header(run_dir: Path, slot: str) -> str:
    r = rel(run_dir)
    return (
        f"[freebuff-dispatch {run_dir.name} slot {slot}]\n"
        f"Workspace root: {WORKSPACE} - work from there; every path below is relative to it.\n"
        f"FIRST ACTION, before anything else: create the file {r}/started/{slot}.txt containing the "
        f"current date and time.\n"
        f"LAST ACTION, only when you are completely finished (or have hit a blocker you cannot work "
        f"around): write {r}/done/{slot}.json in one go, as valid JSON with the keys "
        f'"slot", "status" ("READY", "PARTIAL" or "BLOCKED"), "summary", "changed_files" (list), '
        f'"installer_notes" (exact build/packaging steps and flags the installer needs), '
        f'"manual_checks" (numbered console checks for the user, with the vanilla control), '
        f'"unverified" (list). Nobody is watching this session and nobody can answer questions: '
        f"another agent is blocked until that file exists, so do not stop, do not ask, and do not "
        f"write it early. Writing that file is part of the task: do not send your final message "
        f"before it exists.\n"
        f"This prompt is also saved at {r}/rendered/{slot}.md.\n\n"
    )


def title(run_dir: Path, slot: str) -> str:
    first = (run_dir / "prompts" / f"{slot}.md").read_text(encoding="utf-8").splitlines()[0]
    return first.lstrip("# ").removeprefix("Task:").strip()


def render(run_dir: Path, slot: str) -> str:
    """Header + prompt, with {{COMMON}} (run dir's common.md), {{SLOT}} and {{OTHERS}} filled in."""
    body = (run_dir / "prompts" / f"{slot}.md").read_text(encoding="utf-8")
    common = run_dir / "common.md"
    body = body.replace("{{COMMON}}", common.read_text(encoding="utf-8") if common.exists() else "")
    others = "; ".join(f"({s}) {title(run_dir, s)}" for s in slots(run_dir) if s != slot)
    body = body.replace("{{OTHERS}}", others or "none").replace("{{SLOT}}", slot)
    return header(run_dir, slot) + body


def set_clipboard(text: str, scratch: Path) -> None:
    scratch.write_text(text, encoding="utf-8")
    ps = (
        f"$t = Get-Content -Raw -Encoding UTF8 -LiteralPath '{scratch}'; Set-Clipboard -Value $t; "
        f"$b = Get-Clipboard -Raw; if ($b.Length -lt 20) {{ exit 3 }}"
    )
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], check=True)


class AppServer:
    """Minimal line-delimited JSON-RPC client for `codex app-server` on stdio."""

    def __init__(self, log: Path):
        exe = shutil.which("codex")
        if not exe:
            raise SystemExit("codex CLI not found on PATH")
        self.proc = subprocess.Popen(
            [exe, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=WORKSPACE, encoding="utf-8", errors="replace", bufsize=1,
        )
        self.log = log.open("a", encoding="utf-8")
        self.inbox: queue.Queue = queue.Queue()
        self.next_id = 0
        threading.Thread(target=self._pump, args=(self.proc.stdout, "recv"), daemon=True).start()
        threading.Thread(target=self._pump, args=(self.proc.stderr, "stderr"), daemon=True).start()

    def _write_log(self, kind: str, payload) -> None:
        self.log.write(json.dumps({"t": time.strftime("%H:%M:%S"), "dir": kind, "msg": payload}) + "\n")
        self.log.flush()

    def _pump(self, stream, kind: str) -> None:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            if kind == "stderr":
                self._write_log(kind, line)
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                self._write_log("garbage", line)
                continue
            # Streaming deltas are noise in the log; everything else is kept.
            if not str(msg.get("method", "")).endswith(("/delta", "Delta")):
                self._write_log(kind, msg)
            self.inbox.put(msg)
        self.inbox.put(None)

    def send(self, msg: dict) -> None:
        self._write_log("send", msg)
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def request(self, method: str, params: dict, timeout: float = 120) -> dict:
        self.next_id += 1
        rid = self.next_id
        self.send({"id": rid, "method": method, "params": params})
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = self.inbox.get(timeout=1)
            except queue.Empty:
                continue
            if msg is None:
                raise SystemExit("codex app-server exited")
            if msg.get("id") == rid and "method" not in msg:
                if "error" in msg:
                    raise SystemExit(f"{method} failed: {msg['error']}")
                return msg.get("result", {})
            if "method" in msg and "id" in msg:
                self.answer(msg)
        raise SystemExit(f"{method} timed out")

    def answer(self, msg: dict) -> None:
        """Answer a server->client request. Only a Freebuff app-access prompt is ever accepted."""
        method, params = msg["method"], msg.get("params", {})
        if method == "mcpServer/elicitation/request":
            ok, why = approve(params)
            print(f"  elicitation: {why} -> {'accept' if ok else 'decline'}", flush=True)
            result = {"action": "accept", "content": {}} if ok else {"action": "decline"}
        elif method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval"):
            result = {"decision": "decline"}
        elif method in ("execCommandApproval", "applyPatchApproval"):
            result = {"decision": "denied"}
        elif method == "item/permissions/requestApproval":
            result = {"permissions": {}}
        elif method == "item/tool/requestUserInput":
            result = {"answers": {}}
        else:
            self.send({"id": msg["id"], "error": {"code": -32601, "message": "not supported"}})
            return
        self.send({"id": msg["id"], "result": result})

    def turn(self, thread_id: str, text: str, effort: str, timeout: float) -> tuple[str, str]:
        """Run one turn; return (status, last agent message)."""
        self.request("turn/start", {"threadId": thread_id, "effort": effort,
                                    "input": [{"type": "text", "text": text}]})
        last, deadline = "", time.time() + timeout
        while time.time() < deadline:
            try:
                msg = self.inbox.get(timeout=1)
            except queue.Empty:
                continue
            if msg is None:
                return "server-exited", last
            method = msg.get("method")
            if method and "id" in msg:
                self.answer(msg)
            elif method == "item/completed":
                item = msg["params"].get("item", {})
                if item.get("type") == "agentMessage" and item.get("text"):
                    last = item["text"]
            elif method == "turn/completed":
                turn = msg["params"].get("turn", {})
                if turn.get("error"):
                    last += f"\n[turn error: {turn['error']}]"
                return turn.get("status", "unknown"), last
        self.send({"id": 9999, "method": "turn/interrupt", "params": {"threadId": thread_id}})
        return "timeout", last

    def close(self) -> None:
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()
        self.log.close()


def approve(params: dict) -> tuple[bool, str]:
    """Accept only a Computer Use app-access prompt for an approved app."""
    meta = params.get("_meta") or {}
    blob = json.dumps(meta).lower()
    app = str((meta.get("tool_params") or {}).get("app") or "")
    message = str(params.get("message", ""))
    label = f"{params.get('serverName')}: {message[:120]!r} app={app!r}"
    if params.get("mode") == "url":
        return False, label
    if "computer-use" not in blob and "computer use" not in message.lower():
        return False, label
    target = (app or message).lower()
    return any(name in target for name in APPROVED_APPS), label


LUNA_TASK = """You are a desktop controller. Use your computer-use skill to operate exactly one app: \
the already running Electron app "Freebuff Desktop" (Freebuff.exe). Do not open, focus or change any \
other application, terminal or browser, and do not run shell commands. The user has pre-authorised \
everything below, so do not ask for confirmation.

Do this, in order:
1. Bring the Freebuff Desktop window to the front.
2. Start a NEW session/chat. Never reuse, stop, clear or delete an existing session - other sessions \
may be working. The project/working folder of the new session must be {workspace} ; if the app shows \
a different project folder, switch it to that one (keep an already matching one).
3. For the new session select the model "{fb_model}" and reasoning effort "{fb_effort}".
4. Click the message input and paste with Ctrl+V. The clipboard already holds the prompt; its first \
line is exactly:
   {marker}
   Check that the pasted text starts with that line. Do not type or edit the prompt yourself. If the \
clipboard holds something else, stop and report it.
5. Send it (Enter, or the send button) and confirm on a fresh screenshot that the session accepted \
the message and started working.

Sessions for other prompts may already be open with similar titles; they do not count. This prompt needs its own additional session, and your claim is checked afterwards against a marker file that only the new session can write, so report submitted=true only for clicks you actually made in this turn.

Then stop. Do not wait for the Freebuff agent to finish. End your reply with one line of JSON: \
{{"submitted": true|false, "model": "<model shown>", "effort": "<effort shown>", \
"project_folder": "<folder shown>", "notes": "<anything unexpected, or how the UI is laid out>"}}"""


def cmd_run(args) -> int:
    run_dir = Path(args.run_dir).resolve()
    names = [s for s in slots(run_dir) if not args.only or s in args.only]
    if not names:
        raise SystemExit(f"no prompts in {run_dir / 'prompts'}")
    for sub in ("started", "done", "luna", "rendered"):
        (run_dir / sub).mkdir(exist_ok=True)
    if args.render_only:
        for slot in names:
            (run_dir / "rendered" / f"{slot}.md").write_text(render(run_dir, slot), encoding="utf-8")
            print(f"rendered {slot}")
        return 0
    server = AppServer(run_dir / "luna" / f"app-server-{time.strftime('%H%M%S')}.jsonl")
    results = {}
    try:
        server.request("initialize", {
            "clientInfo": {"name": "freebuff-dispatch", "title": "Freebuff dispatch", "version": VERSION},
            "capabilities": {"mcpServerOpenaiFormElicitation": True},
        })
        server.send({"method": "initialized"})
        for slot in names:
            if (run_dir / "started" / f"{slot}.txt").exists():
                print(f"[{slot}] already started, skipping", flush=True)
                results[slot] = {"status": "skipped"}
                continue
            text = render(run_dir, slot)
            marker = text.splitlines()[0]
            set_clipboard(text, run_dir / "rendered" / f"{slot}.md")
            print(f"[{slot}] clipboard set, asking {args.model}/{args.effort} to submit ...", flush=True)
            task = LUNA_TASK.format(workspace=WORKSPACE, fb_model=args.freebuff_model,
                                    fb_effort=args.freebuff_effort, marker=marker)
            # One fresh thread per slot: in a shared thread the controller answered a later,
            # identical-looking request from memory without touching Freebuff (run1, slot 3).
            thread = server.request("thread/start", {
                "model": args.model, "cwd": str(WORKSPACE), "approvalPolicy": "on-request",
                "sandbox": "read-only", "approvalsReviewer": "user",
            })["thread"]["id"]
            status, reply = server.turn(thread, task, args.effort, args.turn_timeout)
            print(f"[{slot}] turn {status}: {reply[-600:]}", flush=True)
            found = re.findall(r"\{[^{}]*\"submitted\"[^{}]*\}", reply)
            try:
                report = json.loads(found[-1]) if found else {}
            except json.JSONDecodeError:
                report = {}
            started = run_dir / "started" / f"{slot}.txt"
            deadline = time.time() + args.start_timeout
            while report.get("submitted") and not started.exists() and time.time() < deadline:
                time.sleep(5)
            results[slot] = {"turn": status, "report": report, "started_marker": started.exists(),
                             "reply": reply}
            print(f"[{slot}] submitted={report.get('submitted')} started_marker={started.exists()}",
                  flush=True)
            if not (report.get("submitted") and started.exists()):
                # The controller's own claim is not trusted; only the marker written by the
                # Freebuff agent counts. Check the Freebuff window before re-running this slot.
                print(f"[{slot}] NOT confirmed - stopping so nothing is double-sent", flush=True)
                break
    finally:
        server.close()
        (run_dir / "luna" / "run-result.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok = all(r.get("status") == "skipped" or r.get("started_marker")
             for r in results.values()) and len(results) == len(names)
    return 0 if ok else 1


def cmd_status(args) -> int:
    run_dir = Path(args.run_dir).resolve()
    missing = 0
    for slot in slots(run_dir):
        started = (run_dir / "started" / f"{slot}.txt").exists()
        done = run_dir / "done" / f"{slot}.json"
        state = "done" if done.exists() else "running" if started else "not started"
        missing += not done.exists()
        print(f"{slot}: {state}")
    return 0 if not missing else 2


def cmd_wait(args) -> int:
    run_dir = Path(args.run_dir).resolve()
    deadline = time.time() + args.timeout
    seen: set[str] = set()
    while True:
        names = slots(run_dir)
        for slot in names:
            done = run_dir / "done" / f"{slot}.json"
            if slot not in seen and done.exists() and done.stat().st_size > 0:
                seen.add(slot)
                print(f"{time.strftime('%H:%M:%S')} done: {slot}", flush=True)
        if names and len(seen) == len(names):
            time.sleep(args.poll)  # let the last writer finish before anyone reads the files
            print("ALL DONE", flush=True)
            return 0
        if time.time() > deadline:
            print(f"TIMEOUT, still waiting for: {sorted(set(names) - seen)}", flush=True)
            return 2
        time.sleep(args.poll)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="submit every prompts/*.md to a new Freebuff session")
    run.add_argument("--run-dir", required=True)
    run.add_argument("--only", nargs="*", help="slot names to submit (default: all not yet started)")
    run.add_argument("--render-only", action="store_true", help="write rendered/*.md and stop")
    run.add_argument("--model", default="gpt-6-luna", help="Codex controller model")
    run.add_argument("--effort", default="high", help="controller reasoning effort")
    run.add_argument("--freebuff-model", default="Space Bunny Alpha")
    run.add_argument("--freebuff-effort", default="High")
    run.add_argument("--turn-timeout", type=float, default=900, help="seconds per controller turn")
    run.add_argument("--start-timeout", type=float, default=240, help="seconds to wait for started/")
    run.set_defaults(fn=cmd_run)
    wait = sub.add_parser("wait", help="block until every done/<slot>.json exists")
    wait.add_argument("--run-dir", required=True)
    wait.add_argument("--timeout", type=float, default=7000)
    wait.add_argument("--poll", type=float, default=20)
    wait.set_defaults(fn=cmd_wait)
    status = sub.add_parser("status", help="print started/done per slot")
    status.add_argument("--run-dir", required=True)
    status.set_defaults(fn=cmd_status)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
