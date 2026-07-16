# Enough

> You do not need to have the perfect words. You are enough.

Enough is a free, privacy-conscious wellbeing companion for grief, panic, overthinking, and low-energy days. It offers grounding exercises, private reflection, gentle reminders, and real-time conversations with five original AI companions—without pretending to replace therapy, medical care, or human connection.

## Why Enough exists

Loss can make even ordinary moments feel impossibly heavy. Enough is designed for the space between appointments and conversations: the moment when someone needs help slowing down, naming what is happening, or finding one manageable next step.

It is not a diagnosis engine or an artificial therapist. It is a calm set of tools that meets people where they are.

## Highlights

- Four adaptive support paths for panic, overthinking, grief, and feeling stuck
- Step-by-step grounding exercises with clear pause and stop controls
- Private journal, mood check-ins, memory space, and minimum-viable-day planning
- GPT-5.6 structured reflections with a safe offline fallback
- Five original philosophical companions with distinct personalities and voices
- Real-time speech-to-speech conversations over WebRTC with live captions
- Optional conversion of a voice conversation into a structured reflection
- Consent-based “A Little Light” reminders through browser push or email
- Installable Progressive Web App with an offline application shell
- Optional accounts with email verification and secure, HttpOnly sessions
- India-focused support directory featuring Tele-MANAS and emergency services
- Local-first storage for sensitive reflections, plans, memories, and moods

## The companions

| Companion | Presence | Approach |
| --- | --- | --- |
| Rowan | Steady presence | Grounded, patient, and focused on what is here now |
| Mira | Quiet courage | Warm encouragement and small beginnings |
| Elias | Clear seeing | Separates the story in the mind from the present moment |
| Anaya | Gentle care | Makes room for grief without rushing it away |
| Soren | Wider horizon | Reflective perspective for uncertainty and change |

The companions are original characters. They identify themselves as AI and do not impersonate real people, fictional franchises, clinicians, or deceased loved ones.

## Tech stack

- FastAPI and Python
- Vanilla HTML, CSS, and JavaScript
- OpenAI GPT-5.6 and Realtime API
- WebRTC and browser speech captions
- SQLite with scrypt password hashing
- Resend for transactional email
- Web Push with VAPID
- Progressive Web App service worker
- Railway-ready Docker deployment

## Run locally

Requirements: Python 3.12+ and a modern Chromium-based browser.

```powershell
git clone https://github.com/divergent99/Enough.git
cd Enough
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

Open [http://localhost:8770](http://localhost:8770). Core tools and demo reflections work without API credentials. Add `OPENAI_API_KEY` to `.env` to enable live AI features. Never commit `.env`.

## Configuration

Copy `.env.example` to `.env` and configure only the services you want to enable.

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Enables GPT reflection and Realtime conversations |
| `OPENAI_MODEL` | Reflection model; defaults to `gpt-5.6` |
| `OPENAI_REALTIME_MODEL` | Realtime voice model |
| `ENOUGH_DB_PATH` | SQLite database location |
| `APP_BASE_URL` | Public URL used in verification and unsubscribe links |
| `COOKIE_SECURE` | Must be `true` when deployed over HTTPS |
| `RESEND_API_KEY` | Enables verification and reminder emails |
| `EMAIL_FROM` | Sender on a Resend-verified domain |
| `UNSUBSCRIBE_SECRET` | Signs one-click email opt-out links |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | Enable scheduled browser push |
| `SCHEDULER_SECRET` | Protects the external scheduler endpoint |

The full, safe template is in `.env.example`.

## Test

```powershell
pytest -q
```

## Deploy to Railway

1. Create a Railway project from this GitHub repository.
2. Add a persistent volume mounted at `/data`.
3. Set `ENOUGH_DB_PATH=/data/enough.db`.
4. Set `COOKIE_SECURE=true` and `APP_BASE_URL=https://youarenough.org`.
5. Add the required OpenAI, Resend, VAPID, and scheduler secrets in Railway Variables.
6. Keep one replica while using SQLite and the built-in scheduler.
7. Generate a Railway domain, then connect the custom domain and copy Railway’s DNS records to the registrar.

Railway uses `Dockerfile`, `railway.toml`, and `/api/health` from this repository. Container-local SQLite is ephemeral, so the persistent volume is required for accounts and notification preferences.

For one replica, set `ENABLE_NOTIFICATION_SCHEDULER=true`. For multiple replicas, disable the built-in scheduler and invoke `POST /api/internal/notifications/run` from exactly one cron worker using the matching `X-Scheduler-Secret` header.

## Privacy

Guest reflections, memories, plans, mood check-ins, and saved journal entries stay in browser storage. Reflection text or audio reaches OpenAI only after the user explicitly starts the corresponding AI feature. Signed-in notification preferences, verified email ownership, sessions, and push subscriptions are stored server-side.

Enough does not sell personal data. Before a broad public launch, the project still needs a formal privacy policy, retention/deletion controls, security review, and documented data-processing terms.

## Safety boundary

Enough is not a therapist, medical device, crisis service, or substitute for professional care. It does not diagnose conditions, prescribe treatment, or recommend medication changes. Conservative pre-processing detects explicit self-harm language and directs users toward immediate human support, but this is an MVP safeguard—not a clinically validated system.

If you or someone else may be in immediate danger, contact local emergency services. In India, Tele-MANAS can be reached at **14416** or **1-800-891-4416**.

## Responsible contribution

Contributions are welcome, especially improvements to accessibility, privacy, localization, safety testing, and low-stimulation interaction design. Please do not submit features that simulate deceased people, encourage dependency on AI, make clinical claims, or hide the fact that a companion is artificial.

## License

Released under the [MIT License](LICENSE).

---

Built with care by [Abhineet Sharma](https://github.com/divergent99).
