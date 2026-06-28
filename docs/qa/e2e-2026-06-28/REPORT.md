# Cairn - End-to-End GUI Robustness Test Report

**Date:** 2026-06-28  •  **Target:** running dev server (`manage.py runserver`, SQLite, DEBUG=True)  •  **Surface:** web GUI only (authenticated as superuser via the login form), incl. the now-working WebSocket endpoints.

**Method:** informed fuzzing - 12 parallel agents read the view/form/mixin code to locate crash-prone paths, fired malformed GUI requests, and every HTTP 500 / hang was re-reproduced from a *fresh isolated session* with adversarial controls (valid input -> 200, empty -> 200, malformed -> 500) before being accepted. WebSocket consumers were fuzzed separately once the ASGI dev server was fixed.

## Result

- **29 confirmed, reproducible crashes** reachable from the GUI (28 HTTP 500 + 1 WebSocket consumer crash). 380 HTTP probes fired, 54 raw findings, deduplicated and independently verified.

- Severity: **17 High**, **12 Medium**.

- Exception classes: ValidationError (bad UUID/date), ValueError (bad int), AttributeError, OverflowError, OperationalError (DoS), DoesNotExist.

- No full-process crash (the WSGI dev server isolates each request as a 500); the substantive defects are the **DoS** vector (#C) and the systemic **unvalidated-input 500s** (#B/#A). Under `DEBUG=True` every 500 page also **leaks source code, file paths and versions** (info disclosure).

- Bonus: the **WebSocket misconfiguration** (live dashboard/notifications 404 under runserver) was diagnosed and fixed (added `daphne`).


## Cluster B. List/detail views trust raw query/POST params as PK/date (no validation)  (16 frames)

### `assets/views.py:533` - ValueError (HIGH)
- **Repro:** `GET /assets/suppliers/?supplier_type=notanint  (any non-integer, non-empty value, e.g. supplier_type=1.5, also crashes)`
- **Root cause:** SupplierListView.get_queryset (assets/views.py:529-535) reads supplier_type = self.request.GET.get("supplier_type") and, when truthy, does qs.filter(type_id=supplier_type) at line 533. SupplierType.id is models.AutoField(primary_key=True) (assets/models/supplier.py:24), an integer PK. Django coerces the filter value to int when the queryset is evaluated; a non-numeric string raises ValueError: Field 'id' expected a n
- **GUI path:** The Suppliers list (/assets/suppliers/) is filtered by supplier type via the supplier_type query parameter, which is the only consumer of this value in the codebase. A user reaches the 500 by loading/bookmarking the list URL with a malformed supplier_type value, or via a tampered/deep-link "supplier

### `compliance/views.py:463` - ValidationError (HIGH)
- **Repro:** `GET /compliance/requirements/?framework=x (any non-UUID string for the `framework` query param; e.g. ?framework=notauuid). Also reproduces on the HTMX endpoint GET /compliance/requirements/table-body/?framework=notauuid (frame compliance/vi`
- **Root cause:** RequirementListView.get_queryset (compliance/views.py:461-463) reads `framework_filter = self.request.GET.get("framework")` and applies `qs = qs.filter(framework_id=framework_filter)` with no validation that the value is a UUID. `framework_id` is a UUID FK column, so when the lazy queryset is evaluated Django's UUID field calls `to_python()` / `get_prep_value()` on the raw string and raises `django.core.exceptions.Va
- **GUI path:** The requirements list (/compliance/requirements/) and its HTMX table-body partial accept a `framework` query parameter to scope the list to one framework (the framework detail page already constructs `?framework=<uuid>` links, e.g. requirement-create at framework_detail.html:98). A normal user reach

### `core/views.py:955` - ValidationError (HIGH)
- **Repro:** `GET /api/calendar-events/?start=x  (a single malformed start param is sufficient; also reproduces with start=notadate&end=alsonot, with impossible dates start=2020-13-45 or start=0000-00-00, and with only end=x). With categories=action_plan`
- **Root cause:** CalendarEventsView.get (core/views.py:1351-1357) passes request.GET.get("start") and request.GET.get("end") verbatim into get_calendar_events without any parsing or validation. Inside get_calendar_events, the add() helper (core/views.py:948-955) builds an ORM filter dict filters[f"{date_field}__gte"] = start / filters[f"{date_field}__lte"] = end and then evaluates queryset.filter(**filters) at line 955. Django's Date
- **GUI path:** The Calendar page (templates/calendar.html:309) fetches this exact endpoint: fetch('{% url "calendar-events" %}?'+p.toString()) where p carries start/end. A normal button click sends valid YYYY-01-01 dates (from navDate.getFullYear()) so it does not crash, but the in-scope GUI-backing JSON endpoint 

### `risks/views.py:1005` - ValidationError (HIGH)
- **Repro:** `GET /risks/register/?assessment=notauuid`
- **Root cause:** RiskListView.get_queryset() (risks/views.py:999-1029) reads the raw GET param at line 1003 (assessment_id = params.get("assessment")) and passes it directly into the ORM at line 1005: qs = qs.filter(assessment_id=assessment_id). Risk.assessment is a FK to a model with a UUID primary key, so Django coerces the filter value via UUIDField.to_python() during query construction. A non-UUID string like "notauuid" fails coe
- **GUI path:** The ?assessment=<pk> query param is emitted by GUI links across the app, e.g. risks/templates/risks/assessment_detail.html "Manage" (threat-list / vulnerability-list) and "New analysis" (iso27005-create) buttons render href="...?assessment={{ assessment.pk }}". A normal user reaches the risk registe

### `risks/views.py:1024 (RiskListView.get_queryset); same defect at risks/views.py:1258 for the HTMX RiskTableBodyView` - django.core.exceptions.ValidationError (HIGH)
- **Repro:** `GET /risks/register/?essential_asset=xx  (any non-UUID value; even a single char ?essential_asset=a crashes). Confirmed identically for support_asset, threat, vulnerability, linked_requirement, and via the HTMX partial GET /risks/register/t`
- **Root cause:** In RiskListView.get_queryset() (risks/views.py:1014-1024) the view loops over m2m_filters = {essential_asset: affected_essential_assets__id, support_asset: affected_support_assets__id, threat: iso27005_sources__threat_id, vulnerability: iso27005_sources__vulnerability_id, linked_requirement: linked_requirements__id} and does qs.filter(**{lookup: value}) with the raw request.GET value. The lookups target UUID PK/FK co
- **GUI path:** Risk register page (/risks/register/, menu Risks > Risk register). The advanced-filter offcanvas (includes/list_filter_offcanvas.html, populated from essential_asset_choices / support_asset_choices / threat_choices / vulnerability_choices / requirement_choices in get_context_data) renders the Essent

### `risks/views.py:1113` - django.core.exceptions.ValidationError (HIGH)
- **Repro:** `POST /risks/register/bulk/ with body action=approve&risk_ids=notauuid (CSRF token from GET /risks/register/). Identical crash with action=delete&risk_ids=notauuid, with a mixed list action=approve&risk_ids=<valid-uuid>&risk_ids=BAD, and eve`
- **Root cause:** RiskBulkActionView.post() (risks/views.py:1091-1148) reads ids = request.POST.getlist("risk_ids") and at line 1113 builds qs = Risk.objects.filter(pk__in=ids) with no UUID validation. Risk.pk is a UUIDField, so when the queryset is evaluated — iterated in the approve branch (line 1125 `for risk in qs`) or `.delete()`-ed in the delete branch (line 1143) — Django calls UUIDField.get_prep_value/to_python on each entry, 
- **GUI path:** The risk register (/risks/register/) renders row-selection checkboxes plus a bulk-actions bar (templates/components/bulk_actions_bar.html) whose Approve/Delete buttons POST the selected risk_ids to /risks/register/bulk/ (data-bulk-url). A user reaches the 500 by: (a) submitting the form when a check

### `risks/views.py:1239` - ValidationError (HIGH)
- **Repro:** `GET /risks/register/table-body/?assessment=x  (any non-empty, non-UUID value; e.g. "x", "123", "notauuid"). An empty value ?assessment= returns 200 because of the `if assessment_id:` guard.`
- **Root cause:** RiskTableBodyView.get_queryset() (risks/views.py:1233-1239) reads the raw `assessment` query parameter via self.request.GET.get("assessment") and passes it straight to qs.filter(assessment_id=assessment_id). `assessment_id` resolves to a UUIDField, so Django attempts to coerce the string to a UUID during query construction. Any non-empty value that is not a valid UUID raises django.core.exceptions.ValidationError ('“
- **GUI path:** Open the Risk register page (/risks/register/, "Risk register" nav). The page's #item-table-body uses hx-get to risks:risk-table-body with hx-include=".list-filter-form", re-firing the current query parameters on every filter/sort/paginate/refreshTable interaction. The `assessment` parameter is carr

### `risks/views.py:1376` - ValidationError (HIGH)
- **Repro:** `GET /risks/treatments/?assessment=x (any non-UUID value for the ?assessment= query param). Also reproducible on the HTMX partial: GET /risks/treatments/table-body/?assessment=x (crashes at risks/views.py:1451 with the same exception).`
- **Root cause:** TreatmentPlanListView.get_queryset() (risks/views.py:1372-1378) reads the raw assessment query param via self.request.GET.get("assessment") and, if truthy, passes it directly into qs.filter(risk__assessment_id=assessment_id) at line 1376. assessment_id is a UUIDField, so Django's UUID field-conversion calls uuid.UUID() on the user-supplied string; a non-UUID value raises django.core.exceptions.ValidationError, which 
- **GUI path:** Treatment plan list page (/risks/treatments/, "Treatment plans" under Risks). The view and its HTMX table-body partial (/risks/treatments/table-body/) both consume the ?assessment= query param to scope plans to a specific risk assessment. A user reaches the crash via any bookmarked/shared/edited URL

### `risks/views.py:1588` - ValidationError (HIGH)
- **Repro:** `GET /risks/acceptances/?assessment=notauuid (any non-UUID, non-empty value, e.g. ?assessment=1, reproduces it). Table-body HTMX variant: GET /risks/acceptances/table-body/?assessment=notauuid -> 500 at risks/views.py:1655.`
- **Root cause:** RiskAcceptanceListView.get_queryset() at risks/views.py:1584-1590 filters on `risk__assessment_id=self.request.GET.get('assessment')` without validating the value as a UUID; a malformed non-empty string raises an uncaught ValidationError -> HTTP 500. The TableBody variant (lines 1651-1657, frame 1655) has the identical flaw.
- **GUI path:** The risk acceptance list (/risks/acceptances/, linked from the Risks dashboard "Open list" button) supports an `?assessment=<pk>` filter - the same query-param filter convention that the assessment detail page exposes via GUI "Manage" buttons for sibling lists (threat-list ?assessment={{assessment.p

### `risks/views.py:1716` - ValidationError (HIGH)
- **Repro:** `GET /risks/threats/?assessment=notauuid  (any non-empty value that is not a valid UUID, e.g. ?assessment=12345, also crashes; an empty value ?assessment= and a valid UUID both return 200)`
- **Root cause:** In ThreatListView.get_context_data (risks/views.py:1709-1717), the raw GET parameter is read as assessment_id = self.request.GET.get("assessment"), and at line 1716 it is passed directly into RiskAssessment.objects.filter(pk=assessment_id).first(). RiskAssessment.pk is a UUIDField, so Django attempts to coerce the string to a UUID during query construction. A non-empty value that is not a valid UUID (e.g. "notauuid",
- **GUI path:** On a risk assessment detail page (risks/templates/risks/assessment_detail.html line 59), the "Manage" button next to Threats links to {% url 'risks:threat-list' %}?assessment={{ assessment.pk }}. A normal click uses a valid UUID and works (200). The crash is triggered when the assessment query value

### `risks/views.py:1845` - ValidationError (HIGH)
- **Repro:** `GET /risks/vulnerabilities/?assessment=notauuid  (any non-UUID-parseable value crashes, e.g. ?assessment=123)`
- **Root cause:** VulnerabilityListView.get_context_data (risks/views.py:1842-1845) reads the raw `assessment` GET parameter and calls RiskAssessment.objects.filter(pk=assessment_id).first(). RiskAssessment.pk is a UUIDField, so when the value cannot be coerced to a UUID, Django raises django.core.exceptions.ValidationError during query evaluation inside .first(). The exception is never caught, so it propagates and Django returns an H
- **GUI path:** The vulnerabilities list is reached from a risk assessment detail page: assessment_detail.html line 70 renders the "Manage" vulnerabilities button as href="/risks/vulnerabilities/?assessment={{ assessment.pk }}". The `assessment` query parameter is GUI-exposed and fully user-controllable: a user edi

### `risks/views.py:1932` - django.core.exceptions.ValidationError (HIGH)
- **Repro:** `GET /risks/api/scale-choices/?assessment=notauuid (any non-UUID-parseable value, e.g. assessment=123, also triggers it)`
- **Root cause:** scale_choices_api() in risks/views.py (lines 1926-1935) reads request.GET.get("assessment") and calls RiskAssessment.objects.select_related("risk_criteria").get(pk=assessment_id) inside a try/except that only catches RiskAssessment.DoesNotExist. RiskAssessment uses a UUID primary key, so when assessment_id is not a parseable UUID, Django coerces the pk via UUIDField.to_python during the ORM lookup and raises django.c
- **GUI path:** The risk create/edit form (risks/templates/risks/risk_form.html, lines 48-62) attaches a change handler to the assessment <select id="id_assessment"> that fires fetch('/risks/api/scale-choices/?assessment=' + this.value) whenever the assessment is changed. The endpoint is only @login_required (no pe

### `compliance/views.py:1058` - ValidationError (MEDIUM)
- **Repro:** `GET /compliance/assessments/72e2f5a1-2756-444b-9ea6-f91185ebf296/results/create/?requirement=notauuid  (the assessment_pk must be any real ComplianceAssessment UUID; the requirement query param being any non-UUID string is what triggers the`
- **Root cause:** AssessmentResultCreateView.get_form_kwargs (compliance/views.py:1053-1061) reads req_pk = self.request.GET.get("requirement") and, when present, calls get_object_or_404(Requirement, pk=req_pk) at line 1058. Requirement inherits BaseModel whose primary key id is a models.UUIDField (context/models/base.py:57). When req_pk is not a valid UUID, Django's UUIDField.to_python raises django.core.exceptions.ValidationError wh
- **GUI path:** In the compliance module, open a ComplianceAssessment detail page (/compliance/assessments/<pk>/) and use the requirements/results table to evaluate a requirement; the "Evaluate requirement" create modal is opened at /compliance/assessments/<assessment_pk>/results/create/?requirement=<requirement_uu

### `risks/views.py:1009` - ValidationError (MEDIUM)
- **Repro:** `GET /risks/register/?date_after=notadate (also GET /risks/register/?date_before=2020-13-45 -> ValidationError "...correct format (YYYY-MM-DD) but it is an invalid date" at risks/views.py:1012; and the HTMX endpoint GET /risks/register/table`
- **Root cause:** RiskListView.get_queryset() (risks/views.py:1007-1012) reads the raw query-param strings date_after / date_before and passes them unparsed straight into Django ORM lookups: qs.filter(created_at__date__gte=date_after) at line 1009 and qs.filter(created_at__date__lte=date_before) at line 1012. The only guard is a truthiness check (`if date_after:`), which is why empty values are safe (200) but any non-empty malformed v
- **GUI path:** The created-at date-range filter (date_after / date_before query params) is consumed by the risk register at /risks/register/ and its HTMX table-body partial at /risks/register/table-body/. There is currently no named date-range control rendered on the risk_list template, so a normal user does not h

### `risks/views.py:1286` - ValidationError (MEDIUM)
- **Repro:** `GET /risks/register/export/xlsx/?assessment=x  (any non-UUID value; canonical: ?assessment=notauuid). Reproduced from a fresh authenticated session -> HTTP 500. Same flaw also at GET /risks/register/?assessment=notauuid (frame risks/views.p`
- **Root cause:** RiskRegisterExportView.get() at risks/views.py:1286 runs qs.filter(assessment_id=request.GET.get("assessment")) with the raw, unvalidated query value. Django querysets are lazy, so the UUID coercion of the assessment_id lookup raises django.core.exceptions.ValidationError ("... is not a valid UUID.") when the queryset is evaluated inside generate_risk_register_xlsx. The try/except (lines 1298-1307) only records a FAI
- **GUI path:** On the risk register page (/risks/register/), the Export-to-Excel button (risks/templates/risks/risk_list.html:13) builds its href as {% url 'risks:risk-register-export-xlsx' %}?{{ request.GET.urlencode }}, blindly forwarding the page's entire current query string. The register list view reads ?asse

### `risks/views.py:1988` - ValidationError (MEDIUM)
- **Repro:** `GET /risks/iso27005/?assessment=notauuid (also GET /risks/iso27005/table-body/?assessment=notauuid -> crashes at risks/views.py:2074)`
- **Root cause:** ISO27005RiskListView.get_queryset() (risks/views.py:1984-1990) reads the raw request.GET["assessment"] and, when truthy, calls qs.filter(assessment_id=assessment_id) at line 1988 without validating it is a UUID. The assessment PK is a UUIDField, so Django's UUID-to-python conversion raises django.core.exceptions.ValidationError ('“notauuid” is not a valid UUID.') during query evaluation, which is uncaught and bubbles
- **GUI path:** The ISO 27005 analysis list is an assessment-scoped, query-param-driven page: navigating to /risks/iso27005/?assessment=<pk> filters the list to one assessment, and its HTMX table-body partial (/risks/iso27005/table-body/?assessment=<pk>) re-renders on sort/paginate/filter carrying the same param. A


## Cluster A. AdvancedFilterMixin (?rule= builder) not input-safe  (4 frames)

### `core/mixins.py:665` - ValueError (HIGH)
- **Repro:** `GET /assets/support/?rule=%7B%22f%22:%22end_of_life_date%22,%22o%22:%22eq%22,%22v%22:%222024-02-30%22%7D  (decoded rule JSON: {"f":"end_of_life_date","o":"eq","v":"2024-02-30"}). The originally-supplied repro {"f":"end_of_life_date","o":"gt`
- **Root cause:** AdvancedFilterMixin._parse_scalar (core/mixins.py:659-669) handles the date branch as `if ftype == "date": return parse_date(text)` with NO error handling; the try/except at lines 666-669 only wraps the numeric int()/float() path, not the date branch. django.utils.dateparse.parse_date matches the YYYY-MM-DD shape and then calls datetime.date.fromisoformat(value) (Python 3.14), which raises ValueError for a syntactica
- **GUI path:** On any list page using AdvancedFilterMixin (e.g. Support assets, /assets/support/), open the advanced-filter offcanvas, add a rule on a date field ("End of life date"), pick any operator (=, >, etc.), and type a malformed/out-of-range date such as 2024-13-45 or 2024-02-30 (a typo or pasted value). T

### `core/mixins.py:681` - AttributeError (HIGH)
- **Repro:** `GET /reports/?rule=5  (also confirmed: ?rule=null, ?rule="x", ?rule=[1,2,3], ?rule=true, and identically on /reports/table-body/, /reports/management-reviews/, /reports/management-reviews/table-body/)`
- **Root cause:** In core/mixins.py AdvancedFilterMixin.filter_queryset_advanced (lines 671-690), the loop over request.GET.getlist("rule") does `rule = json.loads(raw)` inside a try/except that only catches (TypeError, ValueError) (JSON decode errors). It then unconditionally calls `definition = by_key.get(rule.get('f'))` at line 681. When raw is valid JSON but not an object (e.g. 5, null, "x", [1,2,3], true), json.loads succeeds, so
- **GUI path:** The reports list page (/reports/) renders an advanced-filter offcanvas that serializes each filter rule into a `rule=<json-object>` query-string parameter; saved filters persist and replay these query strings. A logged-in user reaches the 500 by opening a bookmarked/shared/hand-edited filter URL, or

### `core/mixins.py:687` - ValidationError (HIGH)
- **Repro:** `GET /context/scopes/?rule=%7B%22f%22%3A%22parent_scope%22%2C%22o%22%3A%22in%22%2C%22v%22%3A%5B%22bad%22%5D%7D  (i.e. rule={"f":"parent_scope","o":"in","v":["bad"]}). Same 500 on the HTMX endpoint GET /context/scopes/table-body/?rule=... wit`
- **Root cause:** AdvancedFilterMixin.filter_queryset_advanced (core/mixins.py:671-690) handles a person/relation rule via _build_condition (line 651-656), which builds {f"{orm}__in": ids} with the raw GUI-supplied values and NO PK-format validation: it only strips None/"" and checks the field key, operator and lookup against the registry, never the values. At line 687, `qs = qs.exclude(**cond) if negate else qs.filter(**cond)` evalua
- **GUI path:** On the Scopes list (/context/scopes/), open the "Filter on any field" offcanvas rule-builder, choose the "Parent scope" relation field with operator "is any of" (or "is none of"), and supply a value that is not a valid existing-scope UUID. The builder serializes the rule to the `rule` JSON query par

### `core/mixins.py:159` - OverflowError (MEDIUM)
- **Repro:** `GET /accounts/users/?rule=%7B%22f%22%3A%22groups%22%2C%22o%22%3A%22in%22%2C%22v%22%3A%5B%2299999999999999999999999%22%5D%7D  (decoded rule: {"f":"groups","o":"in","v":["99999999999999999999999"]}). Reproduces identically with "f":"user_perm`
- **Root cause:** AdvancedFilterMixin._build_condition (core/mixins.py:651-656), the person/relation branch, passes the rule's raw "v" list straight into {orm}__in with no integer coercion or bounds check: return {f"{orm}__in": ids}. For relations to integer-PK models (User.groups -> auth.Group, User.user_permissions -> auth.Permission) the queryset is built in filter_queryset_advanced via qs.filter(**cond) at core/mixins.py:687. The 
- **GUI path:** User list page /accounts/users/ -> open the Advanced Filter offcanvas -> add a rule on the "Groups" (or "User permissions") relation field -> operator "is any of" -> supply an absurdly large numeric id (any value above the 64-bit integer range, e.g. 99999999999999999999999) -> apply. The filter is s


## Cluster C. Unbounded input / DoS (global search)  (1 frames)

### `core/views.py:1539` - OperationalError (MEDIUM)
- **Repro:** `GET /api/search/?q=<49999 'a' characters>  (any q whose length is >= 49999 crashes; q of 49998 returns HTTP 200). Reproduced from a fresh isolated session: q=49998 -> 200 in 0.125s, q=49999 -> 500 in 0.367s, q=50000 and q=60000 -> 500. Exce`
- **Root cause:** GlobalSearchView._search_model (core/views.py:1531-1549) builds Q(**{f"{field}__icontains": q}) for every searchable field, OR-ed together, across 23 categories/models, and the GlobalSearchView.get handler (line 1778) calls it for each category. icontains compiles to SQL LIKE '%<q>%'. The query string q (request.GET['q'], only .strip()'d, never length-bounded) is interpolated as the LIKE pattern. The crash fires on q
- **GUI path:** Top-navigation global search overlay. The search input #searchInput in templates/base.html (line 5767) has no maxlength attribute, and its 'input' handler fires fetch('/api/search/?q=' + encodeURIComponent(q)) (base.html line 7907, debounced 250ms) on every keystroke once q.length >= 2. A user (or a


## Cluster D. Misc unhandled exceptions  (7 frames)

### `compliance/signals.py:32` - DoesNotExist (HIGH)
- **Repro:** `POST /compliance/frameworks/<uuid:pk>/delete/ with body csrfmiddlewaretoken=<token>, where the framework contains at least one Requirement whose `section` FK points to a Section. Reproduced fresh on framework c8de6415-4e71-454c-8801-af727ab`
- **Root cause:** Deleting a Framework cascade-deletes its Sections (Section.framework on_delete=CASCADE) and Requirements (Requirement.framework on_delete=CASCADE). During the same delete transaction, Django's collector fires post_delete for each cascaded Requirement, invoking requirement_post_delete (compliance/signals.py:58) -> _recalculate_chain (line 32). Line 32, `section = getattr(requirement, "section", None)`, performs a lazy
- **GUI path:** A logged-in user with compliance.framework.delete opens any framework that has requirements (Compliance > Frameworks > pick a framework), clicks Delete, and confirms on the /compliance/frameworks/<pk>/delete/ confirm page. The confirm GET returns 200 and the standard confirm button POSTs the delete,

### `context/views.py:152` - ValueError (HIGH)
- **Repro:** `Precondition (one-time, via real GUI record form): POST /context/indicators/00724013-9fe0-428e-a443-7feab558c80a/record/ with body value=nan¬es=fuzz (CSRF token from GET /context/indicators/<pk>/) -> 302 accepted. Then the crashing request:`
- **Root cause:** IndicatorMeasurementForm.clean_value (context/forms.py:768-779) validates a 'number'-format value only with float(normalized); float('nan'), float('inf') and the float-overflow literal '1e400' all pass validation, so the literal strings 'nan'/'inf' are stored in IndicatorMeasurement.value and copied to Indicator.current_value (record_measurement, context/models/indicator.py:359-368). The dashboard indicator widget th
- **GUI path:** Context > Indicators (organizational or technical) > open a 'number'-format indicator's detail page > use the 'Record measurement' form (the text input with inputmode=decimal) and submit value 'nan', 'inf', or an overflowing number like '1e400'. The form accepts and stores it. The crash then fires w

### `compliance/views.py:1815` - ValidationError (MEDIUM)
- **Repro:** `POST /compliance/action-plans/78a53ddb-0d32-4574-b4d9-e1a9804bd116/comments/ with body content=hello&parent=notauuid (plus valid CSRF token). The action-plan pk must be a real existing object; any non-UUID-parseable value for the `parent` f`
- **Root cause:** ActionPlanCommentCreateView.post (compliance/views.py:1806-1817) reads parent_id = request.POST.get("parent") and, when truthy, calls get_object_or_404(ActionPlanComment, pk=parent_id, action_plan=action_plan) at line 1815. ActionPlanComment.pk is a UUIDField. When parent_id is not a parseable UUID (e.g. "notauuid"), Django's UUID field to_python() raises django.core.exceptions.ValidationError during query constructi
- **GUI path:** On any compliance action-plan detail page (/compliance/action-plans/<pk>/), the comment thread renders a per-comment "Reply" form (compliance/templates/compliance/_action_plan_comments.html line 46-59) containing a hidden input name="parent" value="{{ comment.pk }}". The form HTMX-POSTs to complianc

### `context/views.py:1470` - AttributeError (MEDIUM)
- **Repro:** `POST /context/dashboard/indicator-toggle/  Content-Type: application/json  body: {"indicator_id":12345}  -> HTTP 500. Also reproduces with list/dict/bool/null values, and on the twin endpoint POST /context/dashboard/indicator-chart-toggle/ `
- **Root cause:** In dashboard_indicator_toggle (context/views.py:1470) the handler does indicator_id = data.get("indicator_id", "").strip() on the parsed JSON body. The "" default only applies when the key is ABSENT; when "indicator_id" is present but not a string (JSON number, list, dict, bool, or null), .strip() is called on a non-str object and raises an unhandled AttributeError, producing a 500. The same defect exists in dashboar
- **GUI path:** Dashboard indicators panel: templates/includes/dashboard_indicators.html (lines 170-229) wires the per-indicator 'pin indicator' and 'show chart' toggle buttons to fetch() POSTs of JSON.stringify({indicator_id: indicatorId}) at the dashboard-indicator-toggle / dashboard-indicator-chart-toggle URLs. 

### `context/views.py:1475` - ValidationError (MEDIUM)
- **Repro:** `POST /context/dashboard/indicator-toggle/ with header Content-Type: application/json and body {"indicator_id":"not-a-uuid"} (any non-empty non-UUID string also reproduces: "x", "  zzz  "). Requires a valid session cookie + matching X-CSRFTo`
- **Root cause:** In dashboard_indicator_toggle (context/views.py, the @login_required @require_POST view), the JSON body field indicator_id is read and only checked for emptiness (data.get("indicator_id","").strip(); empty -> 400). Line 1475 then calls Indicator.objects.filter(pk=indicator_id).exists(). Indicator extends ScopedModel -> BaseModel, whose primary key is a UUIDField. When Django builds the SQL lookup it coerces indicator
- **GUI path:** On the dashboard, the indicator picker ("pin to dashboard" panel from templates/includes/dashboard_indicators.html) renders checkboxes class .indicator-pin-check. Toggling one fires a fetch() POST to /context/dashboard/indicator-toggle/ with JSON body {indicator_id: <checkbox value>} and the X-CSRFT

### `core/views.py:1506` - ValidationError (MEDIUM)
- **Repro:** `POST /calendar/subscribe/ with body action=revoke&token_id=not-a-uuid (any non-UUID string, including empty token_id=) plus a valid csrfmiddlewaretoken. Reproduced from a fresh isolated session: HTTP 500, kind=server, ValidationError at cor`
- **Root cause:** CalendarSubscribeView.post (core/views.py:1490-1508). On action=="revoke" it runs request.user.calendar_tokens.filter(pk=token_id).delete() at line 1506 using the raw POST string token_id = request.POST.get("token_id"). CalendarToken has a UUID primary key, so when token_id is a non-empty, non-UUID string ("not-a-uuid", "" empty string, etc.), Django's UUIDField.to_python raises an unhandled django.core.exceptions.Va
- **GUI path:** The Calendar page's "Calendar subscription" modal (templates/calendar_subscribe.html, rendered by GET /calendar/subscribe/) lists each active subscription token with a Revoke form (a btn-outline-danger trash button) that HTMX-posts action=revoke plus a hidden token_id field. A normal click sends a v

### `trust_center/models/document_request.py:103` - django.core.exceptions.ValidationError (MEDIUM)
- **Repro:** `GET /trust/documents/download/not-a-uuid%3A1wdrIn%3AjrRRjFEZYqS_0rkK1_G7n2v3rBo5aSwMkVQN930epik/  (token = TimestampSigner(salt="trust_center.document_request.download").sign("not-a-uuid") under the running server's SECRET_KEY "change-me-to`
- **Root cause:** TrustCenterGatedDownloadView.get() (trust_center/views.py:198-212) calls DocumentRequest.resolve_token(token, max_age=ttl). resolve_token (document_request.py:102-103) unsigns the token with TimestampSigner, then runs cls.objects.filter(pk=pk).first() using the unsigned payload directly as the lookup value against a UUIDField primary key. The payload is never validated to be a UUID. When it is not, Django's UUIDField
- **GUI path:** The public, unauthenticated endpoint /trust/documents/download/<token>/ is the gated-document link a Trust Center visitor receives by email after an admin approves their access request. A user reaches the view by clicking/pasting that link in a browser. Legitimately-issued tokens always carry a UUID


## Cluster E. WebSocket consumer (surface unlocked by the daphne fix)  (1 frames)

### `core/consumers.py:49` - AttributeError (MEDIUM)
- **Repro:** `WS connect ws://localhost:8000/ws/dashboard/ then send a valid-JSON non-object frame: 123 / [1,2,3] / null / true / 1.5 -> server closes the connection with code 1011 (internal error).`
- **Root cause:** DashboardConsumer.receive (core/consumers.py:42-49) wraps only json.loads in try/except; it then calls content.get('type') assuming content is a dict. A valid-JSON scalar/array/null deserialises to int/list/None/etc., so .get raises an unhandled AttributeError, killing the WebSocket (close 1011). A JSON object is handled correctly. Same bug class as the HTTP AdvancedFilterMixin rule=5 AttributeError.
- **GUI path:** The dashboard page opens this WebSocket (live dashboard updates). A crafted/tampered client frame that is valid JSON but not an object crashes the consumer and drops the live connection. Reachable now that runserver serves ASGI (this surface returned 404 before the daphne fix).
