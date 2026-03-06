import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

app = Flask(
    __name__,
    template_folder='../templates',
    static_folder='../static'
)

# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    """Get a database connection using DATABASE_URL env var."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable not set")
    conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id          SERIAL PRIMARY KEY,
            title       VARCHAR(200) NOT NULL,
            description TEXT NOT NULL,
            tech_stack  TEXT[],
            github_url  VARCHAR(300),
            live_url    VARCHAR(300),
            image_url   VARCHAR(300),
            featured    BOOLEAN DEFAULT FALSE,
            created_at  TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS skills (
            id       SERIAL PRIMARY KEY,
            name     VARCHAR(100) NOT NULL,
            category VARCHAR(100),
            level    INTEGER CHECK (level BETWEEN 1 AND 100)
        );

        CREATE TABLE IF NOT EXISTS profile (
            id       INTEGER PRIMARY KEY DEFAULT 1,
            name     VARCHAR(200),
            title    VARCHAR(200),
            bio      TEXT,
            email    VARCHAR(200),
            github   VARCHAR(300),
            linkedin VARCHAR(300),
            location VARCHAR(200)
        );
    """)

    # Seed profile if empty
    cur.execute("SELECT COUNT(*) AS cnt FROM profile")
    if cur.fetchone()['cnt'] == 0:
        cur.execute("""
            INSERT INTO profile (name, title, bio, email, github, linkedin, location)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            "Your Name",
            "Full-Stack Developer & Tech Enthusiast",
            "Passionate developer based in Arusha, Tanzania. I build elegant solutions to complex problems, with a focus on scalable web applications and impactful technology for East Africa.",
            "hello@yourname.dev",
            "https://github.com/yourusername",
            "https://linkedin.com/in/yourname",
            "Arusha, Tanzania 🇹🇿"
        ))

    # Seed sample projects if empty
    cur.execute("SELECT COUNT(*) AS cnt FROM projects")
    if cur.fetchone()['cnt'] == 0:
        projects = [
            ("ATC Smart Campus Assistant", "AI-powered bilingual chatbot for Arusha Technical College with campus navigation, timetable management, and RAG-based Q&A.", ["Flutter", "Flask", "PostgreSQL", "OpenAI"], "https://github.com", "", "", True),
            ("Tanzania Stays", "Airbnb-style property booking platform for Tanzania with M-Pesa payments, dual host/guest roles, and real-time availability.", ["Flutter", "Node.js", "PostgreSQL", "AWS S3"], "https://github.com", "", "", True),
            ("Carbon Tracker", "Blockchain-based carbon emission tracking system for community climate action in East Africa.", ["Solidity", "React", "Node.js", "IPFS"], "https://github.com", "", "", False),
        ]
        for p in projects:
            cur.execute("""
                INSERT INTO projects (title, description, tech_stack, github_url, live_url, image_url, featured)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, p)

    # Seed sample skills if empty
    cur.execute("SELECT COUNT(*) AS cnt FROM skills")
    if cur.fetchone()['cnt'] == 0:
        skills = [
            ("Python", "Backend", 90), ("Flask", "Backend", 85), ("Node.js", "Backend", 80),
            ("Flutter", "Mobile", 85), ("React", "Frontend", 75), ("HTML/CSS", "Frontend", 90),
            ("PostgreSQL", "Database", 85), ("MongoDB", "Database", 70), ("Redis", "Database", 65),
            ("AWS", "Cloud", 75), ("Alibaba Cloud", "Cloud", 70), ("Vercel", "Cloud", 80),
            ("Docker", "DevOps", 70), ("Git", "Tools", 90), ("Linux", "Tools", 80),
            ("Cybersecurity", "Security", 75), ("Blockchain", "Web3", 65), ("Machine Learning", "AI/ML", 70),
        ]
        for s in skills:
            cur.execute("INSERT INTO skills (name, category, level) VALUES (%s,%s,%s)", s)

    conn.commit()
    cur.close()
    conn.close()


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    try:
        init_db()
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM profile WHERE id=1")
        profile = dict(cur.fetchone() or {})

        cur.execute("SELECT * FROM projects ORDER BY featured DESC, created_at DESC")
        projects = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM skills ORDER BY category, level DESC")
        skills = [dict(r) for r in cur.fetchall()]

        cur.close()
        conn.close()

        # Group skills by category
        skills_by_cat = {}
        for s in skills:
            cat = s['category'] or 'Other'
            skills_by_cat.setdefault(cat, []).append(s)

        return render_template("index.html",
                               profile=profile,
                               projects=projects,
                               skills_by_cat=skills_by_cat)
    except Exception as e:
        return f"<h2>Setup Error</h2><pre>{e}</pre><p>Make sure DATABASE_URL is set in Vercel environment variables.</p>", 500


# ── API: Projects ─────────────────────────────────────────────────────────────

@app.route("/api/projects", methods=["GET"])
def get_projects():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects ORDER BY featured DESC, created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r['created_at'] = r['created_at'].isoformat() if r.get('created_at') else None
    cur.close(); conn.close()
    return jsonify(rows)


@app.route("/api/projects", methods=["POST"])
def create_project():
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO projects (title, description, tech_stack, github_url, live_url, image_url, featured)
        VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (
        data.get('title'), data.get('description'),
        data.get('tech_stack', []),
        data.get('github_url', ''), data.get('live_url', ''),
        data.get('image_url', ''), data.get('featured', False)
    ))
    new_id = cur.fetchone()['id']
    conn.commit(); cur.close(); conn.close()
    return jsonify({"id": new_id, "message": "Project created"}), 201


@app.route("/api/projects/<int:pid>", methods=["PUT"])
def update_project(pid):
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE projects SET title=%s, description=%s, tech_stack=%s,
        github_url=%s, live_url=%s, image_url=%s, featured=%s
        WHERE id=%s
    """, (
        data.get('title'), data.get('description'),
        data.get('tech_stack', []),
        data.get('github_url', ''), data.get('live_url', ''),
        data.get('image_url', ''), data.get('featured', False), pid
    ))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Updated"})


@app.route("/api/projects/<int:pid>", methods=["DELETE"])
def delete_project(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM projects WHERE id=%s", (pid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Deleted"})


# ── API: Profile ──────────────────────────────────────────────────────────────

@app.route("/api/profile", methods=["GET"])
def get_profile():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM profile WHERE id=1")
    row = cur.fetchone()
    cur.close(); conn.close()
    return jsonify(dict(row) if row else {})


@app.route("/api/profile", methods=["PUT"])
def update_profile():
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO profile (id, name, title, bio, email, github, linkedin, location)
        VALUES (1,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO UPDATE SET
            name=EXCLUDED.name, title=EXCLUDED.title, bio=EXCLUDED.bio,
            email=EXCLUDED.email, github=EXCLUDED.github,
            linkedin=EXCLUDED.linkedin, location=EXCLUDED.location
    """, (
        data.get('name'), data.get('title'), data.get('bio'),
        data.get('email'), data.get('github'),
        data.get('linkedin'), data.get('location')
    ))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Profile updated"})


# ── Health check ──────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
