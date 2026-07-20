import hashlib, hmac, json, os, secrets, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH=Path(os.getenv("ENOUGH_DB_PATH",Path(__file__).resolve().parent.parent/"enough.db"))
SESSION_DAYS=30

def connection():
    db=sqlite3.connect(DB_PATH); db.row_factory=sqlite3.Row; db.execute("PRAGMA foreign_keys=ON"); return db

def init_db():
    with connection() as db:
        db.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password_hash TEXT NOT NULL,created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL,expires_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);CREATE TABLE IF NOT EXISTS push_subscriptions(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,endpoint TEXT UNIQUE NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);CREATE TABLE IF NOT EXISTS notification_preferences(user_id INTEGER PRIMARY KEY,enabled INTEGER NOT NULL DEFAULT 0,theme TEXT NOT NULL DEFAULT 'gentle',frequency TEXT NOT NULL DEFAULT 'daily',time_local TEXT NOT NULL DEFAULT '09:00',timezone TEXT NOT NULL DEFAULT 'UTC',delivery TEXT NOT NULL DEFAULT 'in-app',last_sent_at TEXT,updated_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);CREATE TABLE IF NOT EXISTS email_verification_tokens(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL,expires_at TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);CREATE TABLE IF NOT EXISTS password_reset_tokens(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL,expires_at TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);""")
        columns={row['name'] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        if 'email_verified_at' not in columns: db.execute("ALTER TABLE users ADD COLUMN email_verified_at TEXT")

def public_user(row):
    return {"id":row['id'],"email":row['email'],"name":row['name'],"email_verified":bool(row['email_verified_at'])}

def hash_password(password,salt=None):
    salt=salt or secrets.token_bytes(16); digest=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32); return f"scrypt${salt.hex()}${digest.hex()}"

def verify_password(password,stored):
    try: _,salt,digest=stored.split('$'); return hmac.compare_digest(hash_password(password,bytes.fromhex(salt)).split('$')[2],digest)
    except (ValueError,TypeError): return False

def create_user(email,name,password):
    now=datetime.now(timezone.utc).isoformat()
    with connection() as db:
        cursor=db.execute("INSERT INTO users(email,name,password_hash,created_at) VALUES(?,?,?,?)",(email.lower().strip(),name.strip(),hash_password(password),now)); row=db.execute("SELECT * FROM users WHERE id=?",(cursor.lastrowid,)).fetchone(); return public_user(row)

def authenticate(email,password):
    with connection() as db: row=db.execute("SELECT * FROM users WHERE email=?",(email.lower().strip(),)).fetchone()
    return ({**dict(row),**public_user(row)} if row and verify_password(password,row['password_hash']) else None)

def create_session(user_id):
    token=secrets.token_urlsafe(32); token_hash=hashlib.sha256(token.encode()).hexdigest(); expires=(datetime.now(timezone.utc)+timedelta(days=SESSION_DAYS)).isoformat()
    with connection() as db: db.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",(token_hash,user_id,expires))
    return token

def session_user(token):
    if not token:return None
    token_hash=hashlib.sha256(token.encode()).hexdigest(); now=datetime.now(timezone.utc).isoformat()
    with connection() as db: row=db.execute("SELECT users.* FROM sessions JOIN users ON users.id=sessions.user_id WHERE token_hash=? AND expires_at>?",(token_hash,now)).fetchone()
    return public_user(row) if row else None

def delete_session(token):
    if token:
        with connection() as db: db.execute("DELETE FROM sessions WHERE token_hash=?",(hashlib.sha256(token.encode()).hexdigest(),))

def create_email_verification(user_id):
    token=secrets.token_urlsafe(32); now=datetime.now(timezone.utc); token_hash=hashlib.sha256(token.encode()).hexdigest()
    with connection() as db:
        db.execute("DELETE FROM email_verification_tokens WHERE user_id=?",(user_id,)); db.execute("INSERT INTO email_verification_tokens(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)",(token_hash,user_id,(now+timedelta(hours=24)).isoformat(),now.isoformat()))
    return token

def verification_on_cooldown(user_id,seconds=60):
    with connection() as db: row=db.execute("SELECT created_at FROM email_verification_tokens WHERE user_id=? ORDER BY created_at DESC LIMIT 1",(user_id,)).fetchone()
    return bool(row and datetime.fromisoformat(row['created_at'])>datetime.now(timezone.utc)-timedelta(seconds=seconds))

def delete_email_verification(token):
    with connection() as db: db.execute("DELETE FROM email_verification_tokens WHERE token_hash=?",(hashlib.sha256(token.encode()).hexdigest(),))

def verify_email(token):
    token_hash=hashlib.sha256(token.encode()).hexdigest(); now=datetime.now(timezone.utc)
    with connection() as db:
        row=db.execute("SELECT user_id,expires_at FROM email_verification_tokens WHERE token_hash=?",(token_hash,)).fetchone()
        if not row or datetime.fromisoformat(row['expires_at'])<=now: return None
        db.execute("UPDATE users SET email_verified_at=? WHERE id=?",(now.isoformat(),row['user_id'])); db.execute("DELETE FROM email_verification_tokens WHERE user_id=?",(row['user_id'],)); user=db.execute("SELECT * FROM users WHERE id=?",(row['user_id'],)).fetchone(); return public_user(user)

def create_password_reset(email):
    normalized=email.lower().strip(); now=datetime.now(timezone.utc)
    with connection() as db:
        user=db.execute("SELECT id,email,name FROM users WHERE email=?",(normalized,)).fetchone()
        if not user: return None
        recent=db.execute("SELECT created_at FROM password_reset_tokens WHERE user_id=? ORDER BY created_at DESC LIMIT 1",(user['id'],)).fetchone()
        if recent and datetime.fromisoformat(recent['created_at'])>now-timedelta(seconds=60): return {"cooldown":True,**dict(user)}
        token=secrets.token_urlsafe(32); token_hash=hashlib.sha256(token.encode()).hexdigest()
        db.execute("DELETE FROM password_reset_tokens WHERE user_id=?",(user['id'],))
        db.execute("INSERT INTO password_reset_tokens(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)",(token_hash,user['id'],(now+timedelta(hours=1)).isoformat(),now.isoformat()))
        return {"token":token,"cooldown":False,**dict(user)}

def delete_password_reset(token):
    with connection() as db: db.execute("DELETE FROM password_reset_tokens WHERE token_hash=?",(hashlib.sha256(token.encode()).hexdigest(),))

def reset_password(token,password):
    token_hash=hashlib.sha256(token.encode()).hexdigest(); now=datetime.now(timezone.utc)
    with connection() as db:
        row=db.execute("SELECT user_id,expires_at FROM password_reset_tokens WHERE token_hash=?",(token_hash,)).fetchone()
        if not row or datetime.fromisoformat(row['expires_at'])<=now: return False
        db.execute("UPDATE users SET password_hash=? WHERE id=?",(hash_password(password),row['user_id']))
        db.execute("DELETE FROM password_reset_tokens WHERE user_id=?",(row['user_id'],))
        db.execute("DELETE FROM sessions WHERE user_id=?",(row['user_id'],))
        return True

def save_subscription(user_id,payload):
    endpoint=payload.get('endpoint','')
    with connection() as db: db.execute("INSERT INTO push_subscriptions(user_id,endpoint,payload,created_at) VALUES(?,?,?,?) ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id,payload=excluded.payload",(user_id,endpoint,json.dumps(payload),datetime.now(timezone.utc).isoformat()))
def remove_subscription(user_id,endpoint):
    with connection() as db: db.execute("DELETE FROM push_subscriptions WHERE user_id=? AND endpoint=?",(user_id,endpoint))
def save_preferences(user_id,prefs):
    values=(user_id,int(prefs['enabled']),prefs['theme'],prefs['frequency'],prefs['time_local'],prefs['timezone'],prefs['delivery'],datetime.now(timezone.utc).isoformat())
    with connection() as db: db.execute("INSERT INTO notification_preferences(user_id,enabled,theme,frequency,time_local,timezone,delivery,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET enabled=excluded.enabled,theme=excluded.theme,frequency=excluded.frequency,time_local=excluded.time_local,timezone=excluded.timezone,delivery=excluded.delivery,updated_at=excluded.updated_at",values)
def get_preferences(user_id):
    with connection() as db: row=db.execute("SELECT enabled,theme,frequency,time_local,timezone,delivery,last_sent_at FROM notification_preferences WHERE user_id=?",(user_id,)).fetchone()
    return ({**dict(row),"enabled":bool(row['enabled'])} if row else None)
def due_notification_rows():
    with connection() as db: rows=db.execute("SELECT p.*,u.name,u.email,u.email_verified_at FROM notification_preferences p JOIN users u ON u.id=p.user_id WHERE p.enabled=1 AND p.delivery IN ('push','email','both')").fetchall()
    return [dict(row) for row in rows]
def push_subscriptions_for_user(user_id):
    with connection() as db: rows=db.execute("SELECT id,payload FROM push_subscriptions WHERE user_id=?",(user_id,)).fetchall()
    return [dict(row) for row in rows]
def disable_notifications(user_id):
    with connection() as db: db.execute("UPDATE notification_preferences SET enabled=0,updated_at=? WHERE user_id=?",(datetime.now(timezone.utc).isoformat(),user_id))
def notification_user(user_id):
    with connection() as db: row=db.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
    return public_user(row) if row else None
def mark_notification_sent(user_id,when):
    with connection() as db: db.execute("UPDATE notification_preferences SET last_sent_at=? WHERE user_id=?",(when,user_id))
def delete_subscription_id(subscription_id):
    with connection() as db: db.execute("DELETE FROM push_subscriptions WHERE id=?",(subscription_id,))