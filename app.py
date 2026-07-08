from flask import Flask, jsonify, request, g
from db   import get_connection, init_db
from auth import hash_password, check_password, create_token, login_required
import psycopg2
import psycopg2.extras

app = Flask(__name__)


@app.post("/auth/register")
def register():
    data = request.get_json()
    if not data:
        return jsonify({
            "error":"Request Body must be json"
        }),400
    username = data.get("username", "").strip()
    email = data.get("email","").strip()
    password = data.get("password","")

    if not username:
        return jsonify({"error":"username is required"}),400
    if not email:
        return jsonify({"error":"email is required"}),400
    if not password or len(password)<6:
        return jsonify({"error":"password must be at least 6 characters"}),400
    
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            """
            INSERT INTO users (username,email,password) VALUES (%s,%s,%s) RETURNING 
            id , username , email , created_at
            """,
            (username,email,hash_password(password))
        )
        user = dict(cur.fetchone())
        token = create_token(user["id"],user["username"])
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error":"username or email already taken"}),409
    finally:
        cur.close()
        conn.close()
    user["created_at"]=user["created_at"].isoformat()
    return jsonify({"user":user,"token":token}),201


@app.post("/auth/login")
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error":"Request body must be JSON"}),400
    email = data.get("email","").strp()
    password = data.get("password","")
    if not email or not password:
        return jsonify({"error":"email and password are required"}),400
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE email = %s",(email,))
    user=cur.fetchone()
    cur.close()
    conn.close()

    if not user or not check_password(password,user[password]):
        return jsonify({"error":"Invalid email or password"}),401
    token = create_token(user["id"],user["username"])
    return jsonify({
        "token":token,
        "user":{
            "id":user[id],
            "username":user["username"],
            "email":user["email"],
        }
    }),200


@app.get("/auth/me")
@login_required
def me():
    conn = get_connection()
    cur= conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id,username,email,created_at FROM users WHERE id = %s",(g.user_id,))
    user=cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({"error":"User not found"}),404
    user=dict(user)
    user["created_at"]=user["created_at"].isoformat()
    return jsonify(user),200

# ─────────────────────────────────────────────────────────────────────────────
# BLOG ROUTES
# GET    /blogs           → all blogs (public)
# GET    /blogs/<id>      → one blog (public)
# POST   /blogs           → create blog (protected)
# PATCH  /blogs/<id>      → update blog (protected, owner only)
# DELETE /blogs/<id>      → delete blog (protected, owner only)
# GET    /blogs/my        → my blogs (protected)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/blogs")
def get_all_blogs():
    """
    Public — anyone can read all blogs.
    Returns blogs joined with the author's username.
    Supports ?limit=10&offset=0 for pagination.
    """
    limit  = int(request.args.get("limit",  10))
    offset = int(request.args.get("offset",  0))

    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT
            b.id, b.title, b.content,
            b.created_at, b.updated_at,
            u.id       AS author_id,
            u.username AS author
        FROM blogs b
        JOIN users u ON b.user_id = u.id
        ORDER BY b.created_at DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset)
    )
    blogs = [serialize_blog(row) for row in cur.fetchall()]
    cur.close()
    conn.close()

    return jsonify(blogs), 200


@app.get("/blogs/my")
@login_required
def get_my_blogs():
    """Protected — returns only the authenticated user's blogs."""
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT
            b.id, b.title, b.content,
            b.created_at, b.updated_at,
            u.id AS author_id, u.username AS author
        FROM blogs b
        JOIN users u ON b.user_id = u.id
        WHERE b.user_id = %s
        ORDER BY b.created_at DESC
        """,
        (g.user_id,)
    )
    blogs = [serialize_blog(row) for row in cur.fetchall()]
    cur.close()
    conn.close()

    return jsonify(blogs), 200


@app.get("/blogs/<int:blog_id>")
def get_blog(blog_id):
    """Public — anyone can read a single blog."""
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT
            b.id, b.title, b.content,
            b.created_at, b.updated_at,
            u.id AS author_id, u.username AS author
        FROM blogs b
        JOIN users u ON b.user_id = u.id
        WHERE b.id = %s
        """,
        (blog_id,)
    )
    blog = cur.fetchone()
    cur.close()
    conn.close()

    if not blog:
        return jsonify({"error": "Blog not found"}), 404

    return jsonify(serialize_blog(blog)), 200


@app.post("/blogs")
@login_required
def create_blog():
    """Protected — only authenticated users can create a blog."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title   = data.get("title",   "").strip()
    content = data.get("content", "").strip()

    if not title:
        return jsonify({"error": "title is required"}), 400
    if not content:
        return jsonify({"error": "content is required"}), 400

    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        INSERT INTO blogs (user_id, title, content)
        VALUES (%s, %s, %s)
        RETURNING id, title, content, created_at, updated_at
        """,
        (g.user_id, title, content)
    )
    blog = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    blog["author_id"] = g.user_id
    blog["author"]    = g.username
    blog["created_at"] = blog["created_at"].isoformat()
    blog["updated_at"] = blog["updated_at"].isoformat()
    return jsonify(blog), 201


@app.patch("/blogs/<int:blog_id>")
@login_required
def update_blog(blog_id):
    """
    Protected + owner only.
    Partial update — send only the fields you want to change.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Fetch the blog first to check ownership
    cur.execute("SELECT * FROM blogs WHERE id = %s", (blog_id,))
    blog = cur.fetchone()

    if not blog:
        cur.close(); conn.close()
        return jsonify({"error": "Blog not found"}), 404

    if blog["user_id"] != g.user_id:
        cur.close(); conn.close()
        return jsonify({"error": "You can only edit your own blogs"}), 403

    # Build SET clause from only the fields provided
    updates = {}
    if "title" in data and data["title"].strip():
        updates["title"] = data["title"].strip()
    if "content" in data and data["content"].strip():
        updates["content"] = data["content"].strip()

    if not updates:
        cur.close(); conn.close()
        return jsonify({"error": "No valid fields to update"}), 400

    # Always bump updated_at on any change
    updates["updated_at"] = "now()"

    # Build dynamic SET clause
    set_parts = []
    values    = []
    for col, val in updates.items():
        if val == "now()":
            set_parts.append(f"{col} = now()")
        else:
            set_parts.append(f"{col} = %s")
            values.append(val)

    values.append(blog_id)

    cur.execute(
        f"""
        UPDATE blogs SET {', '.join(set_parts)}
        WHERE id = %s
        RETURNING id, user_id, title, content, created_at, updated_at
        """,
        values
    )
    updated = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    updated["author_id"] = g.user_id
    updated["author"]    = g.username
    updated["created_at"] = updated["created_at"].isoformat()
    updated["updated_at"] = updated["updated_at"].isoformat()
    return jsonify(updated), 200


@app.delete("/blogs/<int:blog_id>")
@login_required
def delete_blog(blog_id):
    """Protected + owner only."""
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM blogs WHERE id = %s", (blog_id,))
    blog = cur.fetchone()

    if not blog:
        cur.close(); conn.close()
        return jsonify({"error": "Blog not found"}), 404

    if blog["user_id"] != g.user_id:
        cur.close(); conn.close()
        return jsonify({"error": "You can only delete your own blogs"}), 403

    cur.execute("DELETE FROM blogs WHERE id = %s", (blog_id,))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": f"Blog {blog_id} deleted"}), 200


# ── Health check ──────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


# ── Helper: serialize a blog row (converts datetime → ISO string) ─────────
def serialize_blog(row: dict) -> dict:
    row = dict(row)
    if row.get("created_at"): row["created_at"] = row["created_at"].isoformat()
    if row.get("updated_at"): row["updated_at"] = row["updated_at"].isoformat()
    return row


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)