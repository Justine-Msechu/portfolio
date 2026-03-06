import os
import uuid
import hmac
import hashlib
import datetime
import urllib.parse
import urllib.request
import base64
from flask import Flask, request, jsonify, render_template
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(
    __name__,
    template_folder='../templates',
    static_folder='../static'
)

# ─────────────────────────────────────────────
# AWS S3 DIRECT UPLOAD — pure Python stdlib
# Browser sends file to Flask → Flask uploads to S3
# No boto3, no presigned URLs, no CORS issues
# ─────────────────────────────────────────────

def _hmac_bytes(key, msg_bytes):
    return hmac.new(key, msg_bytes, hashlib.sha256).digest()

def _hmac_str(key, msg_str):
    return _hmac_bytes(key, msg_str.encode("utf-8"))

def _s3_signing_key(secret, date_str, region):
    k = _hmac_str(("AWS4" + secret).encode("utf-8"), date_str)
    k = _hmac_str(k, region)
    k = _hmac_str(k, "s3")
    k = _hmac_str(k, "aws4_request")
    return k

def upload_to_s3(file_bytes, key, content_type,
                 bucket, region, access_key, secret_key):
    """Upload bytes directly to S3 using AWS Signature V4. Pure stdlib."""
    now          = datetime.datetime.now(datetime.timezone.utc)
    date_str     = now.strftime("%Y%m%d")
    datetime_str = now.strftime("%Y%m%dT%H%M%SZ")
    host         = f"{bucket}.s3.{region}.amazonaws.com"
    url          = f"https://{host}/{urllib.parse.quote(key, safe='/')}"

    # Hash the file bytes
    payload_hash = hashlib.sha256(file_bytes).hexdigest()

    # Canonical request — include x-amz-acl so object is publicly readable
    headers_to_sign = (f"content-type:{content_type}\nhost:{host}\n"
                       f"x-amz-acl:public-read\n"
                       f"x-amz-content-sha256:{payload_hash}\nx-amz-date:{datetime_str}\n")
    signed_headers  = "content-type;host;x-amz-acl;x-amz-content-sha256;x-amz-date"
    canonical = "\n".join(["PUT",
                           "/" + urllib.parse.quote(key, safe="/"),
                           "",
                           headers_to_sign,
                           signed_headers,
                           payload_hash])

    # String to sign
    cred_scope     = f"{date_str}/{region}/s3/aws4_request"
    string_to_sign = "\n".join(["AWS4-HMAC-SHA256", datetime_str, cred_scope,
                                hashlib.sha256(canonical.encode()).hexdigest()])

    # Signature
    signing_key = _s3_signing_key(secret_key, date_str, region)
    signature   = _hmac_str(signing_key, string_to_sign).hex()

    auth_header = (f"AWS4-HMAC-SHA256 Credential={access_key}/{cred_scope}, "
                   f"SignedHeaders={signed_headers}, Signature={signature}")

    req = urllib.request.Request(url, data=file_bytes, method="PUT")
    req.add_header("Authorization",          auth_header)
    req.add_header("Content-Type",           content_type)
    req.add_header("x-amz-date",             datetime_str)
    req.add_header("x-amz-content-sha256",   payload_hash)
    req.add_header("x-amz-acl",              "public-read")
    req.add_header("Content-Length",         str(len(file_bytes)))

    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status  # 200 on success


# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def get_db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(url, cursor_factory=RealDictCursor)

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY, title VARCHAR(200) NOT NULL,
            description TEXT NOT NULL, tech_stack TEXT[],
            github_url VARCHAR(300), live_url VARCHAR(300),
            featured BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS skills (
            id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL,
            category VARCHAR(100), level INTEGER CHECK (level BETWEEN 1 AND 100)
        );
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY DEFAULT 1, name VARCHAR(200),
            title VARCHAR(200), bio TEXT, email VARCHAR(200),
            github VARCHAR(300), linkedin VARCHAR(300),
            location VARCHAR(200), photo_url VARCHAR(500)
        );
    """)
    cur.execute("ALTER TABLE profile ADD COLUMN IF NOT EXISTS photo_url VARCHAR(500);")
    cur.execute("SELECT COUNT(*) AS cnt FROM profile")
    if cur.fetchone()["cnt"] == 0:
        cur.execute(
            "INSERT INTO profile (name,title,bio,email,github,linkedin,location,photo_url) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            ("Your Name","Full-Stack Developer & Tech Enthusiast",
             "Passionate developer based in Arusha, Tanzania.",
             "hello@yourname.dev","https://github.com/yourusername",
             "https://linkedin.com/in/yourname","Arusha, Tanzania","")
        )
    cur.execute("SELECT COUNT(*) AS cnt FROM projects")
    if cur.fetchone()["cnt"] == 0:
        for p in [
            ("ATC Smart Campus Assistant","AI-powered bilingual chatbot for Arusha Technical College.",["Flutter","Flask","PostgreSQL","OpenAI"],"https://github.com","",True),
            ("Tanzania Stays","Airbnb-style booking platform with M-Pesa payments.",["Flutter","Node.js","PostgreSQL"],"https://github.com","",True),
            ("Carbon Tracker","Blockchain carbon tracking for East Africa.",["Solidity","React","Node.js"],"https://github.com","",False),
        ]:
            cur.execute("INSERT INTO projects (title,description,tech_stack,github_url,live_url,featured) VALUES (%s,%s,%s,%s,%s,%s)", p)
    cur.execute("SELECT COUNT(*) AS cnt FROM skills")
    if cur.fetchone()["cnt"] == 0:
        for s in [
            ("Python","Backend",90),("Flask","Backend",85),("Node.js","Backend",80),
            ("Flutter","Mobile",85),("React","Frontend",75),("HTML/CSS","Frontend",90),
            ("PostgreSQL","Database",85),("MongoDB","Database",70),
            ("AWS S3","Cloud",75),("Alibaba Cloud","Cloud",70),("Vercel","Cloud",80),
            ("Docker","DevOps",70),("Git","Tools",90),("Linux","Tools",80),
            ("Cybersecurity","Security",75),("Blockchain","Web3",65),
        ]:
            cur.execute("INSERT INTO skills (name,category,level) VALUES (%s,%s,%s)", s)
    conn.commit(); cur.close(); conn.close()

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route("/")
def index():
    try:
        init_db()
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM profile WHERE id=1")
        profile = dict(cur.fetchone() or {})
        cur.execute("SELECT * FROM projects ORDER BY featured DESC, created_at DESC")
        projects = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM skills ORDER BY category, level DESC")
        skills = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        cats = {}
        for s in skills:
            cats.setdefault(s["category"] or "Other", []).append(s)
        return render_template("index.html", profile=profile, projects=projects, skills_by_cat=cats)
    except Exception as e:
        return f"<h2>Error</h2><pre>{e}</pre>", 500

@app.route("/flask/projects", methods=["GET"])
def get_projects():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM projects ORDER BY featured DESC, created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if r.get("created_at"): r["created_at"] = r["created_at"].isoformat()
    cur.close(); conn.close()
    return jsonify(rows)

@app.route("/flask/projects", methods=["POST"])
def create_project():
    d = request.get_json()
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO projects (title,description,tech_stack,github_url,live_url,featured) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (d.get("title"),d.get("description"),d.get("tech_stack",[]),
         d.get("github_url",""),d.get("live_url",""),d.get("featured",False))
    )
    nid = cur.fetchone()["id"]
    conn.commit(); cur.close(); conn.close()
    return jsonify({"id": nid}), 201

@app.route("/flask/projects/<int:pid>", methods=["DELETE"])
def delete_project(pid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM projects WHERE id=%s", (pid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Deleted"})

@app.route("/flask/profile", methods=["GET"])
def get_profile():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM profile WHERE id=1")
    row = cur.fetchone()
    cur.close(); conn.close()
    return jsonify(dict(row) if row else {})

@app.route("/flask/profile", methods=["PUT"])
def update_profile():
    d = request.get_json()
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO profile (id,name,title,bio,email,github,linkedin,location,photo_url)
        VALUES (1,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO UPDATE SET
            name=EXCLUDED.name, title=EXCLUDED.title, bio=EXCLUDED.bio,
            email=EXCLUDED.email, github=EXCLUDED.github,
            linkedin=EXCLUDED.linkedin, location=EXCLUDED.location,
            photo_url=EXCLUDED.photo_url
    """, (d.get("name"),d.get("title"),d.get("bio"),d.get("email"),
          d.get("github"),d.get("linkedin"),d.get("location"),d.get("photo_url","")))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Updated"})

@app.route("/flask/upload-photo", methods=["POST"])
def upload_photo():
    """
    Receive a photo from the browser as base64 JSON,
    upload directly to S3 using stdlib — no boto3 needed.
    Body: { "data": "base64string...", "type": "image/jpeg" }
    """
    aws_key    = os.environ.get("AWS_ACCESS_KEY_ID",    "")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY","")
    aws_bucket = os.environ.get("AWS_BUCKET_NAME",      "")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    missing = [k for k,v in {
        "AWS_ACCESS_KEY_ID":     aws_key,
        "AWS_SECRET_ACCESS_KEY": aws_secret,
        "AWS_BUCKET_NAME":       aws_bucket,
    }.items() if not v]
    if missing:
        return jsonify({"error": f"Missing env vars in Vercel: {', '.join(missing)}"}), 500

    try:
        d          = request.get_json(force=True) or {}
        b64_data   = d.get("data", "")
        file_type  = d.get("type", "image/jpeg")

        if not b64_data:
            return jsonify({"error": "No image data received"}), 400

        # Strip data URL prefix if present (e.g. "data:image/jpeg;base64,...")
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]

        file_bytes = base64.b64decode(b64_data)

        # Limit to 4MB (Vercel body limit is 4.5MB)
        if len(file_bytes) > 4 * 1024 * 1024:
            return jsonify({"error": "Photo too large. Please use a photo under 4MB."}), 400

        ext      = file_type.split("/")[-1].replace("jpeg","jpg")
        file_key = f"profile-photos/{uuid.uuid4()}.{ext}"

        upload_to_s3(file_bytes, file_key, file_type,
                     aws_bucket, aws_region, aws_key, aws_secret)

        public_url = f"https://{aws_bucket}.s3.{aws_region}.amazonaws.com/{file_key}"
        return jsonify({"url": public_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/flask/debug-aws")
def debug_aws():
    """Open yoursite.vercel.app/api/debug-aws in your browser to check env vars."""
    return jsonify({
        "AWS_ACCESS_KEY_ID":     "✅ SET" if os.environ.get("AWS_ACCESS_KEY_ID")     else "❌ MISSING",
        "AWS_SECRET_ACCESS_KEY": "✅ SET" if os.environ.get("AWS_SECRET_ACCESS_KEY") else "❌ MISSING",
        "AWS_BUCKET_NAME":       os.environ.get("AWS_BUCKET_NAME", "❌ MISSING"),
        "AWS_REGION":            os.environ.get("AWS_REGION",      "using default: us-east-1"),
    })

@app.route("/flask/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    app.run(debug=True, port=5000)
