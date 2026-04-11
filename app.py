"""
╔══════════════════════════════════════════════════════════╗
║   RE-RECORDING TRACKER  ◆  WEB EDITION                   ║
║   Flask + SQLite  |  Free hosting via Render + GitHub     ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import sqlite3
from datetime import datetime, timedelta, date
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

# ── Database path (writable on Render's ephemeral disk) ──────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "data", "rerecording.db")


# ═══════════════════════════════════════════
#  DATABASE HELPERS
# ═══════════════════════════════════════════

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS records (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                producer    TEXT    NOT NULL,
                project     TEXT    NOT NULL,
                count       INTEGER NOT NULL DEFAULT 1,
                reason      TEXT    NOT NULL,
                description TEXT    DEFAULT '',
                observation TEXT    DEFAULT '',
                created_at  TEXT    NOT NULL
            );
        """)


init_db()


def db_stats():
    with get_db() as c:
        total   = c.execute("SELECT COALESCE(SUM(count),0) FROM records").fetchone()[0]
        top_p   = c.execute(
            "SELECT producer, SUM(count) t FROM records GROUP BY producer ORDER BY t DESC LIMIT 1"
        ).fetchone()
        top_r   = c.execute(
            "SELECT reason, SUM(count) t FROM records GROUP BY reason ORDER BY t DESC LIMIT 1"
        ).fetchone()
        week_t  = c.execute(
            "SELECT COALESCE(SUM(count),0) FROM records WHERE date(created_at)>=date('now','weekday 0','-7 days')"
        ).fetchone()[0]
    return {
        "total":        total,
        "week_total":   week_t,
        "top_producer": dict(top_p) if top_p else None,
        "top_reason":   dict(top_r) if top_r else None,
    }


def db_reason_dist():
    with get_db() as c:
        return [dict(r) for r in c.execute(
            "SELECT reason, SUM(count) total FROM records GROUP BY reason ORDER BY total DESC"
        ).fetchall()]


def db_by_producer():
    with get_db() as c:
        return [dict(r) for r in c.execute(
            """SELECT producer, SUM(count) total,
               (SELECT reason FROM records r2
                WHERE r2.producer=r.producer
                GROUP BY reason ORDER BY SUM(count) DESC LIMIT 1) top_reason
               FROM records r GROUP BY producer ORDER BY total DESC"""
        ).fetchall()]


def db_weekly(weeks_back=0):
    today = date.today()
    mon   = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks_back)
    sun   = mon + timedelta(days=6)
    with get_db() as c:
        rows = c.execute(
            """SELECT * FROM records
               WHERE date(created_at) BETWEEN ? AND ?
               ORDER BY created_at DESC""",
            (mon.isoformat(), sun.isoformat())
        ).fetchall()
    return [dict(r) for r in rows], mon, sun


def db_trend():
    with get_db() as c:
        rows = c.execute(
            """SELECT strftime('%d/%m', created_at) day, SUM(count) total
               FROM records
               WHERE date(created_at) >= date('now', '-14 days')
               GROUP BY day ORDER BY day"""
        ).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════

@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    stats      = db_stats()
    reasons    = db_reason_dist()
    producers  = db_by_producer()
    trend      = db_trend()
    return render_template("dashboard.html",
                           stats=stats, reasons=reasons,
                           producers=producers, trend=trend,
                           active="dashboard")


@app.route("/register", methods=["GET", "POST"])
def register():
    msg = None
    msg_type = None
    if request.method == "POST":
        producer = request.form.get("producer", "").strip()
        project  = request.form.get("project",  "").strip()
        count_s  = request.form.get("count",    "1").strip()
        reason   = request.form.get("reason",   "")
        desc     = request.form.get("description", "").strip()
        obs      = request.form.get("observation",  "").strip()

        errors = []
        if not producer:        errors.append("Produtor obrigatório")
        if not project:         errors.append("Projeto obrigatório")
        if not count_s.isdigit() or int(count_s) < 1:
            errors.append("Número de regravaçôes inválido")
        if reason == "Outro" and not desc:
            errors.append("Descrição obrigatória quando motivo = 'Outro'")

        if errors:
            msg      = " | ".join(errors)
            msg_type = "error"
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with get_db() as c:
                c.execute(
                    "INSERT INTO records (producer,project,count,reason,description,observation,created_at) VALUES (?,?,?,?,?,?,?)",
                    (producer, project, int(count_s), reason, desc, obs, now)
                )
            msg      = f"✔  Registro salvo: {producer} — {project} ({count_s}x)"
            msg_type = "success"

    reasons_list = [
        "Erro de roteiro", "Falta de atenção", "Erro técnico",
        "Não seguiu padrão", "Mudança de ideia (cliente)", "Outro",
    ]
    return render_template("register.html",
                           reasons=reasons_list,
                           msg=msg, msg_type=msg_type,
                           active="register")


@app.route("/reports")
def reports():
    weeks_back   = int(request.args.get("w", 0))
    rows, mon, sun = db_weekly(weeks_back)

    # Annotate severity
    for r in rows:
        r["tag"] = ("high"   if r["count"] >= 5 else
                    "medium" if r["count"] >= 3 else "low")

    total = sum(r["count"] for r in rows)
    return render_template("reports.html",
                           rows=rows, total=total,
                           mon=mon.strftime("%d/%m"),
                           sun=sun.strftime("%d/%m/%Y"),
                           weeks_back=weeks_back,
                           active="reports")


# ── JSON API (used by Chart.js calls) ────────────────────────
@app.route("/api/chart-data")
def chart_data():
    return jsonify({
        "reasons":   db_reason_dist(),
        "producers": db_by_producer(),
        "trend":     db_trend(),
    })


# ── Health check (Render requires a responsive endpoint) ─────
@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
