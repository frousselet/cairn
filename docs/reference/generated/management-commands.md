<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the Django management-command registry by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# Management commands

Commands Cairn adds on top of Django's own. Run them with `python manage.py <command>` (inside the container : `docker compose exec web python manage.py <command>`).

The ones meant to run on a schedule are covered in [../../technical/operations.md](../../technical/operations.md).

## Commands

| Command | App | Purpose |
| --- | --- | --- |
| `detect_spof` | assets | Detect Single Points of Failure (SPOF) in the dependency graph |
| `expire_risk_acceptances` | risks | Set RiskAcceptance.status to EXPIRED for any active acceptance whose valid_until date has passed; print upcoming expirations within --reminder-days (default 30). |
| `generate_docs` | core | Generate the code-derived reference pages under docs/reference/generated/. |
| `mark_overdue_treatment_plans` | risks | Set RiskTreatmentPlan.status to OVERDUE when target_date is past and the plan is not already completed, cancelled or overdue. |
| `rebuild_semantic_index` | assistant | Build or refresh the requirement semantic search index. |
| `recalculate_compliance` | compliance | Recalculate compliance counts for all assessments, then propagate to requirements/sections/frameworks. |
| `refresh_mitre_attack` | risks | Refresh the MITRE ATT&CK catalogue from a JSON fixture. |
| `vendor_assets` | core | Download the front-end libraries into static/vendor/ so the instance serves them from its own origin instead of a CDN. |
