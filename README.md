# NHSM Hub

Student-run study platform for the **National Higher School of Mathematics (NHSM, Algeria)**.
It started as a resource library (filter course notes by semester / module / type and open
them from Google Drive) and is growing into a daily-use study platform.

This is a **Django + DRF** app: HTML is server-rendered with Django templates; JSON is served
by Django REST Framework only where the front-end needs it (e.g. live search). The front-end
is vanilla HTML/CSS/JS — no SPA framework.

---

## Quick start

```bash
cd nhsm_hub
python3 -m venv venv && source venv/bin/activate   # first time only
pip install -r requirements.txt                    # first time only

python manage.py migrate
python manage.py seed_demo        # demo subjects + resources (--reset to wipe)
python manage.py runserver        # http://127.0.0.1:8000
```

Useful commands:

```bash
python manage.py check            # system checks
python manage.py createsuperuser  # admin account for moderation
python manage.py test             # run tests
```

The dev server uses **SQLite** and the `config.settings.development` settings module
(`manage.py` defaults to it). A demo admin already exists in the seeded dev database:
**username `admin`, password `admin12345`** — for local use only, never in production.

To register an **approver** account, use the invite code on the sign-up form. The dev default is
`nhsm-approver` (override with the `APPROVER_INVITE_CODE` env var). Students just leave it blank.

`seed_demo` also creates ~10 demo students (with study sessions) so the leaderboard is populated.
You can log in as any of them (e.g. `maya`, `rania`) with password `demo12345` — local demo only.

### Admins

There's a third role, **`admin`**, above approver — it has full content control through a custom
in-site panel at **`/manage/`** (dashboard + create/edit/delete for resources, exam papers,
subjects, and users/roles). Admin-added resources can be **approved on the spot**. Admins inherit
approver powers too. For safety there is **no public path to admin** — promote an existing user from
the command line:

```bash
python manage.py promote_user <username> admin      # or approver / student
```

Django superusers are treated as admins automatically. The `administration` app holds the panel.

---

## Project structure

```
nhsm_hub/
├── config/
│   ├── settings/
│   │   ├── base.py          # shared settings
│   │   ├── development.py    # SQLite, DEBUG=True (default)
│   │   └── production.py     # Postgres + optional S3, hardened
│   └── urls.py              # root URLconf
├── apps/
│   ├── accounts/            # custom User (role + profile) + UserStats (+ streak logic)
│   ├── resources/           # Subject, Resource (library) + ExamPaper (Annales) + upload
│   ├── moderation/          # approver-only review queue (no models)
│   ├── productivity/        # StudySession (Pomodoro) + leaderboard
│   └── requests/            # ResourceRequest + RequestVote (request/upvote board)
├── templates/               # base.html, home.html, resources/library.html
├── static/css/main.css      # design system (tokens, light + dark)
├── static/js/               # app.js (nav + reveals), resources.js (search)
└── manage.py
```

### Settings & environment

Secrets come from the environment or an optional local `.env` (read by `django-environ`);
dev runs fine without one. Production expects at least `SECRET_KEY`, `DATABASE_URL` and
`ALLOWED_HOSTS`. To run with production settings locally:
`DJANGO_SETTINGS_MODULE=config.settings.production`.

---

## How the resource library works

- **`Subject`** = a module, scoped to a `semester` (1–10). **`Resource`** = a document
  (Cours / TD / TP / Résumé / Livre / Autre) with a `drive_link` and a
  `pending → approved → rejected` status. Only **approved** resources are public.
- The library page (`/resources/`) renders the filter controls server-side, then loads
  results from the JSON API **`GET /api/resources/search`** via `static/js/resources.js`.
  Query params: `semester`, `subject` (slug), `type`, `q` (free text). Results are paginated
  (24/page).
- **Contributing**: signed-in users submit resources at `/resources/upload/` (status `pending`).
- **Moderation**: approvers review the queue at `/moderation/` (approve/reject); Django admin →
  *Resources* also has bulk approve/reject actions. Approving refreshes the uploader's
  denormalised `UserStats.contributions`.

`UserStats` is **denormalised on purpose** (counters instead of live aggregates) so leaderboard
and profile pages stay cheap.

---

## "Status Code 1" pixel theme

The site is skinned as a retro **pixel-art arcade** — deep cosmic starfield, neon pink/cyan/gold,
`Press Start 2P` (display) + `VT323` (body). Because the design system is token-driven, the whole
look lives in the `:root` block of [static/css/main.css](static/css/main.css); the light/dark toggle
is intentionally unified to one cosmic palette. The home page is a **student-platform intro**: a
split hero (glowing "NHSM HUB" title + a frameless transparent book image) over the starfield, and a
"Your Study Toolkit" grid linking to the real features. The site **footer** is a full-bleed pixel
landscape (drifting clouds + moon + the school building + a bus on a ground line) that blends into a
footer bar with the logo, quick links, socials and copyright — à la the reference footer. The NHSM
logo (rendered white via a CSS filter) sits in the nav next to "NHSM HUB" and in the footer. Images
are transparent PNGs in `static/img/` (`logo-nhsm.png`, `2.png` book, `3.png` school, `4.png` bus),
shown frameless. The functional pages (resources, annales, timer, leaderboard, requests) keep all
behaviour — only re-skinned.

## Design system & dark mode

`static/css/main.css` is **token-driven and dark-mode-first**. Colors, type, spacing, radii and
shadows are CSS custom properties on `:root` (light) with a `[data-theme="dark"]` override.
An inline script in `base.html` sets the theme before first paint to avoid a flash, defaulting to
the OS `prefers-color-scheme`. The nav **toggle** (`static/js/theme.js`) flips the theme and saves
it to `localStorage`; per-account persistence for signed-in users arrives in Phase 2.

Fonts: **Sora** (display) + **Inter** (body). Scroll-reveal animations use GSAP via CDN; `.reveal`
elements are only hidden when JS is present, so content stays visible without JS.

The home hero has a **sparkles** layer ([static/js/sparkles.js](static/js/sparkles.js)) built on
**tsParticles** (slim bundle via CDN, loaded only on the home page) — the vanilla-JS equivalent of
the popular React `sparkles.tsx`. Particle colour comes from the `--brand` token; it's disabled
under `prefers-reduced-motion`. We deliberately ported it natively rather than adding React/Tailwind
(see the stack note below).

---

## Roadmap (build order)

0. **Foundation + resource library** — ✅ done.
1. **Dark-mode toggle + Past-exams archive (Annales)** — ✅ done. Theme toggle in the nav;
   `ExamPaper` model + `/annales/` page filtering by year / semester / module / exam type, with a
   "corrigé available" flag and `/api/exams/search`.
2. **Auth + user profiles + in-app moderation** — ✅ done. Register / login / logout
   (`/accounts/…`); approver sign-up gated by `APPROVER_INVITE_CODE`; profile page with academic
   group, display name, anonymity flag and theme; **per-account dark-mode persistence** (overrides
   localStorage); resource upload + approver review queue at `/moderation/`.
3. **Pomodoro focus timer + tracking** — ✅ done. `/timer/` with configurable focus/break
   (default 25/5, long break every 4), module picker, progress ring. Completed focus blocks
   `POST /api/study-sessions` (signed-in only) → `StudySession` + `UserStats` (minutes, sessions,
   **daily streak** via `UserStats.record_study`). Anonymous users can run it untracked.
4. **Leaderboard** — ✅ done. `/leaderboard/` + `GET /api/leaderboard` ranks by focus minutes
   with **window** (today / week / semester / all-time) × **academic group** filters, defaulting to
   the signed-in user's year group. Sortable **streak** column, MVP highlight, "your position" card,
   and **anonymous** users shown as "Anonymous".
5. **Request / upvote board** — ✅ done. `/requests/` lists requests **most-upvoted first**;
   signed-in users post requests and toggle an upvote (one per user via a `RequestVote`
   unique constraint, AJAX). Each request has **Open / In progress / Fulfilled** status (with a
   link when fulfilled), managed by its author or an approver.

All five features are built. Each phase was additive and the resource library still works as
originally. Future ideas: Google OAuth sign-in (the auth layer was kept pluggable), pagination /
"load more" on the library, and an in-app notification when a request you upvoted is fulfilled.
