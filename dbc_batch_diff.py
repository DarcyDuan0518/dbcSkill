"""
DBC批量差异对比工具 - dbc_batch_diff.py

功能：
  - 扫描两个版本目录下的所有DBC文件
  - 按"项目名_通道名"（如 PZCU_CHCAN1）自动匹配同通道文件
  - 每个通道取版本号最高的DBC文件进行对比
  - 生成每个通道的详细差异报告 + 汇总总览报告

文件命名规律（支持）：
  EEA3.0_CAN_Matrix_V{版本}_{日期}_{项目}_{通道}.dbc
  例：EEA3.0_CAN_Matrix_V10.1.5_20260422_PZCU_CHCAN1.dbc

用法：
  python dbc_batch_diff.py <旧版本目录> <新版本目录> [--output-dir <输出目录>] [--format html]
  python dbc_batch_diff.py <旧版本目录> <新版本目录> --can-subdir CAN

示例：
  python dbc_batch_diff.py ^
    "PZBP3.1.8通信矩阵_CAN_V10.1.7_SOA_V10.1.10_0409" ^
    "PZBP3.1.8通信矩阵_CAN_V10.1.7_SOA_V10.1.10_0422" ^
    --output-dir diff_output --format all
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dbc_parser import DBCParser
from dbc_diff import DBCDiff, DBCDiffResult
from dbc_report import (
    TextReporter, MarkdownReporter, HTMLReporter,
    CSVReporter, JSONReporter, DBCSummaryReporter
)


# ---------------------------------------------
# DBC文件信息
# ---------------------------------------------

@dataclass
class DBCFileInfo:
    """DBC文件的解析信息"""
    filepath: str
    filename: str
    channel_key: str    # 匹配键，如 "PZCU_CHCAN1"
    project: str        # 项目名，如 "PZCU"
    channel: str        # 通道名，如 "CHCAN1"
    version: str        # 版本号，如 "10.1.5"
    date: str           # 日期，如 "20260422"
    version_tuple: tuple  # 用于排序的版本元组，如 (10, 1, 5)


def parse_dbc_filename(filepath: str) -> Optional[DBCFileInfo]:
    """
    解析DBC文件名，提取版本、日期、项目、通道信息。

    支持格式：
      EEA3.0_CAN_Matrix_V{ver}_{date}_{project}_{channel}.dbc
      任意前缀_V{ver}_{date}_{project}_{channel}.dbc
      {project}_{channel}.dbc  （简单格式）
    """
    fname = os.path.basename(filepath)
    stem = os.path.splitext(fname)[0]  # 去掉.dbc后缀

    # 主格式：含版本和日期
    # 例：EEA3.0_CAN_Matrix_V10.1.5_20260422_PZCU_CHCAN1
    m = re.search(
        r'_V(\d+\.\d+(?:\.\d+)*)_(\d{6,8})_([A-Za-z0-9]+)_([A-Za-z0-9]+)$',
        stem
    )
    if m:
        ver_str = m.group(1)
        date_str = m.group(2)
        project = m.group(3)
        channel = m.group(4)
        ver_tuple = tuple(int(x) for x in ver_str.split('.'))
        return DBCFileInfo(
            filepath=filepath,
            filename=fname,
            channel_key=f"{project}_{channel}",
            project=project,
            channel=channel,
            version=ver_str,
            date=date_str,
            version_tuple=ver_tuple
        )

    # 备用格式：只有项目_通道（无版本日期）
    # 例：PZCU_CHCAN1.dbc
    m2 = re.match(r'^([A-Za-z0-9]+)_([A-Za-z0-9]+)$', stem)
    if m2:
        project = m2.group(1)
        channel = m2.group(2)
        return DBCFileInfo(
            filepath=filepath,
            filename=fname,
            channel_key=f"{project}_{channel}",
            project=project,
            channel=channel,
            version="0.0.0",
            date="00000000",
            version_tuple=(0, 0, 0)
        )

    return None


def scan_dbc_files(directory: str, subdir: str = "CAN") -> Dict[str, DBCFileInfo]:
    """
    扫描目录下的DBC文件，按通道键分组，每个通道只保留版本最高的文件。

    Args:
        directory: 根目录（如版本文件夹）
        subdir: CAN文件所在子目录名（默认"CAN"），为空则扫描整个目录

    Returns:
        Dict[channel_key, DBCFileInfo]  每个通道的最新版本文件
    """
    scan_root = os.path.join(directory, subdir) if subdir else directory
    if not os.path.isdir(scan_root):
        # 如果子目录不存在，直接扫描根目录
        scan_root = directory

    channel_map: Dict[str, DBCFileInfo] = {}

    for root, dirs, files in os.walk(scan_root):
        for fname in files:
            if not fname.lower().endswith('.dbc'):
                continue
            fpath = os.path.join(root, fname)
            info = parse_dbc_filename(fpath)
            if info is None:
                continue

            key = info.channel_key
            # 保留版本最高的文件（版本相同时保留日期最新的）
            if key not in channel_map:
                channel_map[key] = info
            else:
                existing = channel_map[key]
                if (info.version_tuple > existing.version_tuple or
                        (info.version_tuple == existing.version_tuple and
                         info.date > existing.date)):
                    channel_map[key] = info

    return channel_map


# ---------------------------------------------
# 批量对比结果
# ---------------------------------------------

@dataclass
class ChannelDiffResult:
    """单个通道的对比结果"""
    channel_key: str
    project: str
    channel: str
    old_file: str
    new_file: str
    old_version: str
    new_version: str
    diff_result: Optional[DBCDiffResult]
    error: str = ""

    @property
    def has_changes(self) -> bool:
        return self.diff_result is not None and self.diff_result.has_changes()

    @property
    def stats(self) -> dict:
        if self.diff_result:
            return self.diff_result.stats()
        return {}


@dataclass
class BatchDiffResult:
    """批量对比的完整结果"""
    old_dir: str
    new_dir: str
    channel_results: List[ChannelDiffResult]

    @property
    def only_in_old(self) -> List[str]:
        """只在旧版本中存在的通道"""
        return [r.channel_key for r in self.channel_results if r.error == "only_in_old"]

    @property
    def only_in_new(self) -> List[str]:
        """只在新版本中存在的通道"""
        return [r.channel_key for r in self.channel_results if r.error == "only_in_new"]

    @property
    def compared(self) -> List[ChannelDiffResult]:
        """成功对比的通道"""
        return [r for r in self.channel_results if r.diff_result is not None]

    @property
    def changed(self) -> List[ChannelDiffResult]:
        """有变更的通道"""
        return [r for r in self.compared if r.has_changes]

    @property
    def unchanged(self) -> List[ChannelDiffResult]:
        """无变更的通道"""
        return [r for r in self.compared if not r.has_changes]


# ---------------------------------------------
# 批量对比器
# ---------------------------------------------

class DBCBatchDiff:
    """批量DBC差异对比器"""

    def __init__(self, subdir: str = "CAN"):
        self.subdir = subdir
        self._parser = DBCParser()
        self._differ = DBCDiff()

    def compare_dirs(self, old_dir: str, new_dir: str) -> BatchDiffResult:
        """
        对比两个版本目录下的所有DBC文件。
        按通道名匹配，每个通道取版本最高的文件。
        """
        print(f"扫描旧版本目录: {old_dir}")
        old_map = scan_dbc_files(old_dir, self.subdir)
        print(f"  找到 {len(old_map)} 个通道: {', '.join(sorted(old_map.keys()))}")

        print(f"扫描新版本目录: {new_dir}")
        new_map = scan_dbc_files(new_dir, self.subdir)
        print(f"  找到 {len(new_map)} 个通道: {', '.join(sorted(new_map.keys()))}")

        all_keys = sorted(set(old_map.keys()) | set(new_map.keys()))
        results = []

        for key in all_keys:
            in_old = key in old_map
            in_new = key in new_map

            if in_old and not in_new:
                info = old_map[key]
                results.append(ChannelDiffResult(
                    channel_key=key,
                    project=info.project,
                    channel=info.channel,
                    old_file=info.filepath,
                    new_file="",
                    old_version=info.version,
                    new_version="",
                    diff_result=None,
                    error="only_in_old"
                ))
                print(f"  [仅旧版本] {key}  ({info.filename})")
                continue

            if not in_old and in_new:
                info = new_map[key]
                results.append(ChannelDiffResult(
                    channel_key=key,
                    project=info.project,
                    channel=info.channel,
                    old_file="",
                    new_file=info.filepath,
                    old_version="",
                    new_version=info.version,
                    diff_result=None,
                    error="only_in_new"
                ))
                print(f"  [仅新版本] {key}  ({info.filename})")
                continue

            # 两个版本都有，进行对比
            old_info = old_map[key]
            new_info = new_map[key]

            # 如果是同一个文件（路径相同），跳过
            if os.path.abspath(old_info.filepath) == os.path.abspath(new_info.filepath):
                print(f"  [跳过-同文件] {key}")
                continue

            try:
                old_dbc = self._parser.parse_file(old_info.filepath)
                new_dbc = self._parser.parse_file(new_info.filepath)
                diff = self._differ.compare(old_dbc, new_dbc)

                cr = ChannelDiffResult(
                    channel_key=key,
                    project=old_info.project,
                    channel=old_info.channel,
                    old_file=old_info.filepath,
                    new_file=new_info.filepath,
                    old_version=old_info.version,
                    new_version=new_info.version,
                    diff_result=diff
                )
                results.append(cr)

                if diff.has_changes():
                    stats = diff.stats()
                    print(f"  [有变更] {key}  "
                          f"V{old_info.version}->V{new_info.version}  "
                          f"报文+{stats['msgs_added']}/-{stats['msgs_removed']}/~{stats['msgs_modified']}  "
                          f"信号+{stats['sigs_added']}/-{stats['sigs_removed']}/~{stats['sigs_modified']}")
                else:
                    print(f"  [无变更] {key}  V{old_info.version}->V{new_info.version}")

            except Exception as e:
                results.append(ChannelDiffResult(
                    channel_key=key,
                    project=old_info.project,
                    channel=old_info.channel,
                    old_file=old_info.filepath,
                    new_file=new_info.filepath,
                    old_version=old_info.version,
                    new_version=new_info.version,
                    diff_result=None,
                    error=f"解析错误: {e}"
                ))
                print(f"  [错误] {key}: {e}")

        return BatchDiffResult(
            old_dir=old_dir,
            new_dir=new_dir,
            channel_results=results
        )


# ---------------------------------------------
# 批量报告生成器
# ---------------------------------------------

class BatchReportGenerator:
    """批量报告生成器"""

    def generate(self, batch: BatchDiffResult, output_dir: str, fmt: str = "html"):
        """
        生成批量对比报告。
        - 每个有变更的通道生成独立报告
        - 生成一份汇总总览报告
        """
        os.makedirs(output_dir, exist_ok=True)

        old_name = os.path.basename(batch.old_dir.rstrip('/\\'))
        new_name = os.path.basename(batch.new_dir.rstrip('/\\'))

        generated = []

        # 1. 为每个有变更的通道生成详细报告
        for cr in batch.changed:
            if cr.diff_result is None:
                continue
            safe_key = cr.channel_key.replace('/', '_').replace('\\', '_')
            base = f"diff_{safe_key}"

            if fmt in ('html', 'all'):
                path = os.path.join(output_dir, f"{base}.html")
                HTMLReporter().save(cr.diff_result, path)
                generated.append(path)

            if fmt in ('markdown', 'md', 'all'):
                path = os.path.join(output_dir, f"{base}.md")
                MarkdownReporter().save(cr.diff_result, path)
                generated.append(path)

            if fmt in ('text', 'txt', 'all'):
                path = os.path.join(output_dir, f"{base}.txt")
                TextReporter().save(cr.diff_result, path)
                generated.append(path)

            if fmt in ('csv', 'all'):
                path = os.path.join(output_dir, f"{base}.csv")
                CSVReporter().save(cr.diff_result, path)
                generated.append(path)

            if fmt in ('json', 'all'):
                path = os.path.join(output_dir, f"{base}.json")
                JSONReporter().save(cr.diff_result, path)
                generated.append(path)

        # 2. 生成汇总HTML总览报告
        summary_html = os.path.join(output_dir, "batch_summary.html")
        self._generate_summary_html(batch, summary_html, fmt)
        generated.append(summary_html)

        # 3. 生成汇总文本报告
        summary_txt = os.path.join(output_dir, "batch_summary.txt")
        self._generate_summary_text(batch, summary_txt)
        generated.append(summary_txt)

        print(f"\n[PASS] 批量报告生成完成，共 {len(generated)} 个文件")
        print(f"   输出目录: {output_dir}")
        print(f"   汇总报告: {summary_html}")
        return generated

    def _generate_summary_text(self, batch: BatchDiffResult, filepath: str):
        """生成文本汇总报告"""
        from datetime import datetime
        lines = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        old_name = os.path.basename(batch.old_dir.rstrip('/\\'))
        new_name = os.path.basename(batch.new_dir.rstrip('/\\'))

        lines.append("=" * 72)
        lines.append("  DBC 批量差异对比 - 汇总报告")
        lines.append(f"  生成时间: {now}")
        lines.append(f"  旧版本目录: {old_name}")
        lines.append(f"  新版本目录: {new_name}")
        lines.append("=" * 72)

        lines.append(f"\n【总览】")
        lines.append(f"  对比通道数: {len(batch.compared)}")
        lines.append(f"  有变更通道: {len(batch.changed)}")
        lines.append(f"  无变更通道: {len(batch.unchanged)}")
        lines.append(f"  仅旧版本有: {len(batch.only_in_old)}")
        lines.append(f"  仅新版本有: {len(batch.only_in_new)}")

        if batch.only_in_old:
            lines.append(f"\n【仅旧版本存在的通道】")
            for key in batch.only_in_old:
                lines.append(f"  [x] {key}")

        if batch.only_in_new:
            lines.append(f"\n【仅新版本存在的通道】")
            for key in batch.only_in_new:
                lines.append(f"  [+] {key}")

        if batch.changed:
            lines.append(f"\n【有变更的通道】")
            for cr in sorted(batch.changed, key=lambda x: x.channel_key):
                stats = cr.stats
                lines.append(f"\n  [~] {cr.channel_key}  "
                              f"V{cr.old_version} -> V{cr.new_version}")
                lines.append(f"     旧文件: {os.path.basename(cr.old_file)}")
                lines.append(f"     新文件: {os.path.basename(cr.new_file)}")
                lines.append(f"     节点: +{stats.get('nodes_added',0)}/-{stats.get('nodes_removed',0)}")
                lines.append(f"     报文: +{stats.get('msgs_added',0)}/-{stats.get('msgs_removed',0)}/~{stats.get('msgs_modified',0)}")
                lines.append(f"     信号: +{stats.get('sigs_added',0)}/-{stats.get('sigs_removed',0)}/~{stats.get('sigs_modified',0)}")

                # 打印具体变更摘要
                diff = cr.diff_result
                for mc in diff.added_messages:
                    lines.append(f"       [+] 新增报文: {mc.msg_name} ({mc.can_id_hex})")
                for mc in diff.removed_messages:
                    lines.append(f"       [x] 删除报文: {mc.msg_name} ({mc.can_id_hex})")
                for mc in diff.modified_messages:
                    lines.append(f"       [~] 修改报文: {mc.msg_name} ({mc.can_id_hex})")
                    for sc in mc.signal_changes:
                        icon = {"ADDED": "[+]", "REMOVED": "[x]", "MODIFIED": "[~]"}.get(sc.change_type, "?")
                        label = {"ADDED": "新增", "REMOVED": "删除", "MODIFIED": "修改"}.get(sc.change_type, sc.change_type)
                        lines.append(f"           {icon} [{label}信号] {sc.signal_name}")
                        for fc in sc.field_changes:
                            lines.append(f"               {fc.field_name}: {fc.old_value!r} -> {fc.new_value!r}")

        if batch.unchanged:
            lines.append(f"\n【无变更的通道】")
            for cr in sorted(batch.unchanged, key=lambda x: x.channel_key):
                lines.append(f"  [PASS] {cr.channel_key}  V{cr.old_version} -> V{cr.new_version}")

        lines.append("\n" + "=" * 72)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"[BatchReport] 文本汇总已保存: {filepath}")

    def _generate_summary_html(self, batch: BatchDiffResult, filepath: str, fmt: str = "html"):
        """生成HTML汇总总览报告（含各通道链接）"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        old_name = os.path.basename(batch.old_dir.rstrip('/\\'))
        new_name = os.path.basename(batch.new_dir.rstrip('/\\'))

        css = """
        body{font-family:'Segoe UI',Arial,sans-serif;margin:20px;background:#f5f5f5;color:#333}
        h1{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px}
        h2{color:#2980b9;margin-top:25px}
        .meta{background:#ecf0f1;padding:10px 15px;border-radius:5px;margin-bottom:20px}
        .stats{display:flex;gap:15px;flex-wrap:wrap;margin:15px 0}
        .stat-box{background:white;border-radius:8px;padding:12px 18px;box-shadow:0 2px 5px rgba(0,0,0,.1);text-align:center;min-width:100px}
        .stat-box .num{font-size:1.8em;font-weight:bold}
        .stat-box .lbl{color:#666;font-size:.85em}
        .changed .num{color:#e67e22} .added .num{color:#27ae60} .removed .num{color:#e74c3c} .ok .num{color:#95a5a6}
        table{border-collapse:collapse;width:100%;background:white;border-radius:5px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);margin:10px 0}
        th{background:#3498db;color:white;padding:9px 12px;text-align:left;font-size:.9em}
        td{padding:7px 12px;border-bottom:1px solid #ecf0f1;font-size:.9em}
        tr:hover td{background:#f8f9fa}
        .tag-add{background:#d5f5e3;color:#1e8449;padding:2px 7px;border-radius:3px;font-weight:bold;font-size:.85em}
        .tag-del{background:#fadbd8;color:#922b21;padding:2px 7px;border-radius:3px;font-weight:bold;font-size:.85em}
        .tag-mod{background:#fef9e7;color:#9a7d0a;padding:2px 7px;border-radius:3px;font-weight:bold;font-size:.85em}
        .tag-ok{background:#eaf4fb;color:#1a5276;padding:2px 7px;border-radius:3px;font-size:.85em}
        .tag-only{background:#f5eef8;color:#6c3483;padding:2px 7px;border-radius:3px;font-size:.85em}
        a{color:#2980b9;text-decoration:none} a:hover{text-decoration:underline}
        code{background:#ecf0f1;padding:1px 5px;border-radius:3px;font-family:monospace;font-size:.9em}
        """

        html = [f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>DBC批量差异对比汇总</title>
<style>{css}</style></head>
<body>
<h1> DBC 批量差异对比 - 汇总报告</h1>
<div class="meta">
  <strong>生成时间:</strong> {now}<br>
  <strong>旧版本目录:</strong> <code>{old_name}</code><br>
  <strong>新版本目录:</strong> <code>{new_name}</code>
</div>
"""]

        # 统计卡片
        html.append('<div class="stats">')
        html.append(f'<div class="stat-box changed"><div class="num">{len(batch.changed)}</div><div class="lbl">有变更通道</div></div>')
        html.append(f'<div class="stat-box ok"><div class="num">{len(batch.unchanged)}</div><div class="lbl">无变更通道</div></div>')
        html.append(f'<div class="stat-box added"><div class="num">{len(batch.only_in_new)}</div><div class="lbl">仅新版本有</div></div>')
        html.append(f'<div class="stat-box removed"><div class="num">{len(batch.only_in_old)}</div><div class="lbl">仅旧版本有</div></div>')
        html.append('</div>')

        # 仅旧版本存在
        if batch.only_in_old:
            html.append('<h2>[x] 仅旧版本存在的通道（新版本已删除）</h2>')
            html.append('<table><tr><th>通道</th><th>旧版本文件</th></tr>')
            for cr in [r for r in batch.channel_results if r.error == "only_in_old"]:
                html.append(f'<tr><td><span class="tag-del">已删除</span> <strong>{cr.channel_key}</strong></td>'
                             f'<td><code>{os.path.basename(cr.old_file)}</code></td></tr>')
            html.append('</table>')

        # 仅新版本存在
        if batch.only_in_new:
            html.append('<h2>[+] 仅新版本存在的通道（新增通道）</h2>')
            html.append('<table><tr><th>通道</th><th>新版本文件</th></tr>')
            for cr in [r for r in batch.channel_results if r.error == "only_in_new"]:
                html.append(f'<tr><td><span class="tag-add">新增</span> <strong>{cr.channel_key}</strong></td>'
                             f'<td><code>{os.path.basename(cr.new_file)}</code></td></tr>')
            html.append('</table>')

        # 有变更通道
        if batch.changed:
            html.append('<h2>[~] 有变更的通道</h2>')
            html.append('<table><tr><th>通道</th><th>旧版本</th><th>新版本</th>'
                        '<th>报文变更</th><th>信号变更</th><th>详细报告</th></tr>')
            for cr in sorted(batch.changed, key=lambda x: x.channel_key):
                stats = cr.stats
                safe_key = cr.channel_key.replace('/', '_').replace('\\', '_')
                # 报告链接
                links = []
                if fmt in ('html', 'all'):
                    links.append(f'<a href="diff_{safe_key}.html">HTML</a>')
                if fmt in ('markdown', 'md', 'all'):
                    links.append(f'<a href="diff_{safe_key}.md">MD</a>')
                if fmt in ('csv', 'all'):
                    links.append(f'<a href="diff_{safe_key}.csv">CSV</a>')
                if fmt in ('text', 'txt', 'all'):
                    links.append(f'<a href="diff_{safe_key}.txt">TXT</a>')
                link_str = ' | '.join(links) if links else '-'

                msg_str = (f'<span class="tag-add">+{stats.get("msgs_added",0)}</span> '
                           f'<span class="tag-del">-{stats.get("msgs_removed",0)}</span> '
                           f'<span class="tag-mod">~{stats.get("msgs_modified",0)}</span>')
                sig_str = (f'<span class="tag-add">+{stats.get("sigs_added",0)}</span> '
                           f'<span class="tag-del">-{stats.get("sigs_removed",0)}</span> '
                           f'<span class="tag-mod">~{stats.get("sigs_modified",0)}</span>')

                html.append(f'<tr>'
                             f'<td><strong>{cr.channel_key}</strong></td>'
                             f'<td><code>V{cr.old_version}</code><br><small>{os.path.basename(cr.old_file)}</small></td>'
                             f'<td><code>V{cr.new_version}</code><br><small>{os.path.basename(cr.new_file)}</small></td>'
                             f'<td>{msg_str}</td>'
                             f'<td>{sig_str}</td>'
                             f'<td>{link_str}</td>'
                             f'</tr>')
            html.append('</table>')

            # 变更详情展开
            html.append('<h2>📋 变更详情</h2>')
            for cr in sorted(batch.changed, key=lambda x: x.channel_key):
                diff = cr.diff_result
                html.append(f'<h3 style="color:#e67e22">[~] {cr.channel_key} '
                             f'<small style="color:#888;font-weight:normal">'
                             f'V{cr.old_version} -> V{cr.new_version}</small></h3>')

                # 新增报文
                for mc in diff.added_messages:
                    msg = mc.new_message
                    html.append(f'<p><span class="tag-add">新增报文</span> '
                                 f'<strong>{mc.msg_name}</strong> <code>{mc.can_id_hex}</code> '
                                 f'DLC={msg.dlc} 发送={msg.sender} 信号数={len(msg.signals)}</p>')

                # 删除报文
                for mc in diff.removed_messages:
                    msg = mc.old_message
                    html.append(f'<p><span class="tag-del">删除报文</span> '
                                 f'<strong>{mc.msg_name}</strong> <code>{mc.can_id_hex}</code> '
                                 f'DLC={msg.dlc} 发送={msg.sender}</p>')

                # 修改报文
                for mc in diff.modified_messages:
                    html.append(f'<p><span class="tag-mod">修改报文</span> '
                                 f'<strong>{mc.msg_name}</strong> <code>{mc.can_id_hex}</code></p>')
                    if mc.field_changes:
                        html.append('<ul>')
                        for fc in mc.field_changes:
                            html.append(f'<li>报文属性 <em>{fc.field_name}</em>: '
                                        f'<code>{fc.old_value}</code> -> <code>{fc.new_value}</code></li>')
                        html.append('</ul>')
                    if mc.signal_changes:
                        html.append('<table style="margin-left:20px;width:calc(100% - 20px)">'
                                    '<tr><th>变更类型</th><th>信号名</th><th>变更字段</th></tr>')
                        for sc in mc.signal_changes:
                            tag = {"ADDED": "tag-add", "REMOVED": "tag-del", "MODIFIED": "tag-mod"}.get(sc.change_type, "")
                            label = {"ADDED": "新增", "REMOVED": "删除", "MODIFIED": "修改"}.get(sc.change_type, sc.change_type)
                            field_str = "; ".join(
                                f"{fc.field_name}: <code>{fc.old_value}</code>-><code>{fc.new_value}</code>"
                                for fc in sc.field_changes
                            ) or "-"
                            html.append(f'<tr><td><span class="{tag}">{label}</span></td>'
                                        f'<td><strong>{sc.signal_name}</strong></td>'
                                        f'<td>{field_str}</td></tr>')
                        html.append('</table>')

        # 无变更通道
        if batch.unchanged:
            html.append('<h2>[PASS] 无变更的通道</h2>')
            html.append('<table><tr><th>通道</th><th>旧版本文件</th><th>新版本文件</th></tr>')
            for cr in sorted(batch.unchanged, key=lambda x: x.channel_key):
                html.append(f'<tr><td><span class="tag-ok">无变更</span> {cr.channel_key}</td>'
                             f'<td><code>{os.path.basename(cr.old_file)}</code></td>'
                             f'<td><code>{os.path.basename(cr.new_file)}</code></td></tr>')
            html.append('</table>')

        html.append('</body></html>')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(''.join(html))
        print(f"[BatchReport] HTML汇总已保存: {filepath}")


# ---------------------------------------------
# CLI 入口
# ---------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="dbc_batch_diff",
        description="DBC批量差异对比工具 - 按通道名自动匹配，对比两个版本目录",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 对比两个版本目录（CAN子目录下的DBC文件）
  python dbc_batch_diff.py 旧版本目录 新版本目录

  # 指定输出目录和格式
  python dbc_batch_diff.py 旧版本目录 新版本目录 --output-dir ./diff_out --format all

  # 指定CAN文件所在子目录（默认为CAN）
  python dbc_batch_diff.py 旧版本目录 新版本目录 --can-subdir CAN

  # 直接扫描根目录（不进入子目录）
  python dbc_batch_diff.py 旧版本目录 新版本目录 --can-subdir ""
        """
    )
    parser.add_argument("old_dir", help="旧版本目录路径")
    parser.add_argument("new_dir", help="新版本目录路径")
    parser.add_argument("--output-dir", "-o", default="batch_diff_output",
                        help="输出目录（默认: batch_diff_output）")
    parser.add_argument("--format", "-f", default="html",
                        choices=["text", "txt", "markdown", "md", "html", "csv", "json", "all"],
                        help="报告格式（默认: html）")
    parser.add_argument("--can-subdir", default="CAN",
                        help="CAN文件所在子目录名（默认: CAN，空字符串表示直接扫描根目录）")

    args = parser.parse_args()

    old_dir = args.old_dir
    new_dir = args.new_dir

    for d in [old_dir, new_dir]:
        if not os.path.isdir(d):
            print(f"[错误] 目录不存在: {d}", file=sys.stderr)
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  DBC 批量差异对比")
    print(f"  旧版本: {os.path.basename(old_dir)}")
    print(f"  新版本: {os.path.basename(new_dir)}")
    print(f"{'='*60}\n")

    differ = DBCBatchDiff(subdir=args.can_subdir)
    batch_result = differ.compare_dirs(old_dir, new_dir)

    print(f"\n{'-'*60}")
    print(f"  对比完成: {len(batch_result.compared)} 个通道")
    print(f"  有变更: {len(batch_result.changed)}  无变更: {len(batch_result.unchanged)}")
    print(f"  仅旧版本: {len(batch_result.only_in_old)}  仅新版本: {len(batch_result.only_in_new)}")
    print(f"{'-'*60}\n")

    reporter = BatchReportGenerator()
    reporter.generate(batch_result, args.output_dir, args.format)


if __name__ == "__main__":
    main()
