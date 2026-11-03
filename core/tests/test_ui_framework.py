# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Tests for the layout and content primitives of core.templatetags.ui.

detail_layout, section_card, overview / ov_row, meta_list / meta_item,
record_card, kpi_tile, ref_link, tag_list, choice_badge, dash / or_dash,
back_url, plus the shared page form and delete confirmation shells.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.template import Context, Template, TemplateSyntaxError
from django.test import RequestFactory

from core.templatetags.ui import tag_colors

pytestmark = pytest.mark.django_db


def render(tpl: str, ctx: dict | None = None) -> str:
    return Template("{% load ui %}" + tpl).render(Context(ctx or {}))


class TestDash:
    def test_dash_tag(self):
        out = render("{% dash %}")
        assert 'class="ui-dash"' in out
        assert 'aria-label="Not set"' in out

    @pytest.mark.parametrize("value", [None, "", "   ", []])
    def test_or_dash_on_blank(self, value):
        assert "ui-dash" in render("{{ v|or_dash }}", {"v": value})

    @pytest.mark.parametrize("value", [0, "x", [1]])
    def test_or_dash_keeps_values(self, value):
        assert "ui-dash" not in render("{{ v|or_dash }}", {"v": value})


class TestSlot:
    def test_slot_takes_one_name(self):
        with pytest.raises(TemplateSyntaxError):
            render("{% slot %}x{% endslot %}")

    def test_slot_renders_nothing_alone(self):
        assert render("{% slot rail %}hidden{% endslot %}").strip() == ""


class TestDetailLayout:
    def test_main_and_rail(self):
        out = render("{% detail_layout %}{% slot rail %}RAIL{% endslot %}MAIN{% enddetail_layout %}")
        assert 'class="detail-layout"' in out
        assert '<div class="detail-main">MAIN</div>' in out
        assert 'class="detail-rail"' in out and "RAIL" in out
        assert out.index("MAIN") < out.index("RAIL")

    def test_without_rail(self):
        out = render("{% detail_layout %}MAIN{% enddetail_layout %}")
        assert "detail-layout--single" in out
        assert "detail-rail" not in out

    def test_nested_slots_belong_to_their_own_container(self):
        out = render(
            "{% detail_layout %}"
            "{% section_card 'A' %}{% slot actions %}ACT{% endslot %}body{% endsection_card %}"
            "{% enddetail_layout %}"
        )
        assert "detail-rail" not in out
        assert 'class="section-card__actions">ACT' in out


class TestSectionCard:
    def test_title_icon_count_body(self):
        out = render('{% section_card "Linked risks" icon="exclamation-triangle" count=3 %}BODY{% endsection_card %}')
        assert '<h2 class="section-card__title">' in out
        assert "bi-exclamation-triangle" in out
        assert "Linked risks" in out
        assert 'section-card__count tabular-nums">3<' in out
        assert '<div class="section-card__body">BODY</div>' in out

    def test_zero_count_is_shown(self):
        assert 'tabular-nums">0<' in render('{% section_card "X" count=0 %}b{% endsection_card %}')

    def test_actions_and_footer_slots(self):
        out = render(
            '{% section_card "X" %}{% slot actions %}<a>add</a>{% endslot %}'
            "{% slot footer %}FOOT{% endslot %}body{% endsection_card %}"
        )
        assert '<div class="section-card__actions"><a>add</a></div>' in out
        assert '<footer class="section-card__footer">FOOT</footer>' in out
        assert '<div class="section-card__body">body</div>' in out

    def test_collapsible_closed(self):
        out = render('{% section_card "X" collapsible=True open=False %}b{% endsection_card %}')
        assert "<details" in out and " open" not in out.split("<details", 1)[1].split(">", 1)[0]
        assert "<summary" in out

    def test_flush_and_id(self):
        out = render('{% section_card "X" flush=True id="risks" %}b{% endsection_card %}')
        assert "section-card--flush" in out
        assert 'id="risks"' in out

    def test_hide_empty(self):
        assert render('{% section_card "X" hide_empty=True %}  {% endsection_card %}').strip() == ""

    def test_untitled_card(self):
        out = render("{% section_card %}b{% endsection_card %}")
        assert "section-card__head" not in out


class TestOverview:
    def test_rows_and_empty_rows_dropped(self):
        out = render(
            "{% overview %}"
            '{% ov_row "award" "Issuer" %}ANSSI{% endov_row %}'
            '{% ov_row "hash" "Number" %}{{ missing }}{% endov_row %}'
            "{% endoverview %}"
        )
        assert out.count('class="ov-row"') == 1
        assert 'aria-label="Issuer"' in out
        assert "bi-award" in out and "ANSSI" in out
        assert "bi-hash" not in out

    def test_all_rows_empty_renders_nothing(self):
        out = render('{% overview %}{% ov_row "hash" "N" %}{% endov_row %}{% endoverview %}')
        assert out.strip() == ""

    def test_lead_and_rich(self):
        out = render('{% overview %}{% ov_row "text-left" "Description" lead=True rich=True %}<p>x</p>{% endov_row %}{% endoverview %}')
        assert "ov-row--lead" in out
        assert "ov-rich" in out


class TestMetaList:
    def test_inline_and_block_items(self):
        out = render(
            "{% meta_list cols=2 %}"
            '{% meta_item "Start" start %}'
            '{% meta_item "Owner" %}<b>Ann</b>{% endmeta_item %}'
            "{% endmeta_list %}",
            {"start": "2026-01-01"},
        )
        assert '<dl class="meta-list meta-list--cols-2">' in out
        assert '<dt class="meta-list__label">Start</dt><dd class="meta-list__value">2026-01-01</dd>' in out
        assert "<b>Ann</b>" in out

    def test_empty_values_render_the_dash(self):
        out = render('{% meta_list %}{% meta_item "A" none %}{% meta_item "B" %}{% endmeta_item %}{% endmeta_list %}')
        assert out.count("ui-dash") == 2

    def test_inline_value_is_escaped(self):
        out = render('{% meta_list %}{% meta_item "A" v %}{% endmeta_list %}', {"v": "<script>"})
        assert "<script>" not in out and "&lt;script&gt;" in out

    def test_hide_empty_and_wide(self):
        out = render(
            '{% meta_list %}{% meta_item "A" hide_empty=True %}{% endmeta_item %}'
            '{% meta_item "B" wide=True %}x{% endmeta_item %}{% endmeta_list %}'
        )
        assert ">A<" not in out
        assert "meta-list__item--wide" in out

    def test_translated_label(self):
        out = render('{% meta_list %}{% meta_item _("Version") 3 %}{% endmeta_list %}')
        assert ">Version<" in out and ">3<" in out


class TestKpiTile:
    def test_number_is_large(self):
        out = render('{% kpi_tile "Covered sites" 4 icon="geo-alt" tone="success" %}')
        assert "kpi-tile--success" in out
        assert "kpi-tile__icon--success" in out
        assert "kpi-tile__value--lg" in out
        assert ">Covered sites<" in out

    def test_text_is_small_and_blank_is_dash(self):
        assert "kpi-tile__value--sm" in render('{% kpi_tile "Stage" "Assessment" %}')
        assert "ui-dash" in render('{% kpi_tile "Expiry" none %}')

    def test_unknown_tone_falls_back(self):
        assert "kpi-tile--neutral" in render('{% kpi_tile "X" 1 tone="secondary" %}')
        assert "kpi-tile--accent" in render('{% kpi_tile "X" 1 tone="bogus" %}')

    def test_link_and_suffix(self):
        out = render('{% kpi_tile "Open" 3 href="/x/" suffix="/ 10" %}')
        assert 'href="/x/"' in out and "stretched-link" in out
        assert "/ 10" in out


class TestRefLink:
    def test_url(self):
        obj = SimpleNamespace(reference="RISK-1", name="Phishing")
        out = render('{% ref_link obj url="/r/1/" %}', {"obj": obj})
        assert '<span class="ref">RISK-1</span>' in out
        assert '<a href="/r/1/" class="ref-link__label">Phishing</a>' in out

    def test_preview_opens_the_drawer(self):
        obj = SimpleNamespace(reference="F-2", name="Gap")
        out = render('{% ref_link obj preview_url="/p/2/" %}', {"obj": obj})
        assert 'hx-get="/p/2/"' in out and 'hx-target="#drawer-form-content"' in out

    def test_label_override_and_plain(self):
        obj = SimpleNamespace(reference="", name="N")
        out = render('{% ref_link obj label="Custom" %}', {"obj": obj})
        assert 'class="ref"' not in out
        assert '<span class="ref-link__label">Custom</span>' in out


class TestTagList:
    def test_pills_with_contrast(self):
        tags = [SimpleNamespace(name="GDPR", color="#1E3A8A"), SimpleNamespace(name="Pale", color="#FDE68A")]
        out = render("{% tag_list tags %}", {"tags": tags})
        assert "--tag-bg:#1E3A8A;--tag-fg:#ffffff" in out
        assert "--tag-bg:#FDE68A;--tag-fg:#161312" in out

    def test_unsafe_colour_never_reaches_the_style(self):
        tags = [SimpleNamespace(name="x", color="red;background:url(https://evil)")]
        out = render("{% tag_list tags %}", {"tags": tags})
        assert "evil" not in out
        assert "--tag-bg:var(--surface-subtle)" in out

    def test_empty(self):
        assert render("{% tag_list tags %}", {"tags": []}).strip() == ""
        assert "ui-dash" in render("{% tag_list tags dash=True %}", {"tags": []})

    @pytest.mark.parametrize(
        "color,expected_fg",
        [("#000000", "#ffffff"), ("#ffffff", "#161312"), ("#fff", "#161312"), (None, "var(--text-secondary)")],
    )
    def test_tag_colors(self, color, expected_fg):
        assert tag_colors(color)[1] == expected_fg


class TestChoiceBadge:
    def _obj(self, **kw):
        obj = SimpleNamespace(**kw)
        for field, value in kw.items():
            setattr(obj, f"get_{field}_display", lambda v=value: f"Label {v}")
        return obj

    def test_priority_uses_the_level_scale(self):
        out = render('{% choice_badge o "priority" %}', {"o": self._obj(priority="critical")})
        assert 'class="badge-dot danger"' in out
        assert "Label critical" in out

    def test_compliance_status(self):
        out = render('{% choice_badge o "compliance_status" %}', {"o": self._obj(compliance_status="partially_compliant")})
        assert "badge-dot warning" in out

    def test_explicit_type_and_unknown_value(self):
        out = render('{% choice_badge o "state" type="status" %}', {"o": self._obj(state="ghost")})
        assert "badge-dot secondary" in out

    def test_blank_renders_dash(self):
        assert "ui-dash" in render('{% choice_badge o "priority" %}', {"o": self._obj(priority="")})


class TestRecordCard:
    def test_traceability_fields(self):
        from context.tests.factories import IssueFactory

        issue = IssueFactory()
        out = render("{% record_card obj %}", {"obj": issue})
        assert "Traceability" in out
        assert issue.reference in out
        for label in ("Version", "Created by", "Created on", "Modified on"):
            assert label in out
        assert "<time datetime=" in out


class TestBackUrl:
    def _ctx(self, referer):
        request = RequestFactory().get("/", HTTP_REFERER=referer) if referer else RequestFactory().get("/")
        return {"request": request}

    def test_same_host_referer(self):
        assert render('{% back_url "/list/" %}', self._ctx("http://testserver/risks/")) == "http://testserver/risks/"

    def test_foreign_referer_is_ignored(self):
        assert render('{% back_url "/list/" %}', self._ctx("https://evil.example/")) == "/list/"

    def test_no_referer(self):
        assert render('{% back_url "/list/" %}', self._ctx(None)) == "/list/"


class TestPageForm:
    """The full-page fallback of a modal form (includes/page_form.html)."""

    @pytest.fixture
    def client(self):
        from django.test import Client

        from accounts.tests.factories import UserFactory

        c = Client()
        c.force_login(UserFactory(is_superuser=True))
        return c

    def test_edit_page_renders_the_shared_shell(self, client):
        from django.urls import reverse

        from compliance.tests.factories import ComplianceActionPlanFactory

        plan = ComplianceActionPlanFactory()
        resp = client.get(reverse("compliance:action-plan-update", args=[plan.pk]))
        assert resp.status_code == 200
        html = resp.content.decode()
        assert 'class="card page-form"' in html
        assert "Edit action plan" in html
        assert "page-header__breadcrumb" in html  # form_nav resolved from the list URL
        assert f'href="{reverse("compliance:action-plan-list")}" class="btn btn-secondary me-auto"' in html
        assert "btn-outline-danger" not in html.split('class="card page-form"', 1)[1]

    def test_cancel_ignores_a_foreign_referer(self):
        from core.mixins import page_form_cancel_url

        view = SimpleNamespace(success_url=None, request=RequestFactory().get("/", HTTP_REFERER="https://evil.example/x"))
        assert page_form_cancel_url(view) == "/"
        view.request = RequestFactory().get("/", HTTP_REFERER="http://testserver/risks/")
        assert page_form_cancel_url(view) == "http://testserver/risks/"


class TestFrameworkAdditions:
    @pytest.mark.parametrize("pct,tone", [(85, "success"), (80, "success"), (65, "warning"), (10, "danger"), (None, "neutral"), ("x", "neutral")])
    def test_score_tone(self, pct, tone):
        assert render("{{ p|score_tone }}", {"p": pct}) == tone

    def test_compact_empty_state(self):
        assert "empty-state--compact" in render('{% empty_state message="None yet" compact=True %}')
        assert "empty-state--compact" not in render('{% empty_state message="None yet" %}')

    def test_subhead_count(self):
        out = render('{% subhead "Sites" icon="geo-alt" count=0 %}')
        assert 'section-card__count tabular-nums">0<' in out

    def test_section_card_classes(self):
        assert 'class="card section-card mb-3"' in render('{% section_card "X" classes="mb-3" %}b{% endsection_card %}')

    def test_record_card_skips_rows_a_model_lacks(self):
        from django.contrib.auth.models import Group as AuthGroup

        out = render("{% record_card obj %}", {"obj": AuthGroup(name="g")})
        assert "Version" not in out and "Created by" not in out

    def test_choice_badge_infers_finding_and_effectiveness(self):
        obj = SimpleNamespace(finding_type="major_nc", get_finding_type_display=lambda: "Major",
                              effectiveness_verdict="effective", get_effectiveness_verdict_display=lambda: "Effective")
        assert "badge-dot danger" in render('{% choice_badge o "finding_type" %}', {"o": obj})
        assert "badge-dot success" in render('{% choice_badge o "effectiveness_verdict" %}', {"o": obj})

    def test_form_fields_include(self):
        from django import forms

        class F(forms.Form):
            name = forms.CharField(help_text="Name it")
            secret = forms.CharField(widget=forms.HiddenInput)

        out = Template('{% include "includes/form_fields.html" %}').render(Context({"form": F()}))
        assert 'class="form-label"' in out and "Name it" in out
        assert 'type="hidden" name="secret"' in out
