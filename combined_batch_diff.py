"""
CAN/LIN 通信矩阵批量差异分析工具 - combined_batch_diff.py

功能：
  - 一次运行，同时分析 DBC（CAN）和 LDF（LIN）文件的差异
  - 自动扫描两个版本目录下的所有 DBC 和 LDF 文件
  - 生成统一的综合分析报告（HTML + TXT）
  - 同时保留每个通道的独立详细报告

用法：
  python combined_batch_diff.py <旧版本目录> <新版本目录> [选项]

示例：
  python combined_batch_diff.py ^
    "data/PZBP3.1.8通信矩阵_CAN_V10.1.7_SOA_V10.1.10_0409" ^
    "data/PZBP3.4.0通信矩阵_CAN_V11.1.0_SOA_V11.1.1_0421" ^
    --output-dir combined_diff_output --format all
"""

import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 DBC 相关模块
from dbc_batch_diff import (
    DBCBatchDiff, BatchDiffResult, ChannelDiffResult,
    BatchReportGenerator as DBCBatchReportGenerator
)

# 导入 LDF 相关模块
from ldf_batch_diff import (
    LDFBatchDiff, BatchReportGenerator as LDFBatchReportGenerator,
    scan_ldf_files, LDFFileInfo
)
from ldf_diff import LDFDiffResult


# =====================================================
# 统一综合报告生成器
# =====================================================

class CombinedReportGenerator:
    """
    综合报告生成器
    将 DBC（CAN）和 LDF（LIN）的分析结果合并成一份统一报告
    """

    def generate(
        self,
        dbc_batch: BatchDiffResult,
        ldf_results: List[Tuple[str, LDFDiffResult]],
        output_dir: str,
        fmt: str = "html",
        old_dir: str = "",
        new_dir: str = "",
        ldf_only_old: List[str] = None,
        ldf_only_new: List[str] = None,
    ):
        """
        生成综合报告：
        - combined_report.html  综合 HTML 报告（含 CAN + LIN 两大板块）
        - combined_report.txt   综合文本报告
        """
        os.makedirs(output_dir, exist_ok=True)
        ldf_only_old = ldf_only_old or []
        ldf_only_new = ldf_only_new or []

        html_path = os.path.join(output_dir, "combined_report.html")
        txt_path = os.path.join(output_dir, "combined_report.txt")

        self._generate_html(dbc_batch, ldf_results, html_path, fmt, old_dir, new_dir, ldf_only_old, ldf_only_new)
        self._generate_text(dbc_batch, ldf_results, txt_path, old_dir, new_dir, ldf_only_old, ldf_only_new)

        print(f"\n{'='*60}")
        print(f"  综合报告已生成:")
        print(f"    HTML: {html_path}")
        print(f"    TXT:  {txt_path}")
        print(f"{'='*60}")

        return html_path, txt_path

    # --------------------------------------------------
    # HTML 综合报告
    # --------------------------------------------------

    def _generate_html(
        self,
        dbc_batch: BatchDiffResult,
        ldf_results: List[Tuple[str, LDFDiffResult]],
        filepath: str,
        fmt: str,
        old_dir: str,
        new_dir: str,
        ldf_only_old: List[str] = None,
        ldf_only_new: List[str] = None,
    ):
        ldf_only_old = ldf_only_old or []
        ldf_only_new = ldf_only_new or []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        old_name = os.path.basename(old_dir.rstrip('/\\')) if old_dir else "旧版本"
        new_name = os.path.basename(new_dir.rstrip('/\\')) if new_dir else "新版本"

        # LDF 统计
        ldf_changed = [(ch, r) for ch, r in ldf_results if r.has_changes()]
        ldf_unchanged = [(ch, r) for ch, r in ldf_results if not r.has_changes()]

        # DBC 汇总统计
        dbc_total_msgs_added = sum(r.stats.get("msgs_added", 0) for r in dbc_batch.changed)
        dbc_total_msgs_removed = sum(r.stats.get("msgs_removed", 0) for r in dbc_batch.changed)
        dbc_total_msgs_modified = sum(r.stats.get("msgs_modified", 0) for r in dbc_batch.changed)
        dbc_total_sigs_added = sum(r.stats.get("sigs_added", 0) for r in dbc_batch.changed)
        dbc_total_sigs_removed = sum(r.stats.get("sigs_removed", 0) for r in dbc_batch.changed)
        dbc_total_sigs_modified = sum(r.stats.get("sigs_modified", 0) for r in dbc_batch.changed)

        # LDF 汇总统计
        ldf_total_frames_added = sum(r.stats().get("frames_added", 0) for _, r in ldf_changed)
        ldf_total_frames_removed = sum(r.stats().get("frames_removed", 0) for _, r in ldf_changed)
        ldf_total_frames_modified = sum(r.stats().get("frames_modified", 0) for _, r in ldf_changed)
        ldf_total_sigs_added = sum(r.stats().get("signals_added", 0) for _, r in ldf_changed)
        ldf_total_sigs_removed = sum(r.stats().get("signals_removed", 0) for _, r in ldf_changed)
        ldf_total_sigs_modified = sum(r.stats().get("signals_modified", 0) for _, r in ldf_changed)

        css = self._get_css()

        html = [f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>通信矩阵综合差异分析报告</title>
<style>{css}</style>
</head>
<body>
<div class="page-header">
  <h1>📊 通信矩阵综合差异分析报告</h1>
  <div class="meta-bar">
    <span>🕐 生成时间: {now}</span>
    <span>📁 旧版本: <strong>{old_name}</strong></span>
    <span>📁 新版本: <strong>{new_name}</strong></span>
  </div>
</div>

<!-- 目录导航 -->
<div class="toc">
  <strong>📋 目录</strong>
  <a href="#overview">总体概览</a>
  <a href="#can-section">CAN 通道差异（DBC）</a>
  <a href="#lin-section">LIN 通道差异（LDF）</a>
</div>
"""]

        # ===== 总体概览 =====
        html.append('<section id="overview">')
        html.append('<h2>📈 总体概览</h2>')

        html.append('<div class="overview-grid">')

        # CAN 概览卡
        html.append(f"""
<div class="overview-card can-card">
  <div class="card-title">🔌 CAN 通道（DBC）</div>
  <div class="card-stats">
    <div class="stat-item changed"><span class="num">{len(dbc_batch.changed)}</span><span class="lbl">有变更通道</span></div>
    <div class="stat-item ok"><span class="num">{len(dbc_batch.unchanged)}</span><span class="lbl">无变更通道</span></div>
    <div class="stat-item added"><span class="num">{len(dbc_batch.only_in_new)}</span><span class="lbl">新增通道</span></div>
    <div class="stat-item removed"><span class="num">{len(dbc_batch.only_in_old)}</span><span class="lbl">删除通道</span></div>
  </div>
  <div class="card-detail">
    <table class="mini-table">
      <tr><th></th><th>新增</th><th>删除</th><th>修改</th></tr>
      <tr><td>报文</td>
        <td class="add">+{dbc_total_msgs_added}</td>
        <td class="del">-{dbc_total_msgs_removed}</td>
        <td class="mod">~{dbc_total_msgs_modified}</td>
      </tr>
      <tr><td>信号</td>
        <td class="add">+{dbc_total_sigs_added}</td>
        <td class="del">-{dbc_total_sigs_removed}</td>
        <td class="mod">~{dbc_total_sigs_modified}</td>
      </tr>
    </table>
  </div>
</div>
""")

        # LIN 概览卡
        html.append(f"""
<div class="overview-card lin-card">
  <div class="card-title">🔗 LIN 通道（LDF）</div>
  <div class="card-stats">
    <div class="stat-item changed"><span class="num">{len(ldf_changed)}</span><span class="lbl">有变更通道</span></div>
    <div class="stat-item ok"><span class="num">{len(ldf_unchanged)}</span><span class="lbl">无变更通道</span></div>
    <div class="stat-item added"><span class="num">{len(ldf_only_new)}</span><span class="lbl">新增通道</span></div>
    <div class="stat-item removed"><span class="num">{len(ldf_only_old)}</span><span class="lbl">删除通道</span></div>
  </div>
  <div class="card-detail">
    <table class="mini-table">
      <tr><th></th><th>新增</th><th>删除</th><th>修改</th></tr>
      <tr><td>帧</td>
        <td class="add">+{ldf_total_frames_added}</td>
        <td class="del">-{ldf_total_frames_removed}</td>
        <td class="mod">~{ldf_total_frames_modified}</td>
      </tr>
      <tr><td>信号</td>
        <td class="add">+{ldf_total_sigs_added}</td>
        <td class="del">-{ldf_total_sigs_removed}</td>
        <td class="mod">~{ldf_total_sigs_modified}</td>
      </tr>
    </table>
  </div>
</div>
""")
        html.append('</div>')  # end overview-grid
        html.append('</section>')

        # ===== CAN / DBC 部分 =====
        html.append('<section id="can-section">')
        html.append('<h2>🔌 CAN 通道差异（DBC）</h2>')
        html.append(self._build_dbc_section(dbc_batch, fmt))
        html.append('</section>')

        # ===== LIN / LDF 部分 =====
        html.append('<section id="lin-section">')
        html.append('<h2>🔗 LIN 通道差异（LDF）</h2>')
        html.append(self._build_ldf_section(ldf_results, ldf_changed, ldf_unchanged, ldf_only_old, ldf_only_new))
        html.append('</section>')

        html.append('<div class="footer">本报告由 combined_batch_diff.py 自动生成</div>')
        html.append('</body></html>')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(''.join(html))
        print(f"[CombinedReport] HTML综合报告已保存: {filepath}")

    def _build_dbc_section(self, batch: BatchDiffResult, fmt: str) -> str:
        """构建 DBC 部分的 HTML"""
        parts = []

        # 统计卡片行
        parts.append('<div class="stat-row">')
        parts.append(f'<div class="stat-box changed"><div class="num">{len(batch.changed)}</div><div class="lbl">有变更通道</div></div>')
        parts.append(f'<div class="stat-box ok"><div class="num">{len(batch.unchanged)}</div><div class="lbl">无变更通道</div></div>')
        parts.append(f'<div class="stat-box added"><div class="num">{len(batch.only_in_new)}</div><div class="lbl">仅新版本有</div></div>')
        parts.append(f'<div class="stat-box removed"><div class="num">{len(batch.only_in_old)}</div><div class="lbl">仅旧版本有</div></div>')
        parts.append('</div>')

        # 仅旧版本存在
        if batch.only_in_old:
            parts.append('<h3 class="sub-title del-title">已删除通道</h3>')
            parts.append('<table><tr><th>通道</th><th>旧版本文件</th></tr>')
            for cr in [r for r in batch.channel_results if r.error == "only_in_old"]:
                parts.append(f'<tr><td><span class="tag-del">已删除</span> <strong>{cr.channel_key}</strong></td>'
                             f'<td><code>{os.path.basename(cr.old_file)}</code></td></tr>')
            parts.append('</table>')

        # 仅新版本存在
        if batch.only_in_new:
            parts.append('<h3 class="sub-title add-title">新增通道</h3>')
            parts.append('<table><tr><th>通道</th><th>新版本文件</th></tr>')
            for cr in [r for r in batch.channel_results if r.error == "only_in_new"]:
                parts.append(f'<tr><td><span class="tag-add">新增</span> <strong>{cr.channel_key}</strong></td>'
                             f'<td><code>{os.path.basename(cr.new_file)}</code></td></tr>')
            parts.append('</table>')

        # 有变更通道汇总表
        if batch.changed:
            parts.append('<h3 class="sub-title mod-title">有变更的通道</h3>')
            parts.append('<table><tr><th>通道</th><th>旧版本</th><th>新版本</th>'
                        '<th>报文变更</th><th>信号变更</th><th>详细报告</th></tr>')
            for cr in sorted(batch.changed, key=lambda x: x.channel_key):
                stats = cr.stats
                safe_key = cr.channel_key.replace('/', '_').replace('\\', '_')
                links = []
                if fmt in ('html', 'all'):
                    links.append(f'<a href="can/diff_{safe_key}.html" target="_blank">HTML</a>')
                if fmt in ('markdown', 'md', 'all'):
                    links.append(f'<a href="can/diff_{safe_key}.md" target="_blank">MD</a>')
                if fmt in ('csv', 'all'):
                    links.append(f'<a href="can/diff_{safe_key}.csv" target="_blank">CSV</a>')
                if fmt in ('text', 'txt', 'all'):
                    links.append(f'<a href="can/diff_{safe_key}.txt" target="_blank">TXT</a>')
                link_str = ' | '.join(links) if links else '-'

                msg_str = (f'<span class="tag-add">+{stats.get("msgs_added",0)}</span> '
                           f'<span class="tag-del">-{stats.get("msgs_removed",0)}</span> '
                           f'<span class="tag-mod">~{stats.get("msgs_modified",0)}</span>')
                sig_str = (f'<span class="tag-add">+{stats.get("sigs_added",0)}</span> '
                           f'<span class="tag-del">-{stats.get("sigs_removed",0)}</span> '
                           f'<span class="tag-mod">~{stats.get("sigs_modified",0)}</span>')

                parts.append(f'<tr>'
                             f'<td><strong>{cr.channel_key}</strong></td>'
                             f'<td><code>V{cr.old_version}</code><br><small>{os.path.basename(cr.old_file)}</small></td>'
                             f'<td><code>V{cr.new_version}</code><br><small>{os.path.basename(cr.new_file)}</small></td>'
                             f'<td>{msg_str}</td>'
                             f'<td>{sig_str}</td>'
                             f'<td>{link_str}</td>'
                             f'</tr>')
            parts.append('</table>')

            # 变更详情
            parts.append('<h3 class="sub-title">变更详情</h3>')
            for cr in sorted(batch.changed, key=lambda x: x.channel_key):
                diff = cr.diff_result
                parts.append(f'<div class="channel-block">')
                parts.append(f'<div class="channel-header mod-header">'
                             f'<span class="tag-mod">变更</span> <strong>{cr.channel_key}</strong>'
                             f' <span class="ver-badge">V{cr.old_version} → V{cr.new_version}</span>'
                             f'</div>')
                parts.append('<div class="channel-body">')

                # 新增报文
                for mc in diff.added_messages:
                    msg = mc.new_message
                    parts.append(f'<div class="item-row add-row">'
                                 f'<span class="tag-add">新增报文</span> '
                                 f'<strong>{mc.msg_name}</strong> <code>{mc.can_id_hex}</code> '
                                 f'DLC={msg.dlc} 发送节点={msg.sender}</div>')
                    if msg.signals:
                        _SIG_ATTRS = [
                            ("start_bit", "起始位"), ("length", "位长度"),
                            ("factor", "比例因子"),
                            ("offset", "偏移"), ("min_val", "最小值"),
                            ("max_val", "最大值"), ("unit", "单位"),
                            ("comment", "注释"),
                        ]
                        parts.append('<table class="inner-table"><tr><th>信号名</th><th>属性</th></tr>')
                        for sig_name, sig in sorted(msg.signals.items()):
                            fields = " &nbsp;|&nbsp; ".join(
                                f"<em>{label}</em>: <code class='new-val'>{getattr(sig, attr)}</code>"
                                for attr, label in _SIG_ATTRS
                                if (isinstance(getattr(sig, attr), list) and getattr(sig, attr))
                                or (not isinstance(getattr(sig, attr), list) and getattr(sig, attr) is not None and getattr(sig, attr) != "")
                            )
                            _sst = sig.attributes.get('SigSendType') or sig.attributes.get('GenSigSendType') or ''
                            if _sst:
                                fields = f'<em>SigSendType</em>: <code class="new-val">{_sst}</code>' + (' &nbsp;|&nbsp; ' + fields if fields else '')
                            parts.append(f'<tr style="font-size:1.0em"><td><strong>{sig_name}</strong></td><td>{fields or "-"}</td></tr>')
                        parts.append('</table>')

                # 删除报文
                for mc in diff.removed_messages:
                    msg = mc.old_message
                    parts.append(f'<div class="item-row del-row">'
                                 f'<span class="tag-del">删除报文</span> '
                                 f'<strong>{mc.msg_name}</strong> <code>{mc.can_id_hex}</code> '
                                 f'DLC={msg.dlc} 发送节点={msg.sender}</div>')

                # 修改报文
                for mc in diff.modified_messages:
                    parts.append(f'<div class="item-row mod-row">'
                                 f'<span class="tag-mod">修改报文</span> '
                                 f'<strong>{mc.msg_name}</strong> <code>{mc.can_id_hex}</code></div>')
                    if mc.field_changes:
                        parts.append('<ul class="change-list">')
                        for fc in mc.field_changes:
                            parts.append(f'<li>报文属性 <em>{fc.field_name}</em>: '
                                        f'<code class="old-val">{fc.old_value}</code> → '
                                        f'<code class="new-val">{fc.new_value}</code></li>')
                        parts.append('</ul>')
                    if mc.signal_changes:
                        parts.append('<table class="inner-table"><tr><th>变更类型</th><th>信号名</th><th>变更字段</th></tr>')
                        for sc in mc.signal_changes:
                            tag = {"ADDED": "tag-add", "REMOVED": "tag-del", "MODIFIED": "tag-mod"}.get(sc.change_type, "")
                            label = {"ADDED": "新增", "REMOVED": "删除", "MODIFIED": "修改"}.get(sc.change_type, sc.change_type)
                            if sc.change_type == "ADDED":
                                if sc.field_changes:
                                    field_str = " &nbsp;|&nbsp; ".join(
                                        f"<em>{fc.field_name}</em>: <code class='new-val'>{fc.new_value}</code>"
                                        for fc in sc.field_changes
                                    )
                                elif sc.new_signal is not None:
                                    field_str = (f'起始位=<code>{sc.new_signal.start_bit}</code> '
                                                f'位长度=<code>{sc.new_signal.length}</code>')
                                else:
                                    field_str = "-"
                            elif sc.change_type == "REMOVED" and sc.old_signal is not None:
                                field_str = (f'起始位=<code>{sc.old_signal.start_bit}</code> '
                                            f'位长度=<code>{sc.old_signal.length}</code>')
                            else:
                                if sc.field_changes:
                                    field_str = " &nbsp;|&nbsp; ".join(
                                        f"<em>{fc.field_name}</em>: <code class='old-val'>{fc.old_value}</code> → <code class='new-val'>{fc.new_value}</code>"
                                        for fc in sc.field_changes
                                    )
                                else:
                                    field_str = "-"
                            parts.append(f'<tr><td><span class="{tag}">{label}</span></td>'
                                        f'<td><strong>{sc.signal_name}</strong></td>'
                                        f'<td>{field_str}</td></tr>')
                        parts.append('</table>')

                parts.append('</div></div>')  # end channel-body, channel-block

        # 无变更通道
        if batch.unchanged:
            parts.append('<h3 class="sub-title ok-title">无变更的通道</h3>')
            parts.append('<table><tr><th>通道</th><th>旧版本文件</th><th>新版本文件</th></tr>')
            for cr in sorted(batch.unchanged, key=lambda x: x.channel_key):
                parts.append(f'<tr><td><span class="tag-ok">无变更</span> {cr.channel_key}</td>'
                             f'<td><code>{os.path.basename(cr.old_file)}</code></td>'
                             f'<td><code>{os.path.basename(cr.new_file)}</code></td></tr>')
            parts.append('</table>')

        return ''.join(parts)

    def _build_ldf_section(
        self,
        all_results: List[Tuple[str, LDFDiffResult]],
        ldf_changed: List[Tuple[str, LDFDiffResult]],
        ldf_unchanged: List[Tuple[str, LDFDiffResult]],
        ldf_only_old: List[str] = None,
        ldf_only_new: List[str] = None,
    ) -> str:
        """构建 LDF 部分的 HTML"""
        ldf_only_old = ldf_only_old or []
        ldf_only_new = ldf_only_new or []
        parts = []

        parts.append('<div class="stat-row">')
        parts.append(f'<div class="stat-box changed"><div class="num">{len(ldf_changed)}</div><div class="lbl">有变更通道</div></div>')
        parts.append(f'<div class="stat-box ok"><div class="num">{len(ldf_unchanged)}</div><div class="lbl">无变更通道</div></div>')
        parts.append(f'<div class="stat-box added"><div class="num">{len(ldf_only_new)}</div><div class="lbl">仅新版本有</div></div>')
        parts.append(f'<div class="stat-box removed"><div class="num">{len(ldf_only_old)}</div><div class="lbl">仅旧版本有</div></div>')
        parts.append('</div>')

        if not all_results and not ldf_only_old and not ldf_only_new:
            parts.append('<p class="no-data">未发现 LDF 文件或无可匹配的通道对。</p>')
            return ''.join(parts)

        # 仅旧版本存在（已删除通道）
        if ldf_only_old:
            parts.append('<h3 class="sub-title del-title">已删除通道（仅旧版本存在）</h3>')
            parts.append('<table><tr><th>通道</th></tr>')
            for ch in ldf_only_old:
                parts.append(f'<tr><td><span class="tag-del">已删除</span> <strong>{ch}</strong></td></tr>')
            parts.append('</table>')

        # 仅新版本存在（新增通道）
        if ldf_only_new:
            parts.append('<h3 class="sub-title add-title">新增通道（仅新版本存在）</h3>')
            parts.append('<table><tr><th>通道</th></tr>')
            for ch in ldf_only_new:
                parts.append(f'<tr><td><span class="tag-add">新增</span> <strong>{ch}</strong></td></tr>')
            parts.append('</table>')

        # 有变更通道汇总表
        if ldf_changed:
            parts.append('<h3 class="sub-title mod-title">有变更的通道</h3>')
            parts.append('<table><tr><th>通道</th><th>帧变更</th><th>信号变更</th>'
                        '<th>节点变更</th><th>调度表变更</th><th>详细报告</th></tr>')
            for channel, r in sorted(ldf_changed, key=lambda x: x[0]):
                stats = r.stats()
                safe_ch = re.sub(r'[^\w\-]', '_', channel)
                frame_str = (f'<span class="tag-add">+{stats.get("frames_added",0)}</span> '
                            f'<span class="tag-del">-{stats.get("frames_removed",0)}</span> '
                            f'<span class="tag-mod">~{stats.get("frames_modified",0)}</span>')
                sig_str = (f'<span class="tag-add">+{stats.get("signals_added",0)}</span> '
                          f'<span class="tag-del">-{stats.get("signals_removed",0)}</span> '
                          f'<span class="tag-mod">~{stats.get("signals_modified",0)}</span>')
                node_str = (f'<span class="tag-add">+{stats.get("nodes_added",0)}</span> '
                           f'<span class="tag-del">-{stats.get("nodes_removed",0)}</span> '
                           f'<span class="tag-mod">~{stats.get("nodes_modified",0)}</span>')
                sch_str = (f'<span class="tag-add">+{stats.get("schedules_added",0)}</span> '
                          f'<span class="tag-del">-{stats.get("schedules_removed",0)}</span> '
                          f'<span class="tag-mod">~{stats.get("schedules_modified",0)}</span>')
                link_str = f'<a href="lin/{safe_ch}_diff.html" target="_blank">HTML</a>'

                parts.append(f'<tr>'
                             f'<td><strong>{channel}</strong></td>'
                             f'<td>{frame_str}</td>'
                             f'<td>{sig_str}</td>'
                             f'<td>{node_str}</td>'
                             f'<td>{sch_str}</td>'
                             f'<td>{link_str}</td>'
                             f'</tr>')
            parts.append('</table>')

            # 变更详情
            parts.append('<h3 class="sub-title">变更详情</h3>')
            for channel, r in sorted(ldf_changed, key=lambda x: x[0]):
                parts.append(f'<div class="channel-block">')
                parts.append(f'<div class="channel-header mod-header">'
                             f'<span class="tag-mod">变更</span> <strong>{channel}</strong>'
                             f'</div>')
                parts.append('<div class="channel-body">')
                parts.append(self._render_ldf_diff(r))
                parts.append('</div></div>')

        # 无变更通道
        if ldf_unchanged:
            parts.append('<h3 class="sub-title ok-title">无变更的通道</h3>')
            parts.append('<table><tr><th>通道</th><th>状态</th></tr>')
            for channel, _ in sorted(ldf_unchanged, key=lambda x: x[0]):
                parts.append(f'<tr><td>{channel}</td><td><span class="tag-ok">无变更</span></td></tr>')
            parts.append('</table>')

        return ''.join(parts)

    def _render_ldf_diff(self, r: LDFDiffResult) -> str:
        """渲染单个 LDF 通道的差异详情
        注意: ldf_diff.py 中 change_type 是普通字符串 "ADDED"/"REMOVED"/"MODIFIED"
             LDFFrameChange 使用 signal_added/signal_removed/signal_pos_changes
             LDFScheduleChange 使用 table_name（不是 schedule_name）
        """
        parts = []

        # 节点变更
        if r.node_changes:
            nc_added   = [c for c in r.node_changes if c.change_type == "ADDED"]
            nc_removed = [c for c in r.node_changes if c.change_type == "REMOVED"]
            nc_modified= [c for c in r.node_changes if c.change_type == "MODIFIED"]
            if nc_added or nc_removed or nc_modified:
                parts.append('<div class="diff-category"><strong>节点变更</strong></div>')
                for c in nc_added:
                    parts.append(f'<div class="item-row add-row"><span class="tag-add">新增节点</span> <strong>{c.node_name}</strong></div>')
                for c in nc_removed:
                    parts.append(f'<div class="item-row del-row"><span class="tag-del">删除节点</span> <strong>{c.node_name}</strong></div>')
                for c in nc_modified:
                    parts.append(f'<div class="item-row mod-row"><span class="tag-mod">修改节点</span> <strong>{c.node_name}</strong></div>')
                    if c.field_changes:
                        parts.append('<ul class="change-list">')
                        for fc in c.field_changes:
                            parts.append(f'<li><em>{fc.field_name}</em>: '
                                        f'<code class="old-val">{fc.old_value}</code> → '
                                        f'<code class="new-val">{fc.new_value}</code></li>')
                        parts.append('</ul>')

        # 帧变更（LDFFrameChange: signal_added/signal_removed/signal_pos_changes）
        # 建立 信号名 -> LDFSignalChange 映射，用于在修改帧中展示信号属性/变更字段
        sig_change_map = {sc.signal_name: sc for sc in r.signal_changes}
        if r.frame_changes:
            fc_added   = [c for c in r.frame_changes if c.change_type == "ADDED"]
            fc_removed = [c for c in r.frame_changes if c.change_type == "REMOVED"]
            fc_modified= [c for c in r.frame_changes if c.change_type == "MODIFIED"]
            if fc_added or fc_removed or fc_modified:
                parts.append('<div class="diff-category"><strong>帧变更</strong></div>')
                for c in fc_added:
                    parts.append(f'<div class="item-row add-row"><span class="tag-add">新增帧</span> <strong>{c.frame_name}</strong></div>')
                    # 展示帧内所有信号属性
                    if c.new_frame and c.new_frame.signals:
                        parts.append('<table class="inner-table"><tr><th>信号名</th><th>属性</th></tr>')
                        for fs in c.new_frame.signals:
                            sc = sig_change_map.get(fs.signal_name)
                            if sc and sc.field_changes:
                                attr_str = " &nbsp;|&nbsp; ".join(
                                    f"<em>{fc.field_name}</em>: <code class='new-val'>{fc.new_value}</code>"
                                    for fc in sc.field_changes
                                )
                            else:
                                attr_str = f"起始位: <code>{fs.start_bit}</code>"
                            parts.append(f'<tr style="font-size:1.0em"><td><strong>{fs.signal_name}</strong></td><td>{attr_str}</td></tr>')
                        parts.append('</table>')
                for c in fc_removed:
                    parts.append(f'<div class="item-row del-row"><span class="tag-del">删除帧</span> <strong>{c.frame_name}</strong></div>')
                for c in fc_modified:
                    parts.append(f'<div class="item-row mod-row"><span class="tag-mod">修改帧</span> <strong>{c.frame_name}</strong></div>')
                    if c.field_changes:
                        parts.append('<ul class="change-list">')
                        for fld in c.field_changes:
                            parts.append(f'<li><em>{fld.field_name}</em>: '
                                        f'<code class="old-val">{fld.old_value}</code> → '
                                        f'<code class="new-val">{fld.new_value}</code></li>')
                        parts.append('</ul>')
                    # 帧内信号新增/删除/位置变更/属性变更
                    sig_rows = []
                    for sn in c.signal_added:
                        sc = sig_change_map.get(sn)
                        if sc and sc.field_changes:
                            attr_str = " &nbsp;|&nbsp; ".join(
                                f"<em>{fc.field_name}</em>: <code class='new-val'>{fc.new_value}</code>"
                                for fc in sc.field_changes
                            )
                        else:
                            attr_str = "-"
                        sig_rows.append(f'<tr style="font-size:1.0em"><td><span class="tag-add">新增</span></td><td><strong>{sn}</strong></td><td>{attr_str}</td></tr>')
                    for sn in c.signal_removed:
                        sig_rows.append(f'<tr><td><span class="tag-del">删除</span></td><td><strong>{sn}</strong></td><td>-</td></tr>')
                    for pc in c.signal_pos_changes:
                        sc = sig_change_map.get(pc.signal_name)
                        extra = ""
                        if sc and sc.change_type == "MODIFIED" and sc.field_changes:
                            extra = " &nbsp;|&nbsp; " + " &nbsp;|&nbsp; ".join(
                                f"<em>{fc.field_name}</em>: <code class='old-val'>{fc.old_value}</code>→<code class='new-val'>{fc.new_value}</code>"
                                for fc in sc.field_changes
                            )
                        sig_rows.append(
                            f'<tr style="font-size:1.0em"><td><span class="tag-mod">位置变更</span></td>'
                            f'<td><strong>{pc.signal_name}</strong></td>'
                            f'<td>起始位: <code class="old-val">{pc.old_start_bit}</code>→'
                            f'<code class="new-val">{pc.new_start_bit}</code>{extra}</td></tr>'
                        )
                    # 属性变更的信号（MODIFIED，且属于本帧，但不在 signal_pos_changes 中）
                    pos_changed_names = {pc.signal_name for pc in c.signal_pos_changes}
                    for sn_mod, sc in sig_change_map.items():
                        if (sc.change_type == "MODIFIED" and sc.frame_name == c.frame_name
                                and sn_mod not in pos_changed_names
                                and sn_mod not in c.signal_added
                                and sn_mod not in c.signal_removed):
                            if sc.field_changes:
                                field_str = " &nbsp;|&nbsp; ".join(
                                    f"<em>{fc.field_name}</em>: <code class='old-val'>{fc.old_value}</code>→<code class='new-val'>{fc.new_value}</code>"
                                    for fc in sc.field_changes
                                )
                            else:
                                field_str = "-"
                            sig_rows.append(
                                f'<tr style="font-size:1.0em"><td><span class="tag-mod">属性变更</span></td>'
                                f'<td><strong>{sn_mod}</strong></td>'
                                f'<td>{field_str}</td></tr>'
                            )
                    if sig_rows:
                        parts.append('<table class="inner-table"><tr><th>变更类型</th><th>信号名</th><th>变更字段</th></tr>')
                        parts.extend(sig_rows)
                        parts.append('</table>')

        # 调度表变更（LDFScheduleChange 使用 table_name）
        if r.schedule_changes:
            sc_added   = [c for c in r.schedule_changes if c.change_type == "ADDED"]
            sc_removed = [c for c in r.schedule_changes if c.change_type == "REMOVED"]
            sc_modified= [c for c in r.schedule_changes if c.change_type == "MODIFIED"]
            if sc_added or sc_removed or sc_modified:
                parts.append('<div class="diff-category"><strong>调度表变更</strong></div>')
                for c in sc_added:
                    parts.append(f'<div class="item-row add-row"><span class="tag-add">新增调度表</span> <strong>{c.table_name}</strong></div>')
                for c in sc_removed:
                    parts.append(f'<div class="item-row del-row"><span class="tag-del">删除调度表</span> <strong>{c.table_name}</strong></div>')
                for c in sc_modified:
                    parts.append(f'<div class="item-row mod-row"><span class="tag-mod">修改调度表</span> <strong>{c.table_name}</strong></div>')
                    if c.entries_added or c.entries_removed:
                        entry_parts = []
                        if c.entries_added:
                            entry_parts.append('新增帧: ' + ' '.join(
                                f'<span class="tag-add">{e}</span>' for e in c.entries_added
                            ))
                        if c.entries_removed:
                            entry_parts.append('删除帧: ' + ' '.join(
                                f'<span class="tag-del">{e}</span>' for e in c.entries_removed
                            ))
                        parts.append(f'<ul class="change-list"><li>{"；".join(entry_parts)}</li></ul>')

        if not parts:
            parts.append('<p class="no-data">无变更详情</p>')

        return ''.join(parts)

    # --------------------------------------------------
    # 文本综合报告
    # --------------------------------------------------

    def _generate_text(
        self,
        dbc_batch: BatchDiffResult,
        ldf_results: List[Tuple[str, LDFDiffResult]],
        filepath: str,
        old_dir: str,
        new_dir: str,
        ldf_only_old: List[str] = None,
        ldf_only_new: List[str] = None,
    ):
        ldf_only_old = ldf_only_old or []
        ldf_only_new = ldf_only_new or []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        old_name = os.path.basename(old_dir.rstrip('/\\')) if old_dir else "旧版本"
        new_name = os.path.basename(new_dir.rstrip('/\\')) if new_dir else "新版本"

        ldf_changed = [(ch, r) for ch, r in ldf_results if r.has_changes()]
        ldf_unchanged = [(ch, r) for ch, r in ldf_results if not r.has_changes()]

        lines = []
        w = lines.append
        sep = "=" * 72
        dash = "-" * 72

        w(sep)
        w("  通信矩阵综合差异分析报告")
        w(f"  生成时间: {now}")
        w(f"  旧版本目录: {old_name}")
        w(f"  新版本目录: {new_name}")
        w(sep)

        # ---- CAN 部分 ----
        w("")
        w("【CAN 通道差异（DBC）】")
        w(dash)
        w(f"  对比通道数: {len(dbc_batch.compared)}")
        w(f"  有变更通道: {len(dbc_batch.changed)}")
        w(f"  无变更通道: {len(dbc_batch.unchanged)}")
        w(f"  仅旧版本有: {len(dbc_batch.only_in_old)}")
        w(f"  仅新版本有: {len(dbc_batch.only_in_new)}")

        if dbc_batch.only_in_old:
            w("")
            w("  [已删除通道]")
            for key in dbc_batch.only_in_old:
                w(f"    [-] {key}")

        if dbc_batch.only_in_new:
            w("")
            w("  [新增通道]")
            for key in dbc_batch.only_in_new:
                w(f"    [+] {key}")

        if dbc_batch.changed:
            w("")
            w("  [有变更的通道]")
            for cr in sorted(dbc_batch.changed, key=lambda x: x.channel_key):
                stats = cr.stats
                w(f"\n  [~] {cr.channel_key}  V{cr.old_version} -> V{cr.new_version}")
                w(f"      旧文件: {os.path.basename(cr.old_file)}")
                w(f"      新文件: {os.path.basename(cr.new_file)}")
                w(f"      报文: +{stats.get('msgs_added',0)}/-{stats.get('msgs_removed',0)}/~{stats.get('msgs_modified',0)}")
                w(f"      信号: +{stats.get('sigs_added',0)}/-{stats.get('sigs_removed',0)}/~{stats.get('sigs_modified',0)}")

                diff = cr.diff_result
                for mc in diff.added_messages:
                    w(f"        [+] 新增报文: {mc.msg_name} ({mc.can_id_hex})")
                for mc in diff.removed_messages:
                    w(f"        [-] 删除报文: {mc.msg_name} ({mc.can_id_hex})")
                for mc in diff.modified_messages:
                    w(f"        [~] 修改报文: {mc.msg_name} ({mc.can_id_hex})")
                    for sc in mc.signal_changes:
                        icon = {"ADDED": "[+]", "REMOVED": "[-]", "MODIFIED": "[~]"}.get(sc.change_type, "?")
                        label = {"ADDED": "新增信号", "REMOVED": "删除信号", "MODIFIED": "修改信号"}.get(sc.change_type, sc.change_type)
                        w(f"            {icon} {label}: {sc.signal_name}")
                        for fc in sc.field_changes:
                            w(f"                {fc.field_name}: {fc.old_value!r} -> {fc.new_value!r}")

        if dbc_batch.unchanged:
            w("")
            w("  [无变更的通道]")
            for cr in sorted(dbc_batch.unchanged, key=lambda x: x.channel_key):
                w(f"    [OK] {cr.channel_key}  V{cr.old_version} -> V{cr.new_version}")

        # ---- LIN 部分 ----
        w("")
        w("")
        w("【LIN 通道差异（LDF）】")
        w(dash)
        w(f"  对比通道数: {len(ldf_results)}")
        w(f"  有变更通道: {len(ldf_changed)}")
        w(f"  无变更通道: {len(ldf_unchanged)}")
        w(f"  仅旧版本有: {len(ldf_only_old)}")
        w(f"  仅新版本有: {len(ldf_only_new)}")

        if ldf_only_old:
            w("")
            w("  [已删除通道]")
            for ch in ldf_only_old:
                w(f"    [-] {ch}")

        if ldf_only_new:
            w("")
            w("  [新增通道]")
            for ch in ldf_only_new:
                w(f"    [+] {ch}")

        if ldf_changed:
            w("")
            w("  [有变更的通道]")
            for channel, r in sorted(ldf_changed, key=lambda x: x[0]):
                stats = r.stats()
                w(f"\n  [~] {channel}")
                w(f"      帧: +{stats.get('frames_added',0)}/-{stats.get('frames_removed',0)}/~{stats.get('frames_modified',0)}")
                w(f"      信号: +{stats.get('signals_added',0)}/-{stats.get('signals_removed',0)}/~{stats.get('signals_modified',0)}")
                w(f"      节点: +{stats.get('nodes_added',0)}/-{stats.get('nodes_removed',0)}/~{stats.get('nodes_modified',0)}")
                w(f"      调度表: +{stats.get('schedules_added',0)}/-{stats.get('schedules_removed',0)}/~{stats.get('schedules_modified',0)}")

                # 帧变更详情（信号变更合并到各帧展示）
                sig_change_map_txt = {sc.signal_name: sc for sc in r.signal_changes}
                for fc in r.frame_changes:
                    ctype = fc.change_type
                    icon  = {"ADDED": "[+]", "REMOVED": "[-]", "MODIFIED": "[~]"}.get(ctype, "?")
                    label = {"ADDED": "新增帧", "REMOVED": "删除帧", "MODIFIED": "修改帧"}.get(ctype, ctype)
                    w(f"        {icon} {label}: {fc.frame_name}")
                    if ctype == "MODIFIED":
                        for fld in fc.field_changes:
                            w(f"            {fld.field_name}: {fld.old_value!r} -> {fld.new_value!r}")
                        for sn in fc.signal_added:
                            w(f"            [+] 新增信号: {sn}")
                            sc = sig_change_map_txt.get(sn)
                            if sc and sc.field_changes:
                                for fld in sc.field_changes:
                                    w(f"                {fld.field_name}: {fld.new_value!r}")
                        for sn in fc.signal_removed:
                            w(f"            [-] 删除信号: {sn}")
                        pos_changed_names_txt = {pc.signal_name for pc in fc.signal_pos_changes}
                        for pc in fc.signal_pos_changes:
                            w(f"            [~] 信号位置变更: {pc.signal_name}  起始位 {pc.old_start_bit} -> {pc.new_start_bit}")
                            sc = sig_change_map_txt.get(pc.signal_name)
                            if sc and sc.change_type == "MODIFIED" and sc.field_changes:
                                for fld in sc.field_changes:
                                    w(f"                {fld.field_name}: {fld.old_value!r} -> {fld.new_value!r}")
                        # 属性变更的信号（MODIFIED，属于本帧，未在 pos_changes 中）
                        for sn_mod, sc in sig_change_map_txt.items():
                            if (sc.change_type == "MODIFIED" and sc.frame_name == fc.frame_name
                                    and sn_mod not in pos_changed_names_txt
                                    and sn_mod not in fc.signal_added
                                    and sn_mod not in fc.signal_removed):
                                w(f"            [~] 修改信号: {sn_mod}")
                                for fld in sc.field_changes:
                                    w(f"                {fld.field_name}: {fld.old_value!r} -> {fld.new_value!r}")

        if ldf_unchanged:
            w("")
            w("  [无变更的通道]")
            for channel, _ in sorted(ldf_unchanged, key=lambda x: x[0]):
                w(f"    [OK] {channel}")

        w("")
        w(sep)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"[CombinedReport] 文本综合报告已保存: {filepath}")

    # --------------------------------------------------
    # CSS 样式
    # --------------------------------------------------

    def _get_css(self) -> str:
        return """
* { box-sizing: border-box; }
body {
    font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
    margin: 0; padding: 0;
    background: #f0f2f5; color: #333;
    font-size: 15px;
}
.page-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: white; padding: 30px 40px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.page-header h1 { margin: 0 0 12px 0; font-size: 1.8em; font-weight: 600; }
.meta-bar { display: flex; gap: 25px; flex-wrap: wrap; font-size: 0.9em; opacity: 0.85; }
.toc {
    background: white; padding: 14px 40px;
    border-bottom: 1px solid #e0e0e0;
    display: flex; gap: 20px; align-items: center;
    position: sticky; top: 0; z-index: 100;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
.toc a {
    color: #1565c0; text-decoration: none; font-size: 0.9em;
    padding: 4px 12px; border-radius: 20px;
    background: #e3f2fd; transition: background 0.2s;
}
.toc a:hover { background: #1565c0; color: white; }
section {
    background: white; margin: 20px 40px;
    border-radius: 10px; padding: 25px 30px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
}
h2 {
    color: #1a237e; font-size: 1.3em;
    border-bottom: 3px solid #3f51b5;
    padding-bottom: 10px; margin-top: 0;
}
h3 { color: #37474f; font-size: 1.05em; margin: 20px 0 10px 0; }
.sub-title { padding: 6px 12px; border-radius: 4px; margin-top: 20px; }
.mod-title { background: #fff3e0; color: #e65100; border-left: 4px solid #ff9800; }
.add-title { background: #e8f5e9; color: #1b5e20; border-left: 4px solid #4caf50; }
.del-title { background: #ffebee; color: #b71c1c; border-left: 4px solid #f44336; }
.ok-title  { background: #e3f2fd; color: #0d47a1; border-left: 4px solid #2196f3; }

.overview-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px; margin-top: 15px;
}
.overview-card {
    border-radius: 10px; padding: 20px;
    border: 1px solid #e0e0e0;
}
.can-card { background: linear-gradient(135deg, #e3f2fd, #f8f9fa); border-color: #90caf9; }
.lin-card { background: linear-gradient(135deg, #e8f5e9, #f8f9fa); border-color: #a5d6a7; }
.card-title { font-size: 1.1em; font-weight: 600; margin-bottom: 15px; color: #37474f; }
.card-stats { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 15px; }
.stat-item { text-align: center; padding: 10px 16px; border-radius: 8px; min-width: 80px; border: 2px solid #1a1a1a; }
.stat-item .num { display: block; font-size: 1.6em; font-weight: bold; }
.stat-item .lbl { font-size: 0.78em; color: #666; }
.stat-item.changed { background: #fff3e0; }
.stat-item.changed .num { color: #e65100; }
.stat-item.ok { background: #e8f5e9; }
.stat-item.ok .num { color: #2e7d32; }
.stat-item.added { background: #f3e5f5; }
.stat-item.added .num { color: #6a1b9a; }
.stat-item.removed { background: #ffebee; }
.stat-item.removed .num { color: #c62828; }
.mini-table { width: 100%; border-collapse: collapse; font-size: 0.88em; }
.mini-table th, .mini-table td { padding: 5px 10px; border: 1px solid #e0e0e0; }
.mini-table th { background: #f5f5f5; color: #1a1a1a; font-weight: 600; }
.mini-table .add { color: #2e7d32; font-weight: bold; }
.mini-table .del { color: #c62828; font-weight: bold; }
.mini-table .mod { color: #e65100; font-weight: bold; }

.stat-row {
    display: flex; gap: 12px; flex-wrap: wrap; margin: 15px 0;
}
.stat-box {
    background: white; border-radius: 8px; padding: 12px 18px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1); text-align: center; min-width: 100px;
    border: 1px solid #e0e0e0;
}
.stat-box .num { display: block; font-size: 1.7em; font-weight: bold; }
.stat-box .lbl { color: #666; font-size: 0.82em; }
.stat-box.changed .num { color: #e65100; }
.stat-box.ok .num { color: #1565c0; }
.stat-box.added .num { color: #2e7d32; }
.stat-box.removed .num { color: #c62828; }

table {
    border-collapse: collapse; width: 100%;
    background: white; margin: 10px 0;
    border-radius: 6px; overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
th {
    background: #455a64; color: white;
    padding: 9px 12px; text-align: left; font-size: 0.88em;
}
td { padding: 7px 12px; border-bottom: 1px solid #f0f0f0; font-size: 0.88em; }
tr:hover td { background: #fafafa; }

.channel-block { margin: 12px 0; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
.channel-header {
    padding: 10px 16px; font-size: 0.95em; display: flex; align-items: center; gap: 10px;
}
.mod-header { background: #fff3e0; border-bottom: 1px solid #ffe0b2; }
.ver-badge {
    font-size: 0.82em; color: #666;
    background: white; padding: 2px 8px; border-radius: 12px;
    border: 1px solid #ddd;
}
.channel-body { padding: 12px 16px; }

.item-row { padding: 5px 8px; margin: 4px 0; border-radius: 4px; font-size: 0.9em; }
.add-row { background: #f1f8e9; border-left: 3px solid #66bb6a; }
.del-row { background: #fce4ec; border-left: 3px solid #ef5350; }
.mod-row { background: #fff8e1; border-left: 3px solid #ffa726; }

.diff-category {
    margin: 12px 0 6px 0; padding: 4px 10px;
    background: #e1bee7; border-radius: 4px;
    font-size: 0.9em; color: #000; font-weight: bold;
}
.change-list { margin: 4px 0 4px 16px; padding: 0; font-size: 0.88em; }
.change-list li { padding: 2px 0; }
.inner-table { width: calc(100% - 16px); margin-left: 16px; font-size: 0.85em; }
.inner-table th { background: #607d8b; }

.tag-add { background: #c8e6c9; color: #1b5e20; padding: 2px 7px; border-radius: 3px; font-size: 0.82em; font-weight: bold; white-space: nowrap; }
.tag-del { background: #ffcdd2; color: #b71c1c; padding: 2px 7px; border-radius: 3px; font-size: 0.82em; font-weight: bold; white-space: nowrap; }
.tag-mod { background: #ffe0b2; color: #e65100; padding: 2px 7px; border-radius: 3px; font-size: 0.82em; font-weight: bold; white-space: nowrap; }
.tag-ok  { background: #bbdefb; color: #0d47a1; padding: 2px 7px; border-radius: 3px; font-size: 0.82em; white-space: nowrap; }

.old-val { background: #ffcdd2; color: #b71c1c; padding: 1px 4px; border-radius: 3px; font-family: monospace; }
.new-val { background: #c8e6c9; color: #1b5e20; padding: 1px 4px; border-radius: 3px; font-family: monospace; }
code { background: #eceff1; padding: 1px 5px; border-radius: 3px; font-family: monospace; font-size: 0.9em; }
a { color: #1565c0; text-decoration: none; }
a:hover { text-decoration: underline; }
.no-data { color: #9e9e9e; font-style: italic; padding: 10px; }
.footer {
    text-align: center; color: #9e9e9e; font-size: 0.8em;
    padding: 20px 40px 30px; margin-top: 10px;
}
@media (max-width: 900px) {
    .overview-grid { grid-template-columns: 1fr; }
    section { margin: 10px 15px; padding: 15px; }
    .page-header { padding: 20px; }
    .toc { padding: 10px 15px; }
}
"""


# =====================================================
# 主流程
# =====================================================

def main():
    # 强制 stdout/stderr 使用 UTF-8，避免 Windows GBK 终端 emoji 乱码
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(
        prog="combined_batch_diff",
        description="CAN/LIN 通信矩阵批量差异分析工具 - 一次运行同时分析 DBC 和 LDF 文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 一次分析两个版本目录下的所有 DBC 和 LDF 文件
  python combined_batch_diff.py 旧版本目录 新版本目录

  # 指定输出目录和格式
  python combined_batch_diff.py 旧版本目录 新版本目录 --output-dir ./diff_out --format all

  # 指定 CAN 文件子目录
  python combined_batch_diff.py 旧版本目录 新版本目录 --can-subdir CAN --lin-subdir LIN
        """
    )
    parser.add_argument("old_dir", help="旧版本目录路径")
    parser.add_argument("new_dir", help="新版本目录路径")
    parser.add_argument("--output-dir", "-o", default="combined_diff_output",
                        help="输出目录（默认: combined_diff_output）")
    parser.add_argument("--format", "-f", default="html",
                        choices=["text", "txt", "markdown", "md", "html", "csv", "json", "all"],
                        help="DBC 详细报告格式（默认: html）")
    parser.add_argument("--can-subdir", default="CAN",
                        help="CAN/DBC 文件所在子目录名（默认: CAN，空字符串表示扫描根目录）")
    parser.add_argument("--lin-subdir", default="",
                        help="LIN/LDF 文件所在子目录名（默认: 空，直接扫描根目录）")

    args = parser.parse_args()
    old_dir = args.old_dir
    new_dir = args.new_dir

    for d in [old_dir, new_dir]:
        if not os.path.isdir(d):
            print(f"[错误] 目录不存在: {d}", file=sys.stderr)
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  通信矩阵综合差异分析（CAN + LIN）")
    print(f"  旧版本: {os.path.basename(old_dir)}")
    print(f"  新版本: {os.path.basename(new_dir)}")
    print(f"{'='*60}\n")

    output_dir = args.output_dir
    can_subdir_out = os.path.join(output_dir, "can")
    lin_subdir_out = os.path.join(output_dir, "lin")

    # ---- Step 1: DBC 批量分析 ----
    print(f"\n{'─'*60}")
    print("  [1/3] 正在分析 CAN 通道（DBC）...")
    print(f"{'─'*60}")

    dbc_batch_result = None
    try:
        dbc_differ = DBCBatchDiff(subdir=args.can_subdir)
        dbc_batch_result = dbc_differ.compare_dirs(old_dir, new_dir)

        # 生成 DBC 独立报告（放到 can/ 子目录）
        dbc_reporter = DBCBatchReportGenerator()
        dbc_reporter.generate(dbc_batch_result, can_subdir_out, args.format)

        print(f"\n  [CAN] 完成: "
              f"{len(dbc_batch_result.compared)} 个通道对比，"
              f"{len(dbc_batch_result.changed)} 个有变更，"
              f"{len(dbc_batch_result.unchanged)} 个无变更")
    except Exception as e:
        print(f"  [CAN] 分析失败: {e}")
        import traceback
        traceback.print_exc()

    # ---- Step 2: LDF 批量分析 ----
    print(f"\n{'─'*60}")
    print("  [2/3] 正在分析 LIN 通道（LDF）...")
    print(f"{'─'*60}")

    ldf_results = []
    ldf_only_old = []   # 仅旧版本存在的LIN通道
    ldf_only_new = []   # 仅新版本存在的LIN通道
    try:
        # 如果指定了 lin-subdir，调整扫描目录
        ldf_old_dir = os.path.join(old_dir, args.lin_subdir) if args.lin_subdir else old_dir
        ldf_new_dir = os.path.join(new_dir, args.lin_subdir) if args.lin_subdir else new_dir

        # 处理子目录不存在的情况
        if args.lin_subdir and not os.path.isdir(ldf_old_dir):
            ldf_old_dir = old_dir
        if args.lin_subdir and not os.path.isdir(ldf_new_dir):
            ldf_new_dir = new_dir

        # 先扫描获取单侧通道信息
        from ldf_batch_diff import scan_ldf_files
        ldf_old_map = scan_ldf_files(ldf_old_dir)
        ldf_new_map = scan_ldf_files(ldf_new_dir)
        ldf_only_old = sorted(set(ldf_old_map.keys()) - set(ldf_new_map.keys()))
        ldf_only_new = sorted(set(ldf_new_map.keys()) - set(ldf_old_map.keys()))

        ldf_batch = LDFBatchDiff()
        ldf_results = ldf_batch.compare_dirs(ldf_old_dir, ldf_new_dir)

        if ldf_results:
            ldf_gen = LDFBatchReportGenerator()
            ldf_gen.generate_all(ldf_results, lin_subdir_out)

        ldf_changed_count = sum(1 for _, r in ldf_results if r.has_changes())
        print(f"\n  [LIN] 完成: "
              f"{len(ldf_results)} 个通道对比，"
              f"{ldf_changed_count} 个有变更，"
              f"{len(ldf_results)-ldf_changed_count} 个无变更，"
              f"仅旧版本 {len(ldf_only_old)} 个，仅新版本 {len(ldf_only_new)} 个")
    except Exception as e:
        print(f"  [LIN] 分析失败: {e}")
        import traceback
        traceback.print_exc()

    # ---- Step 3: 生成综合报告 ----
    print(f"\n{'─'*60}")
    print("  [3/3] 正在生成综合报告...")
    print(f"{'─'*60}")

    # 如果 DBC 分析失败，创建空结果对象
    if dbc_batch_result is None:
        from dbc_batch_diff import BatchDiffResult
        dbc_batch_result = BatchDiffResult(
            old_dir=old_dir,
            new_dir=new_dir,
            channel_results=[]
        )

    combined_gen = CombinedReportGenerator()
    html_path, txt_path = combined_gen.generate(
        dbc_batch_result,
        ldf_results,
        output_dir=output_dir,
        fmt=args.format,
        old_dir=old_dir,
        new_dir=new_dir,
        ldf_only_old=ldf_only_old,
        ldf_only_new=ldf_only_new,
    )

    # ---- 汇总输出 ----
    dbc_changed = len(dbc_batch_result.changed)
    dbc_total = len(dbc_batch_result.compared)
    ldf_changed_count = sum(1 for _, r in ldf_results if r.has_changes())
    ldf_total = len(ldf_results)

    print(f"\n{'='*60}")
    print(f"  [DONE] 综合分析完成！")
    print(f"")
    print(f"  CAN (DBC): {dbc_total} 个通道，{dbc_changed} 个有变更")
    print(f"  LIN (LDF): {ldf_total} 个通道，{ldf_changed_count} 个有变更")
    print(f"")
    print(f"  [HTML] 综合报告: {html_path}")
    print(f"  [TXT]  文本报告: {txt_path}")
    print(f"  [DIR]  CAN详细:  {can_subdir_out}/")
    print(f"  [DIR]  LIN详细:  {lin_subdir_out}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
