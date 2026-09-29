"""单元测试：用从 OneMap 导出中抽取的 58 条真实地址作为小型参考库，不依赖下载完整数据。"""

from pathlib import Path

import pytest

from avmvp import Config, ReferenceDB, Validator
from avmvp.parser import parse
from avmvp.validator import ACCEPT, ADD_SUB, CONFIRM, FIX

FIXTURE = Path(__file__).parent / "fixture_reference.csv"


@pytest.fixture(scope="module")
def db():
    return ReferenceDB.load(FIXTURE)


@pytest.fixture(scope="module")
def v(db):
    return Validator(db)


def addr(res):
    e = res.entity
    return f"{e.blk} {e.road} {e.postal}" if e else None


# ---------------------------------------------------------------- 解析
@pytest.mark.parametrize("raw,postal,zero", [
    ("10 Bayfront Avenue, Singapore 018956", "018956", False),
    ("10 bayfront ave S018956", "018956", False),
    ("S(018956) 10 Bayfront Ave", "018956", False),
    ("10 Bayfront Ave 18956", "018956", True),  # 表格软件吞掉前导 0
    ("10 Bayfront Ave", None, False),
])
def test_parse_postal(raw, postal, zero):
    p = parse(raw)
    assert p.postal == postal
    assert p.postal_leading_zero_restored is zero


def test_parse_unit_and_block_marker():
    p = parse("Blk 123 Ang Mo Kio Ave 3 #5-12")
    assert p.block_marked == "123"
    assert p.unit == "#05-12"
    assert p.tokens == ["ANG", "MO", "KIO", "AVE", "3"]


def test_parse_keeps_sin_prefix_of_street_names():
    assert parse("Sin Ming Road, Singapore").tokens == ["SIN", "MING", "RD"]


# ---------------------------------------------------------------- 结论
@pytest.mark.parametrize("raw,action,expected,reason", [
    ("10 Bayfront Avenue, Singapore 018956", ACCEPT, "10 BAYFRONT AVENUE 018956", None),
    ("018956 10 bayfront ave s'pore", ACCEPT, "10 BAYFRONT AVENUE 018956", None),
    ("10 Bayfrnt Avenue 018956", CONFIRM, "10 BAYFRONT AVENUE 018956", "STREET_SPELL_CORRECTED"),
    ("1 Raffles Place", CONFIRM, "1 RAFFLES PLACE 048616", "POSTCODE_INFERRED"),
    ("10 Bayfront Avenue, Singapore 819643", CONFIRM, "10 BAYFRONT AVENUE 018956", "POSTCODE_STREET_MISMATCH"),
    ("999 Bayfront Avenue", FIX, None, "PREMISE_NOT_FOUND"),
    ("Marina Bay Sands", CONFIRM, "1 BAYFRONT AVENUE 018971", "BUILDING_NAME_ONLY"),
    ("Changi Airport Terminal 3", CONFIRM, "65 AIRPORT BOULEVARD 819663", "BUILDING_NAME_ONLY"),
    ("Singapore 018956", CONFIRM, "10 BAYFRONT AVENUE 018956", "POSTCODE_ONLY"),
    ("St George's Rd", FIX, None, "MISSING_PREMISE"),
    # 邮编和楼栋号指向同一条路上的不同楼栋：不知道哪个输错了，不能擅自替换
    ("7B North Canal Road 048821", FIX, None, "POSTCODE_BLOCK_CONFLICT"),
    # 路名里的数字不能被当成楼栋号：TAMPINES AVENUE 7 是一条路，不是"7 号 TAMPINES AVENUE"
    ("Tampines Avenue 7, Singapore", FIX, None, "MISSING_PREMISE"),
    # 真实的长路名不能被模糊成另一条较短的路：KEPPEL BAY VIEW 上没有 24 号，不应改成 24 KEPPEL BAY DRIVE
    ("24 Keppel Bay View", FIX, None, "PREMISE_NOT_FOUND"),
    # 拼写错误与多条真路名等距（POOLE / OXLEY）时，由楼栋号裁决
    ("34A Poxle Road", CONFIRM, "34A POOLE ROAD 437543", "STREET_SPELL_CORRECTED"),
    # 路型词本身拼错
    ("34A Poole Rooad", CONFIRM, "34A POOLE ROAD 437543", None),
])
def test_verdicts(v, raw, action, expected, reason):
    res = v.validate(raw)
    assert res.action == action, res.reasons
    assert addr(res) == expected
    if reason:
        assert reason in res.reasons


def test_unit_is_kept_and_plausible(v):
    res = v.validate("10 Bayfront Avenue #01-23 Singapore 018956")
    assert res.action == ACCEPT
    assert res.status["subpremise"] == "plausible"
    out = v.to_response(res)["result"]
    assert "#01-23" in out["address"]["formattedAddress"]


def test_strictness_profiles(v):
    assert v.validate("1 Raffles Place", strictness="LENIENT").action == ACCEPT
    assert v.validate("1 Raffles Place", strictness="STRICT").action == CONFIRM
    assert v.validate("10 Bayfront Avenue #01-23 018956", strictness="STRICT").action == CONFIRM
    assert v.validate("999 Bayfront Avenue", strictness="LENIENT").action == FIX


def test_building_attributes_floor_check(db, tmp_path):
    attrs = tmp_path / "attrs.csv"
    attrs.write_text("postal,max_floor\n520390,12\n", encoding="utf-8")
    db2 = ReferenceDB.load(FIXTURE)
    db2.load_building_attributes(attrs)
    v2 = Validator(db2)
    bad = v2.validate("390 Tampines Avenue 7 #25-12 520390")
    assert bad.action == FIX and "UNIT_FLOOR_EXCEEDS_BUILDING" in bad.reasons
    assert v2.validate("390 Tampines Avenue 7 #05-12 520390").action == ACCEPT
    missing = v2.validate("390 Tampines Avenue 7 520390")
    assert missing.action == ADD_SUB and "UNIT_MISSING_MULTI_UNIT_BUILDING" in missing.reasons


def test_low_coverage_mode(db):
    v2 = Validator(db, Config(assume_complete=False))
    res = v2.validate("999 Bayfront Avenue")
    assert res.action == CONFIRM
    assert "PREMISE_UNVERIFIED_LOW_COVERAGE" in res.reasons


def test_response_schema(v):
    out = v.to_response(v.validate("10 Bayfrnt Avenue 018956"))
    verdict = out["result"]["verdict"]
    assert verdict["possibleNextAction"] == CONFIRM
    assert verdict["hasSpellCorrectedComponents"] is True
    assert verdict["verificationCode"].startswith("C44-")
    route = next(c for c in out["result"]["address"]["addressComponents"] if c["componentType"] == "route")
    assert route["spellCorrected"] is True and route["originalText"] == "BAYFRNT AVE"
    assert out["result"]["geocode"]["location"]["latitude"] > 1.2
