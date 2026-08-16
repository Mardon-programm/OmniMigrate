from app.services.rule_engine import apply_modernization_rules


def test_xrange_to_range():
    result = apply_modernization_rules("for i in xrange(10):\n    print(i)\n")
    assert "range(10)" in result.code
    assert "xrange" not in result.code
    assert "xrange -> range" in result.applied_rules


def test_utcnow_to_now_timezone():
    result = apply_modernization_rules(
        "from datetime import datetime\nx = datetime.utcnow()\n"
    )
    assert "timezone.utc" in result.code
    assert "utcnow" not in result.code
    assert "import timezone" in result.code
    assert "from datetime import timezone" in result.code


def test_none_comparison_identity():
    code = "if value == None:\n    pass\nif other != None:\n    pass\n"
    result = apply_modernization_rules(code)
    assert "value is None" in result.code
    assert "other is not None" in result.code
    assert "== None" not in result.code
    assert "!= None" not in result.code


def test_legacy_typing_subscript():
    code = "def f(items: List[int]) -> None:\n    return None\n"
    result = apply_modernization_rules(code)
    assert "list[int]" in result.code
    assert "List[int]" not in result.code


def test_rules_idempotent():
    code = "for i in xrange(3):\n    print(i)\n"
    once = apply_modernization_rules(code).code
    twice = apply_modernization_rules(once).code
    assert once == twice


def test_invalid_source_passthrough():
    code = "def broken(:\n    pass\n"
    result = apply_modernization_rules(code)
    assert result.code == code
    assert result.applied_rules == []


def test_removed_distutils_import():
    code = "import distutils.core\nimport os\nfrom distutils import util\n"
    result = apply_modernization_rules(code)
    assert "distutils" not in result.code
    assert "import os" in result.code
    assert any("distutils" in rule for rule in result.applied_rules)
