"""
LDF报告生成模块 - ldf_report.py
支持 Text / Markdown / HTML / CSV / JSON 五种格式输出
以及批量摘要报告 LDFSummaryReporter
"""

import json
import csv
import io
from datetime import datetime
from typing import List, Optional

from ldf_parser import LDFFile
from ldf_diff import (
    LDFDiffResult, ChangeType,
    LDFNodeChange, LDFFrameChange, LDFSignalChange,
    LDFScheduleChange, LDFEncodingChange, LDFNodeAttrChange,
)


# ---------------------------------------------
# 工具函数
# ---------------------------------------------

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _change_icon(ct: str) -> str:
    return {"ADDED": "+", "REMOVED": "-", "MODIFIED": "~"}.get(ct, "?")


def _change_label(ct: str) -> str:
    return {"ADDED": "新增", "REMOVED": "删除", "MODIFIED": "修改"}.get(ct, ct)


# ---------------------------------------------
# 文本报告
# ---------------------------------------------

class LDFTextReporter:
    """纯文本格式报告"""

    def generate(self, result: LDFDiffResult) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("LDF 差异分析报告")
        lines.append(f"生成时间: {_now()}")
        lines.append(f"旧文件: {result.old_file}")
        lines.append(f"新文件: {result.new_file}")
        lines.append("=" * 70)

        if not result.has_changes():
            lines.append("\n[PASS] 两个LDF文件内容完全相同，无任何差异。")
            return "\n".join(lines)

        stats = result.stats()
        lines.append("\n【变更统计】")
        lines.append(f"  节点变更:     +{stats['nodes_added']} -{stats['nodes_removed']} ~{stats['nodes_modified']}")
        lines.append(f"  节点属性变更: +{stats['node_attrs_added']} -{stats['node_attrs_removed']} ~{stats['node_attrs_modified']}")
        lines.append(f"  帧变更:       +{stats['frames_added']} -{stats['frames_removed']} ~{stats['frames_modified']}")
        lines.append(f"  信号变更:     +{stats['signals_added']} -{stats['signals_removed']} ~{stats['signals_modified']}")
        lines.append(f"  调度表:       +{stats['schedules_added']} -{stats['schedules_removed']} ~{stats['schedules_modified']}")

        # 节点变更
        if result.node_changes:
            lines.append("\n" + "-" * 50)
            lines.append("【节点变更】")
            for nc in result.node_changes:
                lines.append(f"  [{_change_icon(nc.change_type)}] {nc.summary()}")
                for fc in nc.field_changes:
                    lines.append(f"      {fc.field_name}: {fc.old_value!r} -> {fc.new_value!r}")

        # 节点属性变更
        if result.node_attr_changes:
            lines.append("\n" + "-" * 50)
            lines.append("【节点属性变更（Node_attributes）】")
            for ac in result.node_attr_changes:
                lines.append(f"  [{_change_icon(ac.change_type)}] {ac.summary()}")
                if ac.change_type == ChangeType.MODIFIED:
                    for fc in ac.field_changes:
                        lines.append(f"      {fc.field_name}: {fc.old_value!r} -> {fc.new_value!r}")
                    for fname in ac.frames_added:
                        lines.append(f"      [+] 新增可配置帧: {fname}")
                    for fname in ac.frames_removed:
                        lines.append(f"      [-] 删除可配置帧: {fname}")
                    for fc in ac.frames_id_changed:
                        lines.append(f"      [~] 帧 {fc.field_name} ID: {fc.old_value} -> {fc.new_value}")

        # 帧变更
        if result.frame_changes:
            lines.append("\n" + "-" * 50)
            lines.append("【帧变更】")
            for fc in result.frame_changes:
                lines.append(f"  [{_change_icon(fc.change_type)}] {fc.summary()}")
                if fc.change_type == ChangeType.MODIFIED:
                    for fld in fc.field_changes:
                        lines.append(f"      属性 {fld.field_name}: {fld.old_value!r} -> {fld.new_value!r}")
                    for sname in fc.signal_added:
                        lines.append(f"      [+] 新增信号: {sname}")
                    for sname in fc.signal_removed:
                        lines.append(f"      [-] 删除信号: {sname}")
                    for pc in fc.signal_pos_changes:
                        lines.append(f"      [~] {pc.summary()}")

        # 信号变更
        if result.signal_changes:
            lines.append("\n" + "-" * 50)
            lines.append("【信号变更】")
            for sc in result.signal_changes:
                lines.append(f"  [{_change_icon(sc.change_type)}] {sc.summary()}")
                if sc.change_type == ChangeType.MODIFIED:
                    for fld in sc.field_changes:
                        lines.append(f"      {fld.field_name}: {fld.old_value!r} -> {fld.new_value!r}")

        # 调度表变更
        if result.schedule_changes:
            lines.append("\n" + "-" * 50)
            lines.append("【调度表变更】")
            for sc in result.schedule_changes:
                lines.append(f"  [{_change_icon(sc.change_type)}] {sc.summary()}")
                if sc.change_type == ChangeType.MODIFIED:
                    for fname in sc.entries_added:
                        lines.append(f"      [+] 新增条目: {fname}")
                    for fname in sc.entries_removed:
                        lines.append(f"      [-] 删除条目: {fname}")
                    for fld in sc.entries_modified:
                        lines.append(f"      [~] {fld.field_name}: {fld.old_value!r}ms -> {fld.new_value!r}ms")
                    for oc in sc.entries_reordered:
                        lines.append(f"      [<>] {oc.summary()}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def save(self, result: LDFDiffResult, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate(result))


# ---------------------------------------------
# Markdown 报告
# ---------------------------------------------

class LDFMarkdownReporter:
    """Markdown格式报告"""

    def generate(self, result: LDFDiffResult) -> str:
        lines = []
        lines.append("# LDF 差异分析报告")
        lines.append(f"\n> 生成时间: {_now()}")
        lines.append(f"\n| 项目 | 内容 |")
        lines.append("|------|------|")
        lines.append(f"| 旧文件 | `{result.old_file}` |")
        lines.append(f"| 新文件 | `{result.new_file}` |")

        if not result.has_changes():
            lines.append("\n## [PASS] 无差异\n\n两个LDF文件内容完全相同。")
            return "\n".join(lines)

        stats = result.stats()
        lines.append("\n## 变更统计\n")
        lines.append("| 类别 | 新增 | 删除 | 修改 |")
        lines.append("|------|------|------|------|")
        lines.append(f"| 节点 | {stats['nodes_added']} | {stats['nodes_removed']} | {stats['nodes_modified']} |")
        lines.append(f"| 节点属性 | {stats['node_attrs_added']} | {stats['node_attrs_removed']} | {stats['node_attrs_modified']} |")
        lines.append(f"| 帧   | {stats['frames_added']} | {stats['frames_removed']} | {stats['frames_modified']} |")
        lines.append(f"| 信号 | {stats['signals_added']} | {stats['signals_removed']} | {stats['signals_modified']} |")
        lines.append(f"| 调度表 | {stats['schedules_added']} | {stats['schedules_removed']} | {stats['schedules_modified']} |")

        # 节点变更
        if result.node_changes:
            lines.append("\n## 节点变更\n")
            for nc in result.node_changes:
                icon = {"ADDED": "🟢", "REMOVED": "🔴", "MODIFIED": "🟡"}.get(nc.change_type, "⚪")
                lines.append(f"- {icon} **{nc.summary()}**")
                for fc in nc.field_changes:
                    lines.append(f"  - `{fc.field_name}`: `{fc.old_value}` -> `{fc.new_value}`")

        # 节点属性变更
        if result.node_attr_changes:
            lines.append("\n## 节点属性变更（Node_attributes）\n")
            for ac in result.node_attr_changes:
                icon = {"ADDED": "🟢", "REMOVED": "🔴", "MODIFIED": "🟡"}.get(ac.change_type, "⚪")
                lines.append(f"### {icon} {ac.node_name} `[{_change_label(ac.change_type)}]`")
                if ac.change_type == ChangeType.MODIFIED:
                    for fc in ac.field_changes:
                        lines.append(f"- **{fc.field_name}**: `{fc.old_value}` -> `{fc.new_value}`")
                    for fname in ac.frames_added:
                        lines.append(f"- 🟢 新增可配置帧: `{fname}`")
                    for fname in ac.frames_removed:
                        lines.append(f"- 🔴 删除可配置帧: `{fname}`")
                    for fc in ac.frames_id_changed:
                        lines.append(f"- 🟡 帧 `{fc.field_name}` ID: `{fc.old_value}` -> `{fc.new_value}`")

        # 帧变更
        if result.frame_changes:
            lines.append("\n## 帧变更\n")
            for fc in result.frame_changes:
                icon = {"ADDED": "🟢", "REMOVED": "🔴", "MODIFIED": "🟡"}.get(fc.change_type, "⚪")
                lines.append(f"### {icon} {fc.frame_name} `[{_change_label(fc.change_type)}]`")
                if fc.change_type == ChangeType.ADDED and fc.new_frame:
                    f = fc.new_frame
                    lines.append(f"- 帧ID: `0x{f.frame_id:02X}` ({f.frame_id})")
                    lines.append(f"- 发布节点: `{f.publisher}`")
                    lines.append(f"- 帧长度: `{f.length}` 字节")
                    if f.signals:
                        lines.append(f"- 信号列表: {', '.join(s.signal_name for s in f.signals)}")
                elif fc.change_type == ChangeType.REMOVED and fc.old_frame:
                    f = fc.old_frame
                    lines.append(f"- 帧ID: `0x{f.frame_id:02X}` ({f.frame_id})")
                    lines.append(f"- 发布节点: `{f.publisher}`")
                elif fc.change_type == ChangeType.MODIFIED:
                    for fld in fc.field_changes:
                        lines.append(f"- **{fld.field_name}**: `{fld.old_value}` -> `{fld.new_value}`")
                    for sname in fc.signal_added:
                        lines.append(f"- 🟢 新增信号: `{sname}`")
                    for sname in fc.signal_removed:
                        lines.append(f"- 🔴 删除信号: `{sname}`")
                    for pc in fc.signal_pos_changes:
                        lines.append(f"- 🟡 `{pc.signal_name}` 起始位: `{pc.old_start_bit}` -> `{pc.new_start_bit}`")

        # 信号变更
        if result.signal_changes:
            lines.append("\n## 信号变更\n")
            lines.append("| 变更类型 | 所属帧 | 信号名 | 变更详情 |")
            lines.append("|----------|--------|--------|----------|")
            for sc in result.signal_changes:
                icon = {"ADDED": "🟢新增", "REMOVED": "🔴删除", "MODIFIED": "🟡修改"}.get(sc.change_type, sc.change_type)
                detail = ""
                if sc.change_type == ChangeType.MODIFIED:
                    detail = "; ".join(
                        f"{c.field_name}: `{c.old_value}`->`{c.new_value}`"
                        for c in sc.field_changes
                    )
                elif sc.change_type == ChangeType.ADDED and sc.new_signal:
                    s = sc.new_signal
                    detail = f"长度:{s.length}bit, 初始值:{s.init_value}, 发布:{s.publisher}"
                elif sc.change_type == ChangeType.REMOVED and sc.old_signal:
                    s = sc.old_signal
                    detail = f"长度:{s.length}bit, 发布:{s.publisher}"
                lines.append(f"| {icon} | {sc.frame_name} | `{sc.signal_name}` | {detail} |")

        # 调度表变更
        if result.schedule_changes:
            lines.append("\n## 调度表变更\n")
            for sc in result.schedule_changes:
                icon = {"ADDED": "🟢", "REMOVED": "🔴", "MODIFIED": "🟡"}.get(sc.change_type, "⚪")
                lines.append(f"### {icon} {sc.table_name} `[{_change_label(sc.change_type)}]`")
                if sc.change_type == ChangeType.MODIFIED:
                    for fname in sc.entries_added:
                        lines.append(f"- 🟢 新增条目: `{fname}`")
                    for fname in sc.entries_removed:
                        lines.append(f"- 🔴 删除条目: `{fname}`")
                    for fld in sc.entries_modified:
                        lines.append(f"- 🟡 `{fld.field_name}`: `{fld.old_value}ms` -> `{fld.new_value}ms`")
                    for oc in sc.entries_reordered:
                        lines.append(f"- <> `{oc.frame_name}`: 第{oc.old_index+1}位 -> 第{oc.new_index+1}位")

        return "\n".join(lines)

    def save(self, result: LDFDiffResult, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate(result))


# ---------------------------------------------
# HTML 报告
# ---------------------------------------------

class LDFHTMLReporter:
    """HTML格式报告（带样式）"""

    _CSS = """
    body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }
    h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
    h2 { color: #34495e; border-left: 4px solid #3498db; padding-left: 10px; margin-top: 30px; }
    h3 { color: #555; margin-top: 15px; }
    .meta { background: #ecf0f1; padding: 12px; border-radius: 6px; margin-bottom: 20px; }
    .meta table { border-collapse: collapse; }
    .meta td { padding: 4px 12px; }
    .stats { display: flex; gap: 12px; flex-wrap: wrap; margin: 15px 0; }
    .stat-card { background: white; border-radius: 8px; padding: 12px 20px;
                 box-shadow: 0 2px 6px rgba(0,0,0,0.1); min-width: 120px; text-align: center; }
    .stat-card .label { font-size: 12px; color: #888; }
    .stat-card .value { font-size: 22px; font-weight: bold; color: #2c3e50; }
    table.diff { width: 100%; border-collapse: collapse; margin: 10px 0; background: white;
                 box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-radius: 6px; overflow: hidden; }
    table.diff th { background: #3498db; color: white; padding: 8px 12px; text-align: left; }
    table.diff td { padding: 7px 12px; border-bottom: 1px solid #eee; vertical-align: top; }
    table.diff tr:last-child td { border-bottom: none; }
    .added    { background: #e8f8e8; color: #27ae60; }
    .removed  { background: #fde8e8; color: #e74c3c; }
    .modified { background: #fef9e7; color: #f39c12; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
             font-size: 12px; font-weight: bold; }
    .badge-add  { background: #27ae60; color: white; }
    .badge-del  { background: #e74c3c; color: white; }
    .badge-mod  { background: #f39c12; color: white; }
    .no-change  { color: #27ae60; font-size: 16px; padding: 20px; }
    code { background: #f0f0f0; padding: 1px 5px; border-radius: 3px; font-size: 13px; }
    .section { background: white; border-radius: 8px; padding: 16px 20px;
               box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 20px; }
    """

    def generate(self, result: LDFDiffResult) -> str:
        parts = []
        parts.append(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>LDF差异分析报告</title>
<style>{self._CSS}</style>
</head>
<body>
<h1>📋 LDF 差异分析报告</h1>
<div class="meta">
  <table>
    <tr><td><b>生成时间</b></td><td>{_now()}</td></tr>
    <tr><td><b>旧文件</b></td><td><code>{result.old_file}</code></td></tr>
    <tr><td><b>新文件</b></td><td><code>{result.new_file}</code></td></tr>
  </table>
</div>""")

        if not result.has_changes():
            parts.append('<p class="no-change">[PASS] 两个LDF文件内容完全相同，无任何差异。</p>')
            parts.append("</body></html>")
            return "\n".join(parts)

        stats = result.stats()
        parts.append('<h2>变更统计</h2><div class="stats">')
        stat_items = [
            ("节点新增", stats["nodes_added"], "add"),
            ("节点删除", stats["nodes_removed"], "del"),
            ("帧新增",   stats["frames_added"], "add"),
            ("帧删除",   stats["frames_removed"], "del"),
            ("帧修改",   stats["frames_modified"], "mod"),
            ("信号新增", stats["signals_added"], "add"),
            ("信号删除", stats["signals_removed"], "del"),
            ("信号修改", stats["signals_modified"], "mod"),
        ]
        for label, val, kind in stat_items:
            color = {"add": "#27ae60", "del": "#e74c3c", "mod": "#f39c12"}.get(kind, "#555")
            parts.append(f'<div class="stat-card"><div class="label">{label}</div>'
                         f'<div class="value" style="color:{color}">{val}</div></div>')
        parts.append("</div>")

        # 节点变更
        if result.node_changes:
            parts.append('<h2>节点变更</h2><div class="section">')
            parts.append('<table class="diff"><tr><th>类型</th><th>节点名</th><th>角色</th><th>变更详情</th></tr>')
            for nc in result.node_changes:
                cls = nc.change_type.lower()
                badge = {"ADDED": '<span class="badge badge-add">新增</span>',
                         "REMOVED": '<span class="badge badge-del">删除</span>',
                         "MODIFIED": '<span class="badge badge-mod">修改</span>'}.get(nc.change_type, nc.change_type)
                role = "主节点" if nc.is_master else "从节点"
                detail = ""
                if nc.field_changes:
                    detail = "<br>".join(
                        f"<code>{fc.field_name}</code>: {fc.old_value!r} -> {fc.new_value!r}"
                        for fc in nc.field_changes
                    )
                parts.append(f'<tr class="{cls}"><td>{badge}</td><td><b>{nc.node_name}</b></td>'
                             f'<td>{role}</td><td>{detail}</td></tr>')
            parts.append("</table></div>")

        # 节点属性变更
        if result.node_attr_changes:
            parts.append('<h2>节点属性变更（Node_attributes）</h2><div class="section">')
            parts.append('<table class="diff"><tr><th>类型</th><th>节点名</th><th>变更详情</th></tr>')
            for ac in result.node_attr_changes:
                cls = ac.change_type.lower()
                badge = {"ADDED": '<span class="badge badge-add">新增</span>',
                         "REMOVED": '<span class="badge badge-del">删除</span>',
                         "MODIFIED": '<span class="badge badge-mod">修改</span>'}.get(ac.change_type, ac.change_type)
                detail_parts = []
                if ac.change_type == ChangeType.MODIFIED:
                    for fc in ac.field_changes:
                        detail_parts.append(f"<code>{fc.field_name}</code>: {fc.old_value!r}->{fc.new_value!r}")
                    for fname in ac.frames_added:
                        detail_parts.append(f'<span style="color:#27ae60">+可配置帧:{fname}</span>')
                    for fname in ac.frames_removed:
                        detail_parts.append(f'<span style="color:#e74c3c">-可配置帧:{fname}</span>')
                    for fc in ac.frames_id_changed:
                        detail_parts.append(f"帧<code>{fc.field_name}</code>ID:{fc.old_value}->{fc.new_value}")
                detail = "<br>".join(detail_parts)
                parts.append(f'<tr class="{cls}"><td>{badge}</td><td><b>{ac.node_name}</b></td>'
                             f'<td>{detail}</td></tr>')
            parts.append("</table></div>")

        # 帧变更
        if result.frame_changes:
            parts.append('<h2>帧变更</h2><div class="section">')
            parts.append('<table class="diff"><tr><th>类型</th><th>帧名</th><th>帧ID</th><th>变更详情</th></tr>')
            for fc in result.frame_changes:
                cls = fc.change_type.lower()
                badge = {"ADDED": '<span class="badge badge-add">新增</span>',
                         "REMOVED": '<span class="badge badge-del">删除</span>',
                         "MODIFIED": '<span class="badge badge-mod">修改</span>'}.get(fc.change_type, fc.change_type)
                frame_id_str = ""
                detail_parts = []
                if fc.change_type == ChangeType.ADDED and fc.new_frame:
                    frame_id_str = f"0x{fc.new_frame.frame_id:02X}"
                    detail_parts.append(f"发布:{fc.new_frame.publisher}, 长度:{fc.new_frame.length}B")
                    if fc.new_frame.signals:
                        sigs = ", ".join(s.signal_name for s in fc.new_frame.signals)
                        detail_parts.append(f"信号: {sigs}")
                elif fc.change_type == ChangeType.REMOVED and fc.old_frame:
                    frame_id_str = f"0x{fc.old_frame.frame_id:02X}"
                elif fc.change_type == ChangeType.MODIFIED:
                    if fc.old_frame:
                        frame_id_str = f"0x{fc.old_frame.frame_id:02X}"
                    for fld in fc.field_changes:
                        detail_parts.append(f"<code>{fld.field_name}</code>: {fld.old_value!r}->{fld.new_value!r}")
                    for sname in fc.signal_added:
                        detail_parts.append(f'<span style="color:#27ae60">+信号:{sname}</span>')
                    for sname in fc.signal_removed:
                        detail_parts.append(f'<span style="color:#e74c3c">-信号:{sname}</span>')
                    for pc in fc.signal_pos_changes:
                        detail_parts.append(f"<code>{pc.signal_name}</code>起始位:{pc.old_start_bit}->{pc.new_start_bit}")
                detail = "<br>".join(detail_parts)
                parts.append(f'<tr class="{cls}"><td>{badge}</td><td><b>{fc.frame_name}</b></td>'
                             f'<td><code>{frame_id_str}</code></td><td>{detail}</td></tr>')
            parts.append("</table></div>")

        # 信号变更
        if result.signal_changes:
            parts.append('<h2>信号变更</h2><div class="section">')
            parts.append('<table class="diff"><tr><th>类型</th><th>所属帧</th><th>信号名</th>'
                         '<th>位长度</th><th>发布节点</th><th>变更详情</th></tr>')
            for sc in result.signal_changes:
                cls = sc.change_type.lower()
                badge = {"ADDED": '<span class="badge badge-add">新增</span>',
                         "REMOVED": '<span class="badge badge-del">删除</span>',
                         "MODIFIED": '<span class="badge badge-mod">修改</span>'}.get(sc.change_type, sc.change_type)
                sig = sc.new_signal or sc.old_signal
                length_str = str(sig.length) if sig else ""
                pub_str = sig.publisher if sig else ""
                detail = ""
                if sc.change_type == ChangeType.MODIFIED:
                    detail = "<br>".join(
                        f"<code>{c.field_name}</code>: {c.old_value!r}->{c.new_value!r}"
                        for c in sc.field_changes
                    )
                parts.append(f'<tr class="{cls}"><td>{badge}</td><td>{sc.frame_name}</td>'
                             f'<td><b>{sc.signal_name}</b></td><td>{length_str}</td>'
                             f'<td>{pub_str}</td><td>{detail}</td></tr>')
            parts.append("</table></div>")

        # 调度表变更
        if result.schedule_changes:
            parts.append('<h2>调度表变更</h2><div class="section">')
            parts.append('<table class="diff"><tr><th>类型</th><th>调度表名</th><th>变更详情</th></tr>')
            for sc in result.schedule_changes:
                cls = sc.change_type.lower()
                badge = {"ADDED": '<span class="badge badge-add">新增</span>',
                         "REMOVED": '<span class="badge badge-del">删除</span>',
                         "MODIFIED": '<span class="badge badge-mod">修改</span>'}.get(sc.change_type, sc.change_type)
                detail_parts = []
                if sc.change_type == ChangeType.MODIFIED:
                    for fname in sc.entries_added:
                        detail_parts.append(f'<span style="color:#27ae60">+{fname}</span>')
                    for fname in sc.entries_removed:
                        detail_parts.append(f'<span style="color:#e74c3c">-{fname}</span>')
                    for fld in sc.entries_modified:
                        detail_parts.append(f"<code>{fld.field_name}</code>: {fld.old_value}ms->{fld.new_value}ms")
                    for oc in sc.entries_reordered:
                        detail_parts.append(f'<span style="color:#8e44ad"><>{oc.frame_name}: 第{oc.old_index+1}->第{oc.new_index+1}位</span>')
                detail = "<br>".join(detail_parts)
                parts.append(f'<tr class="{cls}"><td>{badge}</td><td><b>{sc.table_name}</b></td>'
                             f'<td>{detail}</td></tr>')
            parts.append("</table></div>")

        parts.append("</body></html>")
        return "\n".join(parts)

    def save(self, result: LDFDiffResult, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate(result))


# ---------------------------------------------
# CSV 报告
# ---------------------------------------------

class LDFCSVReporter:
    """CSV格式报告（扁平化，便于Excel分析）"""

    def generate(self, result: LDFDiffResult) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["变更类别", "变更类型", "名称1", "名称2", "字段", "旧值", "新值"])

        # 节点
        for nc in result.node_changes:
            role = "主节点" if nc.is_master else "从节点"
            if nc.field_changes:
                for fc in nc.field_changes:
                    writer.writerow(["节点", _change_label(nc.change_type),
                                     role, nc.node_name, fc.field_name, fc.old_value, fc.new_value])
            else:
                writer.writerow(["节点", _change_label(nc.change_type),
                                 role, nc.node_name, "", "", ""])

        # 帧
        for fc in result.frame_changes:
            if fc.field_changes:
                for fld in fc.field_changes:
                    writer.writerow(["帧", _change_label(fc.change_type),
                                     fc.frame_name, "", fld.field_name, fld.old_value, fld.new_value])
            elif fc.signal_added or fc.signal_removed or fc.signal_pos_changes:
                for sname in fc.signal_added:
                    writer.writerow(["帧", _change_label(fc.change_type),
                                     fc.frame_name, sname, "新增信号", "", ""])
                for sname in fc.signal_removed:
                    writer.writerow(["帧", _change_label(fc.change_type),
                                     fc.frame_name, sname, "删除信号", "", ""])
                for pc in fc.signal_pos_changes:
                    writer.writerow(["帧", _change_label(fc.change_type),
                                     fc.frame_name, pc.signal_name, "起始位",
                                     pc.old_start_bit, pc.new_start_bit])
            else:
                writer.writerow(["帧", _change_label(fc.change_type),
                                 fc.frame_name, "", "", "", ""])

        # 信号
        for sc in result.signal_changes:
            if sc.field_changes:
                for fld in sc.field_changes:
                    writer.writerow(["信号", _change_label(sc.change_type),
                                     sc.frame_name, sc.signal_name,
                                     fld.field_name, fld.old_value, fld.new_value])
            else:
                sig = sc.new_signal or sc.old_signal
                length = sig.length if sig else ""
                pub = sig.publisher if sig else ""
                writer.writerow(["信号", _change_label(sc.change_type),
                                 sc.frame_name, sc.signal_name, "位长度/发布节点",
                                 f"{length}/{pub}", ""])

        # 节点属性
        for ac in result.node_attr_changes:
            if ac.field_changes:
                for fc in ac.field_changes:
                    writer.writerow(["节点属性", _change_label(ac.change_type),
                                     ac.node_name, "", fc.field_name, fc.old_value, fc.new_value])
            elif ac.frames_added or ac.frames_removed or ac.frames_id_changed:
                for fname in ac.frames_added:
                    writer.writerow(["节点属性", _change_label(ac.change_type),
                                     ac.node_name, fname, "新增可配置帧", "", ""])
                for fname in ac.frames_removed:
                    writer.writerow(["节点属性", _change_label(ac.change_type),
                                     ac.node_name, fname, "删除可配置帧", "", ""])
                for fc in ac.frames_id_changed:
                    writer.writerow(["节点属性", _change_label(ac.change_type),
                                     ac.node_name, fc.field_name, "帧ID", fc.old_value, fc.new_value])
            else:
                writer.writerow(["节点属性", _change_label(ac.change_type),
                                 ac.node_name, "", "", "", ""])

        # 调度表
        for sc in result.schedule_changes:
            if sc.entries_added or sc.entries_removed or sc.entries_modified or sc.entries_reordered:
                for fname in sc.entries_added:
                    writer.writerow(["调度表", _change_label(sc.change_type),
                                     sc.table_name, fname, "新增条目", "", ""])
                for fname in sc.entries_removed:
                    writer.writerow(["调度表", _change_label(sc.change_type),
                                     sc.table_name, fname, "删除条目", "", ""])
                for fld in sc.entries_modified:
                    writer.writerow(["调度表", _change_label(sc.change_type),
                                     sc.table_name, fld.field_name, "延迟(ms)",
                                     fld.old_value, fld.new_value])
                for oc in sc.entries_reordered:
                    writer.writerow(["调度表", _change_label(sc.change_type),
                                     sc.table_name, oc.frame_name, "顺序",
                                     f"第{oc.old_index+1}位", f"第{oc.new_index+1}位"])
            else:
                writer.writerow(["调度表", _change_label(sc.change_type),
                                 sc.table_name, "", "", "", ""])

        return output.getvalue()

    def save(self, result: LDFDiffResult, filepath: str):
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            f.write(self.generate(result))


# ---------------------------------------------
# JSON 报告
# ---------------------------------------------

class LDFJSONReporter:
    """JSON格式报告（结构化，便于程序处理）"""

    def generate(self, result: LDFDiffResult) -> str:
        data = {
            "meta": {
                "generated_at": _now(),
                "old_file": result.old_file,
                "new_file": result.new_file,
                "has_changes": result.has_changes(),
            },
            "stats": result.stats(),
            "node_changes": [self._node_change(nc) for nc in result.node_changes],
            "node_attr_changes": [self._node_attr_change(ac) for ac in result.node_attr_changes],
            "frame_changes": [self._frame_change(fc) for fc in result.frame_changes],
            "signal_changes": [self._signal_change(sc) for sc in result.signal_changes],
            "schedule_changes": [self._schedule_change(sc) for sc in result.schedule_changes],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _node_change(self, nc: LDFNodeChange) -> dict:
        return {
            "change_type": nc.change_type,
            "node_name": nc.node_name,
            "is_master": nc.is_master,
            "field_changes": [{"field": fc.field_name, "old": str(fc.old_value), "new": str(fc.new_value)}
                               for fc in nc.field_changes],
        }

    def _node_attr_change(self, ac: LDFNodeAttrChange) -> dict:
        return {
            "change_type": ac.change_type,
            "node_name": ac.node_name,
            "field_changes": [{"field": fc.field_name, "old": str(fc.old_value), "new": str(fc.new_value)}
                               for fc in ac.field_changes],
            "frames_added": ac.frames_added,
            "frames_removed": ac.frames_removed,
            "frames_id_changed": [{"frame": fc.field_name, "old_id": str(fc.old_value), "new_id": str(fc.new_value)}
                                   for fc in ac.frames_id_changed],
        }

    def _frame_change(self, fc: LDFFrameChange) -> dict:
        d = {
            "change_type": fc.change_type,
            "frame_name": fc.frame_name,
            "field_changes": [{"field": f.field_name, "old": str(f.old_value), "new": str(f.new_value)}
                               for f in fc.field_changes],
            "signals_added": fc.signal_added,
            "signals_removed": fc.signal_removed,
            "signal_pos_changes": [{"signal": pc.signal_name,
                                    "old_start_bit": pc.old_start_bit,
                                    "new_start_bit": pc.new_start_bit}
                                   for pc in fc.signal_pos_changes],
        }
        if fc.new_frame:
            d["frame_id"] = fc.new_frame.frame_id
            d["publisher"] = fc.new_frame.publisher
            d["length"] = fc.new_frame.length
        elif fc.old_frame:
            d["frame_id"] = fc.old_frame.frame_id
            d["publisher"] = fc.old_frame.publisher
            d["length"] = fc.old_frame.length
        return d

    def _signal_change(self, sc: LDFSignalChange) -> dict:
        d = {
            "change_type": sc.change_type,
            "frame_name": sc.frame_name,
            "signal_name": sc.signal_name,
            "field_changes": [{"field": fc.field_name, "old": str(fc.old_value), "new": str(fc.new_value)}
                               for fc in sc.field_changes],
        }
        sig = sc.new_signal or sc.old_signal
        if sig:
            d["length"] = sig.length
            d["publisher"] = sig.publisher
            d["init_value"] = str(sig.init_value)
        return d

    def _schedule_change(self, sc: LDFScheduleChange) -> dict:
        return {
            "change_type": sc.change_type,
            "table_name": sc.table_name,
            "entries_added": sc.entries_added,
            "entries_removed": sc.entries_removed,
            "entries_modified": [{"frame": fc.field_name,
                                   "old_delay": fc.old_value,
                                   "new_delay": fc.new_value}
                                  for fc in sc.entries_modified],
            "entries_reordered": [{"frame": oc.frame_name,
                                    "old_index": oc.old_index,
                                    "new_index": oc.new_index}
                                   for oc in sc.entries_reordered],
        }

    def _encoding_change(self, ec: LDFEncodingChange) -> dict:
        return {
            "change_type": ec.change_type,
            "encoding_name": ec.encoding_name,
            "field_changes": [{"field": fc.field_name, "old": str(fc.old_value), "new": str(fc.new_value)}
                               for fc in ec.field_changes],
        }

    def save(self, result: LDFDiffResult, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate(result))


# ---------------------------------------------
# LDF文件信息报告（单文件）
# ---------------------------------------------

class LDFInfoReporter:
    """输出单个LDF文件的结构信息"""

    def generate(self, ldf: LDFFile) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append(f"LDF 文件信息: {ldf.source_file}")
        lines.append("=" * 60)
        lines.append(f"LIN协议版本: {ldf.lin_protocol_version}")
        lines.append(f"LIN语言版本: {ldf.lin_language_version}")
        lines.append(f"总线速率:    {ldf.lin_speed}")
        if ldf.channel_name:
            lines.append(f"通道名称:    {ldf.channel_name}")

        if ldf.master:
            lines.append(f"\n主节点: {ldf.master.name} "
                         f"(时基={ldf.master.time_base}ms, 抖动={ldf.master.jitter}ms)")
        if ldf.slaves:
            lines.append(f"从节点({len(ldf.slaves)}): {', '.join(ldf.slaves)}")

        lines.append(f"\n信号数量:     {len(ldf.signals)}")
        lines.append(f"帧数量:       {len(ldf.frames)}")
        lines.append(f"调度表数量:   {len(ldf.schedule_tables)}")
        lines.append(f"编码类型数量: {len(ldf.encoding_types)}")

        if ldf.frames:
            lines.append("\n【帧列表】")
            for fname, frame in sorted(ldf.frames.items()):
                sig_names = [s.signal_name for s in frame.signals]
                lines.append(f"  0x{frame.frame_id:02X} {frame.name} "
                             f"[{frame.length}B, 发布:{frame.publisher}] "
                             f"信号: {', '.join(sig_names)}")

        if ldf.schedule_tables:
            lines.append("\n【调度表】")
            for tname, table in sorted(ldf.schedule_tables.items()):
                lines.append(f"  {tname} ({len(table.entries)}条目)")

        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------
# 批量摘要报告
# ---------------------------------------------

class LDFSummaryReporter:
    """
    批量比较摘要报告
    输入: List[(channel_name, LDFDiffResult)]
    """

    def generate_text(self, results: List[tuple]) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("LDF 批量差异分析摘要报告")
        lines.append(f"生成时间: {_now()}")
        lines.append(f"共比较 {len(results)} 个LIN通道")
        lines.append("=" * 70)

        changed = [(ch, r) for ch, r in results if r.has_changes()]
        unchanged = [(ch, r) for ch, r in results if not r.has_changes()]

        lines.append(f"\n有变更: {len(changed)} 个通道")
        lines.append(f"无变更: {len(unchanged)} 个通道")

        if changed:
            lines.append("\n" + "-" * 50)
            lines.append("【有变更的通道】")
            for ch, r in changed:
                stats = r.stats()
                lines.append(f"\n  通道: {ch}")
                lines.append(f"    旧: {r.old_file}")
                lines.append(f"    新: {r.new_file}")
                lines.append(f"    节点: +{stats['nodes_added']} -{stats['nodes_removed']} ~{stats['nodes_modified']}")
                lines.append(f"    帧:   +{stats['frames_added']} -{stats['frames_removed']} ~{stats['frames_modified']}")
                lines.append(f"    信号: +{stats['signals_added']} -{stats['signals_removed']} ~{stats['signals_modified']}")

        if unchanged:
            lines.append("\n" + "-" * 50)
            lines.append("【无变更的通道】")
            for ch, r in unchanged:
                lines.append(f"  [PASS] {ch}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def generate_html(self, results: List[tuple]) -> str:
        from ldf_diff import ChangeType
        changed = [(ch, r) for ch, r in results if r.has_changes()]
        unchanged = [(ch, r) for ch, r in results if not r.has_changes()]

        # ---- 概览表格行 ----
        rows = []
        for ch, r in results:
            stats = r.stats()
            status = "有变更" if r.has_changes() else "无变更"
            status_style = "color:#e74c3c;font-weight:bold" if r.has_changes() else "color:#27ae60"
            anchor = f'<a href="#{ch}" style="color:inherit;text-decoration:none">{ch}</a>' if r.has_changes() else ch
            old_fname = r.old_file.replace('\\', '/').split('/')[-1]
            new_fname = r.new_file.replace('\\', '/').split('/')[-1]
            na = stats['nodes_added']; nr = stats['nodes_removed']; nm = stats['nodes_modified']
            fa = stats['frames_added']; fr = stats['frames_removed']; fm = stats['frames_modified']
            sa = stats['signals_added']; sr = stats['signals_removed']; sm = stats['signals_modified']
            sca = stats['schedules_added']; scr = stats['schedules_removed']; scm = stats['schedules_modified']
            rows.append(f"""<tr>
  <td>{anchor}</td>
  <td style="{status_style}">{status}</td>
  <td>{na}/{nr}/{nm}</td>
  <td>{fa}/{fr}/{fm}</td>
  <td>{sa}/{sr}/{sm}</td>
  <td>{sca}/{scr}/{scm}</td>
  <td style="font-size:12px;color:#888">{old_fname}</td>
  <td style="font-size:12px;color:#888">{new_fname}</td>
</tr>""")

        # ---- 每通道详细变更 ----
        def badge(ct):
            if ct == ChangeType.ADDED:   return '<span class="badge badge-add">新增</span>'
            if ct == ChangeType.REMOVED: return '<span class="badge badge-del">删除</span>'
            return '<span class="badge badge-mod">修改</span>'

        detail_sections = []
        for ch, r in changed:
            parts = [f'<div class="channel-block" id="{ch}">']
            parts.append(f'<h2>🔔 通道 {ch}</h2>')
            parts.append(f'<p style="color:#888;font-size:13px">旧: {r.old_file}<br>新: {r.new_file}</p>')

            # 节点变更
            if r.node_changes:
                parts.append('<h3>节点变更</h3>')
                parts.append('<table class="dtbl"><tr><th>类型</th><th>节点名</th><th>角色</th><th>变更详情</th></tr>')
                for nc in r.node_changes:
                    role = "主节点" if nc.is_master else "从节点"
                    detail = "<br>".join(f"<code>{fc.field_name}</code>: {fc.old_value!r} → {fc.new_value!r}" for fc in nc.field_changes)
                    parts.append(f'<tr class="{nc.change_type.lower()}"><td>{badge(nc.change_type)}</td><td><b>{nc.node_name}</b></td><td>{role}</td><td>{detail}</td></tr>')
                parts.append('</table>')

            # 帧变更
            if r.frame_changes:
                parts.append('<h3>帧变更</h3>')
                parts.append('<table class="dtbl"><tr><th>类型</th><th>帧名</th><th>帧ID</th><th>变更详情</th></tr>')
                for fc in r.frame_changes:
                    fid = ""
                    detail_parts = []
                    if fc.change_type == ChangeType.ADDED and fc.new_frame:
                        fid = f"0x{fc.new_frame.frame_id:02X}"
                        detail_parts.append(f"发布:{fc.new_frame.publisher}, 长度:{fc.new_frame.length}B")
                        if fc.new_frame.signals:
                            detail_parts.append("信号: " + ", ".join(s.signal_name for s in fc.new_frame.signals))
                    elif fc.change_type == ChangeType.REMOVED and fc.old_frame:
                        fid = f"0x{fc.old_frame.frame_id:02X}"
                    elif fc.change_type == ChangeType.MODIFIED:
                        if fc.old_frame: fid = f"0x{fc.old_frame.frame_id:02X}"
                        for fld in fc.field_changes:
                            detail_parts.append(f"<code>{fld.field_name}</code>: {fld.old_value!r} → {fld.new_value!r}")
                        for s in fc.signal_added:
                            detail_parts.append(f'<span style="color:#27ae60">+信号:{s}</span>')
                        for s in fc.signal_removed:
                            detail_parts.append(f'<span style="color:#e74c3c">-信号:{s}</span>')
                        for pc in fc.signal_pos_changes:
                            detail_parts.append(f"<code>{pc.signal_name}</code>起始位:{pc.old_start_bit}→{pc.new_start_bit}")
                    detail = "<br>".join(detail_parts)
                    parts.append(f'<tr class="{fc.change_type.lower()}"><td>{badge(fc.change_type)}</td><td><b>{fc.frame_name}</b></td><td><code>{fid}</code></td><td>{detail}</td></tr>')
                parts.append('</table>')

            # 信号变更
            if r.signal_changes:
                parts.append('<h3>信号变更</h3>')
                parts.append('<table class="dtbl"><tr><th>类型</th><th>所属帧</th><th>信号名</th><th>位长度</th><th>发布节点</th><th>变更详情</th></tr>')
                for sc in r.signal_changes:
                    sig = sc.new_signal or sc.old_signal
                    length_str = str(sig.length) if sig else ""
                    pub_str = sig.publisher if sig else ""
                    detail = "<br>".join(f"<code>{c.field_name}</code>: {c.old_value!r} → {c.new_value!r}" for c in sc.field_changes)
                    parts.append(f'<tr class="{sc.change_type.lower()}"><td>{badge(sc.change_type)}</td><td>{sc.frame_name}</td><td><b>{sc.signal_name}</b></td><td>{length_str}</td><td>{pub_str}</td><td>{detail}</td></tr>')
                parts.append('</table>')

            # 调度表变更
            if r.schedule_changes:
                parts.append('<h3>调度表变更</h3>')
                parts.append('<table class="dtbl"><tr><th>类型</th><th>调度表名</th><th>变更详情</th></tr>')
                for sc in r.schedule_changes:
                    detail_parts = []
                    if sc.change_type == ChangeType.MODIFIED:
                        for fn in sc.entries_added:
                            detail_parts.append(f'<span style="color:#27ae60">+{fn}</span>')
                        for fn in sc.entries_removed:
                            detail_parts.append(f'<span style="color:#e74c3c">-{fn}</span>')
                        for fld in sc.entries_modified:
                            detail_parts.append(f"<code>{fld.field_name}</code>: {fld.old_value}ms → {fld.new_value}ms")
                        for oc in sc.entries_reordered:
                            detail_parts.append(f"<code>{oc.frame_name}</code> 顺序: 第{oc.old_index+1}位 → 第{oc.new_index+1}位")
                    detail = "<br>".join(detail_parts)
                    parts.append(f'<tr class="{sc.change_type.lower()}"><td>{badge(sc.change_type)}</td><td><b>{sc.table_name}</b></td><td>{detail}</td></tr>')
                parts.append('</table>')

            parts.append('</div>')
            detail_sections.append("\n".join(parts))

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>LDF批量差异摘要</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; color: #2c3e50; }}
h1 {{ color: #2c3e50; }}
h2 {{ color: #2980b9; border-left: 4px solid #3498db; padding-left: 10px; margin-top: 30px; }}
h3 {{ color: #555; margin: 14px 0 6px; font-size: 15px; }}
.summary {{ display: flex; gap: 20px; margin: 15px 0; }}
.card {{ background: white; border-radius: 8px; padding: 15px 25px;
         box-shadow: 0 2px 6px rgba(0,0,0,0.1); text-align: center; }}
.card .num {{ font-size: 28px; font-weight: bold; }}
table {{ width: 100%; border-collapse: collapse; background: white;
         box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-radius: 6px;
         overflow: hidden; margin-bottom: 10px; }}
th {{ background: #3498db; color: white; padding: 8px 12px; text-align: left; font-size: 13px; }}
td {{ padding: 7px 12px; border-bottom: 1px solid #eee; font-size: 13px; vertical-align: top; }}
tr:last-child td {{ border-bottom: none; }}
tr.added   td {{ background: #f0fff4; }}
tr.removed td {{ background: #fff5f5; }}
tr.modified td {{ background: #fffbf0; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:bold; }}
.badge-add {{ background:#d4edda; color:#155724; }}
.badge-del {{ background:#f8d7da; color:#721c24; }}
.badge-mod {{ background:#fff3cd; color:#856404; }}
.channel-block {{ background: white; border-radius: 8px; padding: 20px 24px;
                  box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-top: 24px; }}
.dtbl th {{ background: #546e7a; }}
code {{ background: #f0f0f0; padding: 1px 5px; border-radius: 3px; font-size: 12px; }}
</style>
</head>
<body>
<h1>📋 LDF 批量差异分析报告</h1>
<p style="color:#888">生成时间: {_now()} &nbsp;|&nbsp; 共 {len(results)} 个通道</p>
<div class="summary">
  <div class="card"><div class="num" style="color:#e74c3c">{len(changed)}</div><div>有变更</div></div>
  <div class="card"><div class="num" style="color:#27ae60">{len(unchanged)}</div><div>无变更</div></div>
</div>

<h2>📊 通道概览</h2>
<table>
<tr><th>通道</th><th>状态</th><th>节点(+/-/~)</th><th>帧(+/-/~)</th>
    <th>信号(+/-/~)</th><th>调度表(+/-/~)</th><th>旧文件</th><th>新文件</th></tr>
{"".join(rows)}
</table>

{"".join(detail_sections)}
</body></html>"""

    def save_text(self, results: List[tuple], filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate_text(results))

    def save_html(self, results: List[tuple], filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate_html(results))
