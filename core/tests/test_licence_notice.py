# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""The licence notice shown in the UI must match the licence the project ships under.

Relicensing touches LICENSE, README and the About modal, and the modal is the
easy one to forget : it is the only place a running instance states its licence
to a user. Under the AGPL that statement is not cosmetic, since section 13
requires network users to be told where the corresponding source is.
"""
import pathlib

import pytest

from accounts.tests.factories import UserFactory

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.mark.django_db
def test_about_modal_states_the_agpl_and_offers_the_source(client):
    client.force_login(UserFactory())
    html = client.get("/").content.decode()

    assert "GNU AGPL v3.0 or later" in html
    assert "github.com/frousselet/cairn/blob/main/LICENSE" in html
    # AGPL section 13 : network users must be pointed at the corresponding source.
    assert "Source code available on GitHub" in html
    assert "MIT" not in html


def test_license_file_is_the_agpl():
    licence = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")

    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in licence
    assert "Version 3, 19 November 2007" in licence
    assert "MIT License" not in licence


def test_readme_declares_the_agpl():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "AGPL-3.0-or-later" in readme
