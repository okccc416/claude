"""模拟订单标注数据：标注规则（仅凭文字能判断到什么程度）、期望结论、评测口径，以及已提交数据的一致性。"""

import csv
import sys
from collections import Counter
from pathlib import Path

import pytest

from avmvp import ReferenceDB, Validator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evaluate_labeled import load, outcome  # noqa: E402
from make_labeled_orders import (  # noqa: E402
    AMBIGUOUS,
    CONFLICTING,
    MISLEADING,
    RESOLVABLE,
    World,
    Written,
    generate,
    gold_action,
    is_hdb,
    resolve,
)

FIXTURE = Path(__file__).parent / "fixture_reference.csv"
DATA = Path(__file__).resolve().parents[1] / "labeled" / "orders_sg_v1.csv"


@pytest.fixture(scope="module")
def world():
    return World(ReferenceDB.load(FIXTURE))


def eid(world, blk, road, postal):
    return next(e.eid for e in world.db.entities if (e.blk, e.road, e.postal) == (blk, road, postal))


def test_hdb_postal_rule(world):
    db = world.db
    assert is_hdb(db.entities[eid(world, "390", "TAMPINES AVENUE 7", "520390")])
    assert not is_hdb(db.entities[eid(world, "15A", "TAMPINES AVENUE", "529789")])
    assert world.ptype[eid(world, "390", "TAMPINES AVENUE 7", "520390")] == "HDB"


def test_clean_and_typo_are_resolvable(world):
    truth = eid(world, "10", "BAYFRONT AVENUE", "018956")
    assert resolve(world, Written("10", "BAYFRONT AVENUE", "018956"))[:2] == (RESOLVABLE, truth)
    assert resolve(world, Written("10", "BAYFRNT AVENUE", None))[:2] == (RESOLVABLE, truth)  # 认得出的错拼


def test_postal_typo_onto_real_postal(world):
    truth = eid(world, "390", "TAMPINES AVENUE 7", "520390")
    other = eid(world, "391", "TAMPINES AVENUE 7", "520391")
    # 只写了邮编：一致地指向另一栋楼 -> 标注规则认为可确定，但与真实地址不符（生成器据此标为 MISLEADING）
    assert resolve(world, Written(None, None, "520391"))[:2] == (RESOLVABLE, other)
    # 楼栋 + 道路指向 390，邮编 + 道路指向 391：2 比 2，无法判断
    assert resolve(world, Written("390", "TAMPINES AVENUE 7", "520391"))[0] == CONFLICTING
    # 楼栋号打成不存在的号码，邮编仍对：按邮编可确定
    assert resolve(world, Written("399", "TAMPINES AVENUE 7", "520390"))[:2] == (RESOLVABLE, truth)


def test_letter_suffix_dropped(world):
    truth = eid(world, "15A", "TAMPINES AVENUE", "529789")
    plain = eid(world, "15", "TAMPINES AVENUE", "529788")
    # 没写邮编：文字指向 15 号（误导）
    assert resolve(world, Written("15", "TAMPINES AVENUE", None))[:2] == (RESOLVABLE, plain)
    # 写了 15A 的邮编：邮编 + 道路 + 半个楼栋号 胜过 楼栋 + 道路
    assert resolve(world, Written("15", "TAMPINES AVENUE", "529789"))[:2] == (RESOLVABLE, truth)


def test_ambiguous(world):
    assert resolve(world, Written(None, "TAMPINES AVENUE 7", None))[0] == AMBIGUOUS
    assert resolve(world, Written(None, None, "238620"))[0] == AMBIGUOUS  # 26 / 26E / 26R … 共用邮编
    assert resolve(world, Written(None, None, None, building="CORALS AT KEPPEL BAY"))[0] == AMBIGUOUS
    orchard = eid(world, "19", "OXLEY ROAD", "238619")
    assert resolve(world, Written(None, None, None, building="ORCHARD COURT"))[:2] == (RESOLVABLE, orchard)


def test_duplicate_reference_rows_are_one_address():
    rows = [{"blk": "11", "road": "SAINT ANDREW'S ROAD", "postal": "178959"},
            {"blk": "11", "road": "ST. ANDREW'S ROAD", "postal": "178959"}]
    w = World(ReferenceDB.from_rows(rows))
    assert resolve(w, Written("11", "ST. ANDREW'S ROAD", "178959"))[0] == RESOLVABLE


def test_gold_action_rules():
    assert gold_action(RESOLVABLE, ["ABBREV", "NOISE_PHONE"], False) == ("ACCEPT", ["ACCEPT"])
    assert gold_action(RESOLVABLE, ["UNIT_MISSING"], True)[0] == "CONFIRM_ADD_SUBPREMISES"
    assert gold_action(RESOLVABLE, ["STREET_TYPO"], False) == ("CONFIRM", ["CONFIRM", "ACCEPT"])
    assert gold_action(RESOLVABLE, ["POSTAL_TYPO"], False) == ("CONFIRM", ["CONFIRM"])
    assert gold_action(AMBIGUOUS, [], False) == ("FIX", ["FIX", "CONFIRM"])
    assert gold_action(MISLEADING, ["POSTAL_TYPO"], False)[0] == "ACCEPT"


def test_generator_labels_are_consistent(world):
    rows = generate(world, 400, seed=7)
    assert rows == generate(world, 400, seed=7)  # 可复现
    for r in rows:
        assert r["gold_action"] in r["acceptable_actions"].split("|")
        has_truth = r["truth_eid"] != ""
        assert has_truth == (r["text_resolution"] not in ("NOT_IN_REFERENCE", "OUT_OF_REGION", "NO_ADDRESS"))
    assert {r["split"] for r in rows} == {"train", "test"}


def test_outcome_categories(world):
    v = Validator(world.db)
    truth = eid(world, "390", "TAMPINES AVENUE 7", "520390")
    e = world.db.entities[truth]

    def row(text, label, gold, ok, truth_eid=truth):
        r = {"input": text, "truth_eid": truth_eid, "text_resolution": label, "gold_action": gold,
             "acceptable": set(ok), "truth_key": (e.blk, e.road_key, e.postal) if truth_eid is not None else None}
        return r, v.validate(text)

    assert outcome(*row("390 Tampines Ave 7, Singapore 520390", RESOLVABLE, "ACCEPT", ["ACCEPT"])) == "正确"
    # App 按打错的邮编带出了 391 号：地址自洽，校验器直接通过，但真实地址是 390 号
    assert outcome(*row("391 Tampines Ave 7, Singapore 520391", MISLEADING, "ACCEPT", ["ACCEPT"])) == "静默错误"
    assert outcome(*row("same as last order", "NO_ADDRESS", "FIX", ["FIX"], None)) == "正确拒绝"


@pytest.mark.skipif(not DATA.exists(), reason="labeled/orders_sg_v1.csv 不存在")
def test_committed_dataset_invariants():
    with open(DATA, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 10000
    labels = Counter(r["text_resolution"] for r in rows)
    assert set(labels) == {"RESOLVABLE", "AMBIGUOUS", "CONFLICTING", "MISLEADING", "NOT_IN_REFERENCE",
                           "OUT_OF_REGION", "NO_ADDRESS"}
    for r in rows:
        assert r["gold_action"] in r["acceptable_actions"].split("|")
    train = {r["truth_eid"] for r in rows if r["split"] == "train" and r["truth_eid"]}
    test = {r["truth_eid"] for r in rows if r["split"] == "test" and r["truth_eid"]}
    assert not train & test  # 同一真实地址不会同时出现在训练和测试部分
    assert len(load(DATA)) == len(rows)
