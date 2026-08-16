from app.services.sandbox import CodeSandbox, check_syntax


def test_syntax_ok():
    ok, _ = check_syntax("def f():\n    return 42\n")
    assert ok is True


def test_syntax_error():
    ok, err = check_syntax("def f(:\n    pass\n")
    assert ok is False
    assert "SyntaxError" in (err or "")


def test_sandbox_valid_python():
    sandbox = CodeSandbox(enabled=False)
    result = sandbox.verify("x = 1 + 1\nassert x == 2\n")
    assert result.success
    assert result.syntax_ok


def test_sandbox_syntax_failure():
    sandbox = CodeSandbox(enabled=True)
    result = sandbox.verify("def broken(:\n    pass\n")
    assert result.success is False
    assert result.syntax_ok is False


def test_sandbox_runtime_failure():
    sandbox = CodeSandbox(enabled=True)
    result = sandbox.verify("raise ValueError('boom')\n")
    assert result.success is False
    assert "ValueError" in "; ".join(result.errors)


def test_sandbox_runtime_success():
    sandbox = CodeSandbox(enabled=True)
    result = sandbox.verify("print('hello from sandbox')\n")
    assert result.success
    assert "hello from sandbox" in result.stdout


def test_generic_balanced_braces():
    sandbox = CodeSandbox()
    result = sandbox.verify("function f() { return 1; }", language="javascript")
    assert result.success


def test_generic_unbalanced_braces():
    sandbox = CodeSandbox()
    result = sandbox.verify("function f() { return 1;", language="javascript")
    assert result.success is False
