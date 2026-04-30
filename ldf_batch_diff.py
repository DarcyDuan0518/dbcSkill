"""
LDF批量差异分析模块 - ldf_batch_diff.py

功能：
  - 扫描两个目录中的LDF文件
  - 按通道名自动匹配（支持命名格式：EEA3.0_LIN_Matrix_V{ver}_{date}_{channel}.ldf）
  - 每个通道取最高版本进行比较
  - 生成批量报告（Text摘要 + 每通道HTML + 总览HTML）

LDF文件命名格式示例：
  EEA3.0_LIN_Matrix_V10.1.0_20260212_LIN11.ldf
  EEA3.0_LIN_Matrix_V10.1.5_20260301_LIN11.ldf
  通道key = "LIN11"
"""

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ldf_parser import LDFParser, LDFFile
from ldf_diff import LDFDiff, LDFDiffResult
from ldf_report import (
    LDFTextReporter, LDFMarkdownReporter, LDFHTMLReporter,
    LDFCSVReporter, LDFJSONReporter, LDFSummaryReporter,
)


# ---------------------------------------------
# 文件信息数据类
# ---------------------------------------------

@dataclass
class LDFFileInfo:
    """LDF文件信息"""
    filepath: str
    filename: str
    version: Tuple[int, ...]   # 版本号元组，如 (10, 1, 5)
    date: str                  # 日期字符串，如 "20260301"
    channel: str               # 通道名，如 "LIN11"
    project: str = ""          # 项目名（可选）
    version_str: str = ""      # 原始版本字符串，如 "V10.1.5"

    def version_display(self) -> str:
        return self.version_str or ".".join(str(v) for v in self.version)


# ---------------------------------------------
# 文件名解析
# ---------------------------------------------

# 支持的命名格式：
#   EEA3.0_LIN_Matrix_V10.1.0_20260212_LIN11.ldf
#   EEA3.0_LIN_Matrix_V10.1.0_20260212_PZBP_LIN11.ldf  (含项目名)
#   任意前缀_V版本_日期_通道.ldf

_LDF_PATTERN = re.compile(
    r"""
    (?P<prefix>[^_]+(?:_[^_]+)*)   # 前缀（可含下划线）
    _V(?P<version>[\d.]+)          # 版本号 V10.1.0
    _(?P<date>\d{8})               # 日期 20260212
    (?:_(?P<project>[A-Za-z0-9]+))? # 可选项目名
    _(?P<channel>LIN\d+)           # 通道名 LIN11
    \.ldf$
    """,
    re.IGNORECASE | re.VERBOSE,
)

# 更宽松的备用模式：只要文件名含 LIN\d+ 就提取通道
_LDF_FALLBACK = re.compile(r'(?:_|^)(LIN\d+)(?:_|\.ldf)', re.IGNORECASE)


def parse_ldf_filename(filepath: str) -> Optional[LDFFileInfo]:
    """
    解析LDF文件名，提取版本、日期、通道等信息。
    返回 LDFFileInfo 或 None（无法解析时）。
    """
    filename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(filename)[0]

    m = _LDF_PATTERN.match(filename)
    if m:
        ver_str = m.group("version")
        ver_tuple = tuple(int(x) for x in ver_str.split("."))
        channel = m.group("channel").upper()
        project = m.group("project") or ""
        return LDFFileInfo(
            filepath=filepath,
            filename=filename,
            version=ver_tuple,
            date=m.group("date"),
            channel=channel,
            project=project,
            version_str=f"V{ver_str}",
        )

    # 备用：尝试提取通道名
    m2 = _LDF_FALLBACK.search(filename)
    if m2:
        channel = m2.group(1).upper()
        # 尝试提取版本
        ver_m = re.search(r'V([\d.]+)', filename, re.IGNORECASE)
        ver_str = ver_m.group(1) if ver_m else "0"
        # 过滤空字符串，避免 int("") 报错
        ver_parts = [x for x in ver_str.split(".") if x]
        ver_tuple = tuple(int(x) for x in ver_parts) if ver_parts else (0,)
        date_m = re.search(r'(\d{8})', filename)
        date_str = date_m.group(1) if date_m else ""
        return LDFFileInfo(
            filepath=filepath,
            filename=filename,
            version=ver_tuple,
            date=date_str,
            channel=channel,
            version_str=f"V{ver_str}" if ver_m else "",
        )

    return None


def scan_ldf_files(directory: str) -> Dict[str, LDFFileInfo]:
    """
    递归扫描目录（含子目录）中的所有LDF文件，按通道名分组，每个通道保留最高版本。
    返回 {channel: LDFFileInfo}
    """
    channel_map: Dict[str, LDFFileInfo] = {}

    if not os.path.isdir(directory):
        raise ValueError(f"目录不存在: {directory}")

    for root, dirs, files in os.walk(directory):
        for fname in files:
            if not fname.lower().endswith(".ldf"):
                continue
            fpath = os.path.join(root, fname)
            info = parse_ldf_filename(fpath)
            if info is None:
                print(f"  [跳过] 无法解析文件名: {fname}")
                continue

            existing = channel_map.get(info.channel)
            if existing is None or info.version > existing.version:
                channel_map[info.channel] = info

    return channel_map


# ---------------------------------------------
# 批量差异分析器
# ---------------------------------------------

class LDFBatchDiff:
    """
    批量LDF差异分析器
    用法：
        batch = LDFBatchDiff()
        results = batch.compare_dirs(old_dir, new_dir)
        # results: List[(channel_name, LDFDiffResult)]
    """

    def compare_dirs(
        self,
        old_dir: str,
        new_dir: str,
    ) -> List[Tuple[str, LDFDiffResult]]:
        """
        比较两个目录中的LDF文件。
        按通道名自动匹配，返回 [(channel, diff_result), ...]
        """
        print(f"[扫描] 旧目录: {old_dir}")
        old_map = scan_ldf_files(old_dir)
        print(f"  找到 {len(old_map)} 个通道: {', '.join(sorted(old_map.keys()))}")

        print(f"[扫描] 新目录: {new_dir}")
        new_map = scan_ldf_files(new_dir)
        print(f"  找到 {len(new_map)} 个通道: {', '.join(sorted(new_map.keys()))}")

        # 找出共同通道
        common = sorted(set(old_map.keys()) & set(new_map.keys()))
        only_old = sorted(set(old_map.keys()) - set(new_map.keys()))
        only_new = sorted(set(new_map.keys()) - set(old_map.keys()))

        if only_old:
            print(f"[提示] 仅在旧目录中存在的通道: {', '.join(only_old)}")
        if only_new:
            print(f"[提示] 仅在新目录中存在的通道: {', '.join(only_new)}")
        print(f"[匹配] 共 {len(common)} 个通道将进行比较")

        parser = LDFParser()
        differ = LDFDiff()
        results = []

        for channel in common:
            old_info = old_map[channel]
            new_info = new_map[channel]
            print(f"  [{channel}] {old_info.version_display()} -> {new_info.version_display()}")

            try:
                old_ldf = parser.parse_file(old_info.filepath)
                new_ldf = parser.parse_file(new_info.filepath)
                diff_result = differ.compare(old_ldf, new_ldf)
                results.append((channel, diff_result))
            except Exception as e:
                print(f"  [错误] {channel} 比较失败: {e}")

        return results

    def compare_files_list(
        self,
        file_pairs: List[Tuple[str, str]],
    ) -> List[Tuple[str, LDFDiffResult]]:
        """
        直接指定文件对进行比较。
        file_pairs: [(old_path, new_path), ...]
        返回 [(channel_name, diff_result), ...]
        """
        parser = LDFParser()
        differ = LDFDiff()
        results = []

        for old_path, new_path in file_pairs:
            channel = os.path.splitext(os.path.basename(new_path))[0]
            info = parse_ldf_filename(new_path)
            if info:
                channel = info.channel

            print(f"  [{channel}] {os.path.basename(old_path)} -> {os.path.basename(new_path)}")
            try:
                old_ldf = parser.parse_file(old_path)
                new_ldf = parser.parse_file(new_path)
                diff_result = differ.compare(old_ldf, new_ldf)
                results.append((channel, diff_result))
            except Exception as e:
                print(f"  [错误] {channel} 比较失败: {e}")

        return results


# ---------------------------------------------
# 批量报告生成器
# ---------------------------------------------

class BatchReportGenerator:
    """
    批量报告生成器
    为每个通道生成独立报告，并生成总览摘要
    """

    def generate_all(
        self,
        results: List[Tuple[str, LDFDiffResult]],
        output_dir: str,
    ):
        """
        生成所有报告：
        - {output_dir}/summary.txt        总览文本摘要
        - {output_dir}/summary.html       总览HTML摘要
        - {output_dir}/{channel}_diff.html  每通道HTML报告
        - {output_dir}/{channel}_diff.txt   每通道文本报告（仅有变更的）
        """
        os.makedirs(output_dir, exist_ok=True)

        text_reporter = LDFTextReporter()
        html_reporter = LDFHTMLReporter()
        summary_reporter = LDFSummaryReporter()

        # 生成每通道报告
        for channel, diff_result in results:
            safe_channel = re.sub(r'[^\w\-]', '_', channel)

            # HTML报告（每个通道都生成）
            html_path = os.path.join(output_dir, f"{safe_channel}_diff.html")
            html_reporter.save(diff_result, html_path)

            # 文本报告（仅有变更的通道）
            if diff_result.has_changes():
                txt_path = os.path.join(output_dir, f"{safe_channel}_diff.txt")
                text_reporter.save(diff_result, txt_path)

        # 生成总览摘要
        summary_txt_path = os.path.join(output_dir, "summary.txt")
        summary_reporter.save_text(results, summary_txt_path)

        summary_html_path = os.path.join(output_dir, "summary.html")
        summary_reporter.save_html(results, summary_html_path)

        # 统计
        changed = [(ch, r) for ch, r in results if r.has_changes()]
        unchanged = [(ch, r) for ch, r in results if not r.has_changes()]

        print(f"\n[报告] 已生成到: {output_dir}/")
        print(f"  总览: summary.txt, summary.html")
        print(f"  有变更通道 ({len(changed)}): " +
              ", ".join(ch for ch, _ in changed) if changed else "  无变更通道")
        print(f"  无变更通道 ({len(unchanged)}): " +
              ", ".join(ch for ch, _ in unchanged) if unchanged else "")

        return {
            "output_dir": output_dir,
            "total": len(results),
            "changed": len(changed),
            "unchanged": len(unchanged),
            "changed_channels": [ch for ch, _ in changed],
        }

    def generate_csv_summary(
        self,
        results: List[Tuple[str, LDFDiffResult]],
        output_path: str,
    ):
        """生成CSV格式的批量摘要（便于Excel分析）"""
        import csv
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "通道", "状态",
                "节点新增", "节点删除", "节点修改",
                "帧新增", "帧删除", "帧修改",
                "信号新增", "信号删除", "信号修改",
                "调度表新增", "调度表删除", "调度表修改",
                "旧文件", "新文件",
            ])
            for channel, r in results:
                stats = r.stats()
                status = "有变更" if r.has_changes() else "无变更"
                writer.writerow([
                    channel, status,
                    stats["nodes_added"], stats["nodes_removed"], stats["nodes_modified"],
                    stats["frames_added"], stats["frames_removed"], stats["frames_modified"],
                    stats["signals_added"], stats["signals_removed"], stats["signals_modified"],
                    stats["schedules_added"], stats["schedules_removed"], stats["schedules_modified"],
                    r.old_file, r.new_file,
                ])
        print(f"[报告] CSV摘要已保存: {output_path}")


# ---------------------------------------------
# 命令行入口（独立运行）
# ---------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="LDF批量差异分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python ldf_batch_diff.py old_dir/ new_dir/
  python ldf_batch_diff.py old_dir/ new_dir/ -o my_output/
        """,
    )
    parser.add_argument("old_dir", help="旧版本LDF文件目录")
    parser.add_argument("new_dir", help="新版本LDF文件目录")
    parser.add_argument("-o", "--output", default="ldf_batch_output",
                        help="输出目录 (默认: ldf_batch_output)")
    parser.add_argument("--csv", action="store_true",
                        help="额外生成CSV摘要文件")

    args = parser.parse_args()

    batch = LDFBatchDiff()
    results = batch.compare_dirs(args.old_dir, args.new_dir)

    if not results:
        print("[警告] 未找到可匹配的LDF文件对")
        exit(0)

    gen = BatchReportGenerator()
    summary = gen.generate_all(results, args.output)

    if args.csv:
        csv_path = os.path.join(args.output, "summary.csv")
        gen.generate_csv_summary(results, csv_path)

    print(f"\n[PASS] 完成！共 {summary['total']} 个通道，"
          f"{summary['changed']} 个有变更，{summary['unchanged']} 个无变更")
