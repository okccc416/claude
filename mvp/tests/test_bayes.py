"""贝叶斯打分：候选后验、置信度模型（Beta 平滑与逐级退回）、按门槛降级。"""

from pathlib import Path

import pytest

from avmvp import ReferenceDB, Validator
from avmvp.bayes import BayesModel, BayesValidator, ConfidenceModel, ConfidenceValidator, compare
from avmvp.validator import ACCEPT, CONFIRM, FIX

FIXTURE = Path(__file__).parent / "fixture_reference.csv"


@pytest.fixture(scope="module")
def v():
    return Validator(ReferenceDB.load(FIXTURE))


def eid(v, blk, road, postal):
    return next(e.eid for e in v.db.entities if (e.blk, e.road, e.postal) == (blk, road, postal))


@pytest.fixture(scope="module")
def rows(v):
    bay = eid(v, "10", "BAYFRONT AVENUE", "018956")
    poole = eid(v, "34A", "POOLE ROAD", "437543")
    raffles = eid(v, "1", "RAFFLES PLACE", "048616")
    return [
        {"input": "10 Bayfront Avenue, Singapore 018956", "expected_eid": bay},
        {"input": "10 bayfrnt ave 018956", "expected_eid": bay},
        {"input": "34A Poole Road 437543", "expected_eid": poole},
        {"input": "34A Poxle Road", "expected_eid": poole},
        {"input": "1 Raffles Place", "expected_eid": raffles},
        {"input": "10 Bayfront Avenue, Singapore 819643", "expected_eid": bay},
        {"input": "999 Bayfront Avenue", "expected_eid": None},
        {"input": "Tampines Avenue 7, Singapore", "expected_eid": None},
        {"input": "same as last order", "expected_eid": None},
    ]


def test_compare_levels(v):
    a = v.analyze("10 Bayfront Avenue, Singapore 819643")
    f = compare(v, a, eid(v, "10", "BAYFRONT AVENUE", "018956"))
    assert f == {"postal": "mismatch", "block": "exact", "street": "exact", "building": "absent"}


@pytest.mark.parametrize("mode", ["independent", "joint"])
def test_posterior_is_a_distribution(v, rows, mode):
    model = BayesModel.fit(v, rows, rows, mode=mode, min_count=1)
    post = model.posterior(v, v.analyze("10 Bayfront Avenue, Singapore 018956"))
    assert abs(sum(p for _, p, _ in post) - 1) < 1e-9
    assert post[0][0] == rows[0]["expected_eid"]
    assert model.posterior(v, v.analyze("same as last order")) == [(None, 1.0, {})]


def test_model_roundtrip(v, rows, tmp_path):
    model = BayesModel.fit(v, rows, rows, mode="joint", min_count=1)
    model.save(tmp_path / "m.json")
    loaded = BayesModel.load(tmp_path / "m.json")
    a = v.analyze("34A Poole Road 437543")
    assert [round(p, 9) for _, p, _ in loaded.posterior(v, a)] == [round(p, 9) for _, p, _ in model.posterior(v, a)]


def test_bayes_validator_attaches_confidence(v, rows):
    bv = BayesValidator(v, BayesModel.fit(v, rows, rows, mode="joint", min_count=1))
    res = bv.validate("10 Bayfront Avenue, Singapore 018956")
    assert res.entity.eid == rows[0]["expected_eid"] and 0 < res.confidence <= 1
    assert "confidence" in bv.to_response(res)["result"]["verdict"]


def test_confidence_model_counts_and_backoff(v, rows):
    results = [(v.validate(r["input"]), True) for r in rows]
    cm = ConfidenceModel().fit(results)
    clean = v.validate("10 Bayfront Avenue, Singapore 018956")
    sig = ConfidenceModel.signatures(clean)[0]
    c, n = cm.table[sig]
    assert c == n >= 1 and 0.5 < cm.confidence(clean) < 1
    assert "条中对了" in cm.explain(clean)
    unseen = v.validate("Marina Bay Sands")  # 训练里没有这一类：逐级退回更粗的类别
    assert ConfidenceModel.signatures(unseen)[0] not in cm.table
    assert 0 < cm.confidence(unseen) < 1


def test_low_confidence_downgrades_accept_only(v):
    clean = v.validate("10 Bayfront Avenue, Singapore 018956")
    fix = v.validate("999 Bayfront Avenue")
    # 同类结论历史上一半是错的：置信度低于门槛，ACCEPT 降为 CONFIRM；FIX 不受影响
    cm = ConfidenceModel().fit([(clean, True), (clean, False)] * 5 + [(fix, True)])
    cv = ConfidenceValidator(v, cm)
    res = cv.validate("10 Bayfront Avenue, Singapore 018956")
    assert res.action == CONFIRM and "LOW_CONFIDENCE" in res.reasons and res.confidence < 0.95
    assert res.entity.eid == clean.entity.eid
    assert cv.validate("999 Bayfront Avenue").action == FIX
    confident = ConfidenceValidator(v, ConfidenceModel().fit([(clean, True)] * 500))
    assert confident.validate("10 Bayfront Avenue, Singapore 018956").action == ACCEPT
