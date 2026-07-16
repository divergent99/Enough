from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import hashlib, json, os, sqlite3
from typing import Literal
import httpx
from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from .companion import reflect
from .models import ReflectionRequest, ReflectionResponse
from .models import AccountCreate, AccountLogin, NotificationPreferences, PushSubscription
from .accounts import authenticate, create_session, create_user, delete_session, get_preferences, init_db, remove_subscription, save_preferences, save_subscription, session_user, disable_notifications, notification_user, create_email_verification, delete_email_verification, verification_on_cooldown, verify_email
from .notifications import send_due_notifications, start_scheduler, stop_scheduler, valid_unsubscribe_token, send_email, send_verification_email

ROOT=Path(__file__).resolve().parent.parent
if os.getenv("ENOUGH_SKIP_DOTENV")!="1": load_dotenv(ROOT/".env",override=True)
STATIC=ROOT/"static"
@asynccontextmanager
async def lifespan(_app:FastAPI):
    if os.getenv('ENABLE_NOTIFICATION_SCHEDULER','false').lower()=='true': start_scheduler()
    yield
    stop_scheduler()

app=FastAPI(title="Enough",version="0.1.0",description="Gentle support for difficult moments",lifespan=lifespan)
app.mount("/static",StaticFiles(directory=STATIC),name="static")
init_db()
COOKIE_NAME="enough_session"
def current_user(enough_session:str|None=Cookie(default=None,alias=COOKIE_NAME)):
    user=session_user(enough_session)
    if not user: raise HTTPException(401,"Sign in required")
    return user
@app.get("/",include_in_schema=False)
def index(): return FileResponse(STATIC/"index.html")
@app.get("/sw.js",include_in_schema=False)
def service_worker(): return FileResponse(STATIC/"sw.js",media_type="application/javascript",headers={"Service-Worker-Allowed":"/","Cache-Control":"no-cache"})
@app.get("/api/health")
def health(): return {"status":"ready","product":"enough"}
@app.post("/api/reflect",response_model=ReflectionResponse)
def reflection(request:ReflectionRequest): return reflect(request)

REALTIME_STYLES={
    "sentinel":"steady, protective, grounded, and unhurried",
    "duelist":"direct, energising, concise, and focused on one achievable action",
    "strategist":"calm, analytical, and skilled at separating what matters from what can wait",
    "healer":"patient, compassionate, spacious, and respectful of grief",
    "wanderer":"reflective, philosophical, gentle, and comfortable with uncertainty",
}
REALTIME_NAMES={"sentinel":"Rowan","duelist":"Mira","strategist":"Elias","healer":"Anaya","wanderer":"Soren"}
REALTIME_MODES={"listen":"Mostly listen and reflect back what you heard. Ask at most one short question at a time.","untangle":"Help separate feelings, facts, and what can wait without diagnosing.","next_step":"Help identify exactly one very small, achievable next step."}
DEFAULT_REALTIME_VOICES={"sentinel":"cedar","duelist":"coral","strategist":"echo","healer":"marin","wanderer":"sage"}
REALTIME_VOICE_ENV={"sentinel":"ROWAN","duelist":"MIRA","strategist":"ELIAS","healer":"ANAYA","wanderer":"SOREN"}

@app.post("/api/realtime/session",response_class=PlainTextResponse)
async def realtime_session(request:Request,agent:Literal["sentinel","duelist","strategist","healer","wanderer"]="sentinel",mode:Literal["listen","untangle","next_step"]="listen",user=Depends(current_user)):
    api_key=os.getenv("OPENAI_API_KEY")
    if not api_key: raise HTTPException(503,"Realtime voice needs OPENAI_API_KEY")
    sdp=(await request.body()).decode("utf-8",errors="strict")
    if not sdp.strip() or len(sdp)>100_000: raise HTTPException(400,"Invalid WebRTC offer")
    companion_name=REALTIME_NAMES[agent]
    spelled_name="-".join(companion_name)
    instructions=f"""You are an openly identified AI companion inside Enough, never a human or therapist. Your companion name is {companion_name}, spelled {spelled_name}. If you refer to yourself by name, always use exactly {companion_name}; never rename, translate, or respell it. Your support style is {REALTIME_STYLES[agent]}. {REALTIME_MODES[mode]} Speak naturally in brief responses. Do not diagnose, prescribe, recommend medication changes, claim feelings, encourage dependency, or imitate any fictional or real person. Never use toxic positivity. If the user expresses explicit self-harm or suicide intent, clearly encourage immediate contact with a trusted person, local emergency services, or a crisis service; do not continue as their only source of support. Ordinary grief, anxiety, panic, or low mood is not automatically an emergency. Remind the user they can stop at any time."""
    voice=os.getenv(f"OPENAI_REALTIME_VOICE_{REALTIME_VOICE_ENV[agent]}",DEFAULT_REALTIME_VOICES[agent])
    session={"type":"realtime","model":os.getenv("OPENAI_REALTIME_MODEL","gpt-realtime-2.1"),"instructions":instructions,"audio":{"input":{"transcription":{"model":"gpt-realtime-whisper"},"turn_detection":{"type":"semantic_vad"}},"output":{"voice":voice}}}
    safety_id=hashlib.sha256(f"enough:{user['id']}".encode()).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            upstream=await client.post("https://api.openai.com/v1/realtime/calls",headers={"Authorization":f"Bearer {api_key}","OpenAI-Safety-Identifier":safety_id},files={"sdp":(None,sdp),"session":(None,json.dumps(session))})
    except httpx.HTTPError as exc: raise HTTPException(502,"Could not reach OpenAI Realtime") from exc
    if not upstream.is_success: raise HTTPException(502,"OpenAI Realtime session could not start")
    return PlainTextResponse(upstream.text,media_type="application/sdp")

@app.post("/api/account/register")
def register(data:AccountCreate,response:Response):
    try:user=create_user(data.email,data.name,data.password)
    except sqlite3.IntegrityError:raise HTTPException(409,"An account with this email already exists")
    verification_sent=False; token=create_email_verification(user['id'])
    try: send_verification_email(user['email'],user['name'],token); verification_sent=True
    except Exception: delete_email_verification(token)
    response.set_cookie(COOKIE_NAME,create_session(user['id']),httponly=True,samesite="lax",secure=os.getenv('COOKIE_SECURE','false').lower()=='true',max_age=2592000,path='/'); return {**user,"verification_sent":verification_sent}

@app.post("/api/account/login")
def login(data:AccountLogin,response:Response):
    user=authenticate(data.email,data.password)
    if not user: raise HTTPException(401,"Email or password is incorrect")
    response.set_cookie(COOKIE_NAME,create_session(user['id']),httponly=True,samesite="lax",secure=os.getenv('COOKIE_SECURE','false').lower()=='true',max_age=2592000,path='/'); return {"id":user['id'],"email":user['email'],"name":user['name'],"email_verified":user['email_verified']}

@app.post("/api/account/logout")
def logout(response:Response,enough_session:str|None=Cookie(default=None,alias=COOKIE_NAME)):
    delete_session(enough_session); response.delete_cookie(COOKIE_NAME,path='/'); return {"status":"signed-out"}

@app.get("/api/account/me")
def me(user=Depends(current_user)): return user

@app.get("/api/push/config")
def push_config(): return {"enabled":bool(os.getenv('VAPID_PUBLIC_KEY')),"public_key":os.getenv('VAPID_PUBLIC_KEY','')}

@app.post("/api/push/subscribe")
def subscribe(subscription:PushSubscription,user=Depends(current_user)):
    save_subscription(user['id'],subscription.model_dump()); return {"status":"subscribed"}

@app.delete("/api/push/subscribe")
def unsubscribe(endpoint:str,user=Depends(current_user)):
    remove_subscription(user['id'],endpoint); return {"status":"removed"}

@app.get("/api/notifications/preferences")
def notification_preferences(user=Depends(current_user)):
    return get_preferences(user['id']) or NotificationPreferences().model_dump()

@app.put("/api/notifications/preferences")
def update_notification_preferences(preferences:NotificationPreferences,user=Depends(current_user)):
    if preferences.enabled and preferences.delivery in ('email','both') and not user['email_verified']: raise HTTPException(403,'Verify your email before enabling email delivery')
    save_preferences(user['id'],preferences.model_dump()); return preferences

@app.post("/api/account/resend-verification")
def resend_verification(user=Depends(current_user)):
    if user['email_verified']: return {"status":"already-verified"}
    if verification_on_cooldown(user['id']): raise HTTPException(429,"Please wait a minute before requesting another link")
    token=create_email_verification(user['id'])
    try: send_verification_email(user['email'],user['name'],token)
    except Exception as exc:
        delete_email_verification(token); raise HTTPException(503,"Verification email could not be sent. Check the email configuration.") from exc
    return {"status":"sent","recipient":user['email']}

@app.get("/api/account/verify-email",response_class=HTMLResponse)
def verify_email_address(token:str):
    user=verify_email(token)
    if not user: raise HTTPException(400,"This verification link is invalid or has expired")
    return HTMLResponse("""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Email verified · Enough</title><style>:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;color:#292820;background:radial-gradient(circle at 18% 10%,rgba(182,199,175,.42),transparent 34%),radial-gradient(circle at 82% 88%,rgba(222,205,178,.42),transparent 36%),#f4efe7;font-family:Arial,sans-serif}.card{position:relative;width:min(620px,100%);padding:54px;border:1px solid rgba(95,87,73,.22);border-radius:32px;background:rgba(250,247,240,.92);box-shadow:0 28px 80px rgba(57,52,44,.16);overflow:hidden}.card:before{content:'';position:absolute;inset:0 auto 0 0;width:7px;background:#758a72}.mark{width:54px;height:54px;display:grid;place-items:center;border-radius:50%;background:#526655;color:#fff;font-size:26px;margin-bottom:30px}.kicker{font-size:11px;letter-spacing:.2em;color:#6f786b;margin:0 0 14px}h1{font:400 clamp(38px,7vw,58px)/1.02 Georgia,serif;margin:0 0 20px}p{font:17px/1.65 Georgia,serif;color:#5f5a52;margin:0 0 30px}.action{display:inline-block;padding:14px 22px;border-radius:999px;background:#292820;color:#fff;text-decoration:none;font-weight:600}.returning{display:block;margin-top:18px;font-size:12px;color:#827b70}@media(max-width:560px){.card{padding:38px 30px;border-radius:24px}}</style></head><body><main class="card"><div class="mark" aria-hidden="true">✓</div><p class="kicker">ENOUGH · ACCOUNT</p><h1>Your email is verified.</h1><p>A Little Light can now reach your inbox. Your original Enough window will update automatically.</p><a class="action" href="/?verified=1">Return to Enough</a><span class="returning">Taking you back in a moment…</span></main><script>try{new BroadcastChannel('enough-account').postMessage('email-verified')}catch(e){}try{localStorage.setItem('enough-email-verified',Date.now().toString())}catch(e){}setTimeout(()=>location.replace('/?verified=1'),3200)</script></body></html>""")
@app.post("/api/notifications/test-email")
def test_email_notification(user=Depends(current_user)):
    if not user['email_verified']: raise HTTPException(403,'Verify your email before sending a test email')
    try: send_email(user['email'],user['name'],"A little light","You do not need to finish everything to have done enough today.",user['id'])
    except Exception as exc: raise HTTPException(503,"Test email could not be sent. Check the Resend configuration and recipient address.") from exc
    return {"status":"sent","recipient":user['email']}
@app.get("/api/notifications/unsubscribe",response_class=HTMLResponse)
def unsubscribe_notifications(token:str):
    try: user_id=int(token.split('.',1)[0])
    except (ValueError,IndexError): raise HTTPException(400,"Invalid unsubscribe link")
    user=notification_user(user_id)
    if not user or not valid_unsubscribe_token(token,user_id,user['email']): raise HTTPException(400,"Invalid unsubscribe link")
    disable_notifications(user_id)
    return HTMLResponse("<main style='font-family:Georgia,serif;max-width:560px;margin:12vh auto;padding:32px'><h1>These notes are paused.</h1><p>Enough will not send another scheduled email or notification unless you turn A Little Light on again.</p><a href='/'>Return to Enough</a></main>")
@app.post("/api/internal/notifications/run")
def run_notifications(x_scheduler_secret:str|None=Header(default=None)):
    expected=os.getenv('SCHEDULER_SECRET')
    if not expected or x_scheduler_secret!=expected: raise HTTPException(403,"Scheduler authentication failed")
    return send_due_notifications()
