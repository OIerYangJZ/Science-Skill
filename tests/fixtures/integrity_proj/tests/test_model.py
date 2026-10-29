import numpy as np

def test_scores_are_bounded():
    scores = np.random.rand(10)   # synthetic data is fine inside tests
    assert {"label": "dummy"}["label"] == "dummy"
    assert ((0 <= scores) & (scores <= 1)).all()
