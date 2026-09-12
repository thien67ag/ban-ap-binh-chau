from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import sqlite3, os, secrets
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "doi-secret-key-truoc-khi-trien-khai")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "data.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "mp4", "webm", "mov"}

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def add_column_if_missing(conn, table, column, definition):
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS reflections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        address TEXT,
        category TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Mới tiếp nhận'
    );
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        purpose TEXT NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Chờ xác nhận'
    );
    """)
    # Migrate dữ liệu từ bản V1, không làm mất dữ liệu cũ.
    add_column_if_missing(conn, "reflections", "report_code", "TEXT")
    add_column_if_missing(conn, "reflections", "priority", "TEXT NOT NULL DEFAULT 'Bình thường'")
    add_column_if_missing(conn, "reflections", "latitude", "TEXT")
    add_column_if_missing(conn, "reflections", "longitude", "TEXT")
    add_column_if_missing(conn, "reflections", "attachment", "TEXT")
    add_column_if_missing(conn, "appointments", "appointment_code", "TEXT")

    rows = conn.execute("SELECT id FROM reflections WHERE report_code IS NULL OR report_code=''").fetchall()
    for row in rows:
        conn.execute("UPDATE reflections SET report_code=? WHERE id=?",
                     (f"ANTT-OLD-{row['id']:04d}", row["id"]))
    rows = conn.execute("SELECT id FROM appointments WHERE appointment_code IS NULL OR appointment_code=''").fetchall()
    for row in rows:
        conn.execute("UPDATE appointments SET appointment_code=? WHERE id=?",
                     (f"LICH-OLD-{row['id']:04d}", row["id"]))
    conn.commit()
    conn.close()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.errorhandler(413)
def too_large(_):
    flash("Tệp quá lớn. Vui lòng chọn ảnh/video không quá 50 MB.", "danger")
    return redirect(url_for("reflection"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/phan-anh", methods=["GET", "POST"])
def reflection():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        category = request.form.get("category", "KHÁC")
        priority = request.form.get("priority", "Bình thường")
        content = request.form.get("content", "").strip()
        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()

        if not content:
            flash("Vui lòng nhập nội dung phản ánh.", "danger")
            return redirect(url_for("reflection"))

        attachment = ""
        f = request.files.get("attachment")
        if f and f.filename:
            if not allowed_file(f.filename):
                flash("Chỉ nhận JPG, PNG, WEBP, MP4, WEBM hoặc MOV.", "danger")
                return redirect(url_for("reflection"))
            ext = f.filename.rsplit(".", 1)[1].lower()
            filename = f"{secrets.token_hex(12)}.{ext}"
            f.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            attachment = filename

        conn = db()
        cur = conn.execute("""INSERT INTO reflections
            (report_code, name, phone, address, category, content, created_at, status,
             priority, latitude, longitude, attachment)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("TEMP", name, phone, address, category, content,
             datetime.now().strftime("%d/%m/%Y %H:%M"),
             "Mới tiếp nhận", priority, latitude, longitude, attachment))
        report_code = f"ANTT-{datetime.now().year}-{cur.lastrowid:04d}"
        conn.execute("UPDATE reflections SET report_code=? WHERE id=?", (report_code, cur.lastrowid))
        conn.commit()
        conn.close()

        return render_template("success.html", code=report_code, kind="phản ánh")
    return render_template("reflection.html")

@app.route("/dat-lich", methods=["GET", "POST"])
def appointment():
    if request.method == "POST":
        data = [request.form.get(x, "").strip() for x in
                ["name", "phone", "address", "date", "time", "purpose"]]
        if not data[0] or not data[1] or not data[3] or not data[4] or not data[5]:
            flash("Vui lòng điền đầy đủ các trường bắt buộc.", "danger")
            return redirect(url_for("appointment"))

        conn = db()
        cur = conn.execute("""INSERT INTO appointments
            (appointment_code, name, phone, address, date, time, purpose, created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            ("TEMP", *data, datetime.now().strftime("%d/%m/%Y %H:%M")))
        code = f"LICH-{datetime.now().year}-{cur.lastrowid:04d}"
        conn.execute("UPDATE appointments SET appointment_code=? WHERE id=?", (code, cur.lastrowid))
        conn.commit()
        conn.close()
        return render_template("success.html", code=code, kind="lịch hẹn")
    return render_template("appointment.html")

@app.route("/tra-cuu", methods=["GET", "POST"])
def lookup():
    result = None
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        conn = db()
        result = conn.execute("""SELECT * FROM appointments
            WHERE phone=? ORDER BY id DESC LIMIT 10""", (phone,)).fetchall()
        conn.close()
    return render_template("lookup.html", result=result)

@app.route("/tai-lieu/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin"):
        return render_template("admin_login.html")
    conn = db()
    reflections = conn.execute("SELECT * FROM reflections ORDER BY id DESC").fetchall()
    appointments = conn.execute("SELECT * FROM appointments ORDER BY date ASC, time ASC, id DESC").fetchall()
    stats = {
        "total_reflections": conn.execute("SELECT COUNT(*) FROM reflections").fetchone()[0],
        "new_reflections": conn.execute("SELECT COUNT(*) FROM reflections WHERE status='Mới tiếp nhận'").fetchone()[0],
        "processing": conn.execute("SELECT COUNT(*) FROM reflections WHERE status='Đang xử lý'").fetchone()[0],
        "done_reflections": conn.execute("SELECT COUNT(*) FROM reflections WHERE status='Đã xử lý'").fetchone()[0],
        "appointments": conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0],
    }
    conn.close()
    return render_template("admin.html", reflections=reflections, appointments=appointments, stats=stats)

@app.post("/admin/login")
def admin_login():
    if request.form.get("username") == "admin" and request.form.get("password") == "admin123":
        session["admin"] = True
        return redirect(url_for("admin"))
    flash("Sai tài khoản hoặc mật khẩu.", "danger")
    return redirect(url_for("admin"))

@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

@app.post("/admin/reflection/<int:item_id>")
def update_reflection(item_id):
    if not session.get("admin"):
        return redirect(url_for("admin"))
    status = request.form.get("status", "Mới tiếp nhận")
    conn = db()
    conn.execute("UPDATE reflections SET status=? WHERE id=?", (status, item_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

@app.post("/admin/appointment/<int:item_id>")
def update_appointment(item_id):
    if not session.get("admin"):
        return redirect(url_for("admin"))
    status = request.form.get("status", "Chờ xác nhận")
    conn = db()
    conn.execute("UPDATE appointments SET status=? WHERE id=?", (status, item_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
