"""
DBC报告生成模块 - dbc_report.py
支持输出：控制台文本报告 / Markdown报告 / HTML报告 / CSV报告
"""

import os
import csv
import json
from datetime import datetime
from typing import List, Optional
from dbc_parser import DBCFile, Message, Signal
from dbc_diff import (
    DBCDiffResult, MessageChange, SignalChange, NodeChange,
    ChangeType, FieldChange, MessageIdChange
)


# ---------------------------------------------
# 工具函数
# ---------------------------------------------

def _byte_order_str(bo: str) -> str:
    return "Intel(小端)" if bo == "1" else "Motorola(大端)"

def _value_type_str(vt: str) -> str:
    return "无符号" if vt == "+" else "有符号"

def _change_icon(ct: str) -> str:
    return {"ADDED": "[+]", "REMOVED": "[x]", "MODIFIED": "[~]"}.get(ct, "?")

def _change_label(ct: str) -> str:
    return {"ADDED": "新增", "REMOVED": "删除", "MODIFIED": "修改"}.get(ct, ct)


# ---------------------------------------------
# 控制台文本报告
# ---------------------------------------------

class TextReporter:
    """生成控制台友好的文本差异报告"""

    def generate(self, result: DBCDiffResult, verbose: bool = True) -> str:
        lines = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines.append("=" * 70)
        lines.append("  DBC 变更差异报告")
        lines.append(f"  生成时间: {now}")
        lines.append(f"  旧版本: {os.path.basename(result.old_file)}")
        lines.append(f"  新版本: {os.path.basename(result.new_file)}")
        lines.append("=" * 70)

        if not result.has_changes():
            lines.append("\n[PASS] 两个DBC文件内容完全一致，无任何变更。")
            return "\n".join(lines)

        # 统计摘要
        stats = result.stats()
        lines.append("\n【变更摘要】")
        lines.append(f"  节点: 新增 {stats['nodes_added']}  删除 {stats['nodes_removed']}")
        lines.append(f"  报文ID变更: {stats['msg_id_changes']}")
        lines.append(f"  报文: 新增 {stats['msgs_added']}  删除 {stats['msgs_removed']}  修改 {stats['msgs_modified']}")
        lines.append(f"  信号: 新增 {stats['sigs_added']}  删除 {stats['sigs_removed']}  修改 {stats['sigs_modified']}")

        # 节点变更
        if result.node_changes:
            lines.append("\n【节点变更】")
            for nc in result.node_changes:
                lines.append(f"  {_change_icon(nc.change_type)} {nc.summary()}")
                if verbose and nc.field_changes:
                    for fc in nc.field_changes:
                        lines.append(f"      {fc.field_name}: {fc.old_value!r} -> {fc.new_value!r}")

        # 报文ID变更
        if result.message_id_changes:
            lines.append("\n【报文ID变更】")
            for ic in result.message_id_changes:
                lines.append(f"  ⇄ {ic.summary()}")
                if verbose:
                    lines.append(f"      旧ID: {ic.old_id_hex}  新ID: {ic.new_id_hex}")

        # 新增报文
        if result.added_messages:
            lines.append("\n【新增报文】")
            for mc in result.added_messages:
                msg = mc.new_message
                lines.append(f"  [+] {mc.msg_name} ({mc.can_id_hex})  DLC={msg.dlc}  发送节点={msg.sender}")
                if verbose and msg.signals:
                    for sig_name, sig in sorted(msg.signals.items()):
                        lines.append(f"      + 信号: {sig_name}  起始位={sig.start_bit}  长度={sig.length}bit"
                                     f"  {_byte_order_str(sig.byte_order)}  因子={sig.factor}  偏移={sig.offset}"
                                     f"  单位={sig.unit!r}")

        # 删除报文
        if result.removed_messages:
            lines.append("\n【删除报文】")
            for mc in result.removed_messages:
                msg = mc.old_message
                lines.append(f"  [x] {mc.msg_name} ({mc.can_id_hex})  DLC={msg.dlc}  发送节点={msg.sender}")
                if verbose and msg.signals:
                    for sig_name in sorted(msg.signals.keys()):
                        lines.append(f"      - 信号: {sig_name}")

        # 修改报文
        if result.modified_messages:
            lines.append("\n【修改报文】")
            for mc in result.modified_messages:
                lines.append(f"  [~] {mc.msg_name} ({mc.can_id_hex})")
                if verbose:
                    # 报文结构字段变更
                    for fc in mc.field_changes:
                        lines.append(f"      字段变更 - {fc.field_name}: {fc.old_value!r} -> {fc.new_value!r}")
                    # BA_ 属性变更
                    for fc in mc.attr_changes:
                        lines.append(f"      属性变更 - {fc.field_name}: {fc.old_value!r} -> {fc.new_value!r}")
                    # 信号变更
                    for sc in mc.signal_changes:
                        icon = _change_icon(sc.change_type)
                        label = _change_label(sc.change_type)
                        lines.append(f"      {icon} [{label}信号] {sc.signal_name}")
                        if sc.change_type == ChangeType.ADDED and sc.new_signal:
                            sig = sc.new_signal
                            lines.append(f"          起始位={sig.start_bit}  长度={sig.length}bit"
                                         f"  {_byte_order_str(sig.byte_order)}  {_value_type_str(sig.value_type)}")
                            lines.append(f"          因子={sig.factor}  偏移={sig.offset}"
                                         f"  范围=[{sig.min_val}, {sig.max_val}]  单位={sig.unit!r}")
                            lines.append(f"          接收节点={sig.receivers}")
                        elif sc.change_type == ChangeType.REMOVED and sc.old_signal:
                            sig = sc.old_signal
                            lines.append(f"          起始位={sig.start_bit}  长度={sig.length}bit")
                        elif sc.change_type == ChangeType.MODIFIED:
                            for fc in sc.field_changes:
                                lines.append(f"          {fc.field_name}: {fc.old_value!r} -> {fc.new_value!r}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def print(self, result: DBCDiffResult, verbose: bool = True):
        print(self.generate(result, verbose))

    def save(self, result: DBCDiffResult, filepath: str, verbose: bool = True):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate(result, verbose))
        print(f"[TextReporter] 报告已保存: {filepath}")


# ---------------------------------------------
# Markdown 报告
# ---------------------------------------------

class MarkdownReporter:
    """生成Markdown格式差异报告"""

    def generate(self, result: DBCDiffResult) -> str:
        lines = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines.append("# DBC 变更差异报告\n")
        lines.append(f"- **生成时间**: {now}")
        lines.append(f"- **旧版本**: `{os.path.basename(result.old_file)}`")
        lines.append(f"- **新版本**: `{os.path.basename(result.new_file)}`\n")

        if not result.has_changes():
            lines.append("> [PASS] 两个DBC文件内容完全一致，无任何变更。")
            return "\n".join(lines)

        # 统计摘要
        stats = result.stats()
        lines.append("## 变更摘要\n")
        lines.append("| 类别 | 新增 | 删除 | 修改 |")
        lines.append("|------|------|------|------|")
        lines.append(f"| 节点 | {stats['nodes_added']} | {stats['nodes_removed']} | - |")
        lines.append(f"| 报文ID变更 | - | - | {stats['msg_id_changes']} |")
        lines.append(f"| 报文 | {stats['msgs_added']} | {stats['msgs_removed']} | {stats['msgs_modified']} |")
        lines.append(f"| 信号 | {stats['sigs_added']} | {stats['sigs_removed']} | {stats['sigs_modified']} |")
        lines.append("")

        # 节点变更
        if result.node_changes:
            lines.append("## 节点变更\n")
            lines.append("| 变更类型 | 节点名称 | 详情 |")
            lines.append("|----------|----------|------|")
            for nc in result.node_changes:
                detail = "; ".join(f"{fc.field_name}: `{fc.old_value}` -> `{fc.new_value}`"
                                   for fc in nc.field_changes) or "-"
                lines.append(f"| {_change_label(nc.change_type)} | `{nc.node_name}` | {detail} |")
            lines.append("")

        # 报文ID变更
        if result.message_id_changes:
            lines.append("## 报文ID变更\n")
            lines.append("| 报文名称 | 旧ID | 新ID |")
            lines.append("|----------|------|------|")
            for ic in result.message_id_changes:
                lines.append(f"| `{ic.msg_name}` | `{ic.old_id_hex}` | `{ic.new_id_hex}` |")
            lines.append("")

        # 新增报文
        if result.added_messages:
            lines.append("## 新增报文\n")
            for mc in result.added_messages:
                msg = mc.new_message
                lines.append(f"### [+] {mc.msg_name} `{mc.can_id_hex}`\n")
                lines.append(f"- **DLC**: {msg.dlc} bytes")
                lines.append(f"- **发送节点**: {msg.sender}")
                if msg.comment:
                    lines.append(f"- **注释**: {msg.comment}")
                if msg.signals:
                    lines.append("\n**信号列表**:\n")
                    lines.append("| 信号名 | 起始位 | 长度(bit) | 字节序 | 类型 | 因子 | 偏移 | 最小值 | 最大值 | 单位 | 接收节点 |")
                    lines.append("|--------|--------|-----------|--------|------|------|------|--------|--------|------|----------|")
                    for sig_name, sig in sorted(msg.signals.items()):
                        lines.append(
                            f"| `{sig_name}` | {sig.start_bit} | {sig.length} | "
                            f"{_byte_order_str(sig.byte_order)} | {_value_type_str(sig.value_type)} | "
                            f"{sig.factor} | {sig.offset} | {sig.min_val} | {sig.max_val} | "
                            f"{sig.unit} | {', '.join(sig.receivers)} |"
                        )
                lines.append("")

        # 删除报文
        if result.removed_messages:
            lines.append("## 删除报文\n")
            for mc in result.removed_messages:
                msg = mc.old_message
                lines.append(f"### [x] {mc.msg_name} `{mc.can_id_hex}`\n")
                lines.append(f"- **DLC**: {msg.dlc} bytes")
                lines.append(f"- **发送节点**: {msg.sender}")
                lines.append(f"- **信号数量**: {len(msg.signals)}")
                if msg.signals:
                    lines.append(f"- **信号列表**: {', '.join(f'`{s}`' for s in sorted(msg.signals.keys()))}")
                lines.append("")

        # 修改报文
        if result.modified_messages:
            lines.append("## 修改报文\n")
            for mc in result.modified_messages:
                lines.append(f"### [~] {mc.msg_name} `{mc.can_id_hex}`\n")

                # 报文结构字段变更
                if mc.field_changes:
                    lines.append("**报文字段变更**:\n")
                    lines.append("| 字段 | 旧值 | 新值 |")
                    lines.append("|------|------|------|")
                    for fc in mc.field_changes:
                        lines.append(f"| {fc.field_name} | `{fc.old_value}` | `{fc.new_value}` |")
                    lines.append("")

                # BA_ 属性变更
                if mc.attr_changes:
                    lines.append("**BA_属性变更**:\n")
                    lines.append("| 属性名 | 旧值 | 新值 |")
                    lines.append("|--------|------|------|")
                    for fc in mc.attr_changes:
                        lines.append(f"| {fc.field_name} | `{fc.old_value}` | `{fc.new_value}` |")
                    lines.append("")

                # 信号变更
                if mc.signal_changes:
                    lines.append("**信号变更**:\n")
                    for sc in mc.signal_changes:
                        icon = _change_icon(sc.change_type)
                        label = _change_label(sc.change_type)
                        lines.append(f"#### {icon} [{label}] `{sc.signal_name}`\n")

                        if sc.change_type == ChangeType.ADDED and sc.new_signal:
                            sig = sc.new_signal
                            lines.append("| 属性 | 值 |")
                            lines.append("|------|----|")
                            lines.append(f"| 起始位 | {sig.start_bit} |")
                            lines.append(f"| 位长度 | {sig.length} |")
                            lines.append(f"| 字节序 | {_byte_order_str(sig.byte_order)} |")
                            lines.append(f"| 数值类型 | {_value_type_str(sig.value_type)} |")
                            lines.append(f"| 因子 | {sig.factor} |")
                            lines.append(f"| 偏移 | {sig.offset} |")
                            lines.append(f"| 范围 | [{sig.min_val}, {sig.max_val}] |")
                            lines.append(f"| 单位 | {sig.unit} |")
                            lines.append(f"| 接收节点 | {', '.join(sig.receivers)} |")
                            if sig.comment:
                                lines.append(f"| 注释 | {sig.comment} |")

                        elif sc.change_type == ChangeType.REMOVED and sc.old_signal:
                            sig = sc.old_signal
                            lines.append(f"- 起始位: {sig.start_bit}, 长度: {sig.length}bit")

                        elif sc.change_type == ChangeType.MODIFIED and sc.field_changes:
                            lines.append("| 字段 | 旧值 | 新值 |")
                            lines.append("|------|------|------|")
                            for fc in sc.field_changes:
                                lines.append(f"| {fc.field_name} | `{fc.old_value}` | `{fc.new_value}` |")

                        lines.append("")

        return "\n".join(lines)

    def save(self, result: DBCDiffResult, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate(result))
        print(f"[MarkdownReporter] 报告已保存: {filepath}")


# ---------------------------------------------
# HTML 报告
# ---------------------------------------------

class HTMLReporter:
    """生成HTML格式差异报告（带样式）"""

    _CSS = """
    body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; color: #333; }
    h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
    h2 { color: #2980b9; margin-top: 30px; }
    h3 { color: #16a085; }
    h4 { color: #8e44ad; }
    .meta { background: #ecf0f1; padding: 10px 15px; border-radius: 5px; margin-bottom: 20px; }
    .summary { display: flex; gap: 20px; flex-wrap: wrap; margin: 15px 0; }
    .stat-box { background: white; border-radius: 8px; padding: 15px 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); min-width: 120px; text-align: center; }
    .stat-box .num { font-size: 2em; font-weight: bold; }
    .stat-box .label { color: #666; font-size: 0.85em; }
    .added .num { color: #27ae60; }
    .removed .num { color: #e74c3c; }
    .modified .num { color: #f39c12; }
    table { border-collapse: collapse; width: 100%; margin: 10px 0; background: white; border-radius: 5px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    th { background: #3498db; color: white; padding: 10px 12px; text-align: left; font-size: 0.9em; }
    td { padding: 8px 12px; border-bottom: 1px solid #ecf0f1; font-size: 0.9em; }
    tr:hover td { background: #f8f9fa; }
    .tag-added { background: #d5f5e3; color: #1e8449; padding: 2px 8px; border-radius: 3px; font-weight: bold; }
    .tag-removed { background: #fadbd8; color: #922b21; padding: 2px 8px; border-radius: 3px; font-weight: bold; }
    .tag-modified { background: #fef9e7; color: #9a7d0a; padding: 2px 8px; border-radius: 3px; font-weight: bold; }
    .msg-block { background: white; border-radius: 8px; padding: 15px 20px; margin: 15px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.08); }
    .msg-block.added { border-left: 5px solid #27ae60; }
    .msg-block.removed { border-left: 5px solid #e74c3c; }
    .msg-block.modified { border-left: 5px solid #f39c12; }
    code { background: #ecf0f1; padding: 1px 5px; border-radius: 3px; font-family: monospace; }
    .no-change { color: #27ae60; font-size: 1.1em; padding: 20px; }
    """

    def generate(self, result: DBCDiffResult) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats = result.stats()

        html = [f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DBC变更差异报告</title>
<style>{self._CSS}</style>
</head>
<body>
<h1> DBC 变更差异报告</h1>
<div class="meta">
  <strong>生成时间:</strong> {now}<br>
  <strong>旧版本:</strong> <code>{os.path.basename(result.old_file)}</code><br>
  <strong>新版本:</strong> <code>{os.path.basename(result.new_file)}</code>
</div>
"""]

        if not result.has_changes():
            html.append('<p class="no-change">[PASS] 两个DBC文件内容完全一致，无任何变更。</p>')
            html.append("</body></html>")
            return "".join(html)

        # 统计摘要
        html.append("<h2> 变更摘要</h2>")
        html.append('<div class="summary">')
        for label, key_add, key_rem, key_mod in [
            ("节点", "nodes_added", "nodes_removed", None),
            ("报文", "msgs_added", "msgs_removed", "msgs_modified"),
            ("信号", "sigs_added", "sigs_removed", "sigs_modified"),
        ]:
            html.append(f'<div class="stat-box added"><div class="num">{stats[key_add]}</div><div class="label">{label}新增</div></div>')
            html.append(f'<div class="stat-box removed"><div class="num">{stats[key_rem]}</div><div class="label">{label}删除</div></div>')
            if key_mod:
                html.append(f'<div class="stat-box modified"><div class="num">{stats[key_mod]}</div><div class="label">{label}修改</div></div>')
        html.append("</div>")

        # 节点变更
        if result.node_changes:
            html.append("<h2> 节点变更</h2>")
            html.append("<table><tr><th>变更类型</th><th>节点名称</th><th>详情</th></tr>")
            for nc in result.node_changes:
                tag_cls = nc.change_type.lower()
                detail = "; ".join(f"{fc.field_name}: <code>{fc.old_value}</code> -> <code>{fc.new_value}</code>"
                                   for fc in nc.field_changes) or "-"
                html.append(f"<tr><td><span class='tag-{tag_cls}'>{_change_label(nc.change_type)}</span></td>"
                             f"<td><code>{nc.node_name}</code></td><td>{detail}</td></tr>")
            html.append("</table>")

        # 报文ID变更
        if result.message_id_changes:
            html.append("<h2>⇄ 报文ID变更</h2>")
            html.append(f'<div class="stat-box modified" style="display:inline-block;margin-bottom:10px">'
                        f'<div class="num">{stats["msg_id_changes"]}</div>'
                        f'<div class="label">报文ID变更</div></div>')
            html.append("<table><tr><th>报文名称</th><th>旧ID</th><th>新ID</th></tr>")
            for ic in result.message_id_changes:
                html.append(f"<tr><td><strong>{ic.msg_name}</strong></td>"
                             f"<td><code>{ic.old_id_hex}</code></td>"
                             f"<td><code>{ic.new_id_hex}</code></td></tr>")
            html.append("</table>")

        # 新增报文
        if result.added_messages:
            html.append("<h2>[+] 新增报文</h2>")
            for mc in result.added_messages:
                msg = mc.new_message
                html.append(f'<div class="msg-block added">')
                html.append(f"<h3>[+] {mc.msg_name} <code>{mc.can_id_hex}</code></h3>")
                html.append(f"<p>DLC: <strong>{msg.dlc}</strong> bytes &nbsp;|&nbsp; 发送节点: <strong>{msg.sender}</strong></p>")
                if msg.comment:
                    html.append(f"<p>注释: {msg.comment}</p>")
                if msg.signals:
                    html.append(self._signal_table(msg.signals))
                html.append("</div>")

        # 删除报文
        if result.removed_messages:
            html.append("<h2>[x] 删除报文</h2>")
            for mc in result.removed_messages:
                msg = mc.old_message
                html.append(f'<div class="msg-block removed">')
                html.append(f"<h3>[x] {mc.msg_name} <code>{mc.can_id_hex}</code></h3>")
                html.append(f"<p>DLC: <strong>{msg.dlc}</strong> bytes &nbsp;|&nbsp; 发送节点: <strong>{msg.sender}</strong></p>")
                if msg.signals:
                    sig_names = ", ".join(f"<code>{s}</code>" for s in sorted(msg.signals.keys()))
                    html.append(f"<p>包含信号: {sig_names}</p>")
                html.append("</div>")

        # 修改报文
        if result.modified_messages:
            html.append("<h2>[~] 修改报文</h2>")
            for mc in result.modified_messages:
                html.append(f'<div class="msg-block modified">')
                html.append(f"<h3>[~] {mc.msg_name} <code>{mc.can_id_hex}</code></h3>")

                if mc.field_changes:
                    html.append("<h4>报文字段变更</h4>")
                    html.append("<table><tr><th>字段</th><th>旧值</th><th>新值</th></tr>")
                    for fc in mc.field_changes:
                        html.append(f"<tr><td>{fc.field_name}</td><td><code>{fc.old_value}</code></td>"
                                    f"<td><code>{fc.new_value}</code></td></tr>")
                    html.append("</table>")

                if mc.attr_changes:
                    html.append("<h4>BA_属性变更</h4>")
                    html.append("<table><tr><th>属性名</th><th>旧值</th><th>新值</th></tr>")
                    for fc in mc.attr_changes:
                        html.append(f"<tr><td>{fc.field_name}</td><td><code>{fc.old_value}</code></td>"
                                    f"<td><code>{fc.new_value}</code></td></tr>")
                    html.append("</table>")

                if mc.signal_changes:
                    html.append("<h4>信号变更</h4>")
                    for sc in mc.signal_changes:
                        tag_cls = sc.change_type.lower()
                        html.append(f"<p><span class='tag-{tag_cls}'>{_change_label(sc.change_type)}</span> "
                                    f"<strong><code>{sc.signal_name}</code></strong></p>")

                        if sc.change_type == ChangeType.ADDED and sc.new_signal:
                            html.append(self._signal_detail_table(sc.new_signal))
                        elif sc.change_type == ChangeType.REMOVED and sc.old_signal:
                            sig = sc.old_signal
                            html.append(f"<p style='color:#888'>起始位: {sig.start_bit}, 长度: {sig.length}bit</p>")
                        elif sc.change_type == ChangeType.MODIFIED and sc.field_changes:
                            html.append("<table><tr><th>字段</th><th>旧值</th><th>新值</th></tr>")
                            for fc in sc.field_changes:
                                html.append(f"<tr><td>{fc.field_name}</td><td><code>{fc.old_value}</code></td>"
                                            f"<td><code>{fc.new_value}</code></td></tr>")
                            html.append("</table>")

                html.append("</div>")

        html.append("</body></html>")
        return "".join(html)

    def _signal_table(self, signals: dict) -> str:
        rows = ["<table><tr><th>信号名</th><th>起始位</th><th>长度(bit)</th><th>字节序</th>"
                "<th>类型</th><th>因子</th><th>偏移</th><th>最小值</th><th>最大值</th><th>单位</th><th>接收节点</th></tr>"]
        for sig_name, sig in sorted(signals.items()):
            rows.append(f"<tr><td><code>{sig_name}</code></td><td>{sig.start_bit}</td><td>{sig.length}</td>"
                        f"<td>{_byte_order_str(sig.byte_order)}</td><td>{_value_type_str(sig.value_type)}</td>"
                        f"<td>{sig.factor}</td><td>{sig.offset}</td><td>{sig.min_val}</td><td>{sig.max_val}</td>"
                        f"<td>{sig.unit}</td><td>{', '.join(sig.receivers)}</td></tr>")
        rows.append("</table>")
        return "".join(rows)

    def _signal_detail_table(self, sig: Signal) -> str:
        rows = ["<table>"]
        fields = [
            ("起始位", sig.start_bit), ("位长度", sig.length),
            ("字节序", _byte_order_str(sig.byte_order)), ("数值类型", _value_type_str(sig.value_type)),
            ("因子", sig.factor), ("偏移", sig.offset),
            ("最小值", sig.min_val), ("最大值", sig.max_val),
            ("单位", sig.unit), ("接收节点", ", ".join(sig.receivers)),
        ]
        if sig.comment:
            fields.append(("注释", sig.comment))
        for k, v in fields:
            rows.append(f"<tr><td><strong>{k}</strong></td><td><code>{v}</code></td></tr>")
        rows.append("</table>")
        return "".join(rows)

    def save(self, result: DBCDiffResult, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate(result))
        print(f"[HTMLReporter] 报告已保存: {filepath}")


# ---------------------------------------------
# CSV 报告
# ---------------------------------------------

class CSVReporter:
    """生成CSV格式差异报告（适合Excel查看）"""

    def save(self, result: DBCDiffResult, filepath: str):
        rows = []
        rows.append(["变更类型", "报文ID(HEX)", "报文名称", "信号名称", "变更字段", "旧值", "新值"])

        # 节点变更
        for nc in result.node_changes:
            if nc.field_changes:
                for fc in nc.field_changes:
                    rows.append([f"节点-{_change_label(nc.change_type)}", "", nc.node_name, "", fc.field_name, fc.old_value, fc.new_value])
            else:
                rows.append([f"节点-{_change_label(nc.change_type)}", "", nc.node_name, "", "", "", ""])

        # 新增报文
        for mc in result.added_messages:
            msg = mc.new_message
            rows.append([f"报文-新增", mc.can_id_hex, mc.msg_name, "", "DLC", "", msg.dlc])
            rows.append([f"报文-新增", mc.can_id_hex, mc.msg_name, "", "发送节点", "", msg.sender])
            for sig_name, sig in sorted(msg.signals.items()):
                rows.append([f"信号-新增", mc.can_id_hex, mc.msg_name, sig_name,
                              "定义", "",
                              f"起始位={sig.start_bit},长度={sig.length},字节序={_byte_order_str(sig.byte_order)},因子={sig.factor},偏移={sig.offset},单位={sig.unit}"])

        # 删除报文
        for mc in result.removed_messages:
            msg = mc.old_message
            rows.append([f"报文-删除", mc.can_id_hex, mc.msg_name, "", "DLC", msg.dlc, ""])
            for sig_name in sorted(msg.signals.keys()):
                rows.append([f"信号-删除", mc.can_id_hex, mc.msg_name, sig_name, "", "", ""])

        # 报文ID变更
        for ic in result.message_id_changes:
            rows.append(["报文ID变更", ic.old_id_hex, ic.msg_name, "", "新ID", ic.old_id_hex, ic.new_id_hex])

        # 修改报文
        for mc in result.modified_messages:
            for fc in mc.field_changes:
                rows.append(["报文-修改(字段)", mc.can_id_hex, mc.msg_name, "", fc.field_name, fc.old_value, fc.new_value])
            for fc in mc.attr_changes:
                rows.append(["报文-修改(属性)", mc.can_id_hex, mc.msg_name, "", fc.field_name, fc.old_value, fc.new_value])
            for sc in mc.signal_changes:
                if sc.change_type == ChangeType.ADDED:
                    sig = sc.new_signal
                    rows.append([f"信号-新增", mc.can_id_hex, mc.msg_name, sc.signal_name,
                                  "定义", "",
                                  f"起始位={sig.start_bit},长度={sig.length},字节序={_byte_order_str(sig.byte_order)},因子={sig.factor},偏移={sig.offset}"])
                elif sc.change_type == ChangeType.REMOVED:
                    rows.append([f"信号-删除", mc.can_id_hex, mc.msg_name, sc.signal_name, "", "", ""])
                elif sc.change_type == ChangeType.MODIFIED:
                    for fc in sc.field_changes:
                        rows.append([f"信号-修改", mc.can_id_hex, mc.msg_name, sc.signal_name,
                                      fc.field_name, fc.old_value, fc.new_value])

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"[CSVReporter] 报告已保存: {filepath}")


# ---------------------------------------------
# JSON 报告
# ---------------------------------------------

class JSONReporter:
    """生成JSON格式差异报告（适合程序化处理）"""

    def generate(self, result: DBCDiffResult) -> dict:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "generated_at": now,
            "old_file": result.old_file,
            "new_file": result.new_file,
            "stats": result.stats(),
            "node_changes": [],
            "message_id_changes": [],
            "message_changes": []
        }

        for nc in result.node_changes:
            data["node_changes"].append({
                "type": nc.change_type,
                "node_name": nc.node_name,
                "field_changes": [{"field": fc.field_name, "old": str(fc.old_value), "new": str(fc.new_value)}
                                   for fc in nc.field_changes]
            })

        for ic in result.message_id_changes:
            data["message_id_changes"].append({
                "msg_name": ic.msg_name,
                "old_id": ic.old_id_hex,
                "new_id": ic.new_id_hex,
            })

        for mc in result.message_changes:
            mc_data = {
                "type": mc.change_type,
                "msg_id": mc.msg_id,
                "can_id_hex": mc.can_id_hex,
                "msg_name": mc.msg_name,
                "field_changes": [{"field": fc.field_name, "old": str(fc.old_value), "new": str(fc.new_value)}
                                   for fc in mc.field_changes],
                "attr_changes": [{"field": fc.field_name, "old": str(fc.old_value), "new": str(fc.new_value)}
                                  for fc in mc.attr_changes],
                "signal_changes": []
            }
            for sc in mc.signal_changes:
                sc_data = {
                    "type": sc.change_type,
                    "signal_name": sc.signal_name,
                    "field_changes": [{"field": fc.field_name, "old": str(fc.old_value), "new": str(fc.new_value)}
                                      for fc in sc.field_changes]
                }
                if sc.new_signal:
                    sig = sc.new_signal
                    sc_data["new_signal"] = {
                        "start_bit": sig.start_bit, "length": sig.length,
                        "byte_order": _byte_order_str(sig.byte_order),
                        "value_type": _value_type_str(sig.value_type),
                        "factor": sig.factor, "offset": sig.offset,
                        "min": sig.min_val, "max": sig.max_val,
                        "unit": sig.unit, "receivers": sig.receivers
                    }
                mc_data["signal_changes"].append(sc_data)
            data["message_changes"].append(mc_data)

        return data

    def save(self, result: DBCDiffResult, filepath: str):
        data = self.generate(result)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[JSONReporter] 报告已保存: {filepath}")


# ---------------------------------------------
# DBC文件内容摘要报告（单文件分析）
# ---------------------------------------------

class DBCSummaryReporter:
    """生成单个DBC文件的内容摘要报告"""

    def generate(self, dbc: DBCFile) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  DBC 文件内容摘要")
        lines.append(f"  文件: {os.path.basename(dbc.source_file)}")
        lines.append(f"  版本: {dbc.version or '(未指定)'}")
        lines.append(f"  波特率: {dbc.baudrate or '(未指定)'}")
        lines.append("=" * 70)

        # 节点
        lines.append(f"\n【网络节点】共 {len(dbc.nodes)} 个")
        for name, node in sorted(dbc.nodes.items()):
            comment = f"  # {node.comment}" if node.comment else ""
            lines.append(f"  - {name}{comment}")

        # 报文统计
        lines.append(f"\n【报文列表】共 {len(dbc.messages)} 条")
        for msg_id, msg in sorted(dbc.messages.items(), key=lambda x: x[1].can_id):
            frame_type = "扩展帧" if msg.is_extended else "标准帧"
            lines.append(f"  {msg.can_id_hex:>8}  {msg.name:<40} DLC={msg.dlc}  "
                         f"发送={msg.sender:<15} 信号数={len(msg.signals)}  [{frame_type}]")

        # 信号统计
        total_sigs = sum(len(m.signals) for m in dbc.messages.values())
        lines.append(f"\n【信号统计】共 {total_sigs} 个信号")

        # 按发送节点统计
        sender_stats: dict = {}
        for msg in dbc.messages.values():
            sender_stats[msg.sender] = sender_stats.get(msg.sender, 0) + 1
        lines.append("\n【发送节点报文数统计】")
        for sender, count in sorted(sender_stats.items(), key=lambda x: -x[1]):
            lines.append(f"  {sender:<20} {count} 条报文")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def print(self, dbc: DBCFile):
        print(self.generate(dbc))
