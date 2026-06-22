# Design: S7–S10 specialities + footer social links

**Date:** 2026-06-22
**Status:** Approved (pending spec review)

## Goal

Two additive changes to NHSM Hub, neither of which may regress the existing
resource library / Annales filtering:

1. **Specialities.** From semester 7 onward (4th & 5th year), modules belong to
   one of three specialities — **Cryptology, Modeling, Data Science**. Make this
   a first-class dimension: editable in both admin surfaces and filterable by
   students on the Library and Annales pages.
2. **Social links.** Replace the placeholder footer links with the real
   GitHub, Instagram, Telegram, and Email.

Out of scope: changing the student `AcademicGroup` choices (the existing
"4th Year — Cryptology" etc. stay as they are). Speciality is a property of a
*module*, not of a *user*.

## Part 1 — Specialities

### Data model (`apps/resources/models.py`)

Add a `TextChoices` and one field on `Subject`:

```python
class Speciality(models.TextChoices):
    CRYPTOLOGY   = "cryptology",   "Cryptology"
    MODELING     = "modeling",     "Modeling"
    DATA_SCIENCE = "data_science", "Data Science"
```

```python
# Subject
speciality = models.CharField(
    max_length=20, choices=Speciality.choices, blank=True,
    help_text="Required for S7–S10; leave blank for the S1–S6 common core.",
)
```

Validation in `Subject.clean()`:
- `semester >= 7` → `speciality` is **required** (raise `ValidationError` if blank).
- `semester <= 6` → `speciality` must be **blank** (raise `ValidationError` if set).

Rationale: a single optional `CharField` with `TextChoices` matches the existing
`ResourceType` / `ExamType` / `AcademicGroup` patterns; only three fixed values,
so no separate model. `Resource` and `ExamPaper` are unchanged — they reach
speciality through `subject.speciality`.

### Migration

One migration adding the nullable/blank field. Existing rows default to blank
(harmless; admins set speciality on the S7–S10 subjects afterwards). No data
migration. Runs automatically in the Render build (`migrate`).

### Django admin (`apps/resources/admin.py`)

- `SubjectAdmin`: add `speciality` to `list_display` and `list_filter`
  (the change form picks it up automatically).
- `ResourceAdmin` and `ExamPaperAdmin`: add `subject__speciality` to `list_filter`.

### Custom management section (`apps/administration`)

- `SubjectAdminForm`: add `"speciality"` to `Meta.fields`.
- `subject_list` view + template: show a **Speciality** column and allow filtering
  the list by speciality (query param `?speciality=`), consistent with how the
  list already filters.
- Resource/Exam forms unchanged — speciality is derived from the chosen subject.

### Student-facing filter

**Serializers (`apps/resources/serializers.py`)** — both serializers use flat
`source="subject.X"` fields (e.g. `subject_name`, `semester`). Add the same way:
```python
speciality       = serializers.CharField(source="subject.speciality", read_only=True)
speciality_label = serializers.CharField(source="subject.get_speciality_display", read_only=True)
```
and add `"speciality"`, `"speciality_label"` to each `Meta.fields`. (`speciality`
is the empty string for S1–S6 subjects — the card omits the badge when blank.)

**Search APIs (`apps/resources/views.py`)** — both `ResourceSearchAPIView` and
`ExamSearchAPIView` accept a new `speciality` query param:
```python
speciality = params.get("speciality")
if speciality:
    qs = qs.filter(subject__speciality=speciality)
```

**Library + Annales pages (`resource_library`, `annales` views & templates)**:
- Pass `Speciality.choices` into the template context.
- Add a **"Speciality"** `<select id="filter-speciality" data-filter="speciality">`
  (All / Cryptology / Modeling / Data Science) beside the existing
  `#filter-semester` select. The existing subject `<option>`s gain a
  `data-speciality="{{ subject.speciality }}"` attribute so the module dropdown
  can also be narrowed (mirroring the current `data-semester` behaviour).
- JS: the filter scripts are `static/js/resources.js` (Library) and
  `static/js/annales.js` (Annales). Both build the query by iterating
  `[data-filter]` elements, so the new speciality select is sent to the API
  **automatically — no change needed** for the filter to work. Optional polish:
  extend the existing subject-dropdown narrowing (currently keyed on
  `data-semester`) to also hide modules whose `data-speciality` doesn't match the
  selected speciality.
- Show a small speciality badge on result cards, rendered only when
  `speciality` is non-empty.

Picking a speciality naturally narrows results to S7–S10 modules (S1–S6 have no
speciality). The semester, module, and type filters keep working exactly as today.

## Part 2 — Social links (`templates/base.html`)

Replace the four placeholder `<a href="#">` entries in `.footer-social` with:

| Label     | href                                       |
|-----------|--------------------------------------------|
| GitHub    | https://github.com/Azzouz-billel           |
| Instagram | https://www.instagram.com/billel_.azzouz/  |
| Telegram  | https://t.me/billel_azz                    |
| Email     | mailto:billel.azzouz@nhsm.edu.dz           |

Keep `target="_blank" rel="noopener"` on the external links (not on `mailto:`).
Hardcoded in the template — simplest for a student project; can move to settings
later if they ever change often.

## Testing

- `Subject.clean()`: S7 subject without speciality raises `ValidationError`;
  S3 subject with a speciality raises `ValidationError`; S8 subject with
  Modeling validates.
- Search API: `?speciality=cryptology` returns only resources whose subject is
  Cryptology; omitting the param returns all (no regression).
- Run the existing resources test file after changes.

## Deployment

No new env vars. The migration applies on the next Render deploy via the build
command's `migrate`. After deploy, set specialities on existing S7–S10 subjects
through the `/manage` section or `/admin`.
