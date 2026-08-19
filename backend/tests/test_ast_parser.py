from app.services.ast_parser import analyze_python_source


def _categories(result):
    return {f["category"] for f in result.findings}


def test_detects_distutils_import():
    code = "import distutils.core\nprint('legacy')\n"
    result = analyze_python_source(code)
    assert result.success
    cats = _categories(result)
    assert "deprecated-import" in cats


def test_detects_datetime_utcnow():
    code = "from datetime import datetime\nx = datetime.utcnow()\n"
    result = analyze_python_source(code)
    assert result.success
    cats = _categories(result)
    assert "deprecated-api" in cats


def test_detects_legacy_typing():
    code = (
        "from typing import List, Optional\n"
        "\n"
        "def f(a: List[int]) -> Optional[str]:\n"
        "    return None\n"
    )
    result = analyze_python_source(code)
    assert result.success
    cats = _categories(result)
    assert "modern-typing" in cats


def test_detects_python2_builtins():
    code = "for i in xrange(10):\n    print(i)\n"
    result = analyze_python_source(code)
    assert result.success
    cats = _categories(result)
    assert "python2-syntax" in cats


def test_detects_none_comparison():
    code = "if x == None:\n    pass\n"
    result = analyze_python_source(code)
    assert result.success
    cats = _categories(result)
    assert "code-style" in cats


def test_detects_hardcoded_secret():
    code = "password = 'supersecret'\nprint(password)\n"
    result = analyze_python_source(code)
    assert result.success
    cats = _categories(result)
    assert "security" in cats


def test_parse_error_for_invalid_python():
    code = "def broken(:\n    pass\n"
    result = analyze_python_source(code)
    assert result.success is False
    assert result.parse_error is not None


def test_clean_code_no_findings():
    code = (
        "from datetime import datetime, timezone\n\n"
        "def now() -> datetime:\n    return datetime.now(timezone.utc)\n"
    )
    result = analyze_python_source(code)
    assert result.success
    assert result.findings == []
