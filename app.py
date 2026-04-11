"""
╔══════════════════════════════════════════════════════════╗
║   RE-RECORDING TRACKER  ◆  WEB EDITION                   ║
║   Flask + SQLite  |  Free hosting via Render + GitHub     ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta, date
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

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

            CREATE TABLE IF NOT EXISTS productions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT    NOT NULL,
                producer     TEXT    NOT NULL,
                total_arcs   INTEGER NOT NULL DEFAULT 11,
                arcs_done    TEXT    DEFAULT '[]',
                status       TEXT    DEFAULT 'iniciado',
                started_at   TEXT    NOT NULL,
                updated_at   TEXT,
                paused_at    TEXT,
                completed_at TEXT,
                notes        TEXT    DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS production_daily (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                production_id INTEGER NOT NULL,
                log_date      TEXT    NOT NULL,
                chars_written INTEGER DEFAULT 0,
                notes         TEXT    DEFAULT '',
                FOREIGN KEY (production_id) REFERENCES productions(id)
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


# ═══════════════════════════════════════════
#  PRODUCTION HELPERS
# ═══════════════════════════════════════════

def business_days_since(start_str):
    """Count business days (Mon-Fri) from start date to today."""
    try:
        start = date.fromisoformat(start_str[:10])
    except Exception:
        return 0
    today = date.today()
    if start > today:
        return 0
    count = 0
    cur = start
    while cur < today:
        if cur.weekday() < 5:
            count += 1
        cur += timedelta(days=1)
    return count


def deadline_color(bdays, status):
    if status == 'concluido':
        return 'green'
    if bdays <= 2:
        return 'green'
    if bdays == 3:
        return 'yellow'
    return 'red'


def prod_total_chars(prod_id):
    with get_db() as c:
        r = c.execute(
            "SELECT COALESCE(SUM(chars_written),0) FROM production_daily WHERE production_id=?",
            (prod_id,)
        ).fetchone()
    return r[0] if r else 0


def prod_today_chars(prod_id):
    today = date.today().isoformat()
    with get_db() as c:
        r = c.execute(
            "SELECT COALESCE(SUM(chars_written),0) FROM production_daily WHERE production_id=? AND log_date=?",
            (prod_id, today)
        ).fetchone()
    return r[0] if r else 0


def enrich_production(p):
    """Add computed fields to a production dict."""
    d = dict(p)
    d['arcs_done_list'] = json.loads(d.get('arcs_done') or '[]')
    d['arcs_done_count'] = len(d['arcs_done_list'])
    d['bdays'] = business_days_since(d['started_at'])
    d['dl_color'] = deadline_color(d['bdays'], d['status'])
    d['total_chars'] = prod_total_chars(d['id'])
    d['today_chars'] = prod_today_chars(d['id'])
    # chars progress per day: goal 5000 * 4 days = 20000 total
    goal = 5000 * 4
    d['chars_pct'] = min(100, int(d['total_chars'] / goal * 100)) if goal else 0
    d['today_pct'] = min(100, int(d['today_chars'] / 5000 * 100))
    d['arc_pct'] = int(d['arcs_done_count'] / d['total_arcs'] * 100) if d['total_arcs'] else 0
    return d


# ═══════════════════════════════════════════
#  PRODUCTION ROUTES
# ═══════════════════════════════════════════

@app.route("/productions")
def productions():
    with get_db() as c:
        rows = c.execute("SELECT * FROM productions ORDER BY started_at DESC").fetchall()
    prods = [enrich_production(r) for r in rows]

    summary = {
        'total':      len(prods),
        'iniciado':   sum(1 for p in prods if p['status'] == 'iniciado'),
        'andamento':  sum(1 for p in prods if p['status'] == 'em_andamento'),
        'pausado':    sum(1 for p in prods if p['status'] == 'pausado'),
        'concluido':  sum(1 for p in prods if p['status'] == 'concluido'),
        'atrasado':   sum(1 for p in prods if p['dl_color'] == 'red' and p['status'] != 'concluido'),
    }
    return render_template("productions.html",
                           prods=prods, summary=summary,
                           active="productions")


@app.route("/productions/new", methods=["GET", "POST"])
def production_new():
    msg = None
    msg_type = None
    if request.method == "POST":
        title      = request.form.get("title", "").strip()
        producer   = request.form.get("producer", "").strip()
        total_arcs = request.form.get("total_arcs", "11").strip()
        notes      = request.form.get("notes", "").strip()

        errors = []
        if not title:    errors.append("Título obrigatório")
        if not producer: errors.append("Produtor obrigatório")
        if not total_arcs.isdigit() or not (1 <= int(total_arcs) <= 15):
            errors.append("Número de arcos inválido (1–15)")

        if errors:
            msg = " | ".join(errors)
            msg_type = "error"
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with get_db() as c:
                c.execute(
                    """INSERT INTO productions
                       (title,producer,total_arcs,arcs_done,status,started_at,updated_at,notes)
                       VALUES (?,?,?,'[]','iniciado',?,?,?)""",
                    (title, producer, int(total_arcs), now, now, notes)
                )
            return redirect(url_for("productions"))

    return render_template("production_new.html",
                           msg=msg, msg_type=msg_type,
                           active="productions")


@app.route("/productions/<int:pid>")
def production_detail(pid):
    with get_db() as c:
        p = c.execute("SELECT * FROM productions WHERE id=?", (pid,)).fetchone()
        if not p:
            return redirect(url_for("productions"))
        daily = c.execute(
            "SELECT * FROM production_daily WHERE production_id=? ORDER BY log_date DESC",
            (pid,)
        ).fetchall()

    prod = enrich_production(p)
    daily_list = [dict(d) for d in daily]
    today = date.today().isoformat()
    return render_template("production_detail.html",
                           prod=prod, daily=daily_list,
                           today=today, active="productions")


@app.route("/productions/<int:pid>/arc", methods=["POST"])
def production_arc(pid):
    arc_num = int(request.form.get("arc", 0))
    action  = request.form.get("action", "toggle")  # toggle | check | uncheck
    with get_db() as c:
        p = c.execute("SELECT * FROM productions WHERE id=?", (pid,)).fetchone()
        if not p:
            return redirect(url_for("productions"))
        done = json.loads(p["arcs_done"] or "[]")
        if action == "check" and arc_num not in done:
            done.append(arc_num)
        elif action == "uncheck" and arc_num in done:
            done.remove(arc_num)
        else:
            if arc_num in done:
                done.remove(arc_num)
            else:
                done.append(arc_num)
        done.sort()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # auto-complete if all arcs done
        status = p["status"]
        if len(done) >= p["total_arcs"] and status not in ("concluido",):
            status = "concluido"
            c.execute(
                "UPDATE productions SET arcs_done=?, status=?, updated_at=?, completed_at=? WHERE id=?",
                (json.dumps(done), status, now, now, pid)
            )
        else:
            if status == "concluido" and len(done) < p["total_arcs"]:
                status = "em_andamento"
            c.execute(
                "UPDATE productions SET arcs_done=?, updated_at=?, status=? WHERE id=?",
                (json.dumps(done), now, status, pid)
            )
    return redirect(url_for("production_detail", pid=pid))


@app.route("/productions/<int:pid>/status", methods=["POST"])
def production_status(pid):
    new_status = request.form.get("status", "")
    valid = ("iniciado", "em_andamento", "pausado", "concluido")
    if new_status not in valid:
        return redirect(url_for("production_detail", pid=pid))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as c:
        if new_status == "pausado":
            c.execute(
                "UPDATE productions SET status=?, paused_at=?, updated_at=? WHERE id=?",
                (new_status, now, now, pid)
            )
        elif new_status == "concluido":
            c.execute(
                "UPDATE productions SET status=?, completed_at=?, updated_at=? WHERE id=?",
                (new_status, now, now, pid)
            )
        else:
            c.execute(
                "UPDATE productions SET status=?, updated_at=? WHERE id=?",
                (new_status, now, pid)
            )
    return redirect(url_for("production_detail", pid=pid))


@app.route("/productions/<int:pid>/log", methods=["POST"])
def production_log(pid):
    chars = request.form.get("chars", "0").strip()
    notes = request.form.get("notes", "").strip()
    log_date = request.form.get("log_date", date.today().isoformat())
    if not chars.isdigit():
        chars = "0"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as c:
        # Update existing log for same date or insert
        existing = c.execute(
            "SELECT id, chars_written FROM production_daily WHERE production_id=? AND log_date=?",
            (pid, log_date)
        ).fetchone()
        if existing:
            new_chars = existing["chars_written"] + int(chars)
            c.execute(
                "UPDATE production_daily SET chars_written=?, notes=? WHERE id=?",
                (new_chars, notes, existing["id"])
            )
        else:
            c.execute(
                "INSERT INTO production_daily (production_id,log_date,chars_written,notes) VALUES (?,?,?,?)",
                (pid, log_date, int(chars), notes)
            )
        c.execute(
            "UPDATE productions SET updated_at=?, status=CASE WHEN status='iniciado' THEN 'em_andamento' ELSE status END WHERE id=?",
            (now_str, pid)
        )
    return redirect(url_for("production_detail", pid=pid))


@app.route("/productions/<int:pid>/delete", methods=["POST"])
def production_delete(pid):
    with get_db() as c:
        c.execute("DELETE FROM production_daily WHERE production_id=?", (pid,))
        c.execute("DELETE FROM productions WHERE id=?", (pid,))
    return redirect(url_for("productions"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
