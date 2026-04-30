"""
LDF分析工具测试脚本 - test_ldf_skill.py
测试 ldf_parser / ldf_diff / ldf_report / ldf_batch_diff 模块
"""

import os
import sys
import traceback

# 确保脚本所在目录在 sys.path 中
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from ldf_parser import LDFParser, LDFFile
from ldf_diff import LDFDiff, ChangeType
from ldf_report import (
    LDFTextReporter, LDFMarkdownReporter, LDFHTMLReporter,
    LDFCSVReporter, LDFJSONReporter, LDFInfoReporter,
)
from ldf_batch_diff import parse_ldf_filename, LDFBatchDiff, BatchReportGenerator

# ---------------------------------------------
# 测试工具
# ---------------------------------------------

_pass = 0
_fail = 0


def test(name: str, fn):
    global _pass, _fail
    try:
        fn()
        print(f"  [PASS] {name}")
        _pass += 1
    except AssertionError as e:
        print(f"  [FAIL] {name}: AssertionError: {e}")
        _fail += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {type(e).__name__}: {e}")
        traceback.print_exc()
        _fail += 1


def section(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


# ---------------------------------------------
# 示例文件路径
# ---------------------------------------------

V1_LDF = os.path.join(_DIR, "examples", "sample_v1.ldf")
V2_LDF = os.path.join(_DIR, "examples", "sample_v2.ldf")


# ---------------------------------------------
# Test 1: LDF解析器基础功能
# ---------------------------------------------

section("Test 1: LDF解析器 - 基础解析")

parser = LDFParser()
ldf_v1 = None
ldf_v2 = None


def t1_parse_v1():
    global ldf_v1
    ldf_v1 = parser.parse_file(V1_LDF)
    assert ldf_v1 is not None, "解析结果不应为None"
    assert ldf_v1.lin_protocol_version == "2.1", f"协议版本应为2.1，实际: {ldf_v1.lin_protocol_version}"
    assert ldf_v1.lin_speed == "19.2 kbps", f"速率应为19.2 kbps，实际: {ldf_v1.lin_speed}"


def t1_parse_nodes():
    assert ldf_v1.master is not None, "主节点不应为None"
    assert ldf_v1.master.name == "LIN_Master", f"主节点名应为LIN_Master，实际: {ldf_v1.master.name}"
    assert ldf_v1.master.time_base == 5.0, f"时基应为5.0ms，实际: {ldf_v1.master.time_base}"
    assert ldf_v1.master.jitter == 0.1, f"抖动应为0.1ms，实际: {ldf_v1.master.jitter}"
    assert len(ldf_v1.slaves) == 3, f"从节点数应为3，实际: {len(ldf_v1.slaves)}"
    assert "SlaveA" in ldf_v1.slaves, "SlaveA应在从节点列表中"
    assert "SlaveB" in ldf_v1.slaves, "SlaveB应在从节点列表中"
    assert "SlaveC" in ldf_v1.slaves, "SlaveC应在从节点列表中"


def t1_parse_signals():
    assert len(ldf_v1.signals) == 8, f"信号数应为8，实际: {len(ldf_v1.signals)}"
    assert "EngineSpeed" in ldf_v1.signals, "EngineSpeed应在信号列表中"
    es = ldf_v1.signals["EngineSpeed"]
    assert es.length == 16, f"EngineSpeed位长度应为16，实际: {es.length}"
    assert es.publisher == "SlaveA", f"EngineSpeed发布节点应为SlaveA，实际: {es.publisher}"
    assert "LIN_Master" in es.subscribers, "LIN_Master应在EngineSpeed订阅列表中"


def t1_parse_frames():
    assert len(ldf_v1.frames) == 4, f"帧数应为4，实际: {len(ldf_v1.frames)}"
    assert "EngineFrame" in ldf_v1.frames, "EngineFrame应在帧列表中"
    ef = ldf_v1.frames["EngineFrame"]
    assert ef.frame_id == 0x01, f"EngineFrame ID应为0x01，实际: 0x{ef.frame_id:02X}"
    assert ef.publisher == "SlaveA", f"EngineFrame发布节点应为SlaveA，实际: {ef.publisher}"
    assert ef.length == 4, f"EngineFrame长度应为4字节，实际: {ef.length}"
    assert len(ef.signals) == 3, f"EngineFrame应有3个信号，实际: {len(ef.signals)}"
    sig_names = [s.signal_name for s in ef.signals]
    assert "EngineSpeed" in sig_names, "EngineSpeed应在EngineFrame中"
    assert "EngineTemp" in sig_names, "EngineTemp应在EngineFrame中"


def t1_parse_schedules():
    assert len(ldf_v1.schedule_tables) == 2, f"调度表数应为2，实际: {len(ldf_v1.schedule_tables)}"
    assert "NormalSchedule" in ldf_v1.schedule_tables, "NormalSchedule应存在"
    ns = ldf_v1.schedule_tables["NormalSchedule"]
    assert len(ns.entries) == 4, f"NormalSchedule应有4条目，实际: {len(ns.entries)}"
    assert ns.entries[0].frame_name == "EngineFrame", f"第一条目应为EngineFrame，实际: {ns.entries[0].frame_name}"
    assert ns.entries[0].delay_ms == 10.0, f"EngineFrame延迟应为10ms，实际: {ns.entries[0].delay_ms}"


def t1_parse_encodings():
    assert len(ldf_v1.encoding_types) >= 4, f"编码类型数应>=4，实际: {len(ldf_v1.encoding_types)}"
    assert "EngineSpeedEncoding" in ldf_v1.encoding_types, "EngineSpeedEncoding应存在"
    enc = ldf_v1.encoding_types["EngineSpeedEncoding"]
    assert len(enc.values) == 1, f"EngineSpeedEncoding应有1个值，实际: {len(enc.values)}"
    v = enc.values[0]
    assert v.encode_type == "physical", f"编码类型应为physical，实际: {v.encode_type}"
    assert v.unit == "rpm", f"单位应为rpm，实际: {v.unit}"


def t1_parse_v2():
    global ldf_v2
    ldf_v2 = parser.parse_file(V2_LDF)
    assert ldf_v2 is not None
    assert len(ldf_v2.slaves) == 4, f"v2从节点数应为4，实际: {len(ldf_v2.slaves)}"
    assert "SlaveD" in ldf_v2.slaves, "SlaveD应在v2从节点列表中"
    assert len(ldf_v2.frames) == 5, f"v2帧数应为5，实际: {len(ldf_v2.frames)}"
    assert "ClimateFrame" in ldf_v2.frames, "ClimateFrame应在v2帧列表中"


test("解析v1 LDF文件", t1_parse_v1)
test("解析节点信息", t1_parse_nodes)
test("解析信号定义", t1_parse_signals)
test("解析帧定义", t1_parse_frames)
test("解析调度表", t1_parse_schedules)
test("解析编码类型", t1_parse_encodings)
test("解析v2 LDF文件", t1_parse_v2)


# ---------------------------------------------
# Test 2: 字符串解析
# ---------------------------------------------

section("Test 2: 字符串解析")

_MINI_LDF = """
LIN_description_file;
LIN_protocol_version = "2.1";
LIN_language_version = "2.1";
LIN_speed = 9.6 kbps;

Nodes {
  Master: ECU, 10 ms, 0.5 ms;
  Slaves: Sensor1, Sensor2;
}

Signals {
  Temperature : 8, 0x00, Sensor1, ECU;
  Pressure    : 16, 0x0000, Sensor2, ECU;
}

Frames {
  SensorFrame : 0x05, Sensor1, 3 {
    Temperature, 0;
    Pressure,    8;
  }
}

Schedule_tables {
  MainSchedule {
    SensorFrame delay 20 ms;
  }
}
"""


def t2_string_parse():
    p = LDFParser()
    ldf = p.parse_string(_MINI_LDF, source="<test>")
    assert ldf.lin_protocol_version == "2.1"
    assert ldf.lin_speed == "9.6 kbps"
    assert ldf.master is not None
    assert ldf.master.name == "ECU"
    assert ldf.master.time_base == 10.0
    assert len(ldf.slaves) == 2
    assert "Sensor1" in ldf.slaves
    assert len(ldf.signals) == 2
    assert "Temperature" in ldf.signals
    assert ldf.signals["Temperature"].length == 8
    assert len(ldf.frames) == 1
    assert "SensorFrame" in ldf.frames
    sf = ldf.frames["SensorFrame"]
    assert sf.frame_id == 0x05
    assert sf.length == 3
    assert len(sf.signals) == 2
    assert len(ldf.schedule_tables) == 1


test("字符串解析LDF", t2_string_parse)


# ---------------------------------------------
# Test 3: 差异分析
# ---------------------------------------------

section("Test 3: 差异分析")

diff_result = None


def t3_diff_basic():
    global diff_result
    differ = LDFDiff()
    diff_result = differ.compare(ldf_v1, ldf_v2)
    assert diff_result is not None
    assert diff_result.has_changes(), "v1和v2应有差异"


def t3_diff_nodes():
    # v2新增了SlaveD，主节点jitter从0.1改为0.2
    node_changes = diff_result.node_changes
    assert len(node_changes) > 0, "应有节点变更"
    # 检查SlaveD被新增
    added_slaves = [nc for nc in node_changes
                    if nc.change_type == ChangeType.ADDED and nc.node_name == "SlaveD"]
    assert len(added_slaves) == 1, "SlaveD应被标记为新增"
    # 检查主节点jitter变更
    master_changes = [nc for nc in node_changes
                      if nc.change_type == ChangeType.MODIFIED and nc.is_master]
    assert len(master_changes) == 1, "主节点应有修改"
    assert any(fc.field_name == "抖动(ms)" for fc in master_changes[0].field_changes), \
        "主节点抖动应有变更"


def t3_diff_frames():
    # v2新增了ClimateFrame，FuelFrame长度从2改为3
    frame_changes = diff_result.frame_changes
    assert len(frame_changes) > 0, "应有帧变更"
    added_frames = [fc for fc in frame_changes if fc.change_type == ChangeType.ADDED]
    assert any(fc.frame_name == "ClimateFrame" for fc in added_frames), \
        "ClimateFrame应被标记为新增"
    modified_frames = [fc for fc in frame_changes if fc.change_type == ChangeType.MODIFIED]
    fuel_changes = [fc for fc in modified_frames if fc.frame_name == "FuelFrame"]
    assert len(fuel_changes) == 1, "FuelFrame应有修改"
    assert any(fc.field_name == "帧长度" for fc in fuel_changes[0].field_changes), \
        "FuelFrame帧长度应有变更"


def t3_diff_signals():
    # v2新增了AmbientTemp和WiperSpeed信号
    sig_changes = diff_result.signal_changes
    added_sigs = [sc for sc in sig_changes if sc.change_type == ChangeType.ADDED]
    sig_names = [sc.signal_name for sc in added_sigs]
    assert "AmbientTemp" in sig_names, "AmbientTemp应被标记为新增"
    assert "WiperSpeed" in sig_names, "WiperSpeed应被标记为新增"


def t3_diff_schedules():
    # v2的NormalSchedule新增了ClimateFrame条目
    sched_changes = diff_result.schedule_changes
    modified = [sc for sc in sched_changes if sc.change_type == ChangeType.MODIFIED]
    normal_changes = [sc for sc in modified if sc.table_name == "NormalSchedule"]
    assert len(normal_changes) == 1, "NormalSchedule应有修改"
    assert "ClimateFrame" in normal_changes[0].entries_added, \
        "ClimateFrame应在NormalSchedule新增条目中"


def t3_diff_encodings():
    # v2的DoorStatusEncoding新增了Locked值
    enc_changes = diff_result.encoding_changes
    modified = [ec for ec in enc_changes if ec.change_type == ChangeType.MODIFIED]
    door_changes = [ec for ec in modified if ec.encoding_name == "DoorStatusEncoding"]
    assert len(door_changes) == 1, "DoorStatusEncoding应有修改"


def t3_diff_stats():
    stats = diff_result.stats()
    assert stats["nodes_added"] >= 1, "应有新增节点"
    assert stats["frames_added"] >= 1, "应有新增帧"
    assert stats["signals_added"] >= 2, "应有新增信号"


def t3_no_diff():
    differ = LDFDiff()
    result = differ.compare(ldf_v1, ldf_v1)
    assert not result.has_changes(), "相同文件比较应无差异"


test("差异分析基础", t3_diff_basic)
test("节点变更检测", t3_diff_nodes)
test("帧变更检测", t3_diff_frames)
test("信号变更检测", t3_diff_signals)
test("调度表变更检测", t3_diff_schedules)
test("编码类型变更检测", t3_diff_encodings)
test("变更统计", t3_diff_stats)
test("相同文件无差异", t3_no_diff)


# ---------------------------------------------
# Test 4: 报告生成
# ---------------------------------------------

section("Test 4: 报告生成")


def t4_text_report():
    reporter = LDFTextReporter()
    text = reporter.generate(diff_result)
    assert "LDF 差异分析报告" in text
    assert "节点变更" in text
    assert "帧变更" in text
    assert "信号变更" in text
    assert len(text) > 200


def t4_markdown_report():
    reporter = LDFMarkdownReporter()
    md = reporter.generate(diff_result)
    assert "# LDF 差异分析报告" in md
    assert "## 变更统计" in md
    assert "| 类别 |" in md
    assert len(md) > 200


def t4_html_report():
    reporter = LDFHTMLReporter()
    html = reporter.generate(diff_result)
    assert "<!DOCTYPE html>" in html
    assert "LDF 差异分析报告" in html
    assert "badge-add" in html or "badge-del" in html or "badge-mod" in html
    assert len(html) > 500


def t4_csv_report():
    reporter = LDFCSVReporter()
    csv_text = reporter.generate(diff_result)
    lines = csv_text.strip().split("\n")
    assert len(lines) > 1, "CSV应有多行"
    assert "变更类别" in lines[0], "CSV首行应为表头"


def t4_json_report():
    import json
    reporter = LDFJSONReporter()
    json_text = reporter.generate(diff_result)
    data = json.loads(json_text)
    assert "meta" in data
    assert "stats" in data
    assert "frame_changes" in data
    assert "signal_changes" in data
    assert data["meta"]["has_changes"] is True


def t4_info_report():
    reporter = LDFInfoReporter()
    info = reporter.generate(ldf_v1)
    assert "LDF 文件信息" in info
    assert "LIN_Master" in info
    assert "EngineFrame" in info
    assert "NormalSchedule" in info


def t4_no_diff_report():
    differ = LDFDiff()
    no_diff = differ.compare(ldf_v1, ldf_v1)
    reporter = LDFTextReporter()
    text = reporter.generate(no_diff)
    assert "完全相同" in text or "无任何差异" in text


test("文本报告生成", t4_text_report)
test("Markdown报告生成", t4_markdown_report)
test("HTML报告生成", t4_html_report)
test("CSV报告生成", t4_csv_report)
test("JSON报告生成", t4_json_report)
test("文件信息报告", t4_info_report)
test("无差异报告", t4_no_diff_report)


# ---------------------------------------------
# Test 5: 文件名解析
# ---------------------------------------------

section("Test 5: 文件名解析")


def t5_parse_standard():
    info = parse_ldf_filename("EEA3.0_LIN_Matrix_V10.1.0_20260212_LIN11.ldf")
    assert info is not None, "标准格式应能解析"
    assert info.channel == "LIN11", f"通道应为LIN11，实际: {info.channel}"
    assert info.version == (10, 1, 0), f"版本应为(10,1,0)，实际: {info.version}"
    assert info.date == "20260212", f"日期应为20260212，实际: {info.date}"
    assert info.version_str == "V10.1.0", f"版本字符串应为V10.1.0，实际: {info.version_str}"


def t5_parse_with_project():
    info = parse_ldf_filename("EEA3.0_LIN_Matrix_V10.1.5_20260301_PZBP_LIN11.ldf")
    assert info is not None, "含项目名格式应能解析"
    assert info.channel == "LIN11"
    assert info.version == (10, 1, 5)


def t5_parse_version_compare():
    info1 = parse_ldf_filename("EEA3.0_LIN_Matrix_V10.1.0_20260212_LIN11.ldf")
    info2 = parse_ldf_filename("EEA3.0_LIN_Matrix_V10.1.5_20260301_LIN11.ldf")
    assert info1 is not None and info2 is not None
    assert info2.version > info1.version, "V10.1.5应大于V10.1.0"


def t5_parse_fallback():
    # 不符合标准格式但含LIN通道名
    info = parse_ldf_filename("my_project_LIN5_v2.ldf")
    assert info is not None, "备用模式应能解析含LIN通道名的文件"
    assert info.channel == "LIN5"


test("标准格式文件名解析", t5_parse_standard)
test("含项目名格式解析", t5_parse_with_project)
test("版本号比较", t5_parse_version_compare)
test("备用模式解析", t5_parse_fallback)


# ---------------------------------------------
# Test 6: 报告文件保存
# ---------------------------------------------

section("Test 6: 报告文件保存")

_OUT_DIR = os.path.join(_DIR, "ldf_test_output")
os.makedirs(_OUT_DIR, exist_ok=True)


def t6_save_html():
    path = os.path.join(_OUT_DIR, "test_diff.html")
    LDFHTMLReporter().save(diff_result, path)
    assert os.path.exists(path), "HTML文件应已创建"
    size = os.path.getsize(path)
    assert size > 500, f"HTML文件大小应>500字节，实际: {size}"


def t6_save_text():
    path = os.path.join(_OUT_DIR, "test_diff.txt")
    LDFTextReporter().save(diff_result, path)
    assert os.path.exists(path)
    with open(path, encoding='utf-8') as f:
        content = f.read()
    assert "LDF 差异分析报告" in content


def t6_save_csv():
    path = os.path.join(_OUT_DIR, "test_diff.csv")
    LDFCSVReporter().save(diff_result, path)
    assert os.path.exists(path)
    size = os.path.getsize(path)
    assert size > 0


def t6_save_json():
    import json
    path = os.path.join(_OUT_DIR, "test_diff.json")
    LDFJSONReporter().save(diff_result, path)
    assert os.path.exists(path)
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    assert "stats" in data


test("保存HTML报告", t6_save_html)
test("保存文本报告", t6_save_text)
test("保存CSV报告", t6_save_csv)
test("保存JSON报告", t6_save_json)


# ---------------------------------------------
# Test 7: 节点属性变更 & 调度表顺序变更
# ---------------------------------------------

section("Test 7: 节点属性变更 & 调度表顺序变更")

_LDF_ATTR_V1 = """
LIN_description_file;
LIN_protocol_version = "2.1";
LIN_language_version = "2.1";
LIN_speed = 19.2 kbps;

Nodes {
  Master: Master, 5 ms, 0.1 ms;
  Slaves: NodeA, NodeB;
}

Signals {
  Sig1 : 8, 0, NodeA, Master;
  Sig2 : 8, 0, NodeB, Master;
}

Frames {
  Frame1 : 0x01, NodeA, 1 { Sig1, 0; }
  Frame2 : 0x02, NodeB, 1 { Sig2, 0; }
}

Node_attributes {
  NodeA {
    LIN_protocol = "2.1";
    configured_NAD = 0x01;
    initial_NAD = 0x01;
    product_id = 0x0001, 0x0001, 0x01;
    response_error = Sig1;
    P2_min = 50 ms;
    ST_min = 0 ms;
    configurable_frames {
      Frame1 = 0x0001;
    }
  }
  NodeB {
    LIN_protocol = "2.1";
    configured_NAD = 0x02;
    initial_NAD = 0x02;
    product_id = 0x0002, 0x0001, 0x01;
    response_error = Sig2;
    P2_min = 50 ms;
    ST_min = 0 ms;
    configurable_frames {
      Frame2 = 0x0002;
    }
  }
}

Schedule_tables {
  Sched1 {
    Frame1 delay 10 ms;
    Frame2 delay 20 ms;
  }
}
"""

_LDF_ATTR_V2 = """
LIN_description_file;
LIN_protocol_version = "2.1";
LIN_language_version = "2.1";
LIN_speed = 19.2 kbps;

Nodes {
  Master: Master, 5 ms, 0.1 ms;
  Slaves: NodeA, NodeB;
}

Signals {
  Sig1 : 8, 0, NodeA, Master;
  Sig2 : 8, 0, NodeB, Master;
}

Frames {
  Frame1 : 0x01, NodeA, 1 { Sig1, 0; }
  Frame2 : 0x02, NodeB, 1 { Sig2, 0; }
}

Node_attributes {
  NodeA {
    LIN_protocol = "2.1";
    configured_NAD = 0x01;
    initial_NAD = 0x01;
    product_id = 0x0001, 0x0001, 0x02;
    response_error = Sig1;
    P2_min = 100 ms;
    ST_min = 0 ms;
    configurable_frames {
      Frame1 = 0x0001;
    }
  }
  NodeB {
    LIN_protocol = "2.1";
    configured_NAD = 0x03;
    initial_NAD = 0x02;
    product_id = 0x0002, 0x0001, 0x01;
    response_error = Sig2;
    P2_min = 50 ms;
    ST_min = 0 ms;
    configurable_frames {
      Frame2 = 0x0002;
    }
  }
}

Schedule_tables {
  Sched1 {
    Frame2 delay 20 ms;
    Frame1 delay 10 ms;
  }
}
"""

_p = LDFParser()
_ldf_a1 = _p.parse_string(_LDF_ATTR_V1, source="attr_v1")
_ldf_a2 = _p.parse_string(_LDF_ATTR_V2, source="attr_v2")
_diff_attr = LDFDiff().compare(_ldf_a1, _ldf_a2)


def t7_node_attr_detected():
    """节点属性变更应被检测到"""
    assert len(_diff_attr.node_attr_changes) > 0, "应有节点属性变更"


def t7_node_attr_field_change():
    """NodeA的product_id和P2_min应被检测为修改"""
    modified = [ac for ac in _diff_attr.node_attr_changes
                if ac.change_type == ChangeType.MODIFIED and ac.node_name == "NodeA"]
    assert len(modified) == 1, f"NodeA应有1条修改记录，实际: {len(modified)}"
    fields = {fc.field_name for fc in modified[0].field_changes}
    assert "product_id" in fields or "P2_min(ms)" in fields, \
        f"NodeA应有product_id或P2_min变更，实际字段: {fields}"


def t7_node_attr_nad_change():
    """NodeB的configured_NAD应被检测为修改"""
    modified = [ac for ac in _diff_attr.node_attr_changes
                if ac.change_type == ChangeType.MODIFIED and ac.node_name == "NodeB"]
    assert len(modified) == 1, f"NodeB应有1条修改记录，实际: {len(modified)}"
    fields = {fc.field_name for fc in modified[0].field_changes}
    assert "configured_NAD" in fields, f"NodeB应有configured_NAD变更，实际字段: {fields}"


def t7_schedule_order_change():
    """Sched1中Frame1和Frame2顺序互换应被检测到"""
    modified = [sc for sc in _diff_attr.schedule_changes
                if sc.change_type == ChangeType.MODIFIED and sc.table_name == "Sched1"]
    assert len(modified) == 1, f"Sched1应有1条修改记录，实际: {len(modified)}"
    reordered = modified[0].entries_reordered
    assert len(reordered) > 0, "Sched1应有顺序变更"
    frame_names = {oc.frame_name for oc in reordered}
    assert "Frame1" in frame_names or "Frame2" in frame_names, \
        f"Frame1或Frame2应在顺序变更中，实际: {frame_names}"


def t7_stats_node_attrs():
    """stats()应包含node_attrs统计"""
    stats = _diff_attr.stats()
    assert "node_attrs_modified" in stats, "stats应包含node_attrs_modified"
    assert stats["node_attrs_modified"] >= 1, \
        f"node_attrs_modified应>=1，实际: {stats['node_attrs_modified']}"


def t7_text_report_node_attrs():
    """文本报告应包含节点属性变更章节"""
    text = LDFTextReporter().generate(_diff_attr)
    assert "节点属性变更" in text, "文本报告应包含节点属性变更章节"
    assert "Node_attributes" in text, "文本报告应包含Node_attributes关键字"


def t7_text_report_schedule_order():
    """文本报告应包含调度表顺序变更"""
    text = LDFTextReporter().generate(_diff_attr)
    assert "顺序" in text or "<>" in text, "文本报告应包含顺序变更标记"


def t7_json_report_node_attrs():
    """JSON报告应包含node_attr_changes字段"""
    import json
    json_text = LDFJSONReporter().generate(_diff_attr)
    data = json.loads(json_text)
    assert "node_attr_changes" in data, "JSON报告应包含node_attr_changes"
    assert len(data["node_attr_changes"]) > 0, "node_attr_changes不应为空"


def t7_json_report_schedule_order():
    """JSON报告的schedule_changes应包含entries_reordered"""
    import json
    json_text = LDFJSONReporter().generate(_diff_attr)
    data = json.loads(json_text)
    sched_changes = data.get("schedule_changes", [])
    modified = [sc for sc in sched_changes if sc["change_type"] == "MODIFIED"]
    assert len(modified) > 0, "应有修改的调度表"
    assert "entries_reordered" in modified[0], "schedule_change应包含entries_reordered"
    assert len(modified[0]["entries_reordered"]) > 0, "entries_reordered不应为空"


def t7_csv_report_node_attrs():
    """CSV报告应包含节点属性行"""
    csv_text = LDFCSVReporter().generate(_diff_attr)
    assert "节点属性" in csv_text, "CSV报告应包含节点属性行"


def t7_csv_report_schedule_order():
    """CSV报告应包含调度表顺序行"""
    csv_text = LDFCSVReporter().generate(_diff_attr)
    assert "顺序" in csv_text, "CSV报告应包含顺序变更行"


test("节点属性变更检测", t7_node_attr_detected)
test("节点属性字段变更(NodeA product_id/P2_min)", t7_node_attr_field_change)
test("节点属性NAD变更(NodeB configured_NAD)", t7_node_attr_nad_change)
test("调度表条目顺序变更检测", t7_schedule_order_change)
test("stats()包含node_attrs统计", t7_stats_node_attrs)
test("文本报告包含节点属性变更章节", t7_text_report_node_attrs)
test("文本报告包含调度表顺序变更", t7_text_report_schedule_order)
test("JSON报告包含node_attr_changes", t7_json_report_node_attrs)
test("JSON报告schedule包含entries_reordered", t7_json_report_schedule_order)
test("CSV报告包含节点属性行", t7_csv_report_node_attrs)
test("CSV报告包含调度表顺序行", t7_csv_report_schedule_order)


# ---------------------------------------------
# 汇总
# ---------------------------------------------

print(f"\n{'='*55}")
print(f"  测试结果: {_pass} 通过 / {_fail} 失败 / {_pass + _fail} 总计")
print(f"{'='*55}")

if _fail == 0:
    print("\n 所有测试通过！")
    print(f"\n生成的测试报告位于: {_OUT_DIR}/")
else:
    print(f"\n[WARN]  有 {_fail} 个测试失败，请检查上方错误信息。")
    sys.exit(1)
