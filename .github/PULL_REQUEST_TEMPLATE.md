<!-- Thanks for contributing to Cairn. Fill in the sections below and tick the checklist. -->

## Summary

<!-- What does this PR do, and why? Keep it concise. -->

## Related issue

<!-- e.g. Closes #123 -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor / tech debt
- [ ] Documentation
- [ ] Build / CI / tooling

## Changes

<!-- Bullet the notable changes. -->

-

## Screenshots

<!-- For any UI change, attach before/after screenshots in BOTH light and dark mode, and confirm mobile rendering. -->

## Checklist

<!-- Tick everything that applies. See CLAUDE.md for the full development guidelines. -->

- [ ] Tests added or updated, and `pytest` passes
- [ ] `ruff check` passes
- [ ] New feature exposed as MCP tools in `mcp/tools.py` (accurate docstrings and parameter descriptions)
- [ ] New feature has REST API endpoints under the app's `api/` (serializers, viewsets, routes under `/api/v1/`)
- [ ] UI renders correctly in light and dark mode
- [ ] UI renders correctly on mobile (multi-selects, sticky bars, form layouts)
- [ ] User-facing strings use `_()` / `{% trans %}` with French translations in `locale/fr/LC_MESSAGES/django.po` (no duplicate `msgid`; `compilemessages` passes)
- [ ] Lifecycle / workflow respected (state metadata and generic stepper UI; no hardcoded status values)
- [ ] `README.md` updated (features, MCP tools, tech stack, install) when behaviour changed
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] Brand guidelines respected (`docs/brand/brand-guidelines.md`); no em dash characters
- [ ] Relevant spec under `docs/modules/` updated in the same PR
- [ ] Project / documentation screenshots captured at 2560x1440 (16:9, 1440p)
- [ ] Audit-grade rigor preserved (approval workflows, versioning, history, permission checks not bypassed)
