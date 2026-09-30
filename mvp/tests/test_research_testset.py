"""按调研比例构造的测试集：噪声统计的比对规则、错误模型、生成与标注的一致性（使用小型夹具，不需要下载数据）。"""

import random
import sys
from pathlib import Path

import pytest

from avmvp import ReferenceDB

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import measure_noise as mn  # noqa: E402
from make_labeled_orders import World  # noqa: E402
from make_research_testset import Builder, digit_typo, fmt_unit, letter_typo  # noqa: E402

FIXTURE = Path(__file__).parent / "fixture_reference.csv"


def test_street_forms_and_house_number():
    text = mn.norm("Blk 26, #01-192 Teck Whye Ln")
    x = mn.expand(text)
    form, pos = mn.street_match(text, x, "TECK WHYE LANE")
    assert form == "缩写" and mn.house_number(x, pos) == "26"  # 跳过夹在中间的单元号
    text = mn.norm("8a Biomedical Groove, Immunos Building")
    assert mn.street_match(text, mn.expand(text), "BIOMEDICAL GROVE")[0] == "拼错（可认出）"
    text = mn.norm("#02-59 Vivo City")
    assert mn.street_match(text, mn.expand(text), "HARBOURFRONT WALK")[0] == "没写 / 认不出"


def test_analyze_detects_postcode_of_another_address():
    by_postal = {"530006": [("6", "HOUGANG AVENUE 3", [])], "530007": [("7", "HOUGANG AVENUE 3", [])]}
    by_num_street = {("6", "HOUGANG AVENUE 3"): {"530006"}, ("7", "HOUGANG AVENUE 3"): {"530007"}}
    mn.STREETS.update({"HOUGANG AVENUE 3"})
    place = {"addresses": [{"freeform": "7 Hougang Ave 3, #01-58", "postcode": "530006"}]}
    r = mn.analyze(place, by_postal, by_num_street)
    assert r["postcode"] == "与所写地址矛盾" and r["number"] == "不同" and r["unit"]
    ok = mn.analyze({"addresses": [{"freeform": "Hougang Ave 3, Block 6", "postcode": "530006"}]},
                    by_postal, by_num_street)
    assert ok["postcode"] == "有效" and ok["number"].startswith("写在别处")


def test_error_models():
    rng = random.Random(1)
    for _ in range(200):
        p = digit_typo("560123", rng)
        assert p != "560123" and len(p) == 6 and p.isdigit()
        w = letter_typo("SERANGOON", rng)
        assert w != "SERANGOON" and w[0] == "S"
    assert fmt_unit(("B1", "05"), random.Random(3), []).startswith(("#", "Unit"))


@pytest.fixture(scope="module")
def builder():
    current = ReferenceDB.load(FIXTURE)
    gone = {e.eid for e in current.entities if e.road == "TAMPINES AVENUE 7"}  # 模拟 2017 参考库里没有的新楼
    return Builder(World(current), current.remove(gone), seed=5)


def test_generated_rows_are_consistent(builder):
    rows = [builder.address() for _ in range(300)] + [builder.special("no_address"), builder.special("out_of_region")]
    labels = {r["text_resolution"] for r in rows}
    assert "NOT_IN_REFERENCE" in labels and "RESOLVABLE" in labels
    for r in rows:
        assert r["gold_action"] in r["acceptable_actions"].split("|")
        if r["text_resolution"] == "NOT_IN_REFERENCE":
            assert r["truth_eid"] == "" and r["truth_street"] == "TAMPINES AVENUE 7" and "NEW_ADDRESS_2026" in r["error_tags"]
        elif r["truth_street"]:
            assert r["truth_eid"] != ""
