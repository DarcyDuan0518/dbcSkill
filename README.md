# DBC Skill - CAN DBC文件分析工具集

用于解析、对比、分析 CAN DBC 文件的 Python 工具集，支持变更差异分析和多格式报告输出。

---

## 📁 文件结构

```
claude-dbcskill/
├── dbc_parser.py        # DBC文件解析器（核心模块）
├── dbc_diff.py          # DBC差异分析模块
├── dbc_report.py        # 报告生成模块（Text/Markdown/HTML/CSV/JSON）
├── dbc_main.py          # 命令行主入口
├── test_dbc_skill.py    # 功能测试脚本
├── README.md            # 本文档
└── examples/
    ├── sample_v1.dbc    # 示例DBC文件（旧版本）
    ├── sample_v2.dbc    # 示例DBC文件（新版本，含多种变更）
    └── output/          # 测试生成的报告输出目录
```

---

## 🚀 快速开始

### 环境要求
- Python 3.7+
- 无需第三方依赖（仅使用标准库）

### 对比两个DBC文件（控制台输出）
```bash
python dbc_main.py diff examples/sample_v1.dbc examples/sample_v2.dbc
```

### 生成HTML差异报告
```bash
python dbc_main.py diff examples/sample_v1.dbc examples/sample_v2.dbc --format html --output diff.html
```

### 生成所有格式报告到指定目录
```bash
python dbc_main.py diff examples/sample_v1.dbc examples/sample_v2.dbc --format all --output-dir ./reports
```

### 查看单个DBC文件摘要
```bash
python dbc_main.py info examples/sample_v1.dbc
python dbc_main.py info examples/sample_v1.dbc --signals   # 显示详细信号列表
```

### 导出DBC内容为JSON/CSV
```bash
python dbc_main.py export examples/sample_v1.dbc --format json
python dbc_main.py export examples/sample_v1.dbc --format csv
```

---

## 📖 命令行参考

### `diff` 子命令 - 差异对比
```
python dbc_main.py diff <旧版本.dbc> <新版本.dbc> [选项]

选项:
  --format, -f    输出格式: text(默认) / markdown / html / csv / json / all
  --output, -o    输出文件路径（单格式时有效）
  --output-dir, -d 输出目录（all格式时有效）
  --brief, -b     简洁模式（不显示详细信号信息）
```

### `info` 子命令 - 文件摘要
```
python dbc_main.py info <文件.dbc> [选项]

选项:
  --output, -o    保存摘要到文件
  --signals, -s   显示详细信号列表
```

### `export` 子命令 - 内容导出
```
python dbc_main.py export <文件.dbc> [选项]

选项:
  --format, -f    导出格式: json(默认) / csv
  --output, -o    输出文件路径
```

---

## 🐍 Python API 使用

### 解析DBC文件
```python
from dbc_parser import DBCParser

parser = DBCParser()
dbc = parser.parse_file("my.dbc")

# 访问节点
for name, node in dbc.nodes.items():
    print(f"节点: {name}  注释: {node.comment}")

# 访问报文和信号
for msg_id, msg in dbc.messages.items():
    print(f"报文: {msg.name} ({msg.can_id_hex})  DLC={msg.dlc}  发送={msg.sender}")
    for sig_name, sig in msg.signals.items():
        bo = "Intel" if sig.byte_order == "1" else "Motorola"
        print(f"  信号: {sig_name}  起始位={sig.start_bit}  长度={sig.length}bit  {bo}")
        print(f"        因子={sig.factor}  偏移={sig.offset}  单位={sig.unit}")
```

### 对比两个DBC文件
```python
from dbc_parser import DBCParser
from dbc_diff import DBCDiff

parser = DBCParser()
old_dbc = parser.parse_file("v1.dbc")
new_dbc = parser.parse_file("v2.dbc")

result = DBCDiff().compare(old_dbc, new_dbc)

# 查看统计
print(result.stats())
# {'nodes_added': 1, 'nodes_removed': 0, 'msgs_added': 1, ...}

# 遍历变更
for mc in result.added_messages:
    print(f"新增报文: {mc.msg_name} ({mc.can_id_hex})")

for mc in result.removed_messages:
    print(f"删除报文: {mc.msg_name} ({mc.can_id_hex})")

for mc in result.modified_messages:
    print(f"修改报文: {mc.msg_name}")
    for sc in mc.signal_changes:
        print(f"  信号变更: [{sc.change_type}] {sc.signal_name}")
        for fc in sc.field_changes:
            print(f"    {fc.field_name}: {fc.old_value!r} → {fc.new_value!r}")
```

### 生成报告
```python
from dbc_diff import compare_dbc_files
from dbc_report import TextReporter, MarkdownReporter, HTMLReporter, CSVReporter, JSONReporter

result = compare_dbc_files("v1.dbc", "v2.dbc")

# 控制台输出
TextReporter().print(result)

# 保存各格式报告
TextReporter().save(result, "diff.txt")
MarkdownReporter().save(result, "diff.md")
HTMLReporter().save(result, "diff.html")
CSVReporter().save(result, "diff.csv")
JSONReporter().save(result, "diff.json")
```

### 单文件摘要
```python
from dbc_parser import DBCParser
from dbc_report import DBCSummaryReporter

dbc = DBCParser().parse_file("my.dbc")
DBCSummaryReporter().print(dbc)
```

---

## 📊 DBC文件结构说明

DBC文件包含以下主要段（Section）：

| 关键字 | 说明 |
|--------|------|
| `VERSION` | 版本字符串 |
| `NS_` | 新符号列表（自动生成，一般忽略） |
| `BS_` | 波特率定义 |
| `BU_` | 网络节点列表 |
| `BO_` | 报文定义（ID、名称、DLC、发送节点） |
| `SG_` | 信号定义（嵌套在BO_内） |
| `CM_` | 注释（节点/报文/信号） |
| `BA_DEF_` | 属性定义 |
| `BA_DEF_DEF_` | 属性默认值 |
| `BA_` | 属性值 |
| `VAL_` | 信号枚举值表 |
| `VAL_TABLE_` | 全局值表 |

### 信号定义格式
```
SG_ <信号名> [多路复用] : <起始位>|<长度>@<字节序><符号类型>
    (<因子>,<偏移>) [<最小值>|<最大值>] "<单位>" <接收节点列表>
```

| 字段 | 说明 |
|------|------|
| 字节序 | `1` = Intel(小端)，`0` = Motorola(大端) |
| 符号类型 | `+` = 无符号，`-` = 有符号 |
| 多路复用 | `M` = 多路复用器，`mN` = 多路复用信号(N为ID) |

---

## 🔍 差异分析能力

工具可检测以下所有类型的变更：

### 节点级别
- ✚ 新增节点
- ✖ 删除节点
- ✎ 节点注释变更

### 报文级别
- ✚ 新增报文
- ✖ 删除报文
- ✎ 报文名称/DLC/发送节点/注释变更

### 信号级别
- ✚ 新增信号
- ✖ 删除信号
- ✎ 以下字段变更：
  - 起始位、位长度
  - 字节序（Intel/Motorola）
  - 数值类型（有符号/无符号）
  - 因子、偏移
  - 最小值、最大值
  - 单位
  - 接收节点列表
  - 多路复用标识
  - 注释
  - 枚举值表

---

## 📝 报告格式说明

| 格式 | 文件扩展名 | 适用场景 |
|------|-----------|---------|
| Text | `.txt` | 控制台查看、日志记录 |
| Markdown | `.md` | Git提交说明、Wiki文档 |
| HTML | `.html` | 浏览器查看、邮件附件 |
| CSV | `.csv` | Excel分析、数据处理 |
| JSON | `.json` | 程序化处理、CI/CD集成 |

---

## ✅ 运行测试

```bash
python test_dbc_skill.py
```

测试覆盖：
- 解析器基础功能（节点/报文/信号/注释/值表/属性）
- 差异分析功能（新增/删除/修改各级别）
- 所有报告格式生成
- 相同文件对比（无差异场景）
- 字符串内容解析
