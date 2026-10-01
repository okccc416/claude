"""多市场引擎测试：用一个微型"悉尼"（A 类，有官方地址点）和一个微型"迪拜"（B 类，只有道路 / 片区 / 楼宇）
走完整的构建流程（与真实数据同样的 parquet 字段），再验证解析、结论、粒度与响应格式。"""

from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")
shapely = pytest.importorskip("shapely")

from avmvp.intl.engine import ACCEPT, ADD_SUB, CONFIRM, FIX, Engine  # noqa: E402
from avmvp.intl.parse import RuleParser, strip_noise  # noqa: E402
from avmvp.intl.reference import build, is_test_place  # noqa: E402
from avmvp.intl.text import core_key, key, tokenize  # noqa: E402


def _bbox(lat, lng, d=0.0003):
    return {"xmin": lng - d, "ymin": lat - d, "xmax": lng + d, "ymax": lat + d}


def _names(primary, *others):
    return {"primary": primary, "common": [["en", o] for o in others] or None}


def _place_ids(n):
    """生成 n 个不会被留出为测试集的 POI 编号（留出规则按编号哈希）。"""
    out, i = [], 0
    while len(out) < n:
        if not is_test_place(f"p{i}"):
            out.append(f"p{i}")
        i += 1
    return out


def _write(d: Path, areas, segments, places, addresses=None):
    """areas: [(名称, 子类型, (xmin, ymin, xmax, ymax))]；segments: [(名称, 纬度, 经度)] 或 [(名称, [(纬度, 经度), …])]
    （后者带线形）；places: [(名称, 类别, 纬度, 经度[, 邮编])]；addresses: [(门牌, 道路, 单元, 邮编, 纬度, 经度)]"""
    from shapely.geometry import LineString, box

    d.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist([
        {"id": f"d{i}", "names": _names(n), "subtype": st,
         "bbox": {"xmin": b[0], "ymin": b[1], "xmax": b[2], "ymax": b[3]}} for i, (n, st, b) in enumerate(areas)]),
        d / "divisions.parquet")
    pq.write_table(pa.Table.from_pylist([
        {"division_id": f"d{i}", "geometry": box(*b).wkb,
         "bbox": {"xmin": b[0], "ymin": b[1], "xmax": b[2], "ymax": b[3]}} for i, (_, _, b) in enumerate(areas)]),
        d / "division_areas.parquet")
    rows = []
    for n, *geo in segments:
        names = _names(*n) if isinstance(n, tuple) else _names(n)
        if len(geo) == 2:
            rows.append({"names": names, "bbox": _bbox(*geo), "geometry": None})
        else:
            line = LineString([(lng, lat) for lat, lng in geo[0]])
            x0, y0, x1, y1 = line.bounds
            rows.append({"names": names, "bbox": {"xmin": x0, "ymin": y0, "xmax": x1, "ymax": y1},
                         "geometry": line.wkb})
    pq.write_table(pa.Table.from_pylist(rows), d / "segments.parquet")
    ids = _place_ids(len(places))
    pq.write_table(pa.Table.from_pylist([
        {"id": pid, "names": _names(n), "basic_category": c,
         "addresses": [{"freeform": "", "locality": "", "postcode": pc[0] if pc else ""}],
         "bbox": _bbox(lat, lng, 0.0001)}
        for pid, (n, c, lat, lng, *pc) in zip(ids, places)]), d / "places.parquet")
    if addresses:
        pq.write_table(pa.Table.from_pylist([
            {"number": n, "street": s, "unit": u, "postcode": pc, "address_levels": [{"value": "Sydney"}],
             "bbox": _bbox(lat, lng, 0.00005)} for n, s, u, pc, lat, lng in addresses]), d / "addresses.parquet")


@pytest.fixture(scope="module")
def au(tmp_path_factory):
    root = tmp_path_factory.mktemp("markets")
    surry, newtown = (151.200, -33.895, 151.220, -33.880), (151.170, -33.905, 151.190, -33.890)
    segs = [("Crown Street", -33.884 - 0.001 * i, 151.212) for i in range(6)]
    segs += [("Bourke Street", -33.884 - 0.001 * i, 151.216) for i in range(4)]
    segs += [("King Street", -33.893 - 0.001 * i, 151.180) for i in range(5)]
    addrs = [("100", "Crown Street", "", "2010", -33.8850, 151.2121),
             ("102", "Crown Street", "1", "2010", -33.8852, 151.2121),
             ("102", "Crown Street", "2", "2010", -33.8852, 151.2121),
             ("104", "Crown Street", "", "2010", -33.8854, 151.2121),
             ("50", "Bourke Street", "", "2010", -33.8860, 151.2161),
             ("200", "King Street", "", "2042", -33.8950, 151.1801)]
    places = [("Crown Street Public School", "elementary_school", -33.8870, 151.2125)]
    _write(root / "AU", [("Surry Hills", "neighborhood", surry), ("Newtown", "neighborhood", newtown)],
           segs, places, addrs)
    return Engine("AU", "rules", build("AU", "A", log=lambda *_: None, root=root))


@pytest.fixture(scope="module")
def ae(tmp_path_factory):
    root = tmp_path_factory.mktemp("markets")
    barsha, deira = (55.19, 25.10, 55.21, 25.12), (55.30, 25.26, 55.32, 25.28)
    segs = [("Sheikh Zayed Road", 25.105 + 0.001 * i, 55.200) for i in range(8)]
    segs += [("6th Street", 25.112 + 0.001 * i, 55.205) for i in range(3)]  # 两个社区都有 6th Street
    segs += [("6th Street", 25.268 + 0.001 * i, 55.310) for i in range(3)]
    places = [("Mall of the Emirates", "shopping_mall", 25.1100, 55.2008),
              ("Barsha Heights Tower", "corporate_or_business_office", 25.1130, 55.2052)]
    _write(root / "AE", [("Al Barsha", "neighborhood", barsha), ("Deira", "neighborhood", deira)], segs, places)
    return Engine("AE", "rules", build("AE", "B", log=lambda *_: None, root=root))


@pytest.fixture(scope="module")
def sa(tmp_path_factory):
    root = tmp_path_factory.mktemp("markets")
    olaya = (46.66, 24.68, 46.70, 24.72)
    segs = [(("طريق الملك فهد", "King Fahd Road"), [(24.685, 46.680), (24.700, 46.680)]),  # 两段各约 1.7 公里
            (("طريق الملك فهد", "King Fahd Road"), [(24.700, 46.680), (24.715, 46.680)]),
            ("شارع ابن تيمية", [(24.700, 46.685), (24.700, 46.690)])]  # 只有阿拉伯文名称
    places = [("Olaya Pharmacy", "pharmacy", 24.69, 46.67)]
    places += [(f"Shop {i}", "retail", 24.700 + 0.001 * i, 46.6805, "12211") for i in range(4)]  # 邮编 12211 的位置
    _write(root / "SA", [("العليا", "neighborhood", olaya)], segs, places)
    return Engine("SA", "rules", build("SA", "B", log=lambda *_: None, root=root))


# ---------------------------------------------------------------------------------------------- 文本
def test_text_normalization():
    assert key("Musterstraße 12", "DE") == key("MUSTERSTRASSE 12", "DE")
    assert key("Đ. Tô Hiến Thành", "VN") == key("Duong To Hien Thanh", "VN")  # 越南文去声调 + 缩写展开
    assert tokenize("339/5 Tô Hiến Thành")[0] == "339/5"
    assert key("١٢ شارع", "AE").startswith("12")  # 阿拉伯-印度数字
    assert core_key("Jalan Ampang", "MY", "street") == core_key("Jln Ampang", "MY", "street") == "AMPANG"
    assert key("شارع الوصل", "AE") == key("شارع الوصل", "AE")  # 阿拉伯文字母统一后稳定


def test_noise_and_codes_are_separated():
    text, noise, codes = strip_noise("Villa 12, 6th St, Al Barsha, Makani 12345 67890, call +971 50 123 4567")
    assert codes.get("makani") == "12345 67890"
    assert noise.get("phones")
    assert "12345" not in text and "4567" not in text


# ---------------------------------------------------------------------------------------------- A 类
def test_au_parse(au):
    p = RuleParser(au.ref).parse("Unit 2/102 Crown St, Surry Hills NSW 2010")
    assert p.number == "102" and p.unit and "2" in p.unit and p.postcode == "2010"
    assert au.ref.streets[p.streets[0].ids[0]].name == "Crown Street"


def test_au_exact_premise_accepts(au):
    r = au.validate("100 Crown Street, Surry Hills NSW 2010")
    assert (r.action, r.granularity) == (ACCEPT, "PREMISE")
    assert abs(r.lat + 33.8850) < 0.001


def test_au_spelling_error_needs_confirmation(au):
    r = au.validate("100 Crown Stret, Surry Hills 2010")
    assert r.granularity == "PREMISE" and r.action == CONFIRM
    assert "STREET_SPELL_CORRECTED" in r.reasons


def test_au_multi_unit_building_asks_for_unit(au):
    assert au.validate("102 Crown St, Surry Hills NSW 2010").action == ADD_SUB
    assert au.validate("2/102 Crown St, Surry Hills NSW 2010").action == ACCEPT


def test_au_missing_or_unknown_number_is_fix(au):
    r = au.validate("999 Crown Street, Surry Hills NSW 2010")
    assert r.action == FIX and "PREMISE_NOT_FOUND" in r.reasons
    assert au.validate("Crown Street, Surry Hills NSW 2010").action == FIX


def test_au_number_range_and_glued_tokens(au):
    r = au.validate("100-104 Crown St, Surry Hills NSW 2010")  # 官方表只记单个门牌时按区间首尾查
    assert r.granularity == "PREMISE" and r.action in (ACCEPT, ADD_SUB)
    assert tokenize("Shop4068, 500Oxford Street, 12th Ave") == ["SHOP", "4068", "500", "OXFORD", "STREET", "12TH", "AVE"]


def test_au_wrong_postcode_is_replaced(au):
    r = au.validate("100 Crown Street, Surry Hills NSW 2042")
    assert r.action == CONFIRM and r.components["postal_code"]["text"] == "2010"
    assert "POSTCODE_REPLACED" in r.reasons


# ---------------------------------------------------------------------------------------------- B 类
def test_ae_building_on_street_accepts(ae):
    r = ae.validate("Mall of the Emirates, Sheikh Zayed Road, Al Barsha, Dubai")
    assert (r.action, r.granularity) == (ACCEPT, "PREMISE_PROXIMITY")
    assert r.components["premise_name"]["text"] == "Mall of the Emirates"


def test_ae_street_with_area_is_located_but_confirmed(ae):
    r = ae.validate("Villa 12, 6th Street, Al Barsha, Dubai")
    assert r.granularity == "ROUTE" and 25.1 < r.lat < 25.13  # 定位到 Al Barsha 的那条 6th Street
    # 同名道路有两条、没有邮编印证：道路级结论要用户确认（开发集上这类直接通过的错误率在 10% 以上）
    assert r.action == CONFIRM and "ROUTE_NOT_CORROBORATED" in r.reasons


def test_ae_duplicate_street_without_area_needs_confirmation(ae):
    r = ae.validate("Villa 12, 6th Street, Dubai")
    assert r.action == CONFIRM and "AMBIGUOUS_MULTIPLE_CANDIDATES" in r.reasons


def test_ae_area_only_is_fix(ae):
    r = ae.validate("Al Barsha, Dubai")
    assert (r.action, r.granularity) == (FIX, "LOCALITY")


def test_response_shape(ae):
    out = ae.to_response(ae.validate("Mall of the Emirates, Sheikh Zayed Road, Al Barsha, Dubai, Makani 12345 67890"))
    v = out["result"]["verdict"]
    assert v["possibleNextAction"] == ACCEPT and v["validationGranularity"] == "PREMISE_PROXIMITY"
    assert all({"code", "message"} <= set(x) for x in v["reasons"])
    assert out["result"]["codes"]["makani"] == "12345 67890"
    assert out["result"]["metadata"]["regionCode"] == "AE"
    json.dumps(out, ensure_ascii=False)


# ---------------------------------------------------------------------------------------------- 中东：线形 / 转写 / Plus Code
def test_long_road_segments_merge_and_follow_geometry(sa):
    from avmvp.intl.engine import dist_to_street

    ids = sa.ref.street_keys[key("King Fahd Road", "SA")]
    assert len(ids) == 1  # 两段首尾相接，合并为一条路（路段中心相距 1.7 公里）
    assert dist_to_street(sa.ref, next(iter(ids)), 24.6925, 46.6801) < 30  # 路段中间也有沿线点


def test_latin_transliteration_matches_arabic_name(sa):
    r = sa.validate("Ibn Taymiyyah St., Olaya, Riyadh")
    assert r.best and r.best.street is not None
    assert sa.ref.streets[r.best.street].name == "شارع ابن تيمية"
    assert "STREET_TRANSLITERATED" in r.reasons


def test_plus_code_locates_address(sa):
    from avmvp.intl.pluscode import encode

    full = encode(24.7001, 46.6802)  # King Fahd Road 旁边
    r = sa.validate(f"{full[4:]}, King Fahd Road, Riyadh")  # 短码，按城市补齐
    assert (r.action, r.granularity) == (ACCEPT, "PREMISE_PROXIMITY")
    assert abs(r.lat - 24.7001) < 0.0002 and abs(r.lng - 46.6802) < 0.0002
    assert "LOCATED_BY_PLUS_CODE" in r.reasons
    far = sa.validate(f"{full[4:]}, Ibn Taymiyyah Street, Riyadh")  # 与所写道路相距约 500 米
    assert far.action == CONFIRM and "PLUS_CODE_STREET_MISMATCH" in far.reasons


def test_route_accept_needs_postcode_corroboration(sa):
    r = sa.validate("12 King Fahd Road, Riyadh 12211")
    assert (r.action, r.granularity) == (ACCEPT, "ROUTE")  # 道路名唯一、邮编就在道路旁
    r = sa.validate("12 King Fahd Road, Riyadh")
    assert r.action == CONFIRM and "ROUTE_NOT_CORROBORATED" in r.reasons


def test_pasted_coordinates_locate_address(sa):
    r = sa.validate("24.700100, 46.680200, King Fahd Road, Riyadh")
    assert (r.action, r.granularity) == (ACCEPT, "PREMISE_PROXIMITY")
    assert "LOCATED_BY_COORDINATES" in r.reasons and abs(r.lat - 24.7001) < 1e-6


def test_placeholder_postcode_is_ignored(sa):
    r = sa.validate("12 King Fahd Road, Al Olaya, Riyadh 00000")
    assert r.parsed.postcode is None and "POSTCODE_STREET_MISMATCH" not in r.reasons


def test_plus_code_decoder_matches_spec():
    from avmvp.intl.pluscode import decode, recover

    lat, lng, _ = decode("9C3W9QCJ+2VX")  # 规范里的测试数据
    assert abs(lat - 51.3701125) < 1e-6 and abs(lng + 1.217765625) < 1e-6
    lat, lng, _ = recover("CJ+2VX", 51.3708675, -1.217765625)
    assert abs(lat - 51.3701125) < 1e-6 and abs(lng + 1.217765625) < 1e-6


# ---------------------------------------------------------------------------------------------- 机器学习解析器
def test_crf_training_and_hybrid(au):
    pytest.importorskip("pycrfsuite")
    from avmvp.intl.crf import train
    from avmvp.intl.render import Renderer

    rd = Renderer(au.ref, "train", 1)
    rd.street_ids = [s.id for s in au.ref.streets]  # 微型参考库只有 3 条路，不分训练 / 测试
    samples = [s for s in (rd.sample(noise=0.2) for _ in range(400)) if s and s.tokens]
    train(au.ref, samples, au.ref.dir / "crf.model", iterations=30)
    eng = Engine("AU", "hybrid", au.ref)
    r = eng.validate("100 Crown Street, Surry Hills NSW 2010")
    assert (r.action, r.granularity) == (ACCEPT, "PREMISE")
    assert Engine("AU", "crf", au.ref).crf.parse("100 Crown Street Surry Hills 2010").streets


# ---------------------------------------------------------------------------------------------- 本地小模型
class StubLLM:
    """替身模型：返回固定字段，用来测试防编造和级联逻辑（真模型的效果见 docs/13）。"""
    name = "stub"

    def __init__(self, fields):
        self.fields = fields

    def extract(self, text, market):
        return dict(self.fields)


def test_llm_guard_drops_invented_fields():
    from avmvp.intl.llm import guard

    fields = {"house_number": "99", "unit": "Office 5", "building": "Burj Khalifa", "street": "Sheikh Zayed Road",
              "area": "", "postcode": ""}
    kept, verbatim = guard(fields, "Office 5, Sheikh Zayed Rd, Dubai", "AE")
    assert "house_number" not in kept  # 99 不在原文里：编造的门牌丢弃
    assert "building" not in kept  # 原文没有 Burj Khalifa
    assert kept["street"] == "Sheikh Zayed Road" and kept["unit"] == "Office 5"
    assert verbatim is False  # Rd -> Road 是改写


def test_llm_cascade_only_when_rules_fail_and_is_capped(ae):
    stub = StubLLM({"house_number": "", "unit": "", "building": "Mall of the Emirates",
                    "street": "Sheikh Zayed Road", "area": "Al Barsha", "postcode": ""})
    eng = Engine("AE", "rules", ae.ref, llm=stub)
    r = eng.validate("MallofEmirates/SheikhZayedRd/AlBarsha")  # 粘连写法，规则解析不出来
    assert r.parser == "rules+llm" and r.granularity == "PREMISE_PROXIMITY"
    assert r.action == CONFIRM and "LLM_REWRITTEN" in r.reasons  # 模型改写过的字段最多给 CONFIRM
    calls = eng.llm.calls
    ok = eng.validate("Mall of the Emirates, Sheikh Zayed Road, Al Barsha, Dubai")
    assert ok.action == ACCEPT and eng.llm.calls == calls  # 规则已经直接通过：不调用模型


# ---------------------------------------------------------------------------------------------- 置信度
def test_confidence_is_calibrated_and_shrinks(au):
    from avmvp.intl.confidence import IntlConfidence, signatures

    r_ok = au.validate("100 Crown Street, Surry Hills NSW 2010")
    r_fix = au.validate("999 Crown Street, Surry Hills NSW 2010")
    s_ok, s_fix = signatures(r_ok, "AU", "A"), signatures(r_fix, "AU", "A")
    assert s_ok[0].startswith("AU|ACCEPT|PREMISE|") and s_ok[-1] == "ACCEPT|PREMISE"
    model = IntlConfidence().fit([(s_ok, True)] * 90 + [(s_ok, False)] * 10 + [(s_fix, False)] * 3)
    assert abs(model.confidence(r_ok, "AU", "A") - 0.9) < 0.02  # 样本多：接近实际比例 90/100
    rare = model.from_signatures(["XX|ACCEPT|PREMISE|z", "A|ACCEPT|PREMISE|z", "A|ACCEPT|PREMISE", "ACCEPT|PREMISE"])
    assert 0.85 < rare < 0.95  # 没见过的细类：退回到粗一级的估计
    out = Engine("AU", "rules", au.ref, confidence=model).to_response(r_ok)
    assert 0 < out["result"]["verdict"]["confidence"] <= 1 and "100" in out["result"]["verdict"]["confidenceNote"]


# ---------------------------------------------------------------------------------------------- 批量清洗
def test_batch_csv_script(au, tmp_path):
    import csv
    import os
    import subprocess
    import sys

    src = tmp_path / "in.csv"
    src.write_text("id,address\n1,\"100 Crown St, Surry Hills NSW 2010\"\n2,\"999 Crown St, Surry Hills 2010\"\n3,\n",
                   encoding="utf-8")
    out = tmp_path / "out.csv"
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "AV_MARKETS_DIR": str(au.ref.dir.parent)}
    subprocess.run([sys.executable, str(root / "scripts" / "batch_validate.py"), str(src), str(out), "--region", "AU",
                    "--parser", "rules"], check=True, env=env, capture_output=True)
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    assert [r["id"] for r in rows] == ["1", "2", "3"]  # 原有列保留
    assert rows[0]["av_action"] == ACCEPT and rows[0]["av_granularity"] == "PREMISE" and rows[0]["av_lat"]
    assert rows[1]["av_action"] == FIX and "PREMISE_NOT_FOUND" in rows[1]["av_reasons"]
    assert rows[2]["av_error"]  # 空地址：记录原因，不中断


# ---------------------------------------------------------------------------------------------- 服务
def test_router_and_http(au, monkeypatch):
    from avmvp import router as router_mod
    from avmvp.server import make_handler

    monkeypatch.setattr(router_mod, "DATA", au.ref.dir.parent)
    r = router_mod.MarketRouter(None, ["SG", "AU", "DE"], "rules")
    assert [m["code"] for m in r.describe()] == ["AU", "DE"]  # 没有新加坡参考库时不开放 SG
    r._engines["AU"] = au
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(r))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        body = json.dumps({"address": {"regionCode": "au", "addressLines": ["100 Crown St"],
                                       "locality": "Surry Hills", "postalCode": "2010"}}).encode()
        out = json.loads(urlopen(Request(f"{base}/v1/address:validate", body,
                                         {"Content-Type": "application/json"})).read())
        assert out["result"]["verdict"]["possibleNextAction"] == ACCEPT
        assert out["result"]["metadata"]["regionCode"] == "AU"
        markets = json.loads(urlopen(f"{base}/v1/markets").read())["markets"]
        assert {"code": "DE", "available": False} .items() <= next(m for m in markets if m["code"] == "DE").items()
        batch = json.dumps({"requests": [
            {"address": {"regionCode": "AU", "addressLines": ["100 Crown St, Surry Hills NSW 2010"]}},
            {"address": {"regionCode": "JP", "addressLines": ["1-1 Chiyoda"]}}]}).encode()
        out = json.loads(urlopen(Request(f"{base}/v1/address:batchValidate", batch,
                                         {"Content-Type": "application/json"})).read())
        assert len(out["responses"]) == 2  # 单条出错不影响其他条
        assert out["responses"][0]["result"]["verdict"]["possibleNextAction"] == ACCEPT
        assert "JP" in out["responses"][1]["error"]
        bad = json.dumps({"address": {"regionCode": "JP", "addressLines": ["1-1 Chiyoda"]}}).encode()
        with pytest.raises(Exception) as e:
            urlopen(Request(f"{base}/v1/address:validate", bad, {"Content-Type": "application/json"}))
        assert getattr(e.value, "code", None) == 400
    finally:
        srv.shutdown()
