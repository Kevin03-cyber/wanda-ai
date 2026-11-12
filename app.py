import json
import sqlite3
import requests
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"
DB = "wanda.db"
CURRENT_USER = 1  # placeholder until login is added
MAX_HISTORY = 20  # last N messages sent to the model (keeps CPU fast)

SYSTEM_PROMPT = (
    "You are Wanda, a helpful AI assistant. "
    "Answer clearly and accurately. "
    "Never invent facts, names, titles, or dates. "
    "If you are not sure, say 'I'm not sure' instead of guessing."
)

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS chats(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New chat',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

def own_chat(c, chat_id):
    return c.execute("SELECT * FROM chats WHERE id=? AND user_id=?",
                     (chat_id, CURRENT_USER)).fetchone()

@app.route("/api/chats", methods=["POST"])
def create_chat():
    with db() as c:
        cur = c.execute("INSERT INTO chats(user_id) VALUES(?)", (CURRENT_USER,))
        return jsonify({"id": cur.lastrowid, "title": "New chat"}), 201

@app.route("/api/chats", methods=["GET"])
def list_chats():
    with db() as c:
        rows = c.execute("SELECT id, title, created_at FROM chats "
                         "WHERE user_id=? ORDER BY id DESC", (CURRENT_USER,)).fetchall()
        return jsonify([dict(r) for r in rows])

@app.route("/api/chats/<int:chat_id>", methods=["GET"])
def get_chat(chat_id):
    with db() as c:
        if not own_chat(c, chat_id):
            return jsonify({"error": "chat not found"}), 404
        rows = c.execute("SELECT role, content, created_at FROM messages "
                         "WHERE chat_id=? ORDER BY id", (chat_id,)).fetchall()
        return jsonify([dict(r) for r in rows])

@app.route("/api/chats/<int:chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    with db() as c:
        if not own_chat(c, chat_id):
            return jsonify({"error": "chat not found"}), 404
        c.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
        c.execute("DELETE FROM chats WHERE id=?", (chat_id,))
    return jsonify({"deleted": chat_id})

@app.route("/api/chats/<int:chat_id>/message", methods=["POST"])
def send_message(chat_id):
    data = request.get_json(silent=True) or {}
    text = (data.get("message") or "").strip()
    if not text:
        return jsonify({"error": "message is required"}), 400

    with db() as c:
        chat = own_chat(c, chat_id)
        if not chat:
            return jsonify({"error": "chat not found"}), 404
        c.execute("INSERT INTO messages(chat_id, role, content) VALUES(?,?,?)",
                  (chat_id, "user", text))
        if chat["title"] == "New chat":
            c.execute("UPDATE chats SET title=? WHERE id=?", (text[:40], chat_id))
        history = c.execute(
            "SELECT role, content FROM messages WHERE chat_id=? "
            "ORDER BY id DESC LIMIT ?", (chat_id, MAX_HISTORY)).fetchall()[::-1]

    payload = {
        "model": MODEL,
        "stream": True,
        "options": {"temperature": 0.2},
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}]
                    + [dict(h) for h in history],
    }

    def generate():
        parts = []
        try:
            with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=300) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    piece = json.loads(line).get("message", {}).get("content", "")
                    if piece:
                        parts.append(piece)
                        yield piece
        except requests.RequestException as e:
            yield f"\n\n[Ollama problem: {e}]"
            return
        answer = "".join(parts)
        if answer:
            with db() as c:
                c.execute("INSERT INTO messages(chat_id, role, content) VALUES(?,?,?)",
                          (chat_id, "assistant", answer))

    return Response(stream_with_context(generate()), mimetype="text/plain")
@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    init_db()
    app.run(port=5004, debug=True)