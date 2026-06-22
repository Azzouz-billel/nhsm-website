# S7–S10 Specialities + Footer Social Links — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Cryptology/Modeling/Data-Science speciality dimension to S7–S10 modules (editable in both admin surfaces, filterable by students) and wire the footer's social links to real URLs.

**Architecture:** A single `speciality` `TextChoices` field on `Subject` (blank for the S1–S6 common core). `Resource`/`ExamPaper` reach it through their `Subject`. The existing search APIs gain a `speciality` query param; the existing `[data-filter]`-driven filter JS picks up a new dropdown automatically. Footer links are static template edits.

**Tech Stack:** Django 5.1, Django REST Framework, vanilla JS, server-rendered templates, SQLite (tests/dev) / Postgres (prod).

## Global Constraints

- Do NOT regress existing resource-library / Annales filtering (semester, module, type, year, solution, text).
- Speciality labels, verbatim: **Cryptology**, **Modeling**, **Data Science**. Stored values: `cryptology`, `modeling`, `data_science`.
- Speciality is **required when `semester >= 7`** and **must be blank when `semester <= 6`**.
- Do NOT change the student `AcademicGroup` choices. Speciality is a property of a module, not a user.
- Run tests with the development settings default: `cd /home/billel/Desktop/claudecode/nhsm_hub && source venv/bin/activate` first.
- Match existing visual identity; use existing CSS tokens (no hardcoded colors).

---

### Task 1: `Subject.speciality` model field + validation + migration

**Files:**
- Modify: `apps/resources/models.py`
- Test: `apps/resources/tests.py`
- Create (generated): `apps/resources/migrations/0003_subject_speciality.py`

**Interfaces:**
- Produces: `Speciality` TextChoices (`CRYPTOLOGY="cryptology"`, `MODELING="modeling"`, `DATA_SCIENCE="data_science"`); `Subject.speciality` (CharField, blank); `Subject.clean()` enforcing the S7–S10 rule.

- [ ] **Step 1: Write the failing tests**

Append to `apps/resources/tests.py`:

```python
from django.core.exceptions import ValidationError

from .models import Speciality


class SubjectValidationTests(TestCase):
    def test_advanced_subject_requires_speciality(self):
        subject = Subject(name="Cryptographie Avancée", semester=7)
        with self.assertRaises(ValidationError):
            subject.full_clean()

    def test_common_core_subject_rejects_speciality(self):
        subject = Subject(name="Analyse 1", semester=3, speciality=Speciality.MODELING)
        with self.assertRaises(ValidationError):
            subject.full_clean()

    def test_advanced_subject_with_speciality_is_valid(self):
        subject = Subject(name="Modélisation", semester=8, speciality=Speciality.MODELING)
        self.assertIsNone(subject.full_clean())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/billel/Desktop/claudecode/nhsm_hub && source venv/bin/activate && python manage.py test apps.resources.tests.SubjectValidationTests -v2`
Expected: FAIL — `ImportError: cannot import name 'Speciality'` (or AttributeError on `speciality`).

- [ ] **Step 3: Add the choices, field, and validation**

In `apps/resources/models.py`, add the import near the top (with the other django imports):

```python
from django.core.exceptions import ValidationError
```

Add this `TextChoices` class just above `class Subject`:

```python
class Speciality(models.TextChoices):
    CRYPTOLOGY = "cryptology", "Cryptology"
    MODELING = "modeling", "Modeling"
    DATA_SCIENCE = "data_science", "Data Science"
```

Add the field to `Subject` (after `description`):

```python
    speciality = models.CharField(
        max_length=20,
        choices=Speciality.choices,
        blank=True,
        help_text="Required for S7–S10; leave blank for the S1–S6 common core.",
    )
```

Add a `clean` method to `Subject` (after `__str__`, before `save`):

```python
    def clean(self):
        super().clean()
        if self.semester is None:
            return
        if self.semester >= 7 and not self.speciality:
            raise ValidationError(
                {"speciality": "Modules from S7 onward must have a speciality."}
            )
        if self.semester <= 6 and self.speciality:
            raise ValidationError(
                {"speciality": "S1–S6 modules are common core; leave speciality blank."}
            )
```

- [ ] **Step 4: Create the migration**

Run: `cd /home/billel/Desktop/claudecode/nhsm_hub && source venv/bin/activate && python manage.py makemigrations resources`
Expected: creates `apps/resources/migrations/0003_subject_speciality.py` adding field `speciality`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python manage.py test apps.resources.tests.SubjectValidationTests -v2`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add apps/resources/models.py apps/resources/tests.py apps/resources/migrations/0003_subject_speciality.py
git commit -m "feat(resources): add Subject.speciality with S7-S10 validation"
```

---

### Task 2: Expose speciality in serializers + search APIs

**Files:**
- Modify: `apps/resources/serializers.py`
- Modify: `apps/resources/views.py`
- Test: `apps/resources/tests.py`

**Interfaces:**
- Consumes: `Subject.speciality`, `Speciality` (Task 1).
- Produces: search APIs accept `?speciality=<value>`; serializers emit `speciality` and `speciality_label`.

- [ ] **Step 1: Write the failing test**

Append to `apps/resources/tests.py`:

```python
class ResourceSpecialityFilterTests(TestCase):
    def setUp(self):
        crypto = Subject.objects.create(
            name="Cryptographie", semester=7, speciality=Speciality.CRYPTOLOGY
        )
        modeling = Subject.objects.create(
            name="Modélisation", semester=7, speciality=Speciality.MODELING
        )
        Resource.objects.create(
            title="Crypto Cours", subject=crypto, resource_type=ResourceType.COURSE,
            drive_link="https://drive.google.com/c", status=ResourceStatus.APPROVED,
        )
        Resource.objects.create(
            title="Modeling Cours", subject=modeling, resource_type=ResourceType.COURSE,
            drive_link="https://drive.google.com/m", status=ResourceStatus.APPROVED,
        )

    def test_filters_resources_by_speciality(self):
        response = self.client.get(SEARCH_URL, {"speciality": "cryptology"})
        titles = [r["title"] for r in response.json()["results"]]
        self.assertEqual(titles, ["Crypto Cours"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /home/billel/Desktop/claudecode/nhsm_hub && source venv/bin/activate && python manage.py test apps.resources.tests.ResourceSpecialityFilterTests -v2`
Expected: FAIL — both titles returned (filter not applied yet), so `assertEqual` fails.

- [ ] **Step 3: Add the speciality param to both search views**

In `apps/resources/views.py`, inside `ResourceSearchAPIView.get_queryset`, add after the `subject` filter block:

```python
        speciality = params.get("speciality")
        if speciality:
            qs = qs.filter(subject__speciality=speciality)
```

In the same file, inside `ExamSearchAPIView.get_queryset`, add the identical block after its `subject` filter:

```python
        speciality = params.get("speciality")
        if speciality:
            qs = qs.filter(subject__speciality=speciality)
```

- [ ] **Step 4: Add speciality fields to both serializers**

In `apps/resources/serializers.py`, add these two lines to `ResourceSerializer` (with the other `source=` fields):

```python
    speciality = serializers.CharField(source="subject.speciality", read_only=True)
    speciality_label = serializers.CharField(source="subject.get_speciality_display", read_only=True)
```

Add `"speciality"` and `"speciality_label"` to `ResourceSerializer.Meta.fields` (after `"semester"`).

Add the same two field declarations to `ExamPaperSerializer`, and add `"speciality"`, `"speciality_label"` to its `Meta.fields` (after `"semester"`).

- [ ] **Step 5: Run the test to verify it passes**

Run: `python manage.py test apps.resources.tests.ResourceSpecialityFilterTests -v2`
Expected: PASS.

- [ ] **Step 6: Run the full resources test file (no regression)**

Run: `python manage.py test apps.resources -v2`
Expected: PASS (all existing + new tests).

- [ ] **Step 7: Commit**

```bash
git add apps/resources/views.py apps/resources/serializers.py apps/resources/tests.py
git commit -m "feat(resources): filter search APIs by speciality + expose it in serializers"
```

---

### Task 3: Surface speciality in both admin surfaces

**Files:**
- Modify: `apps/resources/admin.py`
- Modify: `apps/administration/forms.py`
- Modify: `templates/manage/subjects.html`
- Test: `apps/administration/tests.py`

**Interfaces:**
- Consumes: `Subject.speciality`, `SubjectAdminForm` (Tasks 1).

- [ ] **Step 1: Write the failing tests**

Append to `apps/administration/tests.py` (create imports at top of the new class as needed):

```python
from django.test import TestCase

from apps.administration.forms import SubjectAdminForm


class SubjectAdminFormTests(TestCase):
    def test_rejects_advanced_subject_without_speciality(self):
        form = SubjectAdminForm(data={"name": "Crypto Avancée", "semester": 8, "description": ""})
        self.assertFalse(form.is_valid())

    def test_accepts_advanced_subject_with_speciality(self):
        form = SubjectAdminForm(
            data={"name": "Crypto Avancée", "semester": 8, "speciality": "cryptology", "description": ""}
        )
        self.assertTrue(form.is_valid())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/billel/Desktop/claudecode/nhsm_hub && source venv/bin/activate && python manage.py test apps.administration.tests.SubjectAdminFormTests -v2`
Expected: FAIL — `test_rejects...` fails because the form has no `speciality` field, so the model's `clean()` is bypassed for it (`exclude`d) and the form validates.

- [ ] **Step 3: Add speciality to the custom management form**

In `apps/administration/forms.py`, change `SubjectAdminForm.Meta.fields` to include speciality:

```python
        fields = ("name", "semester", "speciality", "description")
```

- [ ] **Step 4: Add speciality to the Django admin**

In `apps/resources/admin.py`:

Replace the `SubjectAdmin` body's `list_display` and `list_filter`:

```python
    list_display = ("name", "semester", "speciality")
    list_filter = ("semester", "speciality")
```

In `ResourceAdmin.list_filter`, add `"subject__speciality"`:

```python
    list_filter = ("status", "resource_type", "subject__semester", "subject__speciality")
```

In `ExamPaperAdmin.list_filter`, add `"subject__speciality"`:

```python
    list_filter = ("year", "exam_type", "has_solution", "subject__semester", "subject__speciality")
```

- [ ] **Step 5: Add a Speciality column to the manage subjects table**

In `templates/manage/subjects.html`:

Change the table header row (line 12) to add a Speciality column:

```html
  <thead><tr><th>Name</th><th>Semester</th><th>Speciality</th><th>Description</th><th class="col-actions">Actions</th></tr></thead>
```

Add a cell after the Semester `<td>` (after line 17):

```html
        <td class="muted">{{ s.get_speciality_display|default:"—" }}</td>
```

Change the empty-state `colspan` (line 27) from `4` to `5`:

```html
      <tr><td colspan="5" class="muted">No subjects yet.</td></tr>
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python manage.py test apps.administration.tests.SubjectAdminFormTests -v2`
Expected: PASS (2 tests).

- [ ] **Step 7: System check**

Run: `python manage.py check`
Expected: `System check identified no issues`.

- [ ] **Step 8: Commit**

```bash
git add apps/resources/admin.py apps/administration/forms.py templates/manage/subjects.html apps/administration/tests.py
git commit -m "feat(admin): expose subject speciality in Django admin and /manage"
```

---

### Task 4: Student-facing speciality filter (Library + Annales)

**Files:**
- Modify: `apps/resources/views.py` (`resource_library`, `annales`)
- Modify: `templates/resources/library.html`
- Modify: `templates/resources/annales.html`
- Modify: `static/js/resources.js`
- Modify: `static/js/annales.js`
- Modify: `static/css/main.css`
- Test: `apps/resources/tests.py`

**Interfaces:**
- Consumes: `Speciality.choices` (Task 1), `?speciality=` API param + `speciality`/`speciality_label` serializer fields (Task 2).

- [ ] **Step 1: Write the failing tests**

Append to `apps/resources/tests.py`:

```python
from django.urls import reverse


class SpecialityFilterRenderTests(TestCase):
    def test_library_page_renders_speciality_filter(self):
        response = self.client.get(reverse("resource_library"))
        self.assertContains(response, "Cryptology")

    def test_annales_page_renders_speciality_filter(self):
        response = self.client.get(reverse("annales"))
        self.assertContains(response, "Data Science")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/billel/Desktop/claudecode/nhsm_hub && source venv/bin/activate && python manage.py test apps.resources.tests.SpecialityFilterRenderTests -v2`
Expected: FAIL — pages don't render the speciality labels yet.

- [ ] **Step 3: Pass `Speciality.choices` into both view contexts**

In `apps/resources/views.py`, add `Speciality` to the model import block:

```python
from .models import (
    ExamPaper,
    ExamType,
    Resource,
    ResourceStatus,
    ResourceType,
    Speciality,
    Subject,
)
```

In `resource_library`, add to the `context` dict:

```python
        "specialities": Speciality.choices,
```

In `annales`, add to the `context` dict:

```python
        "specialities": Speciality.choices,
```

- [ ] **Step 4: Add the speciality `<select>` to library.html**

In `templates/resources/library.html`, insert this block right after the Semester `filter-group` (after line 32, before the Module group):

```html
        <div class="filter-group">
          <label for="filter-speciality">Speciality</label>
          <select id="filter-speciality" class="field" data-filter="speciality">
            <option value="">All specialities</option>
            {% for value, label in specialities %}
              <option value="{{ value }}">{{ label }}</option>
            {% endfor %}
          </select>
        </div>
```

In the same file, add a `data-speciality` attribute to the Module `<option>` (change line 39):

```html
              <option value="{{ subject.slug }}" data-semester="{{ subject.semester }}" data-speciality="{{ subject.speciality }}">
```

- [ ] **Step 5: Add the speciality `<select>` to annales.html**

In `templates/resources/annales.html`, insert this block right after the Semester `filter-group` (after line 42, before the Module group):

```html
        <div class="filter-group">
          <label for="filter-speciality">Speciality</label>
          <select id="filter-speciality" class="field" data-filter="speciality">
            <option value="">All specialities</option>
            {% for value, label in specialities %}
              <option value="{{ value }}">{{ label }}</option>
            {% endfor %}
          </select>
        </div>
```

In the same file, add `data-speciality` to the Module `<option>` (change line 49):

```html
              <option value="{{ subject.slug }}" data-speciality="{{ subject.speciality }}">S{{ subject.semester }} · {{ subject.name }}</option>
```

- [ ] **Step 6: Add speciality to resources.js state + a card badge**

In `static/js/resources.js`:

Change the initial state (line 10) to include speciality:

```javascript
  var state = { q: "", semester: "", speciality: "", subject: "", type: "" };
```

In `cardHtml`, add a speciality badge after the semester badge (after the `badge sem` line):

```javascript
          (r.speciality ? '<span class="badge spec">' + escapeHtml(r.speciality_label) + "</span>" : "") +
```

Change the reset handler's state reset (line 105) to match:

```javascript
      state = { q: "", semester: "", speciality: "", subject: "", type: "" };
```

- [ ] **Step 7: Add speciality to annales.js state + a card badge**

In `static/js/annales.js`:

Change the initial state (line 10) to include speciality:

```javascript
  var state = { q: "", year: "", semester: "", speciality: "", subject: "", type: "", solution: "" };
```

In `cardHtml`, add a speciality badge after the `S<semester>` badge line:

```javascript
          (exam.speciality ? '<span class="badge spec">' + escapeHtml(exam.speciality_label) + "</span>" : "") +
```

Change the reset handler's state reset (line 123) to match:

```javascript
      state = { q: "", year: "", semester: "", speciality: "", subject: "", type: "", solution: "" };
```

- [ ] **Step 8: Style the speciality badge with existing tokens**

In `static/css/main.css`, add after the `.badge.sem { ... }` rule (after line 524):

```css
.badge.spec {
  background: var(--surface-3);
  color: var(--accent);
}
```

- [ ] **Step 9: Run the tests to verify they pass**

Run: `python manage.py test apps.resources.tests.SpecialityFilterRenderTests -v2`
Expected: PASS (2 tests).

- [ ] **Step 10: Manual smoke check**

Run: `python manage.py runserver` and open `http://127.0.0.1:8000/resources/`. Confirm a "Speciality" dropdown appears with Cryptology / Modeling / Data Science and that selecting one updates results. Repeat at `/annales/`. Stop the server.

- [ ] **Step 11: Commit**

```bash
git add apps/resources/views.py templates/resources/library.html templates/resources/annales.html static/js/resources.js static/js/annales.js static/css/main.css apps/resources/tests.py
git commit -m "feat(resources): student-facing speciality filter on Library and Annales"
```

---

### Task 5: Footer social links

**Files:**
- Modify: `templates/base.html` (lines 109–114, `.footer-social`)
- Test: `apps/resources/tests.py`

- [ ] **Step 1: Write the failing test**

Append to `apps/resources/tests.py`:

```python
class FooterSocialLinksTests(TestCase):
    def test_footer_links_to_github_profile(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "https://github.com/Azzouz-billel")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /home/billel/Desktop/claudecode/nhsm_hub && source venv/bin/activate && python manage.py test apps.resources.tests.FooterSocialLinksTests -v2`
Expected: FAIL — footer still has placeholder `href="#"`.

- [ ] **Step 3: Replace the placeholder footer links**

In `templates/base.html`, replace the `.footer-social` block (lines 109–114):

```html
      <div class="footer-social">
        <a href="https://github.com/Azzouz-billel" target="_blank" rel="noopener">GitHub</a>
        <a href="https://www.instagram.com/billel_.azzouz/" target="_blank" rel="noopener">Instagram</a>
        <a href="https://t.me/billel_azz" target="_blank" rel="noopener">Telegram</a>
        <a href="mailto:billel.azzouz@nhsm.edu.dz">Email</a>
      </div>
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python manage.py test apps.resources.tests.FooterSocialLinksTests -v2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/base.html apps/resources/tests.py
git commit -m "feat: wire footer social links (GitHub, Instagram, Telegram, Email)"
```

---

## Final verification

- [ ] Run the full test suite: `cd /home/billel/Desktop/claudecode/nhsm_hub && source venv/bin/activate && python manage.py test -v2` — Expected: all PASS.
- [ ] `python manage.py check` — Expected: no issues.
- [ ] Deploy note: on the next Render deploy, the build's `migrate` applies `0003_subject_speciality`. Afterwards, set specialities on existing S7–S10 subjects via `/manage/subjects/` or `/admin/`.

## Self-Review (completed by plan author)

- **Spec coverage:** model field + validation (Task 1) ✓; admin both surfaces (Task 3) ✓; serializers + API param (Task 2) ✓; student filter UI (Task 4) ✓; social links (Task 5) ✓; AcademicGroup untouched ✓.
- **Placeholders:** none — every code step shows full code.
- **Type consistency:** `Speciality` values (`cryptology`/`modeling`/`data_science`) and field name `speciality` / `speciality_label` are used identically across models, serializers, views, templates, and JS.
