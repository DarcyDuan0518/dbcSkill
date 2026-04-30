"""
DBC文件解析器 - dbc_parser.py
解析DBC文件的所有Section，构建结构化数据模型
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


# ---------------------------------------------
# 数据模型
# ---------------------------------------------

@dataclass
class Signal:
    """CAN信号定义"""
    name: str
    start_bit: int
    length: int
    byte_order: str          # '1'=Intel(小端) / '0'=Motorola(大端)
    value_type: str          # '+'=无符号 / '-'=有符号
    factor: float
    offset: float
    min_val: float
    max_val: float
    unit: str
    receivers: List[str]
    mux_indicator: str = ""  # '' / 'M' / 'mN'
    comment: str = ""
    value_table: Dict[int, str] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def __eq__(self, other):
        if not isinstance(other, Signal):
            return False
        return (self.start_bit == other.start_bit and
                self.length == other.length and
                self.byte_order == other.byte_order and
                self.value_type == other.value_type and
                self.factor == other.factor and
                self.offset == other.offset and
                self.min_val == other.min_val and
                self.max_val == other.max_val and
                self.unit == other.unit and
                sorted(self.receivers) == sorted(other.receivers) and
                self.mux_indicator == other.mux_indicator)


@dataclass
class Message:
    """CAN报文定义"""
    msg_id: int              # 原始ID（含扩展帧标志位）
    name: str
    dlc: int
    sender: str
    signals: Dict[str, Signal] = field(default_factory=dict)
    comment: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_extended(self) -> bool:
        """是否为扩展帧（29位ID）"""
        return bool(self.msg_id & 0x80000000)

    @property
    def can_id(self) -> int:
        """实际CAN ID（去掉扩展帧标志位）"""
        return self.msg_id & 0x1FFFFFFF

    @property
    def can_id_hex(self) -> str:
        return f"0x{self.can_id:X}"

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False
        return (self.msg_id == other.msg_id and
                self.name == other.name and
                self.dlc == other.dlc and
                self.sender == other.sender)


@dataclass
class Node:
    """网络节点"""
    name: str
    comment: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttributeDef:
    """属性定义"""
    name: str
    object_type: str         # '' / 'BU_' / 'BO_' / 'SG_' / 'EV_'
    value_type: str          # 'INT' / 'HEX' / 'FLOAT' / 'STRING' / 'ENUM'
    default_value: Any = None
    min_val: Any = None
    max_val: Any = None
    enum_values: List[str] = field(default_factory=list)


@dataclass
class DBCFile:
    """DBC文件完整数据模型"""
    version: str = ""
    nodes: Dict[str, Node] = field(default_factory=dict)
    messages: Dict[int, Message] = field(default_factory=dict)   # key=msg_id
    attribute_defs: Dict[str, AttributeDef] = field(default_factory=dict)
    global_attributes: Dict[str, Any] = field(default_factory=dict)
    value_tables: Dict[str, Dict[int, str]] = field(default_factory=dict)
    baudrate: str = ""
    source_file: str = ""

    def get_message_by_name(self, name: str) -> Optional[Message]:
        for msg in self.messages.values():
            if msg.name == name:
                return msg
        return None

    def get_message_by_can_id(self, can_id: int) -> Optional[Message]:
        for msg in self.messages.values():
            if msg.can_id == can_id:
                return msg
        return None


# ---------------------------------------------
# 解析器
# ---------------------------------------------

class DBCParser:
    """
    DBC文件解析器
    支持标准DBC格式，包含：VERSION / NS_ / BS_ / BU_ / BO_ / SG_
    CM_ / BA_DEF_ / BA_DEF_DEF_ / BA_ / VAL_ / VAL_TABLE_
    """

    # 信号行正则：SG_ <name> [mux] : <start>|<len>@<order><sign> (<factor>,<offset>) [<min>|<max>] "<unit>" <receivers>
    _SIG_RE = re.compile(
        r'^\s*SG_\s+(\w+)\s*(M|m\d+|m\d+M)?\s*:\s*'
        r'(\d+)\|(\d+)@([01])([+-])\s*'
        r'\(([^,]+),([^)]+)\)\s*'
        r'\[([^|]+)\|([^\]]+)\]\s*'
        r'"([^"]*)"\s*'
        r'(.*)'
    )

    # 报文行正则：BO_ <id> <name> : <dlc> <sender>
    _MSG_RE = re.compile(
        r'^BO_\s+(\d+)\s+(\w+)\s*:\s*(\d+)\s+(\w+)'
    )

    def __init__(self):
        self._dbc: DBCFile = DBCFile()
        self._current_msg: Optional[Message] = None

    def parse_file(self, filepath: str) -> DBCFile:
        """解析DBC文件，返回DBCFile对象"""
        self._dbc = DBCFile(source_file=filepath)
        self._current_msg = None

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        self._parse(content)
        return self._dbc

    def parse_string(self, content: str, source: str = "<string>") -> DBCFile:
        """从字符串解析DBC内容"""
        self._dbc = DBCFile(source_file=source)
        self._current_msg = None
        self._parse(content)
        return self._dbc

    def _parse(self, content: str):
        """主解析流程"""
        lines = content.splitlines()
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            stripped = line.strip()

            if stripped.startswith('VERSION'):
                self._parse_version(stripped)
                i += 1

            elif stripped.startswith('BS_'):
                self._parse_baudrate(stripped)
                i += 1

            elif stripped.startswith('BU_'):
                self._parse_nodes(stripped)
                i += 1

            elif stripped.startswith('NS_'):
                # NS_ 段：跳过所有缩进子项行，直到遇到非缩进非空行
                i += 1
                while i < n:
                    ln = lines[i]
                    if ln.startswith(' ') or ln.startswith('\t'):
                        i += 1  # NS_ 子项，跳过
                    else:
                        break   # 遇到非缩进行，NS_段结束，不推进i

            elif stripped.startswith('BO_ '):
                self._current_msg = self._parse_message(stripped)
                i += 1

            elif stripped.startswith('SG_ ') and self._current_msg is not None:
                sig = self._parse_signal(stripped)
                if sig:
                    self._current_msg.signals[sig.name] = sig
                i += 1

            elif stripped.startswith('CM_'):
                block, i = self._collect_block(lines, i)
                self._parse_comment(block)
                i += 1

            elif stripped.startswith('BA_DEF_DEF_'):
                block, i = self._collect_block(lines, i)
                self._parse_attr_default(block)
                i += 1

            elif stripped.startswith('BA_DEF_'):
                block, i = self._collect_block(lines, i)
                self._parse_attr_def(block)
                i += 1

            elif stripped.startswith('BA_ '):
                block, i = self._collect_block(lines, i)
                self._parse_attr_value(block)
                i += 1

            elif stripped.startswith('VAL_TABLE_'):
                block, i = self._collect_block(lines, i)
                self._parse_val_table(block)
                i += 1

            elif stripped.startswith('VAL_ '):
                block, i = self._collect_block(lines, i)
                self._parse_val(block)
                i += 1

            else:
                # 遇到非信号行时，重置当前消息（防止跨消息误解析）
                if stripped and not stripped.startswith('SG_'):
                    self._current_msg = None
                i += 1

    def _collect_block(self, lines: List[str], start: int) -> Tuple[str, int]:
        """收集以分号结尾的多行块（最多向后扫描50行，防止死循环）"""
        block_lines = []
        i = start
        max_lines = min(start + 50, len(lines))
        while i < max_lines:
            block_lines.append(lines[i])
            if lines[i].rstrip().endswith(';'):
                break
            i += 1
        return '\n'.join(block_lines), i

    def _parse_version(self, line: str):
        m = re.match(r'VERSION\s+"([^"]*)"', line)
        if m:
            self._dbc.version = m.group(1)

    def _parse_baudrate(self, line: str):
        m = re.match(r'BS_\s*:\s*(.*)', line)
        if m:
            self._dbc.baudrate = m.group(1).strip()

    def _parse_nodes(self, line: str):
        m = re.match(r'BU_\s*:\s*(.*)', line)
        if m:
            names = m.group(1).split()
            for name in names:
                if name:
                    self._dbc.nodes[name] = Node(name=name)

    def _parse_message(self, line: str) -> Optional[Message]:
        m = self._MSG_RE.match(line)
        if not m:
            return None
        msg_id = int(m.group(1))
        msg = Message(
            msg_id=msg_id,
            name=m.group(2),
            dlc=int(m.group(3)),
            sender=m.group(4)
        )
        self._dbc.messages[msg_id] = msg
        return msg

    def _parse_signal(self, line: str) -> Optional[Signal]:
        m = self._SIG_RE.match(line)
        if not m:
            return None
        receivers_str = m.group(12).strip()
        receivers = [r.strip() for r in receivers_str.split(',') if r.strip()]
        try:
            sig = Signal(
                name=m.group(1),
                mux_indicator=m.group(2) or "",
                start_bit=int(m.group(3)),
                length=int(m.group(4)),
                byte_order=m.group(5),
                value_type=m.group(6),
                factor=float(m.group(7)),
                offset=float(m.group(8)),
                min_val=float(m.group(9)),
                max_val=float(m.group(10)),
                unit=m.group(11),
                receivers=receivers
            )
        except ValueError:
            return None
        return sig

    def _parse_comment(self, block: str):
        """解析CM_注释块"""
        # 节点注释: CM_ BU_ <node> "...";
        m = re.match(r'CM_\s+BU_\s+(\w+)\s+"(.*?)"\s*;', block, re.DOTALL)
        if m:
            node_name = m.group(1)
            if node_name in self._dbc.nodes:
                self._dbc.nodes[node_name].comment = m.group(2)
            return

        # 报文注释: CM_ BO_ <id> "...";
        m = re.match(r'CM_\s+BO_\s+(\d+)\s+"(.*?)"\s*;', block, re.DOTALL)
        if m:
            msg_id = int(m.group(1))
            if msg_id in self._dbc.messages:
                self._dbc.messages[msg_id].comment = m.group(2)
            return

        # 信号注释: CM_ SG_ <id> <sig_name> "...";
        m = re.match(r'CM_\s+SG_\s+(\d+)\s+(\w+)\s+"(.*?)"\s*;', block, re.DOTALL)
        if m:
            msg_id = int(m.group(1))
            sig_name = m.group(2)
            if msg_id in self._dbc.messages:
                msg = self._dbc.messages[msg_id]
                if sig_name in msg.signals:
                    msg.signals[sig_name].comment = m.group(3)
            return

    def _parse_attr_def(self, block: str):
        """解析BA_DEF_属性定义"""
        # BA_DEF_ [BU_|BO_|SG_|EV_] "name" type ...;
        m = re.match(r'BA_DEF_\s+(BU_|BO_|SG_|EV_)?\s*"([^"]+)"\s+(\w+)(.*?);', block, re.DOTALL)
        if not m:
            return
        obj_type = (m.group(1) or "").strip()
        attr_name = m.group(2)
        val_type = m.group(3)
        rest = m.group(4).strip()

        attr_def = AttributeDef(name=attr_name, object_type=obj_type, value_type=val_type)

        if val_type in ('INT', 'HEX', 'FLOAT'):
            nums = re.findall(r'[-\d.eE+]+', rest)
            if len(nums) >= 2:
                try:
                    attr_def.min_val = float(nums[0])
                    attr_def.max_val = float(nums[1])
                except ValueError:
                    pass
        elif val_type == 'ENUM':
            enums = re.findall(r'"([^"]*)"', rest)
            attr_def.enum_values = enums

        self._dbc.attribute_defs[attr_name] = attr_def

    def _parse_attr_default(self, block: str):
        """解析BA_DEF_DEF_默认值"""
        m = re.match(r'BA_DEF_DEF_\s+"([^"]+)"\s+(.*?)\s*;', block, re.DOTALL)
        if not m:
            return
        attr_name = m.group(1)
        val_str = m.group(2).strip().strip('"')
        if attr_name in self._dbc.attribute_defs:
            try:
                self._dbc.attribute_defs[attr_name].default_value = float(val_str) if '.' in val_str else int(val_str)
            except ValueError:
                self._dbc.attribute_defs[attr_name].default_value = val_str

    def _parse_attr_value(self, block: str):
        """解析BA_属性值"""
        # 全局属性: BA_ "name" value;
        m = re.match(r'BA_\s+"([^"]+)"\s+(.*?)\s*;', block, re.DOTALL)
        if not m:
            return
        attr_name = m.group(1)
        rest = m.group(2).strip()

        # 节点属性: BA_ "name" BU_ <node> value;
        m2 = re.match(r'BU_\s+(\w+)\s+(.*)', rest)
        if m2:
            node_name = m2.group(1)
            val = self._parse_attr_val_str(m2.group(2))
            if node_name in self._dbc.nodes:
                self._dbc.nodes[node_name].attributes[attr_name] = val
            return

        # 报文属性: BA_ "name" BO_ <id> value;
        m2 = re.match(r'BO_\s+(\d+)\s+(.*)', rest)
        if m2:
            msg_id = int(m2.group(1))
            val = self._parse_attr_val_str(m2.group(2))
            if msg_id in self._dbc.messages:
                self._dbc.messages[msg_id].attributes[attr_name] = val
            return

        # 信号属性: BA_ "name" SG_ <id> <sig> value;
        m2 = re.match(r'SG_\s+(\d+)\s+(\w+)\s+(.*)', rest)
        if m2:
            msg_id = int(m2.group(1))
            sig_name = m2.group(2)
            val = self._parse_attr_val_str(m2.group(3))
            if msg_id in self._dbc.messages:
                msg = self._dbc.messages[msg_id]
                if sig_name in msg.signals:
                    msg.signals[sig_name].attributes[attr_name] = val
            return

        # 全局属性
        val = self._parse_attr_val_str(rest)
        self._dbc.global_attributes[attr_name] = val

    def _parse_attr_val_str(self, s: str) -> Any:
        s = s.strip()
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1]
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return s

    def _parse_val_table(self, block: str):
        """解析VAL_TABLE_全局值表"""
        m = re.match(r'VAL_TABLE_\s+(\w+)\s+(.*?)\s*;', block, re.DOTALL)
        if not m:
            return
        table_name = m.group(1)
        pairs = re.findall(r'(\d+)\s+"([^"]*)"', m.group(2))
        self._dbc.value_tables[table_name] = {int(k): v for k, v in pairs}

    def _parse_val(self, block: str):
        """解析VAL_信号值表"""
        m = re.match(r'VAL_\s+(\d+)\s+(\w+)\s+(.*?)\s*;', block, re.DOTALL)
        if not m:
            return
        msg_id = int(m.group(1))
        sig_name = m.group(2)
        pairs = re.findall(r'(\d+)\s+"([^"]*)"', m.group(3))
        val_map = {int(k): v for k, v in pairs}
        if msg_id in self._dbc.messages:
            msg = self._dbc.messages[msg_id]
            if sig_name in msg.signals:
                msg.signals[sig_name].value_table = val_map
