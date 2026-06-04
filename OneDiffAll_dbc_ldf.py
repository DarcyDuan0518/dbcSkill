#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# Standard Library Imports
# ============================================================
import re
import os
import csv
import json
import sys
import argparse
import io
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path


# ============================================================
# Section: dbc_parser.py
# ============================================================

"""
DBC文件解析器 - dbc_parser.py
解析DBC文件的所有Section，构建结构化数据模型
"""



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
        self._fill_attr_defaults()
        return self._dbc

    def parse_string(self, content: str, source: str = "<string>") -> DBCFile:
        """从字符串解析DBC内容"""
        self._dbc = DBCFile(source_file=source)
        self._current_msg = None
        self._parse(content)
        self._fill_attr_defaults()
        return self._dbc

    def _fill_attr_defaults(self):
        """将 BA_DEF_DEF_ 中的信号/报文属性默认值填充到没有显式赋值的对象"""
        # 信号属性：GenSigSendType
        if 'GenSigSendType' in self._dbc.attribute_defs:
            _default = self._dbc.attribute_defs['GenSigSendType'].default_value
            if _default is not None and _default != '':
                for _msg in self._dbc.messages.values():
                    for _sig in _msg.signals.values():
                        if 'GenSigSendType' not in _sig.attributes:
                            _sig.attributes['GenSigSendType'] = _default
        # 报文属性：GenMsg* 系列
        _MSG_ATTR_NAMES = (
            'GenMsgCycleTime', 'GenMsgCycleTimeFast', 'GenMsgDelayTime',
            'GenMsgNrofRepetition', 'GenMsgSendType', 'GenMsgStartDelayTime',
        )
        for _attr_name in _MSG_ATTR_NAMES:
            if _attr_name in self._dbc.attribute_defs:
                _default = self._dbc.attribute_defs[_attr_name].default_value
                if _default is not None and _default != '':
                    for _msg in self._dbc.messages.values():
                        if _attr_name not in _msg.attributes:
                            _msg.attributes[_attr_name] = _default

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

# ============================================================
# Section: dbc_diff.py
# ============================================================

"""
DBC差异分析模块 - dbc_diff.py
对比两个DBC文件，识别新增、删除、修改的节点/报文/信号
"""



# ---------------------------------------------
# 变更类型枚举
# ---------------------------------------------

class ChangeType:
    ADDED   = "ADDED"    # 新增
    REMOVED = "REMOVED"  # 删除
    MODIFIED = "MODIFIED"  # 修改


# ---------------------------------------------
# 变更记录数据类
# ---------------------------------------------

@dataclass
class FieldChange:
    """单个字段的变更"""
    field_name: str
    old_value: Any
    new_value: Any

    def __str__(self):
        return f"  {self.field_name}: {self.old_value!r} -> {self.new_value!r}"


@dataclass
class SignalChange:
    """信号级别的变更"""
    change_type: str          # ADDED / REMOVED / MODIFIED
    msg_id: int
    msg_name: str
    signal_name: str
    old_signal: Optional[Signal] = None
    new_signal: Optional[Signal] = None
    field_changes: List[FieldChange] = field(default_factory=list)

    @property
    def can_id_hex(self) -> str:
        return f"0x{self.msg_id & 0x1FFFFFFF:X}"

    def summary(self) -> str:
        if self.change_type == ChangeType.ADDED:
            return f"[新增信号] {self.msg_name}({self.can_id_hex}).{self.signal_name}"
        elif self.change_type == ChangeType.REMOVED:
            return f"[删除信号] {self.msg_name}({self.can_id_hex}).{self.signal_name}"
        else:
            changes_str = "; ".join(
                f"{c.field_name}: {c.old_value!r}->{c.new_value!r}"
                for c in self.field_changes
            )
            return f"[修改信号] {self.msg_name}({self.can_id_hex}).{self.signal_name} [{changes_str}]"


@dataclass
class MessageIdChange:
    """报文ID变更（同名报文但ID不同）"""
    msg_name: str
    old_id: int
    new_id: int
    old_message: Optional[Message] = None
    new_message: Optional[Message] = None

    @property
    def old_id_hex(self) -> str:
        return f"0x{self.old_id & 0x1FFFFFFF:X}"

    @property
    def new_id_hex(self) -> str:
        return f"0x{self.new_id & 0x1FFFFFFF:X}"

    def summary(self) -> str:
        return f"[报文ID变更] {self.msg_name}: {self.old_id_hex} -> {self.new_id_hex}"


@dataclass
class MessageChange:
    """报文级别的变更"""
    change_type: str          # ADDED / REMOVED / MODIFIED
    msg_id: int
    msg_name: str
    old_message: Optional[Message] = None
    new_message: Optional[Message] = None
    field_changes: List[FieldChange] = field(default_factory=list)
    attr_changes: List[FieldChange] = field(default_factory=list)   # BA_ attribute 变更
    signal_changes: List[SignalChange] = field(default_factory=list)

    @property
    def can_id_hex(self) -> str:
        return f"0x{self.msg_id & 0x1FFFFFFF:X}"

    def summary(self) -> str:
        if self.change_type == ChangeType.ADDED:
            return f"[新增报文] {self.msg_name}({self.can_id_hex})"
        elif self.change_type == ChangeType.REMOVED:
            return f"[删除报文] {self.msg_name}({self.can_id_hex})"
        else:
            parts = []
            if self.field_changes:
                parts.append(f"{len(self.field_changes)}个属性变更")
            if self.signal_changes:
                added   = sum(1 for s in self.signal_changes if s.change_type == ChangeType.ADDED)
                removed = sum(1 for s in self.signal_changes if s.change_type == ChangeType.REMOVED)
                modified = sum(1 for s in self.signal_changes if s.change_type == ChangeType.MODIFIED)
                sig_parts = []
                if added:   sig_parts.append(f"新增{added}个信号")
                if removed: sig_parts.append(f"删除{removed}个信号")
                if modified: sig_parts.append(f"修改{modified}个信号")
                parts.append("/".join(sig_parts))
            detail = ", ".join(parts) if parts else "无实质变更"
            return f"[修改报文] {self.msg_name}({self.can_id_hex}) [{detail}]"


@dataclass
class NodeChange:
    """节点级别的变更"""
    change_type: str
    node_name: str
    old_node: Optional[Node] = None
    new_node: Optional[Node] = None
    field_changes: List[FieldChange] = field(default_factory=list)

    def summary(self) -> str:
        if self.change_type == ChangeType.ADDED:
            return f"[新增节点] {self.node_name}"
        elif self.change_type == ChangeType.REMOVED:
            return f"[删除节点] {self.node_name}"
        else:
            return f"[修改节点] {self.node_name}"


@dataclass
class DBCDiffResult:
    """DBC差异分析完整结果"""
    old_file: str
    new_file: str
    node_changes: List[NodeChange] = field(default_factory=list)
    message_id_changes: List[MessageIdChange] = field(default_factory=list)
    message_changes: List[MessageChange] = field(default_factory=list)

    # -- 统计快捷属性 --
    @property
    def added_messages(self) -> List[MessageChange]:
        return [c for c in self.message_changes if c.change_type == ChangeType.ADDED]

    @property
    def removed_messages(self) -> List[MessageChange]:
        return [c for c in self.message_changes if c.change_type == ChangeType.REMOVED]

    @property
    def modified_messages(self) -> List[MessageChange]:
        return [c for c in self.message_changes if c.change_type == ChangeType.MODIFIED]

    @property
    def added_nodes(self) -> List[NodeChange]:
        return [c for c in self.node_changes if c.change_type == ChangeType.ADDED]

    @property
    def removed_nodes(self) -> List[NodeChange]:
        return [c for c in self.node_changes if c.change_type == ChangeType.REMOVED]

    @property
    def all_signal_changes(self) -> List[SignalChange]:
        """获取所有信号变更（跨所有报文）"""
        result = []
        for mc in self.message_changes:
            result.extend(mc.signal_changes)
        return result

    def has_changes(self) -> bool:
        return bool(self.node_changes or self.message_id_changes or self.message_changes)

    def stats(self) -> Dict[str, int]:
        sig_changes = self.all_signal_changes
        return {
            "nodes_added":    len(self.added_nodes),
            "nodes_removed":  len(self.removed_nodes),
            "msg_id_changes": len(self.message_id_changes),
            "msgs_added":     len(self.added_messages),
            "msgs_removed":   len(self.removed_messages),
            "msgs_modified":  len(self.modified_messages),
            "sigs_added":     sum(1 for s in sig_changes if s.change_type == ChangeType.ADDED),
            "sigs_removed":   sum(1 for s in sig_changes if s.change_type == ChangeType.REMOVED),
            "sigs_modified":  sum(1 for s in sig_changes if s.change_type == ChangeType.MODIFIED),
        }


# ---------------------------------------------
# 差异分析器
# ---------------------------------------------

class DBCDiff:
    """
    DBC差异分析器
    用法：
        diff = DBCDiff()
        result = diff.compare(old_dbc, new_dbc)
    """

    # 信号需要比较的字段列表
    _SIGNAL_FIELDS = [
        ("start_bit",     "起始位"),
        ("length",        "位长度"),
        ("mux_indicator", "多路复用"),
        ("factor",        "比例因子"),
        ("offset",        "偏移"),
        ("min_val",       "最小值"),
        ("max_val",       "最大值"),
        ("unit",          "单位"),
        ("comment",       "注释"),
    ]

    # 报文需要比较的字段列表
    _MESSAGE_FIELDS = [
        ("name",    "报文名称"),
        ("dlc",     "DLC"),
        ("sender",  "发送节点"),
        ("comment", "注释"),
    ]

    def compare(self, old_dbc: DBCFile, new_dbc: DBCFile) -> DBCDiffResult:
        """
        比较两个DBCFile对象，返回DBCDiffResult
        匹配策略：优先按msg_id匹配，其次按报文名称匹配
        """
        result = DBCDiffResult(
            old_file=old_dbc.source_file,
            new_file=new_dbc.source_file
        )

        # 1. 比较节点
        result.node_changes = self._compare_nodes(old_dbc, new_dbc)

        # 2. 检测同名报文 ID 变更（在按ID比较之前先找出来）
        result.message_id_changes = self._detect_id_changes(old_dbc, new_dbc)

        # 3. 比较报文（按msg_id匹配）
        result.message_changes = self._compare_messages(old_dbc, new_dbc)

        return result

    # -- 节点比较 ------------------------------

    def _compare_nodes(self, old_dbc: DBCFile, new_dbc: DBCFile) -> List[NodeChange]:
        changes = []
        old_names = set(old_dbc.nodes.keys())
        new_names = set(new_dbc.nodes.keys())

        for name in sorted(new_names - old_names):
            changes.append(NodeChange(
                change_type=ChangeType.ADDED,
                node_name=name,
                new_node=new_dbc.nodes[name]
            ))

        for name in sorted(old_names - new_names):
            changes.append(NodeChange(
                change_type=ChangeType.REMOVED,
                node_name=name,
                old_node=old_dbc.nodes[name]
            ))

        for name in sorted(old_names & new_names):
            old_node = old_dbc.nodes[name]
            new_node = new_dbc.nodes[name]
            field_changes = []
            if old_node.comment != new_node.comment:
                field_changes.append(FieldChange("注释", old_node.comment, new_node.comment))
            if field_changes:
                changes.append(NodeChange(
                    change_type=ChangeType.MODIFIED,
                    node_name=name,
                    old_node=old_node,
                    new_node=new_node,
                    field_changes=field_changes
                ))

        return changes

    # -- 报文比较 ------------------------------

    def _compare_messages(self, old_dbc: DBCFile, new_dbc: DBCFile) -> List[MessageChange]:
        changes = []

        old_ids = set(old_dbc.messages.keys())
        new_ids = set(new_dbc.messages.keys())

        # 找出已被识别为 ID 变更的报文，排除在新增/删除之外
        old_name_to_id = {msg.name: msg_id for msg_id, msg in old_dbc.messages.items()}
        new_name_to_id = {msg.name: msg_id for msg_id, msg in new_dbc.messages.items()}
        id_changed_old_ids = set()
        id_changed_new_ids = set()
        for name in set(old_name_to_id) & set(new_name_to_id):
            old_id = old_name_to_id[name]
            new_id = new_name_to_id[name]
            if old_id != new_id:
                id_changed_old_ids.add(old_id)
                id_changed_new_ids.add(new_id)

        # 新增报文（排除 ID 变更的新 ID）
        for msg_id in sorted(new_ids - old_ids):
            if msg_id in id_changed_new_ids:
                continue
            msg = new_dbc.messages[msg_id]
            changes.append(MessageChange(
                change_type=ChangeType.ADDED,
                msg_id=msg_id,
                msg_name=msg.name,
                new_message=msg
            ))

        # 删除报文（排除 ID 变更的旧 ID）
        for msg_id in sorted(old_ids - new_ids):
            if msg_id in id_changed_old_ids:
                continue
            msg = old_dbc.messages[msg_id]
            changes.append(MessageChange(
                change_type=ChangeType.REMOVED,
                msg_id=msg_id,
                msg_name=msg.name,
                old_message=msg
            ))

        # 共同报文：比较属性和信号
        for msg_id in sorted(old_ids & new_ids):
            old_msg = old_dbc.messages[msg_id]
            new_msg = new_dbc.messages[msg_id]
            mc = self._compare_single_message(old_msg, new_msg)
            if mc is not None:
                changes.append(mc)

        return changes

    def _compare_single_message(self, old_msg: Message, new_msg: Message) -> Optional[MessageChange]:
        """比较单个报文，返回MessageChange（无变更则返回None）"""
        field_changes = []

        for attr, label in self._MESSAGE_FIELDS:
            old_val = getattr(old_msg, attr)
            new_val = getattr(new_msg, attr)
            if old_val != new_val:
                field_changes.append(FieldChange(label, old_val, new_val))

        # 比较 GenMsg* 报文属性（带标签转换，存入 attr_changes）
        attr_changes = []
        for _attr_key, _attr_label in _GEN_MSG_ATTRS:
            _old_raw = old_msg.attributes.get(_attr_key)
            _new_raw = new_msg.attributes.get(_attr_key)
            if _attr_key == 'GenMsgSendType':
                _old_v = _gen_msg_send_type_label(_old_raw)
                _new_v = _gen_msg_send_type_label(_new_raw)
            else:
                _old_v = '' if _old_raw is None else str(_old_raw)
                _new_v = '' if _new_raw is None else str(_new_raw)
            if _old_v != _new_v:
                attr_changes.append(FieldChange(_attr_label, _old_v, _new_v))

        # 比较信号
        signal_changes = self._compare_signals(old_msg, new_msg)

        if not field_changes and not attr_changes and not signal_changes:
            return None

        return MessageChange(
            change_type=ChangeType.MODIFIED,
            msg_id=old_msg.msg_id,
            msg_name=new_msg.name,
            old_message=old_msg,
            new_message=new_msg,
            field_changes=field_changes,
            attr_changes=attr_changes,
            signal_changes=signal_changes
        )

    # -- 信号比较 ------------------------------

    def _compare_signals(self, old_msg: Message, new_msg: Message) -> List[SignalChange]:
        changes = []
        old_sigs = old_msg.signals
        new_sigs = new_msg.signals

        old_names = set(old_sigs.keys())
        new_names = set(new_sigs.keys())

        # 新增信号（填充属性字段，old_value="" 表示新增）
        for name in sorted(new_names - old_names):
            sig = new_sigs[name]
            added_fields = []
            for attr, label in self._SIGNAL_FIELDS:
                val = getattr(sig, attr)
                if isinstance(val, list):
                    if val:
                        added_fields.append(FieldChange(label, "", val))
                elif val is not None and val != "":
                    added_fields.append(FieldChange(label, "", val))
            # 新增信号：将 GenSigSendType 插到属性列表首位
            _sst = _gen_sig_send_type_label(sig.attributes.get('GenSigSendType'))
            if _sst:
                added_fields.insert(0, FieldChange('GenSigSendType', '', _sst))
            changes.append(SignalChange(
                change_type=ChangeType.ADDED,
                msg_id=new_msg.msg_id,
                msg_name=new_msg.name,
                signal_name=name,
                new_signal=sig,
                field_changes=added_fields,
            ))

        # 删除信号
        for name in sorted(old_names - new_names):
            changes.append(SignalChange(
                change_type=ChangeType.REMOVED,
                msg_id=old_msg.msg_id,
                msg_name=old_msg.name,
                signal_name=name,
                old_signal=old_sigs[name]
            ))

        # 共同信号：比较字段
        for name in sorted(old_names & new_names):
            old_sig = old_sigs[name]
            new_sig = new_sigs[name]
            field_changes = self._compare_signal_fields(old_sig, new_sig)
            if field_changes:
                changes.append(SignalChange(
                    change_type=ChangeType.MODIFIED,
                    msg_id=new_msg.msg_id,
                    msg_name=new_msg.name,
                    signal_name=name,
                    old_signal=old_sig,
                    new_signal=new_sig,
                    field_changes=field_changes
                ))

        return changes

    def _compare_signal_fields(self, old_sig: Signal, new_sig: Signal) -> List[FieldChange]:
        changes = []
        for attr, label in self._SIGNAL_FIELDS:
            old_val = getattr(old_sig, attr)
            new_val = getattr(new_sig, attr)
            # 对列表类型做排序后比较（接收节点顺序不影响语义）
            if isinstance(old_val, list) and isinstance(new_val, list):
                if sorted(old_val) != sorted(new_val):
                    changes.append(FieldChange(label, old_val, new_val))
            elif old_val != new_val:
                changes.append(FieldChange(label, old_val, new_val))
        # 比较信号属性中的 GenSigSendType
        _sst_old = _gen_sig_send_type_label(old_sig.attributes.get('GenSigSendType'))
        _sst_new = _gen_sig_send_type_label(new_sig.attributes.get('GenSigSendType'))
        if _sst_old != _sst_new:
            changes.append(FieldChange('GenSigSendType', _sst_old, _sst_new))
        return changes

    # -- 报文ID变更检测 ------------------------

    def _detect_id_changes(self, old_dbc: DBCFile, new_dbc: DBCFile) -> List[MessageIdChange]:
        """检测同名报文但ID不同的情况（报文ID变更）"""
        changes = []
        # 构建 name -> id 映射
        old_name_to_id = {msg.name: msg_id for msg_id, msg in old_dbc.messages.items()}
        new_name_to_id = {msg.name: msg_id for msg_id, msg in new_dbc.messages.items()}

        common_names = set(old_name_to_id) & set(new_name_to_id)
        for name in sorted(common_names):
            old_id = old_name_to_id[name]
            new_id = new_name_to_id[name]
            if old_id != new_id:
                changes.append(MessageIdChange(
                    msg_name=name,
                    old_id=old_id,
                    new_id=new_id,
                    old_message=old_dbc.messages[old_id],
                    new_message=new_dbc.messages[new_id],
                ))
        return changes

    # -- 工具方法 ------------------------------

    def _compare_dicts(self, old_d: Dict, new_d: Dict, prefix: str = "") -> List[FieldChange]:
        changes = []
        all_keys = set(old_d.keys()) | set(new_d.keys())
        for k in sorted(all_keys):
            old_v = old_d.get(k, "<不存在>")
            new_v = new_d.get(k, "<不存在>")
            if old_v != new_v:
                label = f"{prefix}.{k}" if prefix else k
                changes.append(FieldChange(label, old_v, new_v))
        return changes


# ============================================================
# Section: dbc_report.py
# ============================================================

"""
DBC报告生成模块 - dbc_report.py
支持输出：控制台文本报告 / Markdown报告 / HTML报告 / CSV报告
"""



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

def _gen_sig_send_type_label(val) -> str:
    """将 GenSigSendType 的值转换为可读字符串（0=Cyclic, 1=OnWrite）"""
    if val is None or val == '':
        return ''
    _MAP = {0: 'Cyclic', 1: 'OnWrite', '0': 'Cyclic', '1': 'OnWrite',
            'Cyclic': 'Cyclic', 'OnWrite': 'OnWrite'}
    return _MAP.get(val, str(val))

def _gen_msg_send_type_label(val) -> str:
    """将 GenMsgSendType 的值转换为可读字符串"""
    if val is None or val == '':
        return ''
    _MAP = {
        0: 'cyclic', 1: 'spontaneous', 2: 'cycliclfActive',
        3: 'spontaneousWithDelay', 4: 'cyclicAndSpontaneous',
        5: 'cyclicAndSpontaneousWithDelay', 6: 'IfActive',
        '0': 'cyclic', '1': 'spontaneous', '2': 'cycliclfActive',
        '3': 'spontaneousWithDelay', '4': 'cyclicAndSpontaneous',
        '5': 'cyclicAndSpontaneousWithDelay', '6': 'IfActive',
        'cyclic': 'cyclic', 'spontaneous': 'spontaneous',
        'cycliclfActive': 'cycliclfActive', 'spontaneousWithDelay': 'spontaneousWithDelay',
        'cyclicAndSpontaneous': 'cyclicAndSpontaneous',
        'cyclicAndSpontaneousWithDelay': 'cyclicAndSpontaneousWithDelay',
        'IfActive': 'IfActive',
    }
    return _MAP.get(val, str(val))

# GenMsg* 报文属性列表（用于比较和展示）
_GEN_MSG_ATTRS = [
    ('GenMsgSendType',         '发送类型'),
    ('GenMsgCycleTime',        '周期时间'),
    ('GenMsgCycleTimeFast',    '快速周期'),
    ('GenMsgDelayTime',        '延迟时间'),
    ('GenMsgNrofRepetition',   '重复次数'),
    ('GenMsgStartDelayTime',   '启动延迟'),
]




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
                    html.append("<table><tr><th>变更类型</th><th>信号名</th><th>变更字段</th></tr>")
                    for sc in mc.signal_changes:
                        tag_cls = sc.change_type.lower()
                        label = _change_label(sc.change_type)
                        if sc.change_type == ChangeType.ADDED and sc.new_signal:
                            sig = sc.new_signal
                            detail = (f'起始位=<code>{sig.start_bit}</code>&nbsp;&nbsp;'
                                      f'位长度=<code>{sig.length}</code>')
                        elif sc.change_type == ChangeType.REMOVED and sc.old_signal:
                            sig = sc.old_signal
                            detail = (f'起始位=<code>{sig.start_bit}</code>&nbsp;&nbsp;'
                                      f'位长度=<code>{sig.length}</code>')
                        elif sc.change_type == ChangeType.MODIFIED and sc.field_changes:
                            detail = "; ".join(
                                f"{fc.field_name}: <code>{fc.old_value}</code>-><code>{fc.new_value}</code>"
                                for fc in sc.field_changes
                            )
                        else:
                            detail = "-"
                        html.append(f"<tr><td><span class='tag-{tag_cls}'>{label}</span></td>"
                                    f"<td><strong><code>{sc.signal_name}</code></strong></td>"
                                    f"<td>{detail}</td></tr>")
                    html.append("</table>")

                html.append("</div>")

        html.append("</body></html>")
        return "".join(html)

    def _signal_table(self, signals: dict) -> str:
        rows = ["<table><tr><th>信号名</th><th>起始位</th><th>长度(bit)</th></tr>"]
        for sig_name, sig in sorted(signals.items()):
            rows.append(f"<tr><td><code>{sig_name}</code></td><td>{sig.start_bit}</td><td>{sig.length}</td></tr>")
        rows.append("</table>")
        return "".join(rows)

    def _signal_detail_table(self, sig: Signal) -> str:
        rows = ["<table>"]
        fields = [
            ("起始位", sig.start_bit),
            ("位长度", sig.length),
        ]
        for k, v in fields:
            rows.append(f"<tr><td><strong>{k}</strong></td><td><code>{v}</code></td></tr>")
        rows.append("</table>")
        return "".join(rows)

    def save(self, result: DBCDiffResult, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate(result))
        print(f"[HTMLReporter] 报告已保存: {filepath}")




# ============================================================
# Section: dbc_batch_diff.py
# ============================================================

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


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))



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

class DBCBatchReportGenerator:
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
                    # GenMsg* 报文属性展示
                    _msg_attr_parts = []
                    for _ak, _al in _GEN_MSG_ATTRS:
                        _av = msg.attributes.get(_ak)
                        if _av is not None and _av != '':
                            _av_label = _gen_msg_send_type_label(_av) if _ak == 'GenMsgSendType' else str(_av)
                            _msg_attr_parts.append(f'<em>{_al}</em>: <code class="new-val">{_av_label}</code>')
                    if _msg_attr_parts:
                        html.append('<div class="attr-row" style="margin-left:4px;margin-bottom:4px;font-size:0.9em">' + ' &nbsp;|&nbsp; '.join(_msg_attr_parts) + '</div>')
                    if msg.signals:
                        html.append('<table style="margin-left:20px;width:calc(100% - 20px)">'
                                    '<tr><th>信号名</th><th>起始位</th><th>位长度</th></tr>')
                        for sig_name, sig in sorted(msg.signals.items()):
                            html.append(f'<tr><td><strong>{sig_name}</strong></td>'
                                        f'<td>{sig.start_bit}</td>'
                                        f'<td>{sig.length}</td></tr>')
                        html.append('</table>')

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
                    if mc.attr_changes:
                        html.append('<ul>')
                        for fc in mc.attr_changes:
                            html.append(f'<li><em>{fc.field_name}</em>: '
                                        f'<code class="old-val">{fc.old_value}</code> → '
                                        f'<code class="new-val">{fc.new_value}</code></li>')
                        html.append('</ul>')
                    if mc.signal_changes:
                        html.append('<table style="margin-left:20px;width:calc(100% - 20px)">'
                                    '<tr><th>变更类型</th><th>信号名</th><th>变更字段</th></tr>')
                        for sc in mc.signal_changes:
                            tag = {"ADDED": "tag-add", "REMOVED": "tag-del", "MODIFIED": "tag-mod"}.get(sc.change_type, "")
                            label = {"ADDED": "新增", "REMOVED": "删除", "MODIFIED": "修改"}.get(sc.change_type, sc.change_type)
                            if sc.change_type == "ADDED" and sc.new_signal is not None:
                                field_str = (f'起始位=<code>{sc.new_signal.start_bit}</code>  '
                                             f'位长度=<code>{sc.new_signal.length}</code>')
                            elif sc.change_type == "REMOVED" and sc.old_signal is not None:
                                field_str = (f'起始位=<code>{sc.old_signal.start_bit}</code>  '
                                             f'位长度=<code>{sc.old_signal.length}</code>')
                            else:
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

    reporter = DBCBatchReportGenerator()
    reporter.generate(batch_result, args.output_dir, args.format)



# ============================================================
# Section: ldf_parser.py
# ============================================================

"""
LDF文件解析器 - ldf_parser.py
解析LIN LDF文件的所有Section，构建结构化数据模型

支持的Section：
  - 头部信息（LIN_protocol_version / LIN_speed 等）
  - Nodes（主从节点）
  - Signals（信号定义）
  - Diagnostic_signals（诊断信号）
  - Frames（数据帧）
  - Diagnostic_frames（诊断帧）
  - Node_attributes（从节点属性）
  - Schedule_tables（调度表）
  - Signal_encoding_types（信号编码类型）
  - Signal_representation（信号编码映射）
"""



# ---------------------------------------------
# 数据模型
# ---------------------------------------------

@dataclass
class LDFSignal:
    """LIN信号定义"""
    name: str
    length: int           # 信号位长度
    init_value: Any       # 初始值（整数或字节数组）
    publisher: str        # 发布节点
    subscribers: List[str] = field(default_factory=list)  # 订阅节点列表
    comment: str = ""
    encoding_type: str = ""   # 关联的编码类型名称

    def __eq__(self, other):
        if not isinstance(other, LDFSignal):
            return False
        return (self.length == other.length and
                self.init_value == other.init_value and
                self.publisher == other.publisher and
                sorted(self.subscribers) == sorted(other.subscribers))


@dataclass
class LDFFrameSignal:
    """帧内信号引用"""
    signal_name: str
    start_bit: int   # 信号在帧内的起始位


@dataclass
class LDFFrame:
    """LIN数据帧定义"""
    name: str
    frame_id: int         # 帧ID（0-63）
    publisher: str        # 发布节点
    length: int           # 帧长度（字节）
    signals: List[LDFFrameSignal] = field(default_factory=list)
    comment: str = ""

    def __eq__(self, other):
        if not isinstance(other, LDFFrame):
            return False
        return (self.frame_id == other.frame_id and
                self.name == other.name and
                self.publisher == other.publisher and
                self.length == other.length)


@dataclass
class LDFMasterNode:
    """LIN主节点"""
    name: str
    time_base: float   # 时基（ms）
    jitter: float      # 抖动（ms）


@dataclass
class LDFScheduleEntry:
    """调度表条目"""
    frame_name: str
    delay_ms: float    # 延迟时间（ms）


@dataclass
class LDFScheduleTable:
    """调度表"""
    name: str
    entries: List[LDFScheduleEntry] = field(default_factory=list)


@dataclass
class LDFEncodingValue:
    """信号编码值（物理值或逻辑值）"""
    encode_type: str    # 'physical' / 'logical' / 'bcd' / 'ascii'
    min_val: float = 0.0
    max_val: float = 0.0
    scale: float = 1.0
    offset: float = 0.0
    unit: str = ""
    text_value: int = 0
    text_name: str = ""


@dataclass
class LDFEncodingType:
    """信号编码类型定义"""
    name: str
    values: List[LDFEncodingValue] = field(default_factory=list)


@dataclass
class LDFNodeAttribute:
    """从节点属性"""
    node_name: str
    lin_protocol: str = ""
    configured_nad: int = 0
    initial_nad: int = 0
    product_id: str = ""
    response_error: str = ""
    fault_state_signals: List[str] = field(default_factory=list)
    p2_min: float = 0.0
    st_min: float = 0.0
    n_as_timeout: float = 0.0
    n_cr_timeout: float = 0.0
    configurable_frames: Dict[str, int] = field(default_factory=dict)


@dataclass
class LDFFile:
    """LDF文件完整数据模型"""
    # 头部信息
    lin_protocol_version: str = ""
    lin_language_version: str = ""
    lin_speed: str = ""          # 如 "19.2 kbps"
    channel_name: str = ""

    # 节点
    master: Optional[LDFMasterNode] = None
    slaves: List[str] = field(default_factory=list)

    # 信号
    signals: Dict[str, LDFSignal] = field(default_factory=dict)
    diagnostic_signals: Dict[str, LDFSignal] = field(default_factory=dict)

    # 帧
    frames: Dict[str, LDFFrame] = field(default_factory=dict)
    diagnostic_frames: Dict[str, LDFFrame] = field(default_factory=dict)

    # 节点属性
    node_attributes: Dict[str, LDFNodeAttribute] = field(default_factory=dict)

    # 调度表
    schedule_tables: Dict[str, LDFScheduleTable] = field(default_factory=dict)

    # 信号编码
    encoding_types: Dict[str, LDFEncodingType] = field(default_factory=dict)
    signal_representations: Dict[str, str] = field(default_factory=dict)  # signal_name -> encoding_type_name

    source_file: str = ""

    def get_frame_by_id(self, frame_id: int) -> Optional[LDFFrame]:
        for f in self.frames.values():
            if f.frame_id == frame_id:
                return f
        return None


# ---------------------------------------------
# 解析器
# ---------------------------------------------

class LDFParser:
    """
    LDF文件解析器
    支持 LIN 2.0 / 2.1 / 2.2 格式
    """

    def __init__(self):
        self._ldf: LDFFile = LDFFile()

    def parse_file(self, filepath: str) -> LDFFile:
        self._ldf = LDFFile(source_file=filepath)
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        self._parse(content)
        return self._ldf

    def parse_string(self, content: str, source: str = "<string>") -> LDFFile:
        self._ldf = LDFFile(source_file=source)
        self._parse(content)
        return self._ldf

    # -- 主解析流程 ----------------------------

    def _parse(self, content: str):
        # 去除注释（// 行注释 和 /* */ 块注释）
        content = re.sub(r'//[^\n]*', '', content)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # 解析头部（Section之前的全局行）
        self._parse_header(content)

        # 提取并解析各Section块
        sections = self._extract_sections(content)
        for sec_name, sec_body in sections.items():
            name_lower = sec_name.lower()
            if name_lower == 'nodes':
                self._parse_nodes(sec_body)
            elif name_lower == 'signals':
                self._parse_signals(sec_body)
            elif name_lower == 'diagnostic_signals':
                self._parse_diagnostic_signals(sec_body)
            elif name_lower == 'frames':
                self._parse_frames(sec_body)
            elif name_lower == 'diagnostic_frames':
                self._parse_diagnostic_frames(sec_body)
            elif name_lower == 'node_attributes':
                self._parse_node_attributes(sec_body)
            elif name_lower == 'schedule_tables':
                self._parse_schedule_tables(sec_body)
            elif name_lower == 'signal_encoding_types':
                self._parse_encoding_types(sec_body)
            elif name_lower == 'signal_representation':
                self._parse_signal_representation(sec_body)

    def _extract_sections(self, content: str) -> Dict[str, str]:
        """
        提取顶层 SectionName { ... } 块。
        只匹配顶层（大括号深度为0时出现的）section，
        避免把帧/节点属性内的嵌套块误识别为section。
        """
        sections = {}
        # 已知的顶层 section 名称（大小写不敏感）
        _TOP_SECTIONS = {
            'nodes', 'signals', 'diagnostic_signals',
            'frames', 'diagnostic_frames', 'node_attributes',
            'schedule_tables', 'signal_encoding_types', 'signal_representation',
        }
        # 匹配 Word { 模式
        pattern = re.compile(r'(\w+)\s*\{', re.MULTILINE)
        pos = 0
        depth = 0  # 当前大括号深度（在section外时为0）
        while pos < len(content):
            m = pattern.search(content, pos)
            if not m:
                break
            sec_name = m.group(1)
            # 只在顶层（depth==0）且是已知section名时才提取
            if depth == 0 and sec_name.lower() in _TOP_SECTIONS:
                brace_start = m.end() - 1
                # 找到匹配的右括号（完整提取，包含嵌套）
                d = 0
                i = brace_start
                while i < len(content):
                    if content[i] == '{':
                        d += 1
                    elif content[i] == '}':
                        d -= 1
                        if d == 0:
                            break
                    i += 1
                sec_body = content[brace_start + 1:i]
                sections[sec_name] = sec_body
                pos = i + 1
                # depth 保持0，因为我们跳过了整个section块
            else:
                # 跳过这个 { 并追踪深度（用于跳过非顶层块）
                # 找到这个 { 的位置
                brace_pos = m.end() - 1
                # 如果在某个section内部，需要追踪深度
                # 但由于我们用整块提取，这里直接跳过
                pos = m.end()
        return sections

    # -- 头部解析 ------------------------------

    def _parse_header(self, content: str):
        m = re.search(r'LIN_protocol_version\s*=\s*"?([^";]+)"?\s*;', content)
        if m:
            self._ldf.lin_protocol_version = m.group(1).strip()

        m = re.search(r'LIN_language_version\s*=\s*"?([^";]+)"?\s*;', content)
        if m:
            self._ldf.lin_language_version = m.group(1).strip()

        m = re.search(r'LIN_speed\s*=\s*([^;]+);', content)
        if m:
            self._ldf.lin_speed = m.group(1).strip()

        m = re.search(r'Channel_name\s*=\s*"?([^";]+)"?\s*;', content)
        if m:
            self._ldf.channel_name = m.group(1).strip()

    # -- Nodes 解析 ----------------------------

    def _parse_nodes(self, body: str):
        # Master: name, time_base, jitter;
        m = re.search(
            r'Master\s*:\s*(\w+)\s*,\s*([\d.]+)\s*ms\s*,\s*([\d.]+)\s*ms\s*;',
            body, re.IGNORECASE
        )
        if m:
            self._ldf.master = LDFMasterNode(
                name=m.group(1),
                time_base=float(m.group(2)),
                jitter=float(m.group(3))
            )

        # Slaves: name1, name2, ...;
        m = re.search(r'Slaves\s*:\s*([^;]+);', body, re.IGNORECASE)
        if m:
            slaves_str = m.group(1)
            self._ldf.slaves = [s.strip() for s in slaves_str.split(',') if s.strip()]

    # -- Signals 解析 -------------------------

    def _parse_signals(self, body: str):
        """
        格式：signal_name : signal_size, init_value, published_by {, subscribed_by} ;
        """
        # 匹配每条信号定义
        pattern = re.compile(
            r'(\w+)\s*:\s*(\d+)\s*,\s*'           # name : size ,
            r'(\{[^}]*\}|0x[\dA-Fa-f]+|\d+)\s*,'  # init_value ,
            r'\s*(\w+)'                             # publisher
            r'((?:\s*,\s*\w+)*)\s*;',              # [, subscriber ...] ;
            re.MULTILINE
        )
        for m in pattern.finditer(body):
            name = m.group(1)
            length = int(m.group(2))
            init_raw = m.group(3).strip()
            publisher = m.group(4).strip()
            subs_raw = m.group(5)

            # 解析初始值
            init_value = self._parse_init_value(init_raw)

            # 解析订阅者
            subscribers = []
            if subs_raw:
                subscribers = [s.strip() for s in subs_raw.split(',') if s.strip()]

            sig = LDFSignal(
                name=name,
                length=length,
                init_value=init_value,
                publisher=publisher,
                subscribers=subscribers
            )
            self._ldf.signals[name] = sig

    def _parse_diagnostic_signals(self, body: str):
        """诊断信号格式与普通信号相同"""
        pattern = re.compile(
            r'(\w+)\s*:\s*(\d+)\s*,\s*'
            r'(\{[^}]*\}|0x[\dA-Fa-f]+|\d+)\s*;',
            re.MULTILINE
        )
        for m in pattern.finditer(body):
            name = m.group(1)
            length = int(m.group(2))
            init_value = self._parse_init_value(m.group(3).strip())
            sig = LDFSignal(
                name=name,
                length=length,
                init_value=init_value,
                publisher="",
                subscribers=[]
            )
            self._ldf.diagnostic_signals[name] = sig

    def _parse_init_value(self, raw: str) -> Any:
        """解析初始值：整数、十六进制、或字节数组 {0x00, 0x01, ...}"""
        raw = raw.strip()
        if raw.startswith('{'):
            # 字节数组
            inner = raw.strip('{}')
            parts = [p.strip() for p in inner.split(',') if p.strip()]
            result = []
            for p in parts:
                try:
                    result.append(int(p, 16) if p.startswith('0x') or p.startswith('0X') else int(p))
                except ValueError:
                    result.append(0)
            return result
        elif raw.startswith('0x') or raw.startswith('0X'):
            try:
                return int(raw, 16)
            except ValueError:
                return 0
        else:
            try:
                return int(raw)
            except ValueError:
                return 0

    # -- Frames 解析 --------------------------

    def _parse_frames(self, body: str):
        """
        格式：
        frame_name : frame_id, published_by, frame_size {
            signal_name, start_bit;
            ...
        }
        frame_id 可以是十进制或十六进制（0x01）
        """
        # 逐个提取帧块（支持嵌套大括号）
        # 先找 "name : id, publisher, size {" 模式
        header_pattern = re.compile(
            r'(\w+)\s*:\s*(0x[\dA-Fa-f]+|\d+)\s*,\s*(\w+)\s*,\s*(\d+)\s*\{',
            re.MULTILINE
        )
        for hm in header_pattern.finditer(body):
            name = hm.group(1)
            fid_raw = hm.group(2)
            frame_id = int(fid_raw, 16) if fid_raw.startswith('0x') or fid_raw.startswith('0X') else int(fid_raw)
            publisher = hm.group(3)
            length = int(hm.group(4))
            # 找到 { 后的内容，直到匹配的 }
            brace_start = hm.end() - 1
            d = 0
            i = brace_start
            while i < len(body):
                if body[i] == '{':
                    d += 1
                elif body[i] == '}':
                    d -= 1
                    if d == 0:
                        break
                i += 1
            signals_body = body[brace_start + 1:i]

            frame = LDFFrame(
                name=name,
                frame_id=frame_id,
                publisher=publisher,
                length=length
            )

            # 解析帧内信号
            sig_pattern = re.compile(r'(\w+)\s*,\s*(\d+)\s*;')
            for sm in sig_pattern.finditer(signals_body):
                frame.signals.append(LDFFrameSignal(
                    signal_name=sm.group(1),
                    start_bit=int(sm.group(2))
                ))

            self._ldf.frames[name] = frame

    def _parse_diagnostic_frames(self, body: str):
        """诊断帧格式与普通帧相同"""
        frame_pattern = re.compile(
            r'(\w+)\s*:\s*(0x[\dA-Fa-f]+|\d+)\s*\{([^}]*)\}',
            re.DOTALL
        )
        for m in frame_pattern.finditer(body):
            name = m.group(1)
            fid_raw = m.group(2)
            frame_id = int(fid_raw, 16) if fid_raw.startswith('0x') else int(fid_raw)
            signals_body = m.group(3)

            frame = LDFFrame(name=name, frame_id=frame_id, publisher="", length=8)
            sig_pattern = re.compile(r'(\w+)\s*,\s*(\d+)\s*;')
            for sm in sig_pattern.finditer(signals_body):
                frame.signals.append(LDFFrameSignal(
                    signal_name=sm.group(1),
                    start_bit=int(sm.group(2))
                ))
            self._ldf.diagnostic_frames[name] = frame

    # -- Node_attributes 解析 -----------------

    def _parse_node_attributes(self, body: str):
        """
        格式：
        node_name {
            LIN_protocol = "2.1";
            configured_NAD = 0x01;
            ...
        }
        """
        node_pattern = re.compile(r'(\w+)\s*\{([^}]*)\}', re.DOTALL)
        for m in node_pattern.finditer(body):
            node_name = m.group(1)
            attrs_body = m.group(2)
            attr = LDFNodeAttribute(node_name=node_name)

            def _get(pattern, text, default=""):
                mm = re.search(pattern, text, re.IGNORECASE)
                return mm.group(1).strip().strip('"') if mm else default

            attr.lin_protocol = _get(r'LIN_protocol\s*=\s*"?([^";]+)"?\s*;', attrs_body)
            nad_raw = _get(r'configured_NAD\s*=\s*(0x[\dA-Fa-f]+|\d+)\s*;', attrs_body)
            if nad_raw:
                attr.configured_nad = int(nad_raw, 16) if nad_raw.startswith('0x') else int(nad_raw)
            initial_nad_raw = _get(r'initial_NAD\s*=\s*(0x[\dA-Fa-f]+|\d+)\s*;', attrs_body)
            if initial_nad_raw:
                attr.initial_nad = int(initial_nad_raw, 16) if initial_nad_raw.startswith('0x') else int(initial_nad_raw)
            attr.product_id = _get(r'product_id\s*=\s*([^;]+);', attrs_body)
            attr.response_error = _get(r'response_error\s*=\s*(\w+)\s*;', attrs_body)

            p2_raw = _get(r'P2_min\s*=\s*([\d.]+)\s*ms\s*;', attrs_body)
            if p2_raw:
                attr.p2_min = float(p2_raw)
            st_raw = _get(r'ST_min\s*=\s*([\d.]+)\s*ms\s*;', attrs_body)
            if st_raw:
                attr.st_min = float(st_raw)

            # configurable_frames
            cf_m = re.search(r'configurable_frames\s*\{([^}]*)\}', attrs_body, re.DOTALL)
            if cf_m:
                for cf in re.finditer(r'(\w+)\s*(?:=\s*(0x[\dA-Fa-f]+|\d+))?\s*;', cf_m.group(1)):
                    fname = cf.group(1)
                    fid_raw = cf.group(2) or "0"
                    fid = int(fid_raw, 16) if fid_raw.startswith('0x') else int(fid_raw)
                    attr.configurable_frames[fname] = fid

            self._ldf.node_attributes[node_name] = attr

    # -- Schedule_tables 解析 -----------------

    def _parse_schedule_tables(self, body: str):
        """
        格式：
        table_name {
            frame_name delay X ms;
            ...
        }
        """
        table_pattern = re.compile(r'(\w+)\s*\{([^}]*)\}', re.DOTALL)
        for m in table_pattern.finditer(body):
            table_name = m.group(1)
            entries_body = m.group(2)
            table = LDFScheduleTable(name=table_name)

            entry_pattern = re.compile(
                r'(\w+)\s+delay\s+([\d.]+)\s*ms\s*;',
                re.IGNORECASE
            )
            for em in entry_pattern.finditer(entries_body):
                table.entries.append(LDFScheduleEntry(
                    frame_name=em.group(1),
                    delay_ms=float(em.group(2))
                ))
            self._ldf.schedule_tables[table_name] = table

    # -- Signal_encoding_types 解析 -----------

    def _parse_encoding_types(self, body: str):
        """
        格式：
        encoding_name {
            physical_value, min, max, scale, offset, "unit";
            logical_value, value, "text";
        }
        """
        enc_pattern = re.compile(r'(\w+)\s*\{([^}]*)\}', re.DOTALL)
        for m in enc_pattern.finditer(body):
            enc_name = m.group(1)
            enc_body = m.group(2)
            enc = LDFEncodingType(name=enc_name)

            # physical_value: min, max, scale, offset, "unit"
            for pm in re.finditer(
                r'physical_value\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.eE+\-]+)\s*,\s*([\d.eE+\-]+)\s*,\s*"([^"]*)"\s*;',
                enc_body, re.IGNORECASE
            ):
                enc.values.append(LDFEncodingValue(
                    encode_type='physical',
                    min_val=float(pm.group(1)),
                    max_val=float(pm.group(2)),
                    scale=float(pm.group(3)),
                    offset=float(pm.group(4)),
                    unit=pm.group(5)
                ))

            # logical_value: value, "text"
            for lm in re.finditer(
                r'logical_value\s*,\s*(\d+)\s*,\s*"([^"]*)"\s*;',
                enc_body, re.IGNORECASE
            ):
                enc.values.append(LDFEncodingValue(
                    encode_type='logical',
                    text_value=int(lm.group(1)),
                    text_name=lm.group(2)
                ))

            # bcd_value / ascii_value
            if re.search(r'bcd_value\s*;', enc_body, re.IGNORECASE):
                enc.values.append(LDFEncodingValue(encode_type='bcd'))
            if re.search(r'ascii_value\s*;', enc_body, re.IGNORECASE):
                enc.values.append(LDFEncodingValue(encode_type='ascii'))

            self._ldf.encoding_types[enc_name] = enc

    # -- Signal_representation 解析 -----------

    def _parse_signal_representation(self, body: str):
        """
        格式：encoding_type_name : signal1, signal2, ... ;
        """
        for m in re.finditer(r'(\w+)\s*:\s*([^;]+);', body):
            enc_name = m.group(1).strip()
            signals_str = m.group(2)
            for sig_name in [s.strip() for s in signals_str.split(',') if s.strip()]:
                self._ldf.signal_representations[sig_name] = enc_name
                # 同步到信号对象
                if sig_name in self._ldf.signals:
                    self._ldf.signals[sig_name].encoding_type = enc_name

# ============================================================
# Section: ldf_diff.py
# ============================================================

"""
LDF差异分析模块 - ldf_diff.py
对比两个LDF文件，识别新增、删除、修改的节点/帧/信号/调度表/编码类型
"""



# ---------------------------------------------
# 变更类型枚举
# ---------------------------------------------

class ChangeType:
    ADDED    = "ADDED"
    REMOVED  = "REMOVED"
    MODIFIED = "MODIFIED"


# ---------------------------------------------
# 变更记录数据类
# ---------------------------------------------

@dataclass
class FieldChange:
    """单个字段的变更"""
    field_name: str
    old_value: Any
    new_value: Any

    def __str__(self):
        return f"  {self.field_name}: {self.old_value!r} -> {self.new_value!r}"


@dataclass
class LDFSignalChange:
    """信号级别的变更"""
    change_type: str
    frame_name: str
    signal_name: str
    old_signal: Optional[LDFSignal] = None
    new_signal: Optional[LDFSignal] = None
    field_changes: List[FieldChange] = field(default_factory=list)

    def summary(self) -> str:
        if self.change_type == ChangeType.ADDED:
            return f"[新增信号] {self.frame_name}.{self.signal_name}"
        elif self.change_type == ChangeType.REMOVED:
            return f"[删除信号] {self.frame_name}.{self.signal_name}"
        else:
            changes_str = "; ".join(
                f"{c.field_name}: {c.old_value!r}->{c.new_value!r}"
                for c in self.field_changes
            )
            return f"[修改信号] {self.frame_name}.{self.signal_name} [{changes_str}]"


@dataclass
class LDFFrameSignalPosChange:
    """帧内信号位置变更"""
    signal_name: str
    old_start_bit: int
    new_start_bit: int

    def summary(self) -> str:
        return f"信号 {self.signal_name} 起始位: {self.old_start_bit}->{self.new_start_bit}"


@dataclass
class LDFFrameChange:
    """帧级别的变更"""
    change_type: str
    frame_name: str
    old_frame: Optional[LDFFrame] = None
    new_frame: Optional[LDFFrame] = None
    field_changes: List[FieldChange] = field(default_factory=list)
    signal_added: List[str] = field(default_factory=list)    # 新增的信号名
    signal_removed: List[str] = field(default_factory=list)  # 删除的信号名
    signal_pos_changes: List[LDFFrameSignalPosChange] = field(default_factory=list)

    def summary(self) -> str:
        if self.change_type == ChangeType.ADDED:
            return f"[新增帧] {self.frame_name}"
        elif self.change_type == ChangeType.REMOVED:
            return f"[删除帧] {self.frame_name}"
        else:
            parts = []
            if self.field_changes:
                parts.append(f"{len(self.field_changes)}个属性变更")
            if self.signal_added:
                parts.append(f"新增{len(self.signal_added)}个信号")
            if self.signal_removed:
                parts.append(f"删除{len(self.signal_removed)}个信号")
            if self.signal_pos_changes:
                parts.append(f"{len(self.signal_pos_changes)}个信号位置变更")
            detail = ", ".join(parts) if parts else "无实质变更"
            return f"[修改帧] {self.frame_name} [{detail}]"

    def has_changes(self) -> bool:
        return bool(self.field_changes or self.signal_added or
                    self.signal_removed or self.signal_pos_changes)


@dataclass
class LDFNodeChange:
    """节点级别的变更"""
    change_type: str
    node_name: str
    is_master: bool = False
    field_changes: List[FieldChange] = field(default_factory=list)

    def summary(self) -> str:
        role = "主节点" if self.is_master else "从节点"
        if self.change_type == ChangeType.ADDED:
            return f"[新增{role}] {self.node_name}"
        elif self.change_type == ChangeType.REMOVED:
            return f"[删除{role}] {self.node_name}"
        else:
            changes_str = "; ".join(
                f"{c.field_name}: {c.old_value!r}->{c.new_value!r}"
                for c in self.field_changes
            )
            return f"[修改{role}] {self.node_name} [{changes_str}]"


@dataclass
class LDFScheduleChange:
    """调度表级别的变更"""
    change_type: str
    table_name: str
    old_table: Optional[LDFScheduleTable] = None
    new_table: Optional[LDFScheduleTable] = None
    entries_added: List[str] = field(default_factory=list)
    entries_removed: List[str] = field(default_factory=list)
    entries_modified: List[FieldChange] = field(default_factory=list)   # 延迟变更
    entries_reordered: List["LDFScheduleOrderChange"] = field(default_factory=list)  # 顺序变更

    def summary(self) -> str:
        if self.change_type == ChangeType.ADDED:
            return f"[新增调度表] {self.table_name}"
        elif self.change_type == ChangeType.REMOVED:
            return f"[删除调度表] {self.table_name}"
        else:
            parts = []
            if self.entries_added:
                parts.append(f"新增{len(self.entries_added)}条目")
            if self.entries_removed:
                parts.append(f"删除{len(self.entries_removed)}条目")
            if self.entries_modified:
                parts.append(f"修改{len(self.entries_modified)}条目延迟")
            if self.entries_reordered:
                parts.append(f"{len(self.entries_reordered)}条目顺序变更")
            detail = ", ".join(parts) if parts else "无实质变更"
            return f"[修改调度表] {self.table_name} [{detail}]"

    def has_changes(self) -> bool:
        return bool(self.entries_added or self.entries_removed or
                    self.entries_modified or self.entries_reordered)


@dataclass
class LDFNodeAttrChange:
    """从节点属性（Node_attributes）级别的变更"""
    change_type: str
    node_name: str
    field_changes: List[FieldChange] = field(default_factory=list)
    # configurable_frames 变更
    frames_added: List[str] = field(default_factory=list)
    frames_removed: List[str] = field(default_factory=list)
    frames_id_changed: List[FieldChange] = field(default_factory=list)

    def summary(self) -> str:
        if self.change_type == ChangeType.ADDED:
            return f"[新增节点属性] {self.node_name}"
        elif self.change_type == ChangeType.REMOVED:
            return f"[删除节点属性] {self.node_name}"
        else:
            parts = []
            if self.field_changes:
                parts.append(f"{len(self.field_changes)}个属性变更")
            if self.frames_added:
                parts.append(f"新增{len(self.frames_added)}个可配置帧")
            if self.frames_removed:
                parts.append(f"删除{len(self.frames_removed)}个可配置帧")
            if self.frames_id_changed:
                parts.append(f"{len(self.frames_id_changed)}个帧ID变更")
            detail = ", ".join(parts) if parts else "无实质变更"
            return f"[修改节点属性] {self.node_name} [{detail}]"

    def has_changes(self) -> bool:
        return bool(self.field_changes or self.frames_added or
                    self.frames_removed or self.frames_id_changed)


@dataclass
class LDFScheduleOrderChange:
    """调度表条目顺序变更"""
    frame_name: str
    old_index: int
    new_index: int

    def summary(self) -> str:
        return f"帧 {self.frame_name} 顺序: 第{self.old_index+1}位 -> 第{self.new_index+1}位"


@dataclass
class LDFEncodingChange:
    """编码类型级别的变更"""
    change_type: str
    encoding_name: str
    field_changes: List[FieldChange] = field(default_factory=list)

    def summary(self) -> str:
        if self.change_type == ChangeType.ADDED:
            return f"[新增编码类型] {self.encoding_name}"
        elif self.change_type == ChangeType.REMOVED:
            return f"[删除编码类型] {self.encoding_name}"
        else:
            return f"[修改编码类型] {self.encoding_name} [{len(self.field_changes)}处变更]"


@dataclass
class LDFDiffResult:
    """LDF差异分析完整结果"""
    old_file: str
    new_file: str
    node_changes: List[LDFNodeChange] = field(default_factory=list)
    node_attr_changes: List[LDFNodeAttrChange] = field(default_factory=list)
    frame_changes: List[LDFFrameChange] = field(default_factory=list)
    signal_changes: List[LDFSignalChange] = field(default_factory=list)
    schedule_changes: List[LDFScheduleChange] = field(default_factory=list)
    encoding_changes: List[LDFEncodingChange] = field(default_factory=list)

    # -- 统计快捷属性 --
    @property
    def added_frames(self) -> List[LDFFrameChange]:
        return [c for c in self.frame_changes if c.change_type == ChangeType.ADDED]

    @property
    def removed_frames(self) -> List[LDFFrameChange]:
        return [c for c in self.frame_changes if c.change_type == ChangeType.REMOVED]

    @property
    def modified_frames(self) -> List[LDFFrameChange]:
        return [c for c in self.frame_changes if c.change_type == ChangeType.MODIFIED]

    @property
    def added_nodes(self) -> List[LDFNodeChange]:
        return [c for c in self.node_changes if c.change_type == ChangeType.ADDED]

    @property
    def removed_nodes(self) -> List[LDFNodeChange]:
        return [c for c in self.node_changes if c.change_type == ChangeType.REMOVED]

    @property
    def added_signals(self) -> List[LDFSignalChange]:
        return [c for c in self.signal_changes if c.change_type == ChangeType.ADDED]

    @property
    def removed_signals(self) -> List[LDFSignalChange]:
        return [c for c in self.signal_changes if c.change_type == ChangeType.REMOVED]

    @property
    def modified_signals(self) -> List[LDFSignalChange]:
        return [c for c in self.signal_changes if c.change_type == ChangeType.MODIFIED]

    def has_changes(self) -> bool:
        # 编码类型变更不影响协议栈代码生成，不计入变更判断
        return bool(self.node_changes or self.node_attr_changes or
                    self.frame_changes or self.signal_changes or
                    self.schedule_changes)

    def stats(self) -> Dict[str, int]:
        return {
            "nodes_added":        len(self.added_nodes),
            "nodes_removed":      len(self.removed_nodes),
            "nodes_modified":     sum(1 for c in self.node_changes if c.change_type == ChangeType.MODIFIED),
            "node_attrs_added":   sum(1 for c in self.node_attr_changes if c.change_type == ChangeType.ADDED),
            "node_attrs_removed": sum(1 for c in self.node_attr_changes if c.change_type == ChangeType.REMOVED),
            "node_attrs_modified":sum(1 for c in self.node_attr_changes if c.change_type == ChangeType.MODIFIED),
            "frames_added":       len(self.added_frames),
            "frames_removed":     len(self.removed_frames),
            "frames_modified":    len(self.modified_frames),
            "signals_added":      len(self.added_signals),
            "signals_removed":    len(self.removed_signals),
            "signals_modified":   len(self.modified_signals),
            "schedules_added":    sum(1 for c in self.schedule_changes if c.change_type == ChangeType.ADDED),
            "schedules_removed":  sum(1 for c in self.schedule_changes if c.change_type == ChangeType.REMOVED),
            "schedules_modified": sum(1 for c in self.schedule_changes if c.change_type == ChangeType.MODIFIED),
            "encodings_added":    0,
            "encodings_removed":  0,
            "encodings_modified": 0,
        }


# ---------------------------------------------
# 差异分析器
# ---------------------------------------------

class LDFDiff:
    """
    LDF差异分析器
    用法：
        diff = LDFDiff()
        result = diff.compare(old_ldf, new_ldf)
    """

    # 信号需要比较的字段（encoding的physical字段通过额外逻辑比较）
    _SIGNAL_FIELDS = [
        ("length",      "位长度"),
        ("init_value",  "初始值"),
        ("publisher",   "发布节点"),
        ("subscribers", "订阅节点"),
        ("comment",     "注释"),
    ]

    # 帧需要比较的字段
    _FRAME_FIELDS = [
        ("frame_id",  "帧ID"),
        ("publisher", "发布节点"),
        ("length",    "帧长度"),
        ("comment",   "注释"),
    ]

    # 主节点需要比较的字段
    _MASTER_FIELDS = [
        ("time_base", "时基(ms)"),
        ("jitter",    "抖动(ms)"),
    ]

    # 从节点属性需要比较的字段
    _NODE_ATTR_FIELDS = [
        ("lin_protocol",    "LIN协议版本"),
        ("configured_nad",  "configured_NAD"),
        ("initial_nad",     "initial_NAD"),
        ("product_id",      "product_id"),
        ("response_error",  "response_error"),
        ("p2_min",          "P2_min(ms)"),
        ("st_min",          "ST_min(ms)"),
        ("n_as_timeout",    "N_As_timeout(ms)"),
        ("n_cr_timeout",    "N_Cr_timeout(ms)"),
    ]

    def compare(self, old_ldf: LDFFile, new_ldf: LDFFile) -> LDFDiffResult:
        result = LDFDiffResult(
            old_file=old_ldf.source_file,
            new_file=new_ldf.source_file,
        )
        self._compare_nodes(old_ldf, new_ldf, result)
        self._compare_node_attributes(old_ldf, new_ldf, result)
        self._compare_signals(old_ldf, new_ldf, result)
        self._compare_frames(old_ldf, new_ldf, result)
        self._compare_schedules(old_ldf, new_ldf, result)
        # 编码类型变更不影响协议栈代码生成，忽略不比较
        # self._compare_encodings(old_ldf, new_ldf, result)
        return result

    # -- 节点比较 ------------------------------

    def _compare_nodes(self, old_ldf: LDFFile, new_ldf: LDFFile, result: LDFDiffResult):
        # 比较主节点
        if old_ldf.master and new_ldf.master:
            field_changes = []
            for attr, label in self._MASTER_FIELDS:
                ov = getattr(old_ldf.master, attr)
                nv = getattr(new_ldf.master, attr)
                if ov != nv:
                    field_changes.append(FieldChange(label, ov, nv))
            if field_changes:
                result.node_changes.append(LDFNodeChange(
                    change_type=ChangeType.MODIFIED,
                    node_name=old_ldf.master.name,
                    is_master=True,
                    field_changes=field_changes,
                ))
        elif old_ldf.master and not new_ldf.master:
            result.node_changes.append(LDFNodeChange(
                change_type=ChangeType.REMOVED,
                node_name=old_ldf.master.name,
                is_master=True,
            ))
        elif not old_ldf.master and new_ldf.master:
            result.node_changes.append(LDFNodeChange(
                change_type=ChangeType.ADDED,
                node_name=new_ldf.master.name,
                is_master=True,
            ))

        # 比较从节点列表
        old_slaves = set(old_ldf.slaves)
        new_slaves = set(new_ldf.slaves)
        for name in sorted(old_slaves - new_slaves):
            result.node_changes.append(LDFNodeChange(
                change_type=ChangeType.REMOVED,
                node_name=name,
                is_master=False,
            ))
        for name in sorted(new_slaves - old_slaves):
            result.node_changes.append(LDFNodeChange(
                change_type=ChangeType.ADDED,
                node_name=name,
                is_master=False,
            ))

    # -- 从节点属性比较 ------------------------

    def _compare_node_attributes(self, old_ldf: LDFFile, new_ldf: LDFFile, result: LDFDiffResult):
        """比较 Node_attributes section 中每个从节点的属性"""
        old_attrs = old_ldf.node_attributes
        new_attrs = new_ldf.node_attributes

        # 删除的节点属性
        for name in sorted(set(old_attrs) - set(new_attrs)):
            result.node_attr_changes.append(LDFNodeAttrChange(
                change_type=ChangeType.REMOVED,
                node_name=name,
            ))

        # 新增的节点属性
        for name in sorted(set(new_attrs) - set(old_attrs)):
            result.node_attr_changes.append(LDFNodeAttrChange(
                change_type=ChangeType.ADDED,
                node_name=name,
            ))

        # 修改的节点属性
        for name in sorted(set(old_attrs) & set(new_attrs)):
            old_a = old_attrs[name]
            new_a = new_attrs[name]
            ac = LDFNodeAttrChange(
                change_type=ChangeType.MODIFIED,
                node_name=name,
            )
            # 比较基本属性字段
            for attr, label in self._NODE_ATTR_FIELDS:
                ov = getattr(old_a, attr)
                nv = getattr(new_a, attr)
                if ov != nv:
                    ac.field_changes.append(FieldChange(label, ov, nv))

            # 比较 configurable_frames
            old_cf = old_a.configurable_frames
            new_cf = new_a.configurable_frames
            for fname in sorted(set(old_cf) - set(new_cf)):
                ac.frames_removed.append(fname)
            for fname in sorted(set(new_cf) - set(old_cf)):
                ac.frames_added.append(fname)
            for fname in sorted(set(old_cf) & set(new_cf)):
                if old_cf[fname] != new_cf[fname]:
                    ac.frames_id_changed.append(FieldChange(
                        fname,
                        f"0x{old_cf[fname]:04X}" if old_cf[fname] else old_cf[fname],
                        f"0x{new_cf[fname]:04X}" if new_cf[fname] else new_cf[fname],
                    ))

            if ac.has_changes():
                result.node_attr_changes.append(ac)

    # -- 信号比较 ------------------------------

    def _compare_signals(self, old_ldf: LDFFile, new_ldf: LDFFile, result: LDFDiffResult):
        old_sigs = old_ldf.signals
        new_sigs = new_ldf.signals

        # 先建立信号->帧的映射（用于显示）
        sig_to_frame_old = self._build_sig_frame_map(old_ldf)
        sig_to_frame_new = self._build_sig_frame_map(new_ldf)

        # 删除的信号
        for name in sorted(set(old_sigs) - set(new_sigs)):
            frame_name = sig_to_frame_old.get(name, "")
            result.signal_changes.append(LDFSignalChange(
                change_type=ChangeType.REMOVED,
                frame_name=frame_name,
                signal_name=name,
                old_signal=old_sigs[name],
            ))

        # 新增的信号
        # 建立 新LDF 信号->起始位 映射（用于展示）
        sig_to_startbit_new = self._build_sig_startbit_map(new_ldf)
        for name in sorted(set(new_sigs) - set(old_sigs)):
            frame_name = sig_to_frame_new.get(name, "")
            new_s = new_sigs[name]
            # 构建属性 field_changes（old_value="" 表示新增）
            added_fields = []
            added_fields.append(FieldChange("位长度", "", new_s.length))
            start_bit = sig_to_startbit_new.get(name, "")
            added_fields.append(FieldChange("起始位", "", start_bit))
            added_fields.append(FieldChange("初始值", "", new_s.init_value))
            # encoding physical 字段
            enc_name = new_s.encoding_type
            enc = new_ldf.encoding_types.get(enc_name) if enc_name else None
            if enc:
                phys = [v for v in enc.values if v.encode_type == 'physical']
                if phys:
                    p = phys[0]
                    added_fields.append(FieldChange("比例因子", "", p.scale))
                    added_fields.append(FieldChange("偏移", "", p.offset))
                    added_fields.append(FieldChange("单位", "", p.unit))
            if new_s.comment:
                added_fields.append(FieldChange("注释", "", new_s.comment))
            result.signal_changes.append(LDFSignalChange(
                change_type=ChangeType.ADDED,
                frame_name=frame_name,
                signal_name=name,
                new_signal=new_s,
                field_changes=added_fields,
            ))

        # 修改的信号
        for name in sorted(set(old_sigs) & set(new_sigs)):
            old_s = old_sigs[name]
            new_s = new_sigs[name]
            field_changes = []
            for attr, label in self._SIGNAL_FIELDS:
                ov = getattr(old_s, attr)
                nv = getattr(new_s, attr)
                # 对列表类型做排序比较
                if isinstance(ov, list) and isinstance(nv, list):
                    if sorted(str(x) for x in ov) != sorted(str(x) for x in nv):
                        field_changes.append(FieldChange(label, ov, nv))
                elif ov != nv:
                    field_changes.append(FieldChange(label, ov, nv))

            # 额外比较关联 encoding_type 的 physical_value 字段（比例因子/偏移/单位）
            enc_name_old = old_s.encoding_type
            enc_name_new = new_s.encoding_type
            old_enc = old_ldf.encoding_types.get(enc_name_old) if enc_name_old else None
            new_enc = new_ldf.encoding_types.get(enc_name_new) if enc_name_new else None
            if old_enc and new_enc:
                old_phys = [v for v in old_enc.values if v.encode_type == 'physical']
                new_phys = [v for v in new_enc.values if v.encode_type == 'physical']
                if old_phys and new_phys:
                    op, np_ = old_phys[0], new_phys[0]
                    for attr, label in [("scale", "比例因子"), ("offset", "偏移"), ("unit", "单位")]:
                        ov, nv = getattr(op, attr), getattr(np_, attr)
                        if ov != nv:
                            field_changes.append(FieldChange(label, ov, nv))
            elif enc_name_old != enc_name_new:
                # encoding_type 名称本身发生了变化
                field_changes.append(FieldChange("编码类型", enc_name_old or "", enc_name_new or ""))

            if field_changes:
                frame_name = sig_to_frame_new.get(name, sig_to_frame_old.get(name, ""))
                result.signal_changes.append(LDFSignalChange(
                    change_type=ChangeType.MODIFIED,
                    frame_name=frame_name,
                    signal_name=name,
                    old_signal=old_s,
                    new_signal=new_s,
                    field_changes=field_changes,
                ))

    def _build_sig_frame_map(self, ldf: LDFFile) -> Dict[str, str]:
        """构建 信号名 -> 帧名 的映射"""
        mapping = {}
        for frame in ldf.frames.values():
            for fs in frame.signals:
                mapping[fs.signal_name] = frame.name
        return mapping

    def _build_sig_startbit_map(self, ldf: LDFFile) -> Dict[str, int]:
        """构建 信号名 -> 起始位 的映射"""
        mapping = {}
        for frame in ldf.frames.values():
            for fs in frame.signals:
                mapping[fs.signal_name] = fs.start_bit
        return mapping

    # -- 帧比较 --------------------------------

    def _compare_frames(self, old_ldf: LDFFile, new_ldf: LDFFile, result: LDFDiffResult):
        old_frames = old_ldf.frames
        new_frames = new_ldf.frames

        # 删除的帧
        for name in sorted(set(old_frames) - set(new_frames)):
            result.frame_changes.append(LDFFrameChange(
                change_type=ChangeType.REMOVED,
                frame_name=name,
                old_frame=old_frames[name],
            ))

        # 新增的帧
        for name in sorted(set(new_frames) - set(old_frames)):
            result.frame_changes.append(LDFFrameChange(
                change_type=ChangeType.ADDED,
                frame_name=name,
                new_frame=new_frames[name],
            ))

        # 修改的帧
        for name in sorted(set(old_frames) & set(new_frames)):
            old_f = old_frames[name]
            new_f = new_frames[name]
            fc = LDFFrameChange(
                change_type=ChangeType.MODIFIED,
                frame_name=name,
                old_frame=old_f,
                new_frame=new_f,
            )
            # 比较帧属性
            for attr, label in self._FRAME_FIELDS:
                ov = getattr(old_f, attr)
                nv = getattr(new_f, attr)
                if ov != nv:
                    fc.field_changes.append(FieldChange(label, ov, nv))

            # 比较帧内信号列表
            old_sig_map = {fs.signal_name: fs.start_bit for fs in old_f.signals}
            new_sig_map = {fs.signal_name: fs.start_bit for fs in new_f.signals}

            for sname in sorted(set(old_sig_map) - set(new_sig_map)):
                fc.signal_removed.append(sname)
            for sname in sorted(set(new_sig_map) - set(old_sig_map)):
                fc.signal_added.append(sname)
            for sname in sorted(set(old_sig_map) & set(new_sig_map)):
                if old_sig_map[sname] != new_sig_map[sname]:
                    fc.signal_pos_changes.append(LDFFrameSignalPosChange(
                        signal_name=sname,
                        old_start_bit=old_sig_map[sname],
                        new_start_bit=new_sig_map[sname],
                    ))

            if fc.has_changes():
                result.frame_changes.append(fc)

    # -- 调度表比较 ----------------------------

    def _compare_schedules(self, old_ldf: LDFFile, new_ldf: LDFFile, result: LDFDiffResult):
        old_tables = old_ldf.schedule_tables
        new_tables = new_ldf.schedule_tables

        for name in sorted(set(old_tables) - set(new_tables)):
            result.schedule_changes.append(LDFScheduleChange(
                change_type=ChangeType.REMOVED,
                table_name=name,
                old_table=old_tables[name],
            ))

        for name in sorted(set(new_tables) - set(old_tables)):
            result.schedule_changes.append(LDFScheduleChange(
                change_type=ChangeType.ADDED,
                table_name=name,
                new_table=new_tables[name],
            ))

        for name in sorted(set(old_tables) & set(new_tables)):
            old_t = old_tables[name]
            new_t = new_tables[name]
            sc = LDFScheduleChange(
                change_type=ChangeType.MODIFIED,
                table_name=name,
                old_table=old_t,
                new_table=new_t,
            )
            # 调度表中同一帧名可能重复出现，必须用完整有序列表比较，不能用字典
            old_seq = [(e.frame_name, e.delay_ms) for e in old_t.entries]
            new_seq = [(e.frame_name, e.delay_ms) for e in new_t.entries]

            if old_seq != new_seq:
                # 用帧名集合检测新增/删除（去重后比较）
                old_names = set(e.frame_name for e in old_t.entries)
                new_names = set(e.frame_name for e in new_t.entries)
                for fname in sorted(old_names - new_names):
                    sc.entries_removed.append(fname)
                for fname in sorted(new_names - old_names):
                    sc.entries_added.append(fname)

                # 检测 delay 变更（仅对两边都存在且不重复的帧名）
                for fname in sorted(old_names & new_names):
                    old_delays = [e.delay_ms for e in old_t.entries if e.frame_name == fname]
                    new_delays = [e.delay_ms for e in new_t.entries if e.frame_name == fname]
                    if old_delays != new_delays and len(old_delays) == 1 and len(new_delays) == 1:
                        sc.entries_modified.append(FieldChange(
                            fname, old_delays[0], new_delays[0],
                        ))

                # 若帧集合相同但顺序/内容不同，记录为顺序变更（找第一处差异）
                if not sc.entries_removed and not sc.entries_added:
                    min_len = min(len(old_seq), len(new_seq))
                    for idx in range(min_len):
                        if old_seq[idx] != new_seq[idx]:
                            sc.entries_reordered.append(LDFScheduleOrderChange(
                                frame_name=new_seq[idx][0],
                                old_index=idx,
                                new_index=idx,
                            ))
                            break

            if sc.has_changes():
                result.schedule_changes.append(sc)

    # -- 编码类型比较 --------------------------

    def _compare_encodings(self, old_ldf: LDFFile, new_ldf: LDFFile, result: LDFDiffResult):
        old_enc = old_ldf.encoding_types
        new_enc = new_ldf.encoding_types

        for name in sorted(set(old_enc) - set(new_enc)):
            result.encoding_changes.append(LDFEncodingChange(
                change_type=ChangeType.REMOVED,
                encoding_name=name,
            ))

        for name in sorted(set(new_enc) - set(old_enc)):
            result.encoding_changes.append(LDFEncodingChange(
                change_type=ChangeType.ADDED,
                encoding_name=name,
            ))

        for name in sorted(set(old_enc) & set(new_enc)):
            old_e = old_enc[name]
            new_e = new_enc[name]
            # 简单比较：将values序列化为字符串比较
            old_repr = self._encoding_repr(old_e)
            new_repr = self._encoding_repr(new_e)
            if old_repr != new_repr:
                result.encoding_changes.append(LDFEncodingChange(
                    change_type=ChangeType.MODIFIED,
                    encoding_name=name,
                    field_changes=[FieldChange("编码值", old_repr, new_repr)],
                ))

    def _encoding_repr(self, enc: LDFEncodingType) -> str:
        parts = []
        for v in enc.values:
            if v.encode_type == 'physical':
                parts.append(f"physical({v.min_val},{v.max_val},{v.scale},{v.offset},{v.unit})")
            elif v.encode_type == 'logical':
                parts.append(f"logical({v.text_value},{v.text_name})")
            else:
                parts.append(v.encode_type)
        return "|".join(parts)

# ============================================================
# Section: ldf_report.py
# ============================================================

"""
LDF报告生成模块 - ldf_report.py
支持 Text / Markdown / HTML / CSV / JSON 五种格式输出
以及批量摘要报告 LDFSummaryReporter
"""




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
    .stat-card .label { font-size: 14px; color: #888; }
    .stat-card .value { font-size: 24px; font-weight: bold; color: #2c3e50; }
    table.diff { width: 100%; border-collapse: collapse; margin: 10px 0; background: white;
                 box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-radius: 6px; overflow: hidden; }
    table.diff th { background: #3498db; color: white; padding: 8px 12px; text-align: left; }
    table.diff td { padding: 7px 12px; border-bottom: 1px solid #eee; vertical-align: top; }
    table.diff tr:last-child td { border-bottom: none; }
    .added    { background: #e8f8e8; color: #27ae60; }
    .removed  { background: #fde8e8; color: #e74c3c; }
    .modified { background: #fef9e7; color: #f39c12; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
             font-size: 14px; font-weight: bold; }
    .badge-add  { background: #27ae60; color: white; }
    .badge-del  { background: #e74c3c; color: white; }
    .badge-mod  { background: #f39c12; color: white; }
    .no-change  { color: #27ae60; font-size: 18px; padding: 20px; }
    code { background: #f0f0f0; padding: 1px 5px; border-radius: 3px; font-size: 16px; }
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
                        detail_parts.append(f'<span style="background:#c8e6c9;color:#333;padding:1px 4px;border-radius:2px">{fname}</span>')
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
  <td style="font-size:14px;color:#888">{old_fname}</td>
  <td style="font-size:14px;color:#888">{new_fname}</td>
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
            parts.append(f'<p style="color:#888;font-size:16px">旧: {r.old_file}<br>新: {r.new_file}</p>')

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
h3 {{ color: #555; margin: 14px 0 6px; font-size: 18px; }}
.summary {{ display: flex; gap: 20px; margin: 15px 0; }}
.card {{ background: white; border-radius: 8px; padding: 15px 25px;
         box-shadow: 0 2px 6px rgba(0,0,0,0.1); text-align: center; }}
.card .num {{ font-size: 30px; font-weight: bold; }}
table {{ width: 100%; border-collapse: collapse; background: white;
         box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-radius: 6px;
         overflow: hidden; margin-bottom: 10px; }}
th {{ background: #3498db; color: white; padding: 8px 12px; text-align: left; font-size: 16px; }}
td {{ padding: 7px 12px; border-bottom: 1px solid #eee; font-size: 16px; vertical-align: top; }}
tr:last-child td {{ border-bottom: none; }}
tr.added   td {{ background: #f0fff4; }}
tr.removed td {{ background: #fff5f5; }}
tr.modified td {{ background: #fffbf0; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:14px; font-weight:bold; }}
.badge-add {{ background:#d4edda; color:#155724; }}
.badge-del {{ background:#f8d7da; color:#721c24; }}
.badge-mod {{ background:#fff3cd; color:#856404; }}
.channel-block {{ background: white; border-radius: 8px; padding: 20px 24px;
                  box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-top: 24px; }}
.dtbl th {{ background: #546e7a; }}
code {{ background: #f0f0f0; padding: 1px 5px; border-radius: 3px; font-size: 14px; }}
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

# ============================================================
# Section: ldf_batch_diff.py
# ============================================================

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

class LDFBatchReportGenerator:
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


# ============================================================
# Section: combined_batch_diff.py
# ============================================================

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


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 DBC 相关模块

# 导入 LDF 相关模块


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
        - matrix_diff_report.html  综合 HTML 报告（含 CAN + LIN 两大板块）
        - matrix_diff_report.txt   综合文本报告
        """
        os.makedirs(output_dir, exist_ok=True)
        ldf_only_old = ldf_only_old or []
        ldf_only_new = ldf_only_new or []

        html_path = os.path.join(output_dir, "matrix_diff_report.html")
        txt_path = os.path.join(output_dir, "matrix_diff_report.txt")

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
                    # GenMsg* 报文属性展示
                    _msg_attr_parts = []
                    for _ak, _al in _GEN_MSG_ATTRS:
                        _av = msg.attributes.get(_ak)
                        if _av is not None and _av != '':
                            _av_label = _gen_msg_send_type_label(_av) if _ak == 'GenMsgSendType' else str(_av)
                            _msg_attr_parts.append(f'<em>{_al}</em>: <code class="new-val">{_av_label}</code>')
                    if _msg_attr_parts:
                        parts.append('<div class="attr-row" style="margin-left:4px;margin-bottom:4px;font-size:0.9em">' + ' &nbsp;|&nbsp; '.join(_msg_attr_parts) + '</div>')
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
                            _sst = _gen_sig_send_type_label(sig.attributes.get('GenSigSendType'))
                            if _sst:
                                fields = f'<em>GenSigSendType</em>: <code class="new-val">{_sst}</code>' + (' &nbsp;|&nbsp; ' + fields if fields else '')
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
                    if mc.attr_changes:
                        parts.append('<ul class="change-list">')
                        for fc in mc.attr_changes:
                            parts.append(f'<li><em>{fc.field_name}</em>: '
                                         f'<code class="old-val">{fc.old_value}</code> '
                                         f'→ <code class="new-val">{fc.new_value}</code></li>')
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
        if r.frame_changes:
            fc_added   = [c for c in r.frame_changes if c.change_type == "ADDED"]
            fc_removed = [c for c in r.frame_changes if c.change_type == "REMOVED"]
            fc_modified= [c for c in r.frame_changes if c.change_type == "MODIFIED"]
            if fc_added or fc_removed or fc_modified:
                # 建立 信号名 -> LDFSignalChange 映射，用于在帧展示中关联信号变更
                sig_change_map = {sc.signal_name: sc for sc in r.signal_changes}
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
                    # 信号新增/删除/位置变更，附带属性信息
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
                        sig_rows.append(f'<tr style="font-size:1.0em"><td><span class="tag-del">删除</span></td><td><strong>{sn}</strong></td><td>-</td></tr>')
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
                    # 属性变更的信号（MODIFIED，属于本帧，未在pos_changes/added/removed中）
                    pos_changed_names = {pc.signal_name for pc in c.signal_pos_changes}
                    for sn_mod, sc in sig_change_map.items():
                        if (sc.change_type == "MODIFIED"
                                and sc.frame_name == c.frame_name
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
                            sig_rows.append(f'<tr style="font-size:1.0em"><td><span class="tag-mod">属性变更</span></td><td><strong>{sn_mod}</strong></td><td>{field_str}</td></tr>')
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
                                f'<span style="background:#c8e6c9;color:#333;padding:1px 5px;border-radius:3px;font-weight:bold">{e}</span>' for e in c.entries_added
                            ))
                        if c.entries_removed:
                            entry_parts.append('删除帧: ' + ' '.join(
                                f'<span class="tag-del">{e}</span>' for e in c.entries_removed
                            ))
                        _sep = '；'
                        parts.append(f'<ul class="change-list"><li>{_sep.join(entry_parts)}</li></ul>')

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

                # 帧变更详情（change_type 是字符串；LDFFrameChange 有 signal_added/removed/pos_changes）
                sig_change_map_txt = {sc.signal_name: sc for sc in r.signal_changes}
                for fc in r.frame_changes:
                    ctype = fc.change_type   # 直接是字符串
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
                        for pc in fc.signal_pos_changes:
                            w(f"            [~] 信号位置变更: {pc.signal_name}  起始位: {pc.old_start_bit} -> {pc.new_start_bit}")
                            sc = sig_change_map_txt.get(pc.signal_name)
                            if sc and sc.change_type == "MODIFIED" and sc.field_changes:
                                for fld in sc.field_changes:
                                    w(f"                {fld.field_name}: {fld.old_value!r} -> {fld.new_value!r}")
                        # 属性变更信号（MODIFIED，属于本帧，未在pos_changes/added/removed中）
                        pos_changed_names_txt = {pc.signal_name for pc in fc.signal_pos_changes}
                        for sn_mod, sc in sig_change_map_txt.items():
                            if (sc.change_type == "MODIFIED"
                                    and sc.frame_name == fc.frame_name
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
    font-size: 16px;
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


def main():
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
        prog="OneDiffAll_dbc_ldf",
        description="CAN/LIN 通信矩阵批量差异分析工具 - 一次运行同时分析 DBC 和 LDF 文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python OneDiffAll_dbc_ldf.py 旧版本目录 新版本目录
  python OneDiffAll_dbc_ldf.py 旧版本目录 新版本目录 -o ./diff_out
        """
    )
    parser.add_argument("old_dir", help="旧版本目录路径")
    parser.add_argument("new_dir", help="新版本目录路径")
    parser.add_argument("--output-dir", "-o", default="combined_diff_output",
                        help="输出目录（默认: combined_diff_output）")

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

    can_subdir = "CAN" if os.path.isdir(os.path.join(old_dir, "CAN")) else ""
    lin_subdir = "LIN" if os.path.isdir(os.path.join(old_dir, "LIN")) else ""

    print(f"\n{'─'*60}")
    print("  [1/3] 正在分析 CAN 通道（DBC）...")
    print(f"{'─'*60}")
    dbc_batch_result = None
    try:
        dbc_differ = DBCBatchDiff(subdir=can_subdir)
        dbc_batch_result = dbc_differ.compare_dirs(old_dir, new_dir)
        dbc_reporter = DBCBatchReportGenerator()
        dbc_reporter.generate(dbc_batch_result, can_subdir_out, "html")
        print(f"\n  [CAN] 完成: {len(dbc_batch_result.compared)} 个通道对比，"
              f"{len(dbc_batch_result.changed)} 个有变更，{len(dbc_batch_result.unchanged)} 个无变更")
    except Exception as e:
        print(f"  [CAN] 分析失败: {e}")
        import traceback; traceback.print_exc()

    print(f"\n{'─'*60}")
    print("  [2/3] 正在分析 LIN 通道（LDF）...")
    print(f"{'─'*60}")
    ldf_results = []; ldf_only_old = []; ldf_only_new = []
    try:
        ldf_old_dir = os.path.join(old_dir, lin_subdir) if lin_subdir else old_dir
        ldf_new_dir = os.path.join(new_dir, lin_subdir) if lin_subdir else new_dir
        ldf_old_map = scan_ldf_files(ldf_old_dir)
        ldf_new_map = scan_ldf_files(ldf_new_dir)
        ldf_only_old = sorted(set(ldf_old_map.keys()) - set(ldf_new_map.keys()))
        ldf_only_new = sorted(set(ldf_new_map.keys()) - set(ldf_old_map.keys()))
        ldf_batch = LDFBatchDiff()
        ldf_results = ldf_batch.compare_dirs(ldf_old_dir, ldf_new_dir)
        if ldf_results:
            ldf_gen = LDFBatchReportGenerator()
            ldf_gen.generate_all(ldf_results, lin_subdir_out)
        ldf_changed = sum(1 for _, r in ldf_results if r.has_changes())
        print(f"\n  [LIN] 完成: {len(ldf_results)} 个通道对比，{ldf_changed} 个有变更，"
              f"{len(ldf_results)-ldf_changed} 个无变更，"
              f"仅旧版本 {len(ldf_only_old)} 个，仅新版本 {len(ldf_only_new)} 个")
    except Exception as e:
        print(f"  [LIN] 分析失败: {e}")
        import traceback; traceback.print_exc()

    print(f"\n{'─'*60}")
    print("  [3/3] 正在生成综合报告...")
    print(f"{'─'*60}")
    if dbc_batch_result is None:
        dbc_batch_result = BatchDiffResult(old_dir=old_dir, new_dir=new_dir, channel_results=[])
    combined_gen = CombinedReportGenerator()
    html_path, txt_path = combined_gen.generate(
        dbc_batch_result, ldf_results, output_dir=output_dir, fmt="html",
        old_dir=old_dir, new_dir=new_dir, ldf_only_old=ldf_only_old, ldf_only_new=ldf_only_new,
    )
    dbc_changed = len(dbc_batch_result.changed)
    dbc_total = len(dbc_batch_result.compared)
    ldf_changed = sum(1 for _, r in ldf_results if r.has_changes())
    print(f"\n{'='*60}")
    print(f"  [DONE] 综合分析完成！")
    print(f"  CAN (DBC): {dbc_total} 个通道，{dbc_changed} 个有变更")
    print(f"  LIN (LDF): {len(ldf_results)} 个通道，{ldf_changed} 个有变更")
    print(f"  [HTML] 综合报告: {html_path}")
    print(f"  [TXT]  文本报告: {txt_path}")
    print(f"  [DIR]  CAN详细:  {can_subdir_out}/")
    print(f"  [DIR]  LIN详细:  {lin_subdir_out}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
