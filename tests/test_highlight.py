from prose_clinic.analyzer import analyze
from prose_clinic.highlight import change_ratio, render_diff, render_highlighted, render_in_context
from prose_clinic.sample_text import SAMPLE_PASSAGE


def test_highlighting_escapes_html_and_numbers_findings():
    text = 'She typed <script>alert(1)</script> and whispered quietly, "Your feelings are valid."'
    a = analyze(text, {})
    numbers = {f.uid: i + 1 for i, f in enumerate(a.findings)}
    out = render_highlighted(text, a.findings, numbers)
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert 'class="pc-num"' in out


def test_highlighting_handles_overlaps():
    a = analyze(SAMPLE_PASSAGE, {})
    numbers = {f.uid: i + 1 for i, f in enumerate(a.findings)}
    out = render_highlighted(SAMPLE_PASSAGE, a.findings, numbers)
    assert out.count('class="pc-num"') == len(a.span_findings)


def test_context_snippet():
    a = analyze(SAMPLE_PASSAGE, {})
    f = next(f for f in a.findings if f.excerpt == "nodded her head")
    snippet = render_in_context(SAMPLE_PASSAGE, f)
    assert "nodded her head" in snippet and "pc-hl" in snippet


def test_diff():
    left, right = render_diff("The cat sat on the mat.", "The cat lay on the mat.")
    assert 'pc-del">sat' in left and 'pc-ins">lay' in right
    assert change_ratio("a b c d", "a b c d") == 0
    assert 0 < change_ratio("a b c d", "a b x d") < 1
