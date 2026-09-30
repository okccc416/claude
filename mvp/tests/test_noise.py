"""真实客户输入里的业务噪声：电话、邮箱、订单号、收件人、公司名、配送备注、本地缩写、粘连写法。"""

from pathlib import Path

import pytest

from avmvp import Config, ReferenceDB, Validator
from avmvp.noise import strip_noise
from avmvp.validator import ACCEPT, ADD_SUB, CONFIRM, FIX

FIXTURE = Path(__file__).parent / "fixture_reference.csv"


@pytest.fixture(scope="module")
def v():
    return Validator(ReferenceDB.load(FIXTURE))


def addr(res):
    e = res.entity
    return f"{e.blk} {e.road} {e.postal}" if e else None


def test_strip_noise_extracts_each_kind():
    r = strip_noise("Attn: Jason Teo, ABC Trading Pte Ltd, 10 Bayfront Ave, S(018956) "
                    "HP +65 9123 4567, jason@gmail.com (Order #SG2024-504992) pls leave at door 请放门口",
                    lambda seg: "BAYFRONT" in seg)
    assert r.recipients == ["Jason Teo"]
    assert r.organizations == ["ABC Trading Pte Ltd"]
    assert r.emails == ["jason@gmail.com"]
    assert r.order_refs == ["Order #SG2024-504992"]
    assert any("9123 4567" in x for x in r.phones)
    assert "pls leave at door" in r.notes and "请放门口" in r.notes
    assert "BAYFRONT" in r.text.upper() and "018956" in r.text


@pytest.mark.parametrize("raw,action,expected", [
    # 地址本身完整正确：噪声剥离后直接通过，非地址信息单独返回
    ("Attn: Jason Teo, 10 Bayfront Avenue, S(018956) pls call b4 delivery 91234567", ACCEPT,
     "10 BAYFRONT AVENUE 018956"),
    ("Mr Tan Ah Kow 10 Bayfront Ave 018956 pls leave at door", ACCEPT, "10 BAYFRONT AVENUE 018956"),
    ("TO: DANIEL LEE  BLK7B NORTH CANAL RD  SINGAPORE 048820 PH: +6568966654", ACCEPT, "7B NORTH CANAL ROAD 048820"),
    ("Kopi Corner Pte. Ltd. ;10 bayfront ave ;018956 tel: 64393769", ACCEPT, "10 BAYFRONT AVENUE 018956"),
    # 订单号里的 6 位数字不能被当成邮编
    ("Order #SG2024-504992, 10 Bayfront Avenue", CONFIRM, "10 BAYFRONT AVENUE 018956"),
    # 本地缩写与粘连写法
    ("390 Tamp Ave 7, S520390", ADD_SUB, "390 TAMPINES AVENUE 7 520390"),  # 组屋没写单元号：提示补充
    ("10BAYFRONT AVE S018956", ACCEPT, "10 BAYFRONT AVENUE 018956"),
    ("34APOOLE RD, 437543", ACCEPT, "34A POOLE ROAD 437543"),
    # 楼宇名里有 "Pte Ltd" / 备注词时不能当噪声删掉
    ("Sands Expo And Convention Centre", CONFIRM, "10 BAYFRONT AVENUE 018956"),
    # 根本没有地址
    ("same as last order 91234567", FIX, None),
    ("pls whatsapp me", FIX, None),
])
def test_noisy_inputs(v, raw, action, expected):
    res = v.validate(raw)
    assert res.action == action, (res.reasons, addr(res))
    assert addr(res) == expected


@pytest.mark.parametrize("raw,unit", [
    ("10 Bayfront Ave, # 01 - 23, S018956", "#01-23"),
    ("10 Bayfront Ave, Unit #01-23, S018956", "#01-23"),
    ("Level 1 Unit 23, 10 Bayfront Ave 018956", "#01-23"),
    ("10 Bayfront Ave Lvl 1 #23 018956", "#01-23"),
    ("10 Bayfront Ave level 3 018956", "Level 3"),
])
def test_unit_variants(v, raw, unit):
    res = v.validate(raw)
    assert res.parsed.unit == unit
    assert addr(res) == "10 BAYFRONT AVENUE 018956"


def test_response_carries_non_address_info(v):
    out = v.to_response(v.validate("Attn: Jason Teo, 10 Bayfront Avenue, 018956, jason@gmail.com"))["result"]
    assert out["nonAddressInfo"] == {"emails": ["jason@gmail.com"], "recipients": ["Jason Teo"]}
    assert "Jason" not in out["address"]["formattedAddress"]
    assert "NON_ADDRESS_INFO_EXTRACTED" in [r["code"] for r in out["verdict"]["reasons"]]


def test_noise_stripping_can_be_disabled(v):
    v2 = Validator(v.db, Config(strip_noise=False))
    res = v2.validate("Attn: Jason Teo, 10 Bayfront Avenue, S(018956)")
    # 不剥噪声时，收件人留在地址里：楼栋 + 道路 + 邮编三者一致，名称只记为"未验证"，但不会被识别为非地址信息
    assert res.noise is None and "UNVERIFIED_NAME" in res.reasons and "JASON" in res.unverified
