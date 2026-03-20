"""Flask web dashboard for LinkedinTouch."""
import os
import re
import sys
import sqlite3
import subprocess
import threading
import uuid

# Allow imports from project root regardless of CWD
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json as _json

from flask import Flask, jsonify, render_template, request
import config
from db.repo import get_stats, get_daily_counts, set_prospect_status
from db.schema import init_db

app = Flask(__name__)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# job_id → {"status": "running"|"done"|"error", "output": str}
_jobs: dict = {}
_jobs_lock = threading.Lock()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHF]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _build_cmd(command: str, args: dict) -> list[str]:
    cmd_map = {
        "scrape":        ["main.py", "scrape", "--limit", str(args.get("limit", 20))],
        "generate_mock": ["main.py", "generate", "--mock"],
        "generate":      ["main.py", "generate"],
        "send_dry":      ["main.py", "send", "--dry-run"],
        "send":          ["main.py", "send"],
    }
    parts = cmd_map.get(command)
    if parts is None:
        raise ValueError(f"Unknown command: {command}")
    return [sys.executable] + parts


def _run_job(job_id: str, cmd: list[str]) -> None:
    try:
        proc = subprocess.run(
            cmd,
            cwd=_PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = _strip_ansi(proc.stdout or "")
        status = "done" if proc.returncode == 0 else "error"
    except Exception as exc:
        output = str(exc)
        status = "error"

    with _jobs_lock:
        _jobs[job_id]["output"] = output
        _jobs[job_id]["status"] = status


def _conn() -> sqlite3.Connection:
    return init_db(config.DB_FILE)


@app.route("/api/run", methods=["POST"])
def api_run():
    body = request.get_json(force=True) or {}
    command = body.get("command", "")
    args = body.get("args", {})
    try:
        cmd = _build_cmd(command, args)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"status": "running", "output": ""}

    t = threading.Thread(target=_run_job, args=(job_id, cmd), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/job/<job_id>")
def api_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(job)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    conn = _conn()

    # Prospects joined with their latest message
    rows = conn.execute(
        """
        SELECT
            p.id,
            p.name,
            p.headline,
            p.company,
            p.location,
            p.status,
            p.profile_url,
            p.scraped_at,
            m.message_text,
            m.sent_at
        FROM prospects p
        LEFT JOIN messages m ON m.id = (
            SELECT id FROM messages
            WHERE prospect_id = p.id
            ORDER BY generated_at DESC
            LIMIT 1
        )
        ORDER BY p.scraped_at DESC
        """
    ).fetchall()
    conn.close()

    prospects = [
        {
            "id": r["id"],
            "name": r["name"] or "",
            "headline": r["headline"] or "",
            "company": r["company"] or "",
            "location": r["location"] or "",
            "status": r["status"],
            "profile_url": r["profile_url"],
            "scraped_at": r["scraped_at"],
            "message_text": r["message_text"] or "",
            "sent_at": r["sent_at"] or "",
        }
        for r in rows
    ]

    stats = get_stats()
    daily = get_daily_counts()

    return jsonify(
        {
            "prospects": prospects,
            "stats": {
                "total": sum(stats.get(s, 0) for s in ("new", "messaged", "skipped", "failed")),
                "new": stats.get("new", 0),
                "messaged": stats.get("messaged", 0),
                "failed": stats.get("failed", 0),
                "skipped": stats.get("skipped", 0),
            },
            "daily": {
                "scraped": daily["scraped"],
                "messaged": daily["messaged"],
                "scrape_cap": config.DAILY_SCRAPE_CAP,
                "message_cap": config.DAILY_MESSAGE_CAP,
            },
        }
    )


@app.route("/api/campaign/suggest", methods=["POST"])
def api_campaign_suggest():
    body = request.get_json(force=True) or {}
    description = (body.get("description") or "").strip()
    if not description:
        return jsonify({"error": "description is required"}), 400
    if not config.OPENAI_API_KEY:
        return jsonify({"error": "OPENAI_API_KEY not configured"}), 500

    try:
        import openai
        client = openai.OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
        )
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a B2B sales targeting expert. "
                        "Given a campaign description, return ONLY valid JSON with two keys: "
                        '"job_titles" (array of 8-12 job title strings) and '
                        '"industry_keywords" (array of 4-8 industry keyword strings). '
                        "No explanation, no markdown, just raw JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Campaign target description: {description}",
                },
            ],
            max_tokens=400,
            temperature=0.5,
        )
        raw = response.choices[0].message.content
        # Extract JSON even if model wraps it in markdown code fences
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return jsonify({"error": "AI did not return valid JSON"}), 500
        result = _json.loads(match.group())
        return jsonify({
            "job_titles": result.get("job_titles", []),
            "industry_keywords": result.get("industry_keywords", []),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


_VALID_STATUSES = {"new", "messaged", "skipped", "failed"}


@app.route("/api/prospect/<int:pid>/status", methods=["PATCH"])
def api_prospect_status(pid: int):
    body = request.get_json(force=True) or {}
    status = body.get("status", "")
    if status not in _VALID_STATUSES:
        return jsonify({"error": f"invalid status '{status}'"}), 400
    set_prospect_status(pid, status)
    return jsonify({"ok": True})


_CAMPAIGN_OVERRIDE = os.path.join(_PROJECT_ROOT, "campaign.json")
_CAMPAIGN_ALLOWED_KEYS = {"job_titles", "industry_keywords", "company_sizes", "regions"}


@app.route("/api/campaign", methods=["GET"])
def api_campaign_get():
    return jsonify(config.CAMPAIGN)


@app.route("/api/campaign", methods=["POST"])
def api_campaign_post():
    body = request.get_json(force=True) or {}
    campaign = {k: v for k, v in body.items() if k in _CAMPAIGN_ALLOWED_KEYS}
    with open(_CAMPAIGN_OVERRIDE, "w", encoding="utf-8") as f:
        _json.dump(campaign, f, indent=2, ensure_ascii=False)
    config.CAMPAIGN.update(campaign)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
