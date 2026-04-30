"""
DBC Skill 功能测试脚本 - test_dbc_skill.py
运行此脚本验证所有模块功能是否正常
"""

import sys
import os

# 将当前目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dbc_parser import DBCParser, DBCFile
from dbc_diff import DBCDiff, ChangeType
from dbc_report import (
    TextReporter, MarkdownReporter, HTMLReporter,
    CSVReporter, JSONReporter, DBCSummaryReporter
)

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")
V1_PATH = os.path.join(EXAMPLES_DIR, "sample_v1.dbc")
V2_PATH = os.path.join(EXAMPLES_DIR, "sample_v2.dbc")
OUT_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples", "output")

PASS = "[PASS]"
FAIL = "[FAIL]"


def section(title: str):
    print(f"\n{'-'*60}")
    print(f"  {title}")
    print(f"{'-'*60}")


def check(desc: str, condition: bool):
    status = PASS if condition else FAIL
    print(f"  {status}  {desc}")
    if not condition:
        raise AssertionError(f"测试失败: {desc}")


# ---------------------------------------------
# 测试1：解析器基础功能
# ---------------------------------------------

def test_parser():
    section("测试1: DBC解析器 (dbc_parser.py)")

    parser = DBCParser()
    dbc = parser.parse_file(V1_PATH)

    check("解析成功，返回DBCFile对象", isinstance(dbc, DBCFile))
    check("节点数量正确 (4个)", len(dbc.nodes) == 4)
    check("节点包含VCU", "VCU" in dbc.nodes)
    check("节点包含MCU", "MCU" in dbc.nodes)
    check("节点包含BMS", "BMS" in dbc.nodes)
    check("节点包含GW",  "GW"  in dbc.nodes)

    check("报文数量正确 (4条)", len(dbc.messages) == 4)
    check("报文256存在", 256 in dbc.messages)
    check("报文512存在", 512 in dbc.messages)
    check("报文768存在", 768 in dbc.messages)
    check("报文1024存在", 1024 in dbc.messages)

    msg256 = dbc.messages[256]
    check("报文256名称正确", msg256.name == "VCU_Status")
    check("报文256 DLC=8", msg256.dlc == 8)
    check("报文256发送节点=VCU", msg256.sender == "VCU")
    check("报文256信号数=6", len(msg256.signals) == 6)

    sig_speed = msg256.signals.get("VCU_VehicleSpeed")
    check("VCU_VehicleSpeed信号存在", sig_speed is not None)
    check("VCU_VehicleSpeed起始位=4", sig_speed.start_bit == 4)
    check("VCU_VehicleSpeed长度=12", sig_speed.length == 12)
    check("VCU_VehicleSpeed字节序=Intel", sig_speed.byte_order == "1")
    check("VCU_VehicleSpeed因子=0.1", sig_speed.factor == 0.1)
    check("VCU_VehicleSpeed单位=km/h", sig_speed.unit == "km/h")
    check("VCU_VehicleSpeed接收节点包含MCU", "MCU" in sig_speed.receivers)

    # 注释解析
    check("节点VCU注释正确", dbc.nodes["VCU"].comment == "整车控制器")
    check("报文256注释非空", len(msg256.comment) > 0)

    # 值表解析
    sig_gear = msg256.signals.get("VCU_GearPos")
    check("VCU_GearPos值表存在", len(sig_gear.value_table) > 0)
    check("VCU_GearPos值表0=P", sig_gear.value_table.get(0) == "P")
    check("VCU_GearPos值表3=D", sig_gear.value_table.get(3) == "D")

    # 属性解析
    check("报文256周期属性存在", "GenMsgCycleTime" in msg256.attributes)
    check("报文256周期=10ms", msg256.attributes["GenMsgCycleTime"] == 10)

    print(f"\n  解析摘要: {len(dbc.nodes)}节点 / {len(dbc.messages)}报文 / "
          f"{sum(len(m.signals) for m in dbc.messages.values())}信号")


# ---------------------------------------------
# 测试2：差异分析功能
# ---------------------------------------------

def test_diff():
    section("测试2: DBC差异分析 (dbc_diff.py)")

    parser = DBCParser()
    old_dbc = parser.parse_file(V1_PATH)
    new_dbc = parser.parse_file(V2_PATH)

    diff = DBCDiff()
    result = diff.compare(old_dbc, new_dbc)

    check("差异结果非空", result.has_changes())

    # 节点变更：v2新增ADAS节点
    check("节点变更存在", len(result.node_changes) > 0)
    added_node_names = [nc.node_name for nc in result.added_nodes]
    check("新增节点ADAS", "ADAS" in added_node_names)
    check("无删除节点", len(result.removed_nodes) == 0)

    # 报文变更
    # v2: GW_TimeSync ID从1024改为1040（ID变更），新增ADAS_CtrlCmd(1280)
    added_msg_ids = [mc.msg_id for mc in result.added_messages]
    removed_msg_ids = [mc.msg_id for mc in result.removed_messages]
    check("新增报文1280(ADAS_CtrlCmd)", 1280 in added_msg_ids)
    check("无删除报文（GW_TimeSync是ID变更，不是删除）", len(removed_msg_ids) == 0)

    # 报文ID变更
    check("报文ID变更存在", len(result.message_id_changes) > 0)
    id_change = next((ic for ic in result.message_id_changes if ic.msg_name == "GW_TimeSync"), None)
    check("GW_TimeSync ID变更被检测到", id_change is not None)
    check("GW_TimeSync旧ID=0x400(1024)", id_change.old_id == 1024)
    check("GW_TimeSync新ID=0x410(1040)", id_change.new_id == 1040)
    check("GW_TimeSync旧ID_hex=0x400", id_change.old_id_hex == "0x400")
    check("GW_TimeSync新ID_hex=0x410", id_change.new_id_hex == "0x410")

    # 修改报文
    modified_msg_ids = [mc.msg_id for mc in result.modified_messages]
    check("报文256有修改", 256 in modified_msg_ids)
    check("报文512有修改", 512 in modified_msg_ids)

    # 信号变更：报文256新增VCU_SteerAngle
    mc256 = next(mc for mc in result.modified_messages if mc.msg_id == 256)
    added_sig_names = [sc.signal_name for sc in mc256.signal_changes
                       if sc.change_type == ChangeType.ADDED]
    check("报文256新增信号VCU_SteerAngle", "VCU_SteerAngle" in added_sig_names)

    # 信号修改：VCU_VehicleSpeed因子从0.1改为0.05
    modified_sigs = [sc for sc in mc256.signal_changes
                     if sc.change_type == ChangeType.MODIFIED]
    speed_change = next((sc for sc in modified_sigs
                         if sc.signal_name == "VCU_VehicleSpeed"), None)
    check("VCU_VehicleSpeed有修改", speed_change is not None)
    factor_change = next((fc for fc in speed_change.field_changes
                          if fc.field_name == "因子"), None)
    check("VCU_VehicleSpeed因子变更存在", factor_change is not None)
    check("VCU_VehicleSpeed因子旧值=0.1", factor_change.old_value == 0.1)
    check("VCU_VehicleSpeed因子新值=0.05", factor_change.new_value == 0.05)

    # 信号修改：MCU_FaultCode长度从8改为12
    mc512 = next(mc for mc in result.modified_messages if mc.msg_id == 512)
    fault_change = next((sc for sc in mc512.signal_changes
                         if sc.signal_name == "MCU_FaultCode"), None)
    check("MCU_FaultCode有修改", fault_change is not None)
    len_change = next((fc for fc in fault_change.field_changes
                       if fc.field_name == "位长度"), None)
    check("MCU_FaultCode位长度变更存在", len_change is not None)
    check("MCU_FaultCode位长度旧值=8", len_change.old_value == 8)
    check("MCU_FaultCode位长度新值=12", len_change.new_value == 12)

    # BA_ 属性变更：v2中 BMS_BattInfo(768) 新增 GenMsgSendType=1（Event）
    mc768 = next((mc for mc in result.modified_messages if mc.msg_id == 768), None)
    check("报文768有修改（BA_属性变更）", mc768 is not None)
    if mc768:
        send_type_change = next((fc for fc in mc768.attr_changes
                                 if fc.field_name == "GenMsgSendType"), None)
        check("BMS_BattInfo GenMsgSendType属性变更存在", send_type_change is not None)
        check("BMS_BattInfo GenMsgSendType旧值=<不存在>", send_type_change.old_value == "<不存在>")
        check("BMS_BattInfo GenMsgSendType新值=1", send_type_change.new_value == 1)

    # BA_ 属性变更：v2中 VCU_Status(256) 新增 GenMsgStartDelayTime=5
    mc256_attr = next((mc for mc in result.modified_messages if mc.msg_id == 256), None)
    if mc256_attr:
        delay_change = next((fc for fc in mc256_attr.attr_changes
                             if fc.field_name == "GenMsgStartDelayTime"), None)
        check("VCU_Status GenMsgStartDelayTime属性变更存在", delay_change is not None)
        check("VCU_Status GenMsgStartDelayTime新值=5", delay_change.new_value == 5)

    # 统计
    stats = result.stats()
    check("统计-节点新增=1", stats["nodes_added"] == 1)
    check("统计-节点删除=0", stats["nodes_removed"] == 0)
    check("统计-报文ID变更=1", stats["msg_id_changes"] == 1)
    check("统计-报文新增=1", stats["msgs_added"] == 1)
    check("统计-报文删除=0（GW_TimeSync是ID变更）", stats["msgs_removed"] == 0)
    check("统计-信号新增>=1", stats["sigs_added"] >= 1)
    check("统计-信号修改>=1", stats["sigs_modified"] >= 1)

    print(f"\n  差异统计: {stats}")


# ---------------------------------------------
# 测试3：报告生成功能
# ---------------------------------------------

def test_reporters():
    section("测试3: 报告生成 (dbc_report.py)")

    os.makedirs(OUT_DIR, exist_ok=True)

    parser = DBCParser()
    old_dbc = parser.parse_file(V1_PATH)
    new_dbc = parser.parse_file(V2_PATH)
    result = DBCDiff().compare(old_dbc, new_dbc)

    # 文本报告
    text_path = os.path.join(OUT_DIR, "diff_report.txt")
    TextReporter().save(result, text_path)
    check("文本报告文件生成", os.path.isfile(text_path))
    check("文本报告非空", os.path.getsize(text_path) > 100)

    # Markdown报告
    md_path = os.path.join(OUT_DIR, "diff_report.md")
    MarkdownReporter().save(result, md_path)
    check("Markdown报告文件生成", os.path.isfile(md_path))
    with open(md_path, encoding='utf-8') as f:
        md_content = f.read()
    check("Markdown包含标题", "# DBC 变更差异报告" in md_content)
    check("Markdown包含变更摘要", "变更摘要" in md_content)

    # HTML报告
    html_path = os.path.join(OUT_DIR, "diff_report.html")
    HTMLReporter().save(result, html_path)
    check("HTML报告文件生成", os.path.isfile(html_path))
    with open(html_path, encoding='utf-8') as f:
        html_content = f.read()
    check("HTML包含DOCTYPE", "<!DOCTYPE html>" in html_content)
    check("HTML包含变更摘要", "变更摘要" in html_content)

    # CSV报告
    csv_path = os.path.join(OUT_DIR, "diff_report.csv")
    CSVReporter().save(result, csv_path)
    check("CSV报告文件生成", os.path.isfile(csv_path))
    check("CSV报告非空", os.path.getsize(csv_path) > 50)

    # JSON报告
    json_path = os.path.join(OUT_DIR, "diff_report.json")
    JSONReporter().save(result, json_path)
    check("JSON报告文件生成", os.path.isfile(json_path))
    import json
    with open(json_path, encoding='utf-8') as f:
        json_data = json.load(f)
    check("JSON包含stats字段", "stats" in json_data)
    check("JSON包含message_changes字段", "message_changes" in json_data)

    # 单文件摘要报告
    summary_path = os.path.join(OUT_DIR, "summary_v1.txt")
    reporter = DBCSummaryReporter()
    content = reporter.generate(old_dbc)
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(content)
    check("摘要报告文件生成", os.path.isfile(summary_path))
    check("摘要包含节点信息", "网络节点" in content)
    check("摘要包含报文列表", "报文列表" in content)

    print(f"\n  所有报告已生成到: {OUT_DIR}")


# ---------------------------------------------
# 测试4：相同文件对比（无差异）
# ---------------------------------------------

def test_no_diff():
    section("测试4: 相同文件对比（应无差异）")

    parser = DBCParser()
    dbc = parser.parse_file(V1_PATH)
    result = DBCDiff().compare(dbc, dbc)

    check("相同文件无变更", not result.has_changes())
    check("节点变更为空", len(result.node_changes) == 0)
    check("报文变更为空", len(result.message_changes) == 0)

    text = TextReporter().generate(result)
    check("文本报告包含无变更提示", "完全一致" in text)


# ---------------------------------------------
# 测试5：字符串解析
# ---------------------------------------------

def test_parse_string():
    section("测试5: 字符串解析")

    dbc_content = """
VERSION "1.0"
BS_: 500000
BU_: ECU1 ECU2

BO_ 100 TestMsg : 4 ECU1
 SG_ Signal1 : 0|8@1+ (1,0) [0|255] "unit" ECU2
 SG_ Signal2 : 8|16@1- (0.01,-100) [-100|100] "%" ECU2

CM_ SG_ 100 Signal1 "测试信号1";
VAL_ 100 Signal1 0 "Off" 1 "On" ;
"""
    parser = DBCParser()
    dbc = parser.parse_string(dbc_content, source="<test>")

    check("字符串解析成功", isinstance(dbc, DBCFile))
    check("版本解析正确", dbc.version == "1.0")
    check("波特率解析正确", dbc.baudrate == "500000")
    check("节点数量=2", len(dbc.nodes) == 2)
    check("报文100存在", 100 in dbc.messages)

    msg = dbc.messages[100]
    check("报文名称正确", msg.name == "TestMsg")
    check("信号数量=2", len(msg.signals) == 2)

    sig1 = msg.signals["Signal1"]
    check("Signal1注释解析", sig1.comment == "测试信号1")
    check("Signal1值表解析", sig1.value_table.get(0) == "Off")
    check("Signal1值表1=On", sig1.value_table.get(1) == "On")

    sig2 = msg.signals["Signal2"]
    check("Signal2有符号", sig2.value_type == "-")
    check("Signal2因子=0.01", sig2.factor == 0.01)
    check("Signal2偏移=-100", sig2.offset == -100.0)


# ---------------------------------------------
# 主函数
# ---------------------------------------------

def main():
    print("=" * 60)
    print("  DBC Skill 功能测试")
    print("=" * 60)

    tests = [
        ("解析器基础功能", test_parser),
        ("差异分析功能",   test_diff),
        ("报告生成功能",   test_reporters),
        ("相同文件对比",   test_no_diff),
        ("字符串解析",     test_parse_string),
    ]

    passed = 0
    failed = 0

    for name, func in tests:
        try:
            func()
            passed += 1
        except AssertionError as e:
            print(f"\n  [FAIL] 测试失败: {e}")
            failed += 1
        except Exception as e:
            print(f"\n  [FAIL] 测试异常: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"  测试结果: {passed} 通过 / {failed} 失败 / {passed+failed} 总计")
    print(f"{'='*60}")

    if failed == 0:
        print("\n   所有测试通过！DBC Skill 功能正常。")
    else:
        print(f"\n  [WARN]  有 {failed} 个测试失败，请检查相关模块。")
        sys.exit(1)


if __name__ == "__main__":
    main()
