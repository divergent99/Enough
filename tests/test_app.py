import os, tempfile, uuid
os.environ.pop("OPENAI_API_KEY",None)
os.environ["ENOUGH_SKIP_DOTENV"]="1"
os.environ["ENOUGH_DB_PATH"]=os.path.join(tempfile.gettempdir(),f"enough-test-{uuid.uuid4().hex}.db")
from fastapi.testclient import TestClient
from app.companion import is_urgent
from app.main import app
from app.accounts import create_email_verification
from app.notifications import due, send_due_notifications, send_email, unsubscribe_token, valid_unsubscribe_token
from datetime import datetime, timezone

client=TestClient(app)
def test_health(): assert client.get('/api/health').json()['status']=='ready'
def test_grief_reflection_is_not_escalated():
    r=client.post('/api/reflect',json={'moment':'grief','text':'I miss my mum and feel very low','energy':2,'preference':'untangle'})
    assert r.status_code==200 and r.json()['safety']=='support'
def test_explicit_self_harm_language_escalates(): assert is_urgent('I want to hurt myself')
def test_generic_low_mood_does_not_escalate(): assert not is_urgent('I feel low and anxious today')
def test_validation_rejects_blank_reflection(): assert client.post('/api/reflect',json={'moment':'stuck','text':'','energy':2,'preference':'untangle'}).status_code==422
def test_help_directory_contains_verified_india_numbers():
    page=client.get('/').text
    assert '14416' in page and '1800-89-14416' in page and 'tel:112' in page
def test_private_first_features_are_present():
    page=client.get('/').text
    assert 'id="grounding"' in page and 'id="journal"' in page and 'Continue as guest' in page
def test_account_session_lifecycle():
    email=f"person-{uuid.uuid4().hex[:8]}@example.com"
    registered=client.post('/api/account/register',json={'email':email,'name':'A','password':'a-safe-password'})
    assert registered.status_code==200
    assert client.get('/api/account/me').json()['email']==email
    assert client.post('/api/account/logout').status_code==200
    assert client.get('/api/account/me').status_code==401
def test_pwa_assets_and_service_worker_scope():
    assert client.get('/static/manifest.webmanifest').status_code==200
    worker=client.get('/sw.js')
    assert worker.status_code==200 and worker.headers['service-worker-allowed']=='/'
def test_grounding_interaction_assets_are_cache_busted():
    page=client.get('/').text
    css=client.get('/static/interaction-fix.css').text
    script=client.get('/static/app.js').text
    assert 'app.js?v=13' in page and '[hidden]{display:none!important}' in css
    assert 'startExercise' in script and "$('exerciseNext').addEventListener" in script
def test_notification_diagnostic_uses_direct_service_worker_api():
    script=client.get('/static/app.js').text
    assert 'registration.showNotification' in script
    assert 'updateNotificationStatus' in script
    assert 'requestPermissionWithTimeout' in script

def test_notification_preferences_require_account_and_round_trip():
    isolated=TestClient(app)
    assert isolated.get('/api/notifications/preferences').status_code==401
    email=f"light-{uuid.uuid4().hex[:8]}@example.com"
    assert isolated.post('/api/account/register',json={'email':email,'name':'Light','password':'a-safe-password'}).status_code==200
    payload={'enabled':True,'theme':'grief','frequency':'weekly','time_local':'21:15','timezone':'Asia/Kolkata','delivery':'push'}
    assert isolated.put('/api/notifications/preferences',json=payload).json()==payload
    assert isolated.get('/api/notifications/preferences').json()=={**payload,'last_sent_at':None}

def test_timezone_aware_due_calculation():
    row={'timezone':'Asia/Kolkata','time_local':'09:00','frequency':'daily','last_sent_at':None}
    assert due(row,datetime(2026,7,16,3,30,tzinfo=timezone.utc))
    assert not due(row,datetime(2026,7,16,3,29,tzinfo=timezone.utc))

def test_sender_is_honest_when_vapid_is_not_configured(monkeypatch):
    monkeypatch.delenv('VAPID_PUBLIC_KEY',raising=False)
    monkeypatch.delenv('VAPID_PRIVATE_KEY',raising=False)
    monkeypatch.delenv('VAPID_SUBJECT',raising=False)
    assert send_due_notifications()['status']=='not-configured'

def test_email_button_uses_email_endpoint(monkeypatch):
    isolated=TestClient(app)
    email=f"email-test-{uuid.uuid4().hex[:8]}@example.com"
    assert isolated.post('/api/account/register',json={'email':email,'name':'Email Test','password':'a-safe-password'}).status_code==200
    assert isolated.post('/api/notifications/test-email').status_code==403
    token=create_email_verification(isolated.get('/api/account/me').json()['id'])
    verified=isolated.get('/api/account/verify-email',params={'token':token})
    assert verified.status_code==200 and 'enough-account' in verified.text and 'Taking you back' in verified.text
    assert isolated.get('/api/account/verify-email',params={'token':token}).status_code==400
    assert isolated.get('/api/account/me').json()['email_verified'] is True
    monkeypatch.setattr('app.main.send_email',lambda *args,**kwargs: {'id':'test'})
    response=isolated.post('/api/notifications/test-email')
    assert response.status_code==200 and response.json()['recipient']==email
    script=isolated.get('/static/app.js').text
    assert '/api/notifications/test-email' in script and 'testEmailNotification' in script
def test_unverified_email_cannot_enable_email_delivery():
    isolated=TestClient(app)
    email=f"unverified-{uuid.uuid4().hex[:8]}@example.com"
    isolated.post('/api/account/register',json={'email':email,'name':'Unverified','password':'a-safe-password'})
    payload={'enabled':True,'theme':'gentle','frequency':'daily','time_local':'09:00','timezone':'Asia/Kolkata','delivery':'email'}
    response=isolated.put('/api/notifications/preferences',json=payload)
    assert response.status_code==403 and 'Verify your email' in response.json()['detail']
def test_email_delivery_is_private_and_unsubscribable(monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY','test-key')
    monkeypatch.setenv('EMAIL_FROM','Enough <notes@example.com>')
    monkeypatch.setenv('UNSUBSCRIBE_SECRET','test-unsubscribe-secret')
    monkeypatch.setenv('APP_BASE_URL','https://enough.example')
    captured=[]
    send_email('person@example.com','Ava','A little light','Rest is allowed.',42,captured.append)
    payload=captured[0]
    assert payload['subject']=='A gentle note from Enough'
    assert 'person@example.com' not in payload['html']
    assert '/api/notifications/unsubscribe?token=' in payload['html']
    assert payload['html'].count('A LITTLE LIGHT')==1 and '<h1' not in payload['html']
    token=unsubscribe_token(42,'person@example.com')
    assert valid_unsubscribe_token(token,42,'person@example.com')
    assert not valid_unsubscribe_token(token,43,'person@example.com')

def test_both_delivery_is_accepted():
    from app.models import NotificationPreferences
    assert NotificationPreferences(delivery='both').delivery=='both'
def test_internal_scheduler_endpoint_is_protected(monkeypatch):
    monkeypatch.setenv('SCHEDULER_SECRET','test-scheduler-secret')
    assert client.post('/api/internal/notifications/run').status_code==403
    response=client.post('/api/internal/notifications/run',headers={'X-Scheduler-Secret':'test-scheduler-secret'})
    assert response.status_code==200 and response.json()['status']=='not-configured'

def test_agent_selection_reaches_structured_reflection():
    response=client.post('/api/reflect',json={'moment':'grief','text':'I miss someone today','energy':2,'preference':'listen','agent':'healer'})
    assert response.status_code==200 and response.json()['safety']=='support'
    assert client.get('/static/agents.js').status_code==200
    assert client.get('/static/enough-agents.png').status_code==200

def test_unknown_agent_is_rejected():
    response=client.post('/api/reflect',json={'moment':'stuck','text':'I cannot begin','energy':1,'preference':'next_step','agent':'copyrighted-hero'})
    assert response.status_code==422

def test_voice_assets_are_present_and_api_key_stays_server_side():
    page=client.get('/').text
    script=client.get('/static/voice.js').text
    assert 'voice.js?v=2' in page and 'RTCPeerConnection' in script
    assert '/api/realtime/session' in script and 'OPENAI_API_KEY' not in script

def test_companions_use_human_philosophical_names_not_tactical_titles():
    agents=client.get('/static/agents.js').text
    assert all(name in agents for name in ['Rowan','Mira','Elias','Anaya','Soren'])
    assert all(title not in agents for title in ['The Sentinel','The Duelist','The Strategist','The Healer','The Wanderer'])

def test_companions_have_distinct_supported_realtime_voices():
    from app.main import DEFAULT_REALTIME_VOICES
    supported={'alloy','ash','ballad','coral','echo','sage','shimmer','verse','marin','cedar'}
    assert len(DEFAULT_REALTIME_VOICES)==5
    assert len(set(DEFAULT_REALTIME_VOICES.values()))==5
    assert set(DEFAULT_REALTIME_VOICES.values()) <= supported

def test_realtime_companions_have_public_names():
    from app.main import REALTIME_NAMES
    assert REALTIME_NAMES=={'sentinel':'Rowan','duelist':'Mira','strategist':'Elias','healer':'Anaya','wanderer':'Soren'}

def test_companion_copy_has_a_stable_three_line_box():
    css=client.get('/static/agents-layout.css').text
    assert '-webkit-line-clamp: 3' in css and 'min-height: 4.2em' in css
def test_realtime_session_requires_authentication():
    isolated=TestClient(app)
    response=isolated.post('/api/realtime/session',params={'agent':'sentinel','mode':'listen'},headers={'Content-Type':'application/sdp'},content='v=0')
    assert response.status_code==401

def test_realtime_session_reports_missing_api_configuration():
    isolated=TestClient(app)
    email=f"voice-{uuid.uuid4().hex[:8]}@example.com"
    assert isolated.post('/api/account/register',json={'email':email,'name':'Voice','password':'a-safe-password'}).status_code==200
    response=isolated.post('/api/realtime/session',headers={'Content-Type':'application/sdp'},content='v=0')
    assert response.status_code==503 and 'OPENAI_API_KEY' in response.json()['detail']
