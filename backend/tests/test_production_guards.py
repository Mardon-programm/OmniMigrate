"""Production startup guards for the anti-shrinkage contract."""

from __future__ import annotations

from app.core.config import settings
from app.main import _production_contract_issues


def test_production_contract_guard(monkeypatch):
    monkeypatch.setattr(settings, "contract_enabled", True)
    monkeypatch.setattr(settings, "contract_min_line_ratio", 0.75)
    assert _production_contract_issues() == []

    monkeypatch.setattr(settings, "contract_enabled", False)
    assert any("CONTRACT_ENABLED" in issue for issue in _production_contract_issues())

    monkeypatch.setattr(settings, "contract_enabled", True)
    monkeypatch.setattr(settings, "contract_min_line_ratio", 0.5)
    assert any(
        "CONTRACT_MIN_LINE_RATIO" in issue for issue in _production_contract_issues()
    )
