# NHSM Hub — Feature Build Brief for Claude Code

## Context

NHSM Hub (`nhsmhub.online`) is a student-run resource library for the National Higher School of Mathematics (NHSM, Algeria). It currently lets students filter study resources by semester / module / resource type and opens Google Drive links. Contributions go through GitHub and Google Forms.

**This brief describes a set of new features to build on top of the existing site.** Read the whole brief, then ask me clarifying questions before writing any code (see "Questions to ask me" at the end).

## Tech stack (already in use — do not change without asking)

- **Front-end:** HTML/CSS/JS, with React / Next.js
- **Back-end:** Django
- **Auth/DB for new features:** Django's built-in auth + Django ORM (Postgres or whatever the project already uses — confirm with me)
- **Hosting:** confirm with me (front-end may be on GitHub Pages today; the Django backend needs proper hosting — confirm where it lives)

Optional later: Google OAuth sign-in (students already have Google accounts via Drive/Forms). Build the auth layer so this can be added later without rework, but do **not** implement it in this first pass unless I confirm.

## Goal

Turn the site from a passive link directory into a sticky daily-use study platform, while keeping the existing resource library exactly as it works now. Nothing in the current resource-filtering experience should break or regress.

## Features to build (must-haves)

### 1. Pomodoro timer + tracking
- A focus-timer page: configurable focus/break durations (default 25/5), with long-break every 4 cycles.
- User picks a **subject/module** before starting — reuse the existing module list (semesters, modules) so logged time maps to real courses.
- Each completed focus block logs **minutes studied** to the logged-in user's account, tagged with subject and timestamp.
- Show the user their own stats: total focus time, time per subject, and a **daily streak** (consecutive days with at least one completed block).
- Requires user accounts (Django auth). A user who isn't signed in can use the timer but their time is not saved — prompt them to sign in to track.

### 2. Leaderboard / rankings
- Rank users by focus minutes.
- **Filters:** time window (today / this week / this semester / all-time) and **academic group** (cycle/year/promo, matching the site's existing structure: First Cycle, Second Year, Third Year, 4th-year tracks: Modeling / Cryptology / Data Science, Fifth Year).
- Default views should be **"my year group"** and **personal best**, with the global board optional. Rationale: avoid exam-season stress and avoid first-years competing against fifth-years.
- Let users choose a **display name** or stay **anonymous** on the board.
- Include **streak** as a sortable column alongside total minutes.

### 3. Dark mode
- Site-wide toggle, remembered per user (persisted setting; for signed-out users use local storage).
- Must apply to both the existing pages and all new pages. Respect `prefers-color-scheme` on first visit.

### 4. Past-exams archive ("Annales")
- A dedicated section, **separate** from course notes, for past exam papers (sujets d'examen: EMD, rattrapage, etc.).
- Browsable by year / semester / module, same taxonomy as the resource library.
- Each entry: title, year, exam type, module, and a link (Google Drive link, consistent with current resources) plus optional "corrigé available" flag.
- This is high-value for a math school — make it easy to find and prominent.

### 5. Request / upvote board
- Students post a request for a missing resource (e.g. "TD 3 corrigé for Analysis 2").
- Other students **upvote**. Sort by most-upvoted.
- Each request has a status: Open / In progress / Fulfilled (with link when fulfilled).
- Gives contributors a prioritized to-do list and turns passive users into participants.
- Requires accounts (to prevent vote spam — one vote per user per request).

## Data model (starting point — refine with me)

- **User** (Django auth) extended with profile: academic group/year/track, display name, anonymous flag, dark-mode preference.
- **FocusSession**: user, subject/module, minutes, started_at, completed_at.
- **ExamPaper**: title, year, exam_type, semester, module, drive_link, has_solution.
- **ResourceRequest**: author, title, description, module, status, fulfilled_link, created_at.
- **RequestVote**: user, request (unique together to enforce one vote per user).

## Constraints & principles

- **Do not break the existing resource library or its filtering.** New features are additive.
- Keep the existing visual identity (logo, layout, the current look). New pages should match.
- Mobile-friendly — students mostly use phones.
- Build features so they can be shipped incrementally; this is a student project with limited maintenance time. Prefer simple, well-documented code over clever abstractions.
- Write a short **README / handover note** so the next student cohort can maintain it.
- Anonymous/privacy-respecting leaderboard options matter — students should never be forced to expose their name or ranking.

## Suggested build order

1. Dark mode + Past-exams archive (lowest risk, no heavy backend logic).
2. Django auth + user profile (foundation for the rest).
3. Pomodoro timer + tracking.
4. Leaderboard.
5. Request/upvote board.

## Questions to ask me before coding

1. Where does the Django backend currently live (hosting), and what database does it use?
2. Is the front-end a single Next.js app, or static HTML pages plus separate React components? How are front-end and Django wired together (Django templates? separate API + Next.js frontend)?
3. Should I build a REST API (Django REST Framework) for the new features, or use Django templates/views?
4. Confirm the exact list of academic groups/years/tracks and how a user selects theirs on sign-up.
5. Do you want Google OAuth sign-in now, or Django username/password now with OAuth added later?
6. For the leaderboard, what's the default view you want students to land on?
7. Any existing design tokens / CSS variables / component library I should match?