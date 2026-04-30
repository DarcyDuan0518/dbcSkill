"""
LDF分析工具 CLI入口 - ldf_main.py

用法示例：
  # 比较两个LDF文件，输出文本报告
  python ldf_main.py diff old.ldf new.ldf

  # 输出HTML报告到指定文件
  python ldf_main.py diff old.ldf new.ldf -f html -o report.html

  # 查看单个LDF文件信息
  python ldf_main.py info file.ldf

  # 导出LDF文件为JSON
  python ldf_main.py export file.ldf -o output.json

  # 批量比较两个目录
  python ldf_main.py batch old_dir/ new_dir/ -o batch_output/
"""

import argparse
import os
import sys

from ldf_parser import LDFParser
from ldf_diff import LDFDiff
from ldf_report import (
    LDFTextReporter, LDFMarkdownReporter, LDFHTMLReporter,
    LDFCSVReporter, LDFJSONReporter, LDFInfoReporter,
)


# ---------------------------------------------
# 子命令：diff
# ---------------------------------------------

def cmd_diff(args):
    """比较两个LDF文件"""
    parser = LDFParser()

    print(f"[解析] {args.old_file}")
    try:
        old_ldf = parser.parse_file(args.old_file)
    except Exception as e:
        print(f"[错误] 解析旧文件失败: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[解析] {args.new_file}")
    try:
        new_ldf = parser.parse_file(args.new_file)
    except Exception as e:
        print(f"[错误] 解析新文件失败: {e}", file=sys.stderr)
        sys.exit(1)

    print("[分析] 正在比较差异...")
    diff = LDFDiff()
    result = diff.compare(old_ldf, new_ldf)

    # 选择报告格式
    fmt = args.format.lower()
    reporters = {
        "text": LDFTextReporter(),
        "markdown": LDFMarkdownReporter(),
        "md": LDFMarkdownReporter(),
        "html": LDFHTMLReporter(),
        "csv": LDFCSVReporter(),
        "json": LDFJSONReporter(),
    }
    reporter = reporters.get(fmt)
    if reporter is None:
        print(f"[错误] 不支持的格式: {fmt}，可选: text/markdown/html/csv/json", file=sys.stderr)
        sys.exit(1)

    content = reporter.generate(result)

    if args.output:
        # 确保输出目录存在
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        reporter.save(result, args.output)
        print(f"[完成] 报告已保存到: {args.output}")
    else:
        print(content)

    # 打印统计摘要
    if result.has_changes():
        stats = result.stats()
        print(f"\n[摘要] 节点: +{stats['nodes_added']} -{stats['nodes_removed']} ~{stats['nodes_modified']} | "
              f"帧: +{stats['frames_added']} -{stats['frames_removed']} ~{stats['frames_modified']} | "
              f"信号: +{stats['signals_added']} -{stats['signals_removed']} ~{stats['signals_modified']}")
    else:
        print("\n[摘要] 两个LDF文件无差异")


# ---------------------------------------------
# 子命令：info
# ---------------------------------------------

def cmd_info(args):
    """显示单个LDF文件的结构信息"""
    parser = LDFParser()
    print(f"[解析] {args.ldf_file}")
    try:
        ldf = parser.parse_file(args.ldf_file)
    except Exception as e:
        print(f"[错误] 解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    reporter = LDFInfoReporter()
    content = reporter.generate(ldf)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[完成] 信息已保存到: {args.output}")
    else:
        print(content)


# ---------------------------------------------
# 子命令：export
# ---------------------------------------------

def cmd_export(args):
    """将LDF文件导出为JSON格式"""
    import json
    parser = LDFParser()
    print(f"[解析] {args.ldf_file}")
    try:
        ldf = parser.parse_file(args.ldf_file)
    except Exception as e:
        print(f"[错误] 解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 构建导出数据
    data = {
        "source_file": ldf.source_file,
        "lin_protocol_version": ldf.lin_protocol_version,
        "lin_language_version": ldf.lin_language_version,
        "lin_speed": ldf.lin_speed,
        "channel_name": ldf.channel_name,
        "master": {
            "name": ldf.master.name,
            "time_base": ldf.master.time_base,
            "jitter": ldf.master.jitter,
        } if ldf.master else None,
        "slaves": ldf.slaves,
        "signals": {
            name: {
                "length": s.length,
                "init_value": str(s.init_value),
                "publisher": s.publisher,
                "subscribers": s.subscribers,
                "encoding_type": s.encoding_type,
            }
            for name, s in ldf.signals.items()
        },
        "frames": {
            name: {
                "frame_id": f.frame_id,
                "frame_id_hex": f"0x{f.frame_id:02X}",
                "publisher": f.publisher,
                "length": f.length,
                "signals": [
                    {"signal_name": fs.signal_name, "start_bit": fs.start_bit}
                    for fs in f.signals
                ],
            }
            for name, f in ldf.frames.items()
        },
        "schedule_tables": {
            name: [
                {"frame_name": e.frame_name, "delay_ms": e.delay_ms}
                for e in t.entries
            ]
            for name, t in ldf.schedule_tables.items()
        },
        "encoding_types": {
            name: [
                {
                    "type": v.encode_type,
                    "min": v.min_val,
                    "max": v.max_val,
                    "scale": v.scale,
                    "offset": v.offset,
                    "unit": v.unit,
                    "text_value": v.text_value,
                    "text_name": v.text_name,
                }
                for v in et.values
            ]
            for name, et in ldf.encoding_types.items()
        },
        "signal_representations": ldf.signal_representations,
    }

    content = json.dumps(data, ensure_ascii=False, indent=2)

    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[完成] 已导出到: {args.output}")
    else:
        print(content)


# ---------------------------------------------
# 子命令：batch
# ---------------------------------------------

def cmd_batch(args):
    """批量比较两个目录中的LDF文件"""
    try:
        from ldf_batch_diff import LDFBatchDiff, BatchReportGenerator
    except ImportError as e:
        print(f"[错误] 无法导入批量比较模块: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[批量] 旧目录: {args.old_dir}")
    print(f"[批量] 新目录: {args.new_dir}")

    batch = LDFBatchDiff()
    results = batch.compare_dirs(args.old_dir, args.new_dir)

    if not results:
        print("[警告] 未找到可匹配的LDF文件对")
        sys.exit(0)

    out_dir = args.output or "ldf_batch_output"
    os.makedirs(out_dir, exist_ok=True)

    gen = BatchReportGenerator()
    gen.generate_all(results, out_dir)

    # 统计
    changed = sum(1 for _, r in results if r.has_changes())
    print(f"\n[完成] 共比较 {len(results)} 个通道，{changed} 个有变更")
    print(f"[完成] 报告已保存到: {out_dir}/")


# ---------------------------------------------
# 主入口
# ---------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="ldf_main",
        description="LDF文件分析工具 - 支持差异比较、信息查看、导出",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python ldf_main.py diff v1.ldf v2.ldf
  python ldf_main.py diff v1.ldf v2.ldf -f html -o diff_report.html
  python ldf_main.py info my.ldf
  python ldf_main.py export my.ldf -o my.json
  python ldf_main.py batch old_dir/ new_dir/ -o output/
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # -- diff 子命令 --
    p_diff = subparsers.add_parser("diff", help="比较两个LDF文件的差异")
    p_diff.add_argument("old_file", help="旧版本LDF文件路径")
    p_diff.add_argument("new_file", help="新版本LDF文件路径")
    p_diff.add_argument("-f", "--format", default="text",
                        choices=["text", "markdown", "md", "html", "csv", "json"],
                        help="报告格式 (默认: text)")
    p_diff.add_argument("-o", "--output", help="输出文件路径（不指定则打印到控制台）")

    # -- info 子命令 --
    p_info = subparsers.add_parser("info", help="查看LDF文件结构信息")
    p_info.add_argument("ldf_file", help="LDF文件路径")
    p_info.add_argument("-o", "--output", help="输出文件路径")

    # -- export 子命令 --
    p_export = subparsers.add_parser("export", help="将LDF文件导出为JSON")
    p_export.add_argument("ldf_file", help="LDF文件路径")
    p_export.add_argument("-o", "--output", help="输出JSON文件路径")

    # -- batch 子命令 --
    p_batch = subparsers.add_parser("batch", help="批量比较两个目录中的LDF文件")
    p_batch.add_argument("old_dir", help="旧版本目录路径")
    p_batch.add_argument("new_dir", help="新版本目录路径")
    p_batch.add_argument("-o", "--output", help="输出目录 (默认: ldf_batch_output)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "diff":   cmd_diff,
        "info":   cmd_info,
        "export": cmd_export,
        "batch":  cmd_batch,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
