import os
import sqlite3
import secrets
from datetime import timedelta

import requests
from flask import Flask, redirect, request, session, jsonify
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(days=7)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8080")
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:5000/api/callback")
DB_PATH = os.environ.get("DB_PATH", "bot.db")

DISCORD_API = "https://discord.com/api/v10"
DISCORD_OAUTH = "https://discord.com/api/oauth2"

CORS(app, supports_credentials=True, origins=[FRONTEND_URL])


def get_db_account(discord_id: str):
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            "SELECT discord_id, account_id, code, verified, created_at FROM users WHERE discord_id = ?",
            (discord_id,),
        )
        row = cur.fetchone()
        con.close()
        if row:
            return dict(row)
        return None
    except Exception:
        return None


@app.route("/api/login")
def login():
    params = (
        f"client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={requests.utils.quote(REDIRECT_URI, safe='')}"
        f"&response_type=code"
        f"&scope=identify"
    )
    return redirect(f"{DISCORD_OAUTH}/authorize?{params}")


@app.route("/api/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect(f"{FRONTEND_URL}/dashboard.html?error=no_code")

    token_resp = requests.post(
        f"{DISCORD_OAUTH}/token",
        data={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if not token_resp.ok:
        return redirect(f"{FRONTEND_URL}/dashboard.html?error=token_failed")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")

    user_resp = requests.get(
        f"{DISCORD_API}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if not user_resp.ok:
        return redirect(f"{FRONTEND_URL}/dashboard.html?error=user_failed")

    user = user_resp.json()
    session.permanent = True
    session["discord_id"] = user["id"]
    session["username"] = user.get("username", "")
    session["avatar"] = user.get("avatar")

    return redirect(f"{FRONTEND_URL}/dashboard.html")


@app.route("/api/me")
def me():
    if "discord_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    discord_id = session["discord_id"]
    account = get_db_account(discord_id)

    return jsonify({
        "discord_id": discord_id,
        "username": session.get("username", ""),
        "avatar": session.get("avatar"),
        "account": account,
    })


@app.route("/api/logout")
def logout():
    session.clear()
    return redirect(f"{FRONTEND_URL}/")


if __name__ == "__main__":
    app.run(debug=False, port=5000)
