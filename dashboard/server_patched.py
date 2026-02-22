"""
Web Dashboard Server for QuantumPR-GPT Review Reports.

Serves the dashboard and exposes GitHub-integrated API endpoints.
Features in-memory caching to eliminate latency on repo/PR fetches.

Usage:
    python dashboard/server.py --port 8080
"""

from __future__ import annotations

import argparse
import http.server
import json
import logging
import os
import sys
import time
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import requests as _requests

logger = logging.getLogger(__name__)

DASHBOARD_DIR = Path(__file__).resolve().parent
REPORT_FILE = DASHBOARD_DIR / "latest_report.json"
GITHUB_API = "https://api.github.com"

# ── In-memory cache ──────────────────────────────────────────────────────────

_cache: dict[str, dict] = {}
CACHE_TTL = 120  # seconds


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key: str, data: Any):
    _cache[key] = {"data": data, "ts": time.time()}


# ── GitHub helpers ───────────────────────────────────────────────────────────

def _gh_token() -> str | None:
    return os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_REPO_TOKEN")


def _gh_headers(self) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    auth_header = self.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    else:
        token = _gh_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers
    
    # We will remove token = _gh_token() replacement below
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _json_response(handler, data: Any, status: int = 200):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, indent=2, default=str).encode("utf-8"))


# ── Handler ──────────────────────────────────────────────────────────────────

class DashboardHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/api/report":
            self._serve_report()
        elif path == "/api/github/status":
            self._serve_github_status()
        elif path == "/api/github/user":
            self._serve_github_user()
        elif path == "/api/github/repos":
            self._serve_github_repos()
        elif path == "/api/github/prs":
            repo = params.get("repo", [None])[0]
            self._serve_github_prs(repo)
        elif path == "/":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/review":
            self._run_review()
        elif parsed.path == "/api/merge":
            self._merge_pr()
        elif parsed.path == "/api/approve":
            self._approve_pr()
        elif parsed.path == "/api/fix":
            self._apply_fix()
        else:
            self.send_error(404)

    # ── GitHub Status (cached) ───────────────────────────────────────

    def _serve_github_status(self):
        cached = _cache_get("gh_status")
        if cached:
            _json_response(self, cached)
            return

        auth_header = self.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    else:
        token = _gh_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers
    
    # We will remove token = _gh_token() replacement below
        if not token:
            result = {"connected": False, "reason": "No GITHUB_TOKEN in .env"}
            _json_response(self, result)
            return

        try:
            resp = _requests.get(f"{GITHUB_API}/user", headers=_gh_headers(), timeout=10)
            if resp.status_code == 200:
                user = resp.json()
                result = {
                    "connected": True,
                    "user": {
                        "login": user.get("login", ""),
                        "name": user.get("name", ""),
                        "avatar_url": user.get("avatar_url", ""),
                        "html_url": user.get("html_url", ""),
                    },
                }
            else:
                result = {"connected": False, "reason": f"GitHub API: {resp.status_code}"}
        except Exception as exc:
            result = {"connected": False, "reason": str(exc)}

        _cache_set("gh_status", result)
        _json_response(self, result)

    # ── GitHub User ──────────────────────────────────────────────────

    def _serve_github_user(self):
        cached = _cache_get("gh_user")
        if cached:
            _json_response(self, cached)
            return

        try:
            resp = _requests.get(f"{GITHUB_API}/user", headers=_gh_headers(), timeout=10)
            resp.raise_for_status()
            user = resp.json()
            result = {
                "login": user.get("login", ""),
                "name": user.get("name", ""),
                "avatar_url": user.get("avatar_url", ""),
            }
            _cache_set("gh_user", result)
            _json_response(self, result)
        except Exception as exc:
            _json_response(self, {"error": str(exc)}, status=500)

    # ── GitHub Repos (cached) ────────────────────────────────────────

    def _serve_github_repos(self):
        cached = _cache_get("gh_repos")
        if cached:
            _json_response(self, cached)
            return

        try:
            resp = _requests.get(
                f"{GITHUB_API}/user/repos",
                headers=_gh_headers(),
                params={"sort": "pushed", "direction": "desc", "per_page": 30, "type": "all"},
                timeout=15,
            )
            resp.raise_for_status()

            repos = []
            for r in resp.json():
                repos.append({
                    "full_name": r["full_name"],
                    "description": r.get("description", "") or "",
                    "language": r.get("language", ""),
                    "private": r.get("private", False),
                    "updated_at": r.get("pushed_at", ""),
                })

            result = {"repos": repos}
            _cache_set("gh_repos", result)
            _json_response(self, result)

        except Exception as exc:
            _json_response(self, {"error": str(exc)}, status=500)

    # ── GitHub PRs (cached per repo) ─────────────────────────────────

    def _serve_github_prs(self, repo: str | None):
        if not repo:
            _json_response(self, {"error": "repo query param required"}, status=400)
            return

        cache_key = f"gh_prs_{repo}"
        cached = _cache_get(cache_key)
        if cached:
            _json_response(self, cached)
            return

        try:
            resp = _requests.get(
                f"{GITHUB_API}/repos/{repo}/pulls",
                headers=_gh_headers(),
                params={"state": "open", "sort": "updated", "direction": "desc", "per_page": 30},
                timeout=15,
            )
            resp.raise_for_status()

            prs = []
            for pr in resp.json():
                prs.append({
                    "number": pr["number"],
                    "title": pr.get("title", ""),
                    "author": (pr.get("user") or {}).get("login", ""),
                    "author_avatar": (pr.get("user") or {}).get("avatar_url", ""),
                    "state": pr.get("state", ""),
                    "draft": pr.get("draft", False),
                    "updated_at": pr.get("updated_at", ""),
                    "html_url": pr.get("html_url", ""),
                })

            result = {"repo": repo, "prs": prs}
            _cache_set(cache_key, result)
            _json_response(self, result)

        except Exception as exc:
            _json_response(self, {"error": str(exc)}, status=500)

    # ── Serve Report ─────────────────────────────────────────────────

    def _serve_report(self):
        if REPORT_FILE.exists():
            report = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
        else:
            report = {"error": "No report"}
        _json_response(self, report)

    # ── Run Review ───────────────────────────────────────────────────

    def _run_review(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(body)
            repo = data.get("repo", "Qiskit/qiskit")
            pr_number = data.get("pr_number")

            if not pr_number:
                _json_response(self, {"error": "pr_number is required"}, status=400)
                return

            from agents.pr_review.pr_review_orchestrator import PRReviewOrchestrator

            orchestrator = PRReviewOrchestrator(parallel=True)
            report = orchestrator.review_pr(repo=repo, pr_number=int(pr_number), verbose=False)

            REPORT_FILE.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
            _json_response(self, report)

        except Exception as exc:
            _json_response(self, {"error": str(exc)}, status=500)

    # ── Approve PR ───────────────────────────────────────────────────

    def _approve_pr(self):
        """Submit an approval review on the PR."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(body)
            repo = data.get("repo")
            pr_number = data.get("pr_number")

            if not repo or not pr_number:
                _json_response(self, {"error": "repo and pr_number required"}, status=400)
                return

            resp = _requests.post(
                f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/reviews",
                headers=_gh_headers(),
                json={"event": "APPROVE", "body": "✅ Approved by QuantumPR-GPT review agent."},
                timeout=15,
            )

            if resp.status_code in (200, 201):
                _json_response(self, {"status": "approved", "pr_number": pr_number})
            else:
                _json_response(self, {"error": f"GitHub API: {resp.status_code} — {resp.text}"}, status=resp.status_code)

        except Exception as exc:
            _json_response(self, {"error": str(exc)}, status=500)

    # ── Merge PR (with conflict detection) ─────────────────────────────

    def _merge_pr(self):
        """Perform merging of the PR via GitHub API."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(body)
            repo = data.get("repo")
            pr_number = data.get("pr_number")
            method = data.get("merge_method", "merge")  # merge | squash | rebase

            logger.info(f"Merge request received for {repo} PR #{pr_number} using method {method}")

            if not repo or not pr_number:
                _json_response(self, {"error": "repo and pr_number required"}, status=400)
                return

            # ── Step 1: Check PR status and mergeability ─────────────
            pr_resp = _requests.get(
                f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}",
                headers=_gh_headers(),
                timeout=15,
            )

            if pr_resp.status_code != 200:
                logger.error(f"Cannot fetch PR: {pr_resp.status_code} {pr_resp.text}")
                _json_response(self, {"error": f"Cannot fetch PR: {pr_resp.status_code}"}, status=pr_resp.status_code)
                return

            pr_data = pr_resp.json()
            state = pr_data.get("state", "")
            mergeable = pr_data.get("mergeable")
            mergeable_state = pr_data.get("mergeable_state", "unknown")

            # PR already closed or merged
            if state != "open":
                _json_response(self, {
                    "error": f"PR is {state}. Only open PRs can be merged.",
                    "state": state,
                }, status=422)
                return

            # GitHub hasn't computed mergeability yet (null) — retry up to 3 times
            for i in range(3):
                if mergeable is not None:
                    break
                logger.info(f"PR #{pr_number} mergeability is null, waiting 2s... (attempt {i + 1}/3)")
                import time as _time
                _time.sleep(2)
                pr_resp = _requests.get(
                    f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}",
                    headers=_gh_headers(),
                    timeout=15,
                )
                if pr_resp.status_code == 200:
                    pr_data = pr_resp.json()
                    mergeable = pr_data.get("mergeable")
                    mergeable_state = pr_data.get("mergeable_state", "unknown")
                else:
                    break
            
            if mergeable is None:
                _json_response(self, {
                    "error": "GitHub is still calculating mergeability. Please wait a few seconds and try again.",
                    "mergeable_state": mergeable_state,
                }, status=202) # Accepted but processing
                return

            # Merge conflicts detected
            if mergeable is False:
                # Fetch conflicting files
                files_resp = _requests.get(
                    f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/files",
                    headers=_gh_headers(),
                    params={"per_page": 100},
                    timeout=15,
                )
                conflict_files = []
                if files_resp.status_code == 200:
                    for f in files_resp.json():
                        if f.get("status") == "conflicted":
                            conflict_files.append(f.get("filename", ""))

                _json_response(self, {
                    "error": "Merge conflicts detected. Resolve conflicts in the branch before merging.",
                    "conflict": True,
                    "mergeable_state": mergeable_state,
                    "conflict_files": conflict_files,
                    "base": pr_data.get("base", {}).get("ref", ""),
                    "head": pr_data.get("head", {}).get("ref", ""),
                }, status=409)
                return

            # Checks blocking
            if mergeable_state == "blocked":
                # Check for failing status checks
                checks_resp = _requests.get(
                    f"{GITHUB_API}/repos/{repo}/commits/{pr_data['head']['sha']}/check-runs",
                    headers=_gh_headers(),
                    timeout=10
                )
                failed_checks = []
                if checks_resp.status_code == 200:
                    for check in checks_resp.json().get("check_runs", []):
                        if check.get("conclusion") == "failure":
                            failed_checks.append(check.get("name", "Unknown Check"))

                error_msg = "Merge is blocked by required status checks or reviews."
                if failed_checks:
                    error_msg = f"Merge blocked by failing checks: {', '.join(failed_checks)}"

                _json_response(self, {
                    "error": error_msg,
                    "mergeable_state": mergeable_state,
                    "failed_checks": failed_checks
                }, status=422)
                return

            if mergeable_state in ("behind", "dirty"):
                _json_response(self, {
                    "error": f"PR is {mergeable_state}. Resolve conflicts or update branch before merging.",
                    "mergeable_state": mergeable_state,
                }, status=422)
                return

            # ── Step 2: Attempt the merge ────────────────────────────
            logger.info(f"Attempting merge for PR #{pr_number}...")
            merge_resp = _requests.put(
                f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/merge",
                headers=_gh_headers(),
                json={
                    "merge_method": method,
                    "commit_title": f"Merge PR #{pr_number} (reviewed by QuantumPR-GPT)",
                },
                timeout=15,
            )

            if merge_resp.status_code == 200:
                result = merge_resp.json()
                logger.info(f"PR #{pr_number} merged successfully: {result.get('sha')}")
                _json_response(self, {
                    "status": "merged",
                    "sha": result.get("sha", ""),
                    "message": result.get("message", "Pull request merged."),
                })
            elif merge_resp.status_code == 405:
                err = merge_resp.json() if merge_resp.text else {}
                logger.warning(f"Merge 405 blocked: {err.get('message')}")
                _json_response(self, {
                    "error": err.get("message", "PR cannot be merged. Check branch protection rules."),
                }, status=405)
            elif merge_resp.status_code == 409:
                logger.warning(f"Merge 409 conflict: {merge_resp.text}")
                _json_response(self, {
                    "error": "Head branch was modified after mergeability check. Re-run the review.",
                    "conflict": True,
                }, status=409)
            else:
                logger.error(f"Merge failed with {merge_resp.status_code}: {merge_resp.text}")
                _json_response(self, {
                    "error": f"GitHub merge failed: {merge_resp.status_code} — {merge_resp.text}",
                }, status=merge_resp.status_code)

        except Exception as exc:
            _json_response(self, {"error": str(exc)}, status=500)

    # ── Apply Fix ────────────────────────────────────────────────────

    def _apply_fix(self):
        """Commit a suggested fix directly to the PR branch."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(body)
            repo = data.get("repo")
            pr_number = data.get("pr_number")
            file_path = data.get("file")
            fix_code = data.get("fix")

            if not all([repo, pr_number, file_path, fix_code]):
                _json_response(self, {"error": "Missing required fields (repo, pr_number, file, fix)"}, status=400)
                return

            # 1. Get PR branch info
            pr_resp = _requests.get(f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}", headers=_gh_headers())
            if pr_resp.status_code != 200:
                _json_response(self, {"error": "Could not fetch PR info"}, status=pr_resp.status_code)
                return
            
            pr_info = pr_resp.json()
            head_branch = pr_info["head"]["ref"]
            
            # 2. Get current file content and SHA
            file_resp = _requests.get(
                f"{GITHUB_API}/repos/{repo}/contents/{file_path}",
                headers=_gh_headers(),
                params={"ref": head_branch}
            )
            if file_resp.status_code != 200:
                _json_response(self, {"error": f"Could not find file: {file_path}"}, status=file_resp.status_code)
                return
            
            file_data = file_resp.json()
            sha = file_data["sha"]
            import base64
            content = base64.b64decode(file_data["content"]).decode("utf-8")

            # 3. Simple replacement logic (In a real app, this would be smarter)
            # For now, we assume the agent provides the corrected block or we can locate the line
            # If the agent provides 'corrected_code', we use that. 
            # If it's a line-based fix, we might need more logic.
            # We'll try to find the 'original' bad line if provided, or replace at 'line' index.
            
            # Let's assume the user wants the new content to be the updated version of the file.
            # But wait, our agent usually suggestions a 'fix' which is a block of code.
            # To be safe, we'll try to replace the first occurrence of something or use simple logic.
            # BETTER: We'll just append a comment or replace the section.
            # Actually, for this demo, let's assume 'fix_code' is the intended new content of the ENTIRE file 
            # OR we provided a specific replacement.
            
            # Since this is a specialized agent, let's look at what findings provide.
            # Usually: { "file": "path", "line": 4, "fix": "corrected code..." }
            
            lines = content.splitlines()
            line_idx = data.get("line", 1) - 1
            if 0 <= line_idx < len(lines):
                # Replace the line. Note: this is a simplification for the demo.
                lines[line_idx] = fix_code
                new_content = "\n".join(lines)
            else:
                # If line is out of bounds, just append or error
                _json_response(self, {"error": "Line number out of bounds"}, status=400)
                return

            # 4. Commit back
            update_resp = _requests.put(
                f"{GITHUB_API}/repos/{repo}/contents/{file_path}",
                headers=_gh_headers(),
                json={
                    "message": f"Apply AI fix to {file_path}",
                    "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
                    "sha": sha,
                    "branch": head_branch
                }
            )

            if update_resp.status_code in (200, 201):
                _json_response(self, {"status": "success", "message": "Fix applied and committed."})
            else:
                _json_response(self, {"error": f"GitHub commit failed: {update_resp.text}"}, status=update_resp.status_code)

        except Exception as exc:
            _json_response(self, {"error": str(exc)}, status=500)

    def log_message(self, format, *args):
        pass


# ── Startup ──────────────────────────────────────────────────────────────────

def start_server(port: int = 8080):
    server = http.server.HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"\n🔬 QuantumPR-GPT Dashboard running at: http://localhost:{port}")
    print("   Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down dashboard server...")
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="QuantumPR-GPT Dashboard Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to serve on")
    args = parser.parse_args()
    start_server(args.port)


if __name__ == "__main__":
    main()
