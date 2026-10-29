def check(text, v):
    assert str(v) in text
    assert f"{v:.2f}" in text
