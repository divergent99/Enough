<div align="center">

# Enough

### You do not need to have the perfect words. You are enough.

A privacy-conscious AI wellbeing companion for grief, panic, overthinking, and the days when getting started feels impossible.

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--5.6%20%2B%20Realtime-111111?style=flat-square&logo=openai&logoColor=white)](https://developers.openai.com/)
[![PWA](https://img.shields.io/badge/PWA-Installable-5A0FC8?style=flat-square&logo=pwa&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)
[![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white)](https://railway.com/)
[![License](https://img.shields.io/badge/License-MIT-58705d?style=flat-square)](LICENSE)

[Live site — coming soon](https://youarenough.org) · [Report an issue](https://github.com/divergent99/Enough/issues) · [OpenAPI docs](http://localhost:8770/docs)

</div>

Enough is a free, gentle set of tools for the moments between therapy appointments, conversations, and better days. It helps someone slow down, name what is happening, make room for grief, and find one manageable next step—without pretending that AI can replace professional care or human connection.

![Enough AI companions](static/enough-agents.png)

## Why Enough

Loss and anxiety rarely arrive in neat sentences. Many wellbeing apps expect a person to already know what they feel, what tool they need, and how to explain it. Enough begins earlier than that.

1. Choose what feels closest: panic, racing thoughts, grief, or feeling stuck.
2. Follow a low-stimulation grounding path or speak naturally with a companion.
3. Turn the moment into a private, structured reflection.
4. Choose one compassionate next step—not an entire life plan.
5. Receive optional reminders only with explicit permission.

Enough is shaped by lived experience with grief, panic attacks, overthinking, medication, and therapy. Its purpose is not to “fix” a person. It is to remind them that a difficult moment does not make them inadequate.

## Highlights

- Adaptive support paths for panic, overthinking, grief, and low-energy days.
- Four step-by-step grounding exercises with clear pause and stop controls.
- Private journal, mood check-ins, memory space, and minimum-viable-day planning.
- GPT-5.6 structured reflections with an offline demo fallback.
- Five original philosophical companions with distinct personalities and Realtime voices.
- Live speech-to-speech conversations over WebRTC with rolling captions.
- One-click conversion of a voice conversation into a structured reflection.
- Consent-based “A Little Light” reminders through browser push or verified email.
- Optional accounts with single-use email verification and secure HttpOnly sessions.
- Installable Progressive Web App with an offline application shell.
- Local-first storage for sensitive reflections, memories, moods, and plans.
- India-focused support directory featuring Tele-MANAS and emergency services.

## Five companions, five ways of being present

| Companion | Presence | Voice | Approach |
|---|---|---|---|
| **Rowan** | Steady presence | Cedar | Grounded and unhurried; returns to what is here now |
| **Mira** | Quiet courage | Coral | Warm encouragement and beginnings small enough to attempt |
| **Elias** | Clear seeing | Echo | Separates the story in the mind from the present moment |
| **Anaya** | Gentle care | Marin | Makes room for grief without explaining or rushing it away |
| **Soren** | Wider horizon | Sage | Offers perspective while leaving space for uncertainty |

The companions are original characters. They know their own names, clearly identify themselves as AI, and never impersonate clinicians, real people, copyrighted characters, or deceased loved ones.

## More than a chat wrapper

GPT-5.6 is used for a bounded reflection task, while the Realtime API powers an explicitly initiated voice conversation. The browser owns the user experience and local private tools; the server protects credentials, sessions, verification, and scheduled delivery.

```text
User chooses a support path
             |
             v
   Grounding / journal / voice
       /             \
      v               v
local-first tools   Realtime companion
      \               /
       \             /
        GPT-5.6 reflection
               |
               v
       one gentle next step
```

Safety copy and crisis routing do not depend on the model inventing a response. Enough applies conservative checks before AI reflection and maintains a visible boundary: AI companion, not person or therapist.

## Architecture

```text
Browser PWA (HTML / CSS / JavaScript)
                 |
                 v
          FastAPI application
      /          |           \
     v           v            v
 accounts     reflection    Realtime session
 + SQLite     GPT-5.6       WebRTC / audio
     |                        |
     +---- notifications -----+
          Web Push / Resend
```

FastAPI serves both the frontend and API, keeping local development and Railway deployment in one service without cross-origin configuration.

## Run locally

Requirements: Python 3.12 or newer and a modern Chromium-based browser.

### Windows PowerShell

```powershell
git clone https://github.com/divergent99/Enough.git
cd Enough
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

### macOS or Linux

```bash
git clone https://github.com/divergent99/Enough.git
cd Enough
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Open [http://localhost:8770](http://localhost:8770). The grounding, journal, planning, and demo-reflection experiences work without API credentials. To enable live AI features, edit `.env`:

```env
OPENAI_API_KEY=your_secret_api_key
OPENAI_MODEL=gpt-5.6
OPENAI_REALTIME_MODEL=gpt-realtime-2.1
```

Never commit `.env` or expose service credentials in frontend code.

## Configuration

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Enables GPT reflection and Realtime conversations |
| `OPENAI_MODEL` | Reflection model; defaults to `gpt-5.6` |
| `OPENAI_REALTIME_MODEL` | Speech-to-speech model |
| `ENOUGH_DB_PATH` | SQLite database path |
| `APP_BASE_URL` | Public URL used in verification and unsubscribe links |
| `COOKIE_SECURE` | Must be `true` in production over HTTPS |
| `RESEND_API_KEY` | Enables verification and reminder email |
| `EMAIL_FROM` | Sender on a Resend-verified domain |
| `UNSUBSCRIBE_SECRET` | Signs one-click email opt-out links |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` | Enable scheduled browser push |
| `SCHEDULER_SECRET` | Protects the external notification runner |

See [`.env.example`](.env.example) for the complete safe template.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service readiness |
| `POST` | `/api/reflect` | Generate a structured GPT-5.6 reflection |
| `POST` | `/api/realtime/session` | Create a short-lived Realtime client session |
| `POST` | `/api/account/register` | Create an optional account |
| `POST` | `/api/account/login` | Start an HttpOnly account session |
| `GET` | `/api/account/me` | Read the current account and verification state |
| `GET` | `/api/account/verify-email` | Consume a single-use verification token |
| `GET/PUT` | `/api/notifications/preferences` | Read or update reminder preferences |
| `POST` | `/api/push/subscribe` | Store an authenticated Web Push subscription |
| `POST` | `/api/notifications/test-email` | Send a verified-address test email |
| `POST` | `/api/internal/notifications/run` | Run scheduled delivery with a protected secret |
| `GET` | `/docs` | Interactive OpenAPI documentation |

## Deploy on Railway

Enough is deployed as **one Railway service**. FastAPI already serves the static frontend, so a separate Vercel frontend is unnecessary.

1. Push this repository to GitHub.
2. In Railway, choose **New Project → Deploy from GitHub repo**.
3. Select `divergent99/Enough`.
4. Add a persistent volume mounted at `/data`.
5. Set `ENOUGH_DB_PATH=/data/enough.db`.
6. Set `COOKIE_SECURE=true` and `APP_BASE_URL=https://youarenough.org`.
7. Add OpenAI, Resend, VAPID, and scheduler secrets in Railway Variables.
8. Keep one replica while using SQLite and the built-in scheduler.
9. Generate a Railway domain, then connect `youarenough.org`.

Railway uses the included [`Dockerfile`](Dockerfile), [`railway.toml`](railway.toml), and `/api/health`. Container-local SQLite is ephemeral; the persistent volume is required for accounts and notification preferences.

For one replica, set `ENABLE_NOTIFICATION_SCHEDULER=true`. With multiple replicas, disable the built-in scheduler and call `POST /api/internal/notifications/run` from exactly one cron worker using the matching `X-Scheduler-Secret` header.

## Test

```bash
pytest -q
```

The suite covers reflection fallbacks, safety routing, account sessions, email ownership verification, notification preferences, unsubscribe behavior, and protected scheduling.

## Project structure

```text
enough/
|-- app/
|   |-- main.py            # FastAPI routes and static application
|   |-- companion.py       # reflection and companion behavior
|   |-- accounts.py        # users, verification, and sessions
|   |-- notifications.py   # email, push, preferences, scheduler
|   `-- models.py          # validated request and response models
|-- static/
|   |-- index.html         # application shell
|   |-- app.js             # private tools and primary interactions
|   |-- voice.js           # WebRTC Realtime conversation client
|   |-- agents.js          # companion selection and presentation
|   `-- sw.js              # offline shell and notifications
|-- tests/                 # automated API and safety checks
|-- Dockerfile
|-- railway.toml
|-- Procfile
`-- requirements.txt
```

## Privacy

Guest reflections, memories, plans, mood check-ins, and saved journal entries remain in browser storage. Text or audio reaches OpenAI only after the user explicitly starts the corresponding AI feature. Signed-in notification preferences, verified email ownership, sessions, and push subscriptions are stored server-side.

Enough does not sell personal data. Before a broad public launch, the project still requires a formal privacy policy, account deletion and retention controls, a security review, and documented processor terms.

## Scope and safety

Enough is not a therapist, medical device, crisis service, or substitute for professional care. It does not diagnose conditions, prescribe treatment, or recommend medication changes. Its conservative self-harm language routing is an MVP safeguard, not a clinically validated classifier.

If you or someone else may be in immediate danger, contact local emergency services. In India, Tele-MANAS is available at **14416** or **1-800-891-4416**.

Contributions are welcome, especially improvements to accessibility, privacy, localization, safety evaluation, and low-stimulation design. Features that simulate deceased people, encourage emotional dependency, make clinical claims, or conceal that a companion is AI are intentionally out of scope.

## License

Enough is available under the [MIT License](LICENSE).

---

<div align="center">

Built with care by [Abhineet Sharma](https://github.com/divergent99).

**Enough is not here to fix you. It is here to meet you where you are.**

</div>
