import hashlib, hmac, html, json, os, threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import httpx
from .accounts import delete_subscription_id, due_notification_rows, mark_notification_sent, push_subscriptions_for_user

MESSAGES={
 "gentle":[("A little light","You do not need to finish everything to have done enough today."),("A little light","Make the next hour smaller. One kind step is still a step."),("A little light","Rest is not something you have to earn.")],
 "grief":[("Carrying love forward","Missing them today does not mean you are moving backward."),("Carrying love forward","You are allowed to remember without turning the memory into a lesson."),("Carrying love forward","Grief can share the day with ordinary moments. Neither cancels the other.")],
 "philosophy":[("Marcus Aurelius","The happiness of your life depends upon the quality of your thoughts."),("Epictetus","No man is free who is not master of himself."),("Seneca","Sometimes even to live is an act of courage.")],
 "poetry":[("A little light","Let this moment be unfinished. You may return when you have more to give."),("A little light","Some days are crossed quietly, one breath and one doorway at a time."),("A little light","The day asks only that you arrive as you are.")],
}

def due(row,now=None):
    now=now or datetime.now(timezone.utc)
    try: local=now.astimezone(ZoneInfo(row['timezone']))
    except ZoneInfoNotFoundError: return False
    hour,minute=map(int,row['time_local'].split(':'))
    if local.hour!=hour or local.minute!=minute or row['frequency']=='request': return False
    if not row.get('last_sent_at'): return True
    last=datetime.fromisoformat(row['last_sent_at']).astimezone(ZoneInfo(row['timezone']))
    if row['frequency']=='daily': return last.date()<local.date()
    return local-last>=timedelta(days=7)

def choose_message(theme,user_id,now=None):
    messages=MESSAGES.get(theme,MESSAGES['gentle']); day=(now or datetime.now(timezone.utc)).date().toordinal(); return messages[(day+user_id)%len(messages)]

def unsubscribe_token(user_id,email):
    secret=os.getenv('UNSUBSCRIBE_SECRET')
    if not secret: raise RuntimeError('UNSUBSCRIBE_SECRET is required for email delivery')
    value=f"{user_id}:{email.lower()}"
    signature=hmac.new(secret.encode(),value.encode(),hashlib.sha256).hexdigest()
    return f"{user_id}.{signature}"

def valid_unsubscribe_token(token,user_id,email):
    return hmac.compare_digest(token,unsubscribe_token(user_id,email))

def send_verification_email(to,name,token,email_fn=None):
    api_key=os.getenv('RESEND_API_KEY'); sender=os.getenv('EMAIL_FROM'); base=os.getenv('APP_BASE_URL')
    if not(api_key and sender and base): raise RuntimeError('Email delivery is not configured')
    url=f"{base.rstrip('/')}/api/account/verify-email?token={token}"
    payload={"from":sender,"to":[to],"subject":"Verify your email for Enough","text":f"Hello {name},\n\nVerify your email: {url}\n\nThis link expires in 24 hours.","html":f"<div style='font-family:Georgia,serif;max-width:560px;margin:auto;padding:32px;color:#292820'><p style='font:12px Arial,sans-serif;letter-spacing:.14em'>ENOUGH</p><h1 style='font-weight:400'>Verify your email</h1><p style='font-size:18px;line-height:1.65'>Confirm that {html.escape(to)} belongs to you before receiving A Little Light by email.</p><p><a href='{html.escape(url)}' style='display:inline-block;padding:13px 20px;background:#526655;color:white;text-decoration:none;border-radius:999px'>Verify my email</a></p><p style='font:12px Arial,sans-serif;color:#716d64;margin-top:32px'>This link expires in 24 hours. If you did not create an Enough account, you can ignore this message.</p></div>"}
    if email_fn: return email_fn(payload)
    response=httpx.post('https://api.resend.com/emails',headers={'Authorization':f'Bearer {api_key}','Content-Type':'application/json'},json=payload,timeout=20)
    response.raise_for_status(); return response.json()
def send_email(to,name,title,body,user_id,email_fn=None):
    api_key=os.getenv('RESEND_API_KEY'); sender=os.getenv('EMAIL_FROM')
    if not(api_key and sender): raise RuntimeError('Email delivery is not configured')
    base=os.environ['APP_BASE_URL'].rstrip('/')
    url=f"{base}/api/notifications/unsubscribe?token={unsubscribe_token(user_id,to)}"
    heading="" if title.strip().lower()=="a little light" else f"<h1 style='font-weight:400'>{html.escape(title)}</h1>"
    text_heading="" if not heading else f"{title}\n\n"
    payload={"from":sender,"to":[to],"subject":"A gentle note from Enough","text":f"{text_heading}{body}\n\nPause these notes: {url}","html":f"<div style='font-family:Georgia,serif;max-width:560px;margin:auto;padding:32px;color:#292820'><p style='font:12px Arial,sans-serif;letter-spacing:.14em'>A LITTLE LIGHT</p>{heading}<p style='font-size:18px;line-height:1.65'>{html.escape(body)}</p><p style='font:12px Arial,sans-serif;color:#716d64;margin-top:36px'>Sent because {html.escape(name)} opted in. <a href='{html.escape(url)}'>Pause these notes</a>.</p></div>"}
    if email_fn: return email_fn(payload)
    response=httpx.post('https://api.resend.com/emails',headers={'Authorization':f'Bearer {api_key}','Content-Type':'application/json','Idempotency-Key':f"enough-{user_id}-{datetime.now(timezone.utc).date().isoformat()}"},json=payload,timeout=20)
    response.raise_for_status(); return response.json()

def send_due_notifications(now=None,webpush_fn=None,email_fn=None):
    now=now or datetime.now(timezone.utc)
    public=os.getenv('VAPID_PUBLIC_KEY'); private=os.getenv('VAPID_PRIVATE_KEY'); subject=os.getenv('VAPID_SUBJECT')
    push_configured=bool(public and private and subject); email_configured=bool(os.getenv('RESEND_API_KEY') and os.getenv('EMAIL_FROM') and os.getenv('UNSUBSCRIBE_SECRET') and os.getenv('APP_BASE_URL'))
    if not(push_configured or email_configured): return {"status":"not-configured","sent":0,"expired":0,"failed":0}
    if webpush_fn is None and push_configured:
        from pywebpush import webpush
        webpush_fn=webpush
    sent=expired=failed=0; sent_users=set()
    for row in due_notification_rows():
        if not due(row,now): continue
        title,body=choose_message(row['theme'],row['user_id'],now); delivered=False
        if row['delivery'] in ('email','both'):
            if not row.get('email_verified_at'): failed+=1
            elif email_configured:
                try: send_email(row['email'],row['name'],title,body,row['user_id'],email_fn); sent+=1; delivered=True
                except Exception: failed+=1
            else: failed+=1
        if row['delivery'] in ('push','both'):
            subscriptions=push_subscriptions_for_user(row['user_id'])
            if not push_configured or not subscriptions: failed+=1
            else:
                for subscription in subscriptions:
                    try:
                        webpush_fn(subscription_info=json.loads(subscription['payload']),data=json.dumps({"title":title,"body":body,"url":"/?screen=light"}),vapid_private_key=private,vapid_claims={"sub":subject})
                        sent+=1; delivered=True
                    except Exception as exc:
                        status=getattr(getattr(exc,'response',None),'status_code',None)
                        if status in (404,410): delete_subscription_id(subscription['id']); expired+=1
                        else: failed+=1
        if delivered: sent_users.add(row['user_id'])
    stamp=now.isoformat()
    for user_id in sent_users: mark_notification_sent(user_id,stamp)
    return {"status":"completed","sent":sent,"expired":expired,"failed":failed}

_stop=threading.Event(); _thread=None
def start_scheduler():
    global _thread
    if _thread and _thread.is_alive(): return
    _stop.clear()
    def loop():
        while not _stop.wait(max(10,int(os.getenv('NOTIFICATION_POLL_SECONDS','30')))):
            try: send_due_notifications()
            except Exception: pass
    _thread=threading.Thread(target=loop,name='enough-notifications',daemon=True); _thread.start()
def stop_scheduler(): _stop.set()