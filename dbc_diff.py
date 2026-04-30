"""
DBC差异分析模块 - dbc_diff.py
对比两个DBC文件，识别新增、删除、修改的节点/报文/信号
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from dbc_parser import DBCFile, Message, Signal, Node


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
    # 以下字段不影响协议栈代码生成，忽略：
    #   byte_order(字节序)、value_type(数值类型)、factor(因子)、offset(偏移)、
    #   min_val(最小值)、max_val(最大值)、unit(单位)、receivers(接收节点)、
    #   comment(注释)、value_table(值表)
    _SIGNAL_FIELDS = [
        ("start_bit",     "起始位"),
        ("length",        "位长度"),
        ("mux_indicator", "多路复用"),
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

        # 比较 BA_ 属性字典（单独存入 attr_changes，不混入 field_changes）
        attr_changes = self._compare_dicts(old_msg.attributes, new_msg.attributes)

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

        # 新增信号
        for name in sorted(new_names - old_names):
            changes.append(SignalChange(
                change_type=ChangeType.ADDED,
                msg_id=new_msg.msg_id,
                msg_name=new_msg.name,
                signal_name=name,
                new_signal=new_sigs[name]
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


# ---------------------------------------------
# 便捷函数
# ---------------------------------------------

def compare_dbc_files(old_path: str, new_path: str) -> DBCDiffResult:
    """
    直接比较两个DBC文件路径，返回差异结果
    示例：
        result = compare_dbc_files("v1.dbc", "v2.dbc")
    """
    from dbc_parser import DBCParser
    parser = DBCParser()
    old_dbc = parser.parse_file(old_path)
    new_dbc = parser.parse_file(new_path)
    return DBCDiff().compare(old_dbc, new_dbc)
