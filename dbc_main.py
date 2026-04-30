"""
DBC分析工具主入口 - dbc_main.py
命令行工具，支持：
  1. diff   - 对比两个DBC文件差异
  2. info   - 显示单个DBC文件摘要
  3. export - 导出DBC内容为JSON/CSV

用法示例：
  python dbc_main.py diff old.dbc new.dbc
  python dbc_main.py diff old.dbc new.dbc --format html --output report.html
  python dbc_main.py diff old.dbc new.dbc --format all --output-dir ./reports
  python dbc_main.py info my.dbc
  python dbc_main.py export my.dbc --format json --output my.json
"""

import sys
import os
import argparse
from pathlib import Path

# 将当前目录加入路径（支持直接运行）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dbc_parser import DBCParser
from dbc_diff import DBCDiff, compare_dbc_files
from dbc_report import (
    TextReporter, MarkdownReporter, HTMLReporter,
    CSVReporter, JSONReporter, DBCSummaryReporter
)


# ---------------------------------------------
# 子命令：diff
# ---------------------------------------------

def cmd_diff(args):
    """对比两个DBC文件"""
    old_path = args.old_dbc
    new_path = args.new_dbc

    # 检查文件存在
    for p in [old_path, new_path]:
        if not os.path.isfile(p):
            print(f"[错误] 文件不存在: {p}", file=sys.stderr)
            sys.exit(1)

    print(f"正在解析 DBC 文件...")
    print(f"  旧版本: {old_path}")
    print(f"  新版本: {new_path}")

    parser = DBCParser()
    old_dbc = parser.parse_file(old_path)
    new_dbc = parser.parse_file(new_path)

    print(f"  旧版本: {len(old_dbc.messages)} 条报文, "
          f"{sum(len(m.signals) for m in old_dbc.messages.values())} 个信号")
    print(f"  新版本: {len(new_dbc.messages)} 条报文, "
          f"{sum(len(m.signals) for m in new_dbc.messages.values())} 个信号")

    diff = DBCDiff()
    result = diff.compare(old_dbc, new_dbc)

    fmt = args.format.lower()
    output = args.output
    output_dir = args.output_dir

    # 确定输出目录
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    def _out_path(ext: str) -> str:
        if output:
            return output
        base = f"dbc_diff_{Path(old_path).stem}_vs_{Path(new_path).stem}"
        if output_dir:
            return os.path.join(output_dir, f"{base}.{ext}")
        return f"{base}.{ext}"

    if fmt in ('text', 'txt', 'all'):
        reporter = TextReporter()
        if fmt == 'all':
            reporter.save(result, _out_path('txt'), verbose=not args.brief)
        else:
            if output:
                reporter.save(result, output, verbose=not args.brief)
            else:
                reporter.print(result, verbose=not args.brief)

    if fmt in ('markdown', 'md', 'all'):
        reporter = MarkdownReporter()
        reporter.save(result, _out_path('md'))

    if fmt in ('html', 'all'):
        reporter = HTMLReporter()
        reporter.save(result, _out_path('html'))

    if fmt in ('csv', 'all'):
        reporter = CSVReporter()
        reporter.save(result, _out_path('csv'))

    if fmt in ('json', 'all'):
        reporter = JSONReporter()
        reporter.save(result, _out_path('json'))

    # 默认：仅文本输出到控制台
    if fmt not in ('text', 'txt', 'markdown', 'md', 'html', 'csv', 'json', 'all'):
        print(f"[警告] 未知格式 '{fmt}'，使用默认文本格式")
        TextReporter().print(result, verbose=not args.brief)

    # 打印统计
    stats = result.stats()
    print(f"\n[PASS] 差异分析完成:")
    print(f"   节点变更: +{stats['nodes_added']} / -{stats['nodes_removed']}")
    print(f"   报文变更: +{stats['msgs_added']} / -{stats['msgs_removed']} / ~{stats['msgs_modified']}")
    print(f"   信号变更: +{stats['sigs_added']} / -{stats['sigs_removed']} / ~{stats['sigs_modified']}")


# ---------------------------------------------
# 子命令：info
# ---------------------------------------------

def cmd_info(args):
    """显示单个DBC文件摘要"""
    dbc_path = args.dbc_file
    if not os.path.isfile(dbc_path):
        print(f"[错误] 文件不存在: {dbc_path}", file=sys.stderr)
        sys.exit(1)

    parser = DBCParser()
    dbc = parser.parse_file(dbc_path)

    reporter = DBCSummaryReporter()

    if args.output:
        content = reporter.generate(dbc)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"摘要已保存: {args.output}")
    else:
        reporter.print(dbc)

    if args.signals:
        print("\n【详细信号列表】")
        for msg_id, msg in sorted(dbc.messages.items(), key=lambda x: x[1].can_id):
            if msg.signals:
                print(f"\n  报文: {msg.name} ({msg.can_id_hex})  DLC={msg.dlc}  发送={msg.sender}")
                for sig_name, sig in sorted(msg.signals.items()):
                    bo = "Intel" if sig.byte_order == "1" else "Motorola"
                    vt = "U" if sig.value_type == "+" else "S"
                    print(f"    {sig_name:<40} 起始位={sig.start_bit:>3}  长度={sig.length:>3}bit  "
                          f"{bo:<8}  {vt}  因子={sig.factor}  偏移={sig.offset}  "
                          f"[{sig.min_val}, {sig.max_val}]  单位={sig.unit!r}")
                    if sig.value_table:
                        for k, v in sorted(sig.value_table.items()):
                            print(f"      {k} = {v!r}")


# ---------------------------------------------
# 子命令：export
# ---------------------------------------------

def cmd_export(args):
    """导出DBC内容为结构化格式"""
    dbc_path = args.dbc_file
    if not os.path.isfile(dbc_path):
        print(f"[错误] 文件不存在: {dbc_path}", file=sys.stderr)
        sys.exit(1)

    parser = DBCParser()
    dbc = parser.parse_file(dbc_path)

    fmt = args.format.lower()
    output = args.output or f"{Path(dbc_path).stem}_export.{fmt}"

    if fmt == 'json':
        import json
        data = _dbc_to_dict(dbc)
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已导出 JSON: {output}")

    elif fmt == 'csv':
        import csv
        rows = [["报文ID(HEX)", "报文名称", "DLC", "发送节点", "报文注释",
                 "信号名称", "起始位", "长度(bit)", "字节序", "数值类型",
                 "因子", "偏移", "最小值", "最大值", "单位", "接收节点", "信号注释"]]
        for msg_id, msg in sorted(dbc.messages.items(), key=lambda x: x[1].can_id):
            if msg.signals:
                for sig_name, sig in sorted(msg.signals.items()):
                    bo = "Intel(小端)" if sig.byte_order == "1" else "Motorola(大端)"
                    vt = "无符号" if sig.value_type == "+" else "有符号"
                    rows.append([
                        msg.can_id_hex, msg.name, msg.dlc, msg.sender, msg.comment,
                        sig_name, sig.start_bit, sig.length, bo, vt,
                        sig.factor, sig.offset, sig.min_val, sig.max_val,
                        sig.unit, ", ".join(sig.receivers), sig.comment
                    ])
            else:
                rows.append([msg.can_id_hex, msg.name, msg.dlc, msg.sender, msg.comment,
                              "", "", "", "", "", "", "", "", "", "", "", ""])
        with open(output, 'w', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerows(rows)
        print(f"已导出 CSV: {output}")

    else:
        print(f"[错误] 不支持的导出格式: {fmt}，支持: json, csv", file=sys.stderr)
        sys.exit(1)


def _dbc_to_dict(dbc) -> dict:
    """将DBCFile转换为可序列化的字典"""
    return {
        "version": dbc.version,
        "baudrate": dbc.baudrate,
        "source_file": dbc.source_file,
        "nodes": {
            name: {"name": node.name, "comment": node.comment}
            for name, node in dbc.nodes.items()
        },
        "messages": {
            str(msg_id): {
                "msg_id": msg.msg_id,
                "can_id": msg.can_id,
                "can_id_hex": msg.can_id_hex,
                "name": msg.name,
                "dlc": msg.dlc,
                "sender": msg.sender,
                "is_extended": msg.is_extended,
                "comment": msg.comment,
                "attributes": msg.attributes,
                "signals": {
                    sig_name: {
                        "name": sig.name,
                        "start_bit": sig.start_bit,
                        "length": sig.length,
                        "byte_order": "Intel(小端)" if sig.byte_order == "1" else "Motorola(大端)",
                        "value_type": "无符号" if sig.value_type == "+" else "有符号",
                        "factor": sig.factor,
                        "offset": sig.offset,
                        "min_val": sig.min_val,
                        "max_val": sig.max_val,
                        "unit": sig.unit,
                        "receivers": sig.receivers,
                        "mux_indicator": sig.mux_indicator,
                        "comment": sig.comment,
                        "value_table": {str(k): v for k, v in sig.value_table.items()},
                        "attributes": sig.attributes
                    }
                    for sig_name, sig in msg.signals.items()
                }
            }
            for msg_id, msg in dbc.messages.items()
        },
        "value_tables": {
            name: {str(k): v for k, v in table.items()}
            for name, table in dbc.value_tables.items()
        }
    }


# ---------------------------------------------
# 参数解析
# ---------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dbc_main",
        description="DBC文件分析工具 - 支持差异对比、内容摘要、数据导出",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 对比两个DBC文件，输出到控制台
  python dbc_main.py diff old.dbc new.dbc

  # 对比并生成HTML报告
  python dbc_main.py diff old.dbc new.dbc --format html --output diff.html

  # 对比并生成所有格式报告到指定目录
  python dbc_main.py diff old.dbc new.dbc --format all --output-dir ./reports

  # 查看DBC文件摘要
  python dbc_main.py info my.dbc

  # 查看DBC文件摘要并显示所有信号
  python dbc_main.py info my.dbc --signals

  # 导出DBC内容为JSON
  python dbc_main.py export my.dbc --format json --output my.json

  # 导出DBC内容为CSV（可用Excel打开）
  python dbc_main.py export my.dbc --format csv
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # -- diff 子命令 --
    diff_parser = subparsers.add_parser("diff", help="对比两个DBC文件的差异")
    diff_parser.add_argument("old_dbc", help="旧版本DBC文件路径")
    diff_parser.add_argument("new_dbc", help="新版本DBC文件路径")
    diff_parser.add_argument(
        "--format", "-f",
        default="text",
        choices=["text", "txt", "markdown", "md", "html", "csv", "json", "all"],
        help="输出格式 (默认: text)"
    )
    diff_parser.add_argument("--output", "-o", help="输出文件路径（单格式时有效）")
    diff_parser.add_argument("--output-dir", "-d", help="输出目录（all格式时有效）")
    diff_parser.add_argument("--brief", "-b", action="store_true", help="简洁模式（不显示详细信号信息）")

    # -- info 子命令 --
    info_parser = subparsers.add_parser("info", help="显示DBC文件内容摘要")
    info_parser.add_argument("dbc_file", help="DBC文件路径")
    info_parser.add_argument("--output", "-o", help="保存摘要到文件")
    info_parser.add_argument("--signals", "-s", action="store_true", help="显示详细信号列表")

    # -- export 子命令 --
    export_parser = subparsers.add_parser("export", help="导出DBC内容为结构化格式")
    export_parser.add_argument("dbc_file", help="DBC文件路径")
    export_parser.add_argument(
        "--format", "-f",
        default="json",
        choices=["json", "csv"],
        help="导出格式 (默认: json)"
    )
    export_parser.add_argument("--output", "-o", help="输出文件路径")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "diff":
        cmd_diff(args)
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "export":
        cmd_export(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
