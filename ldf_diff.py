"""
LDF差异分析模块 - ldf_diff.py
对比两个LDF文件，识别新增、删除、修改的节点/帧/信号/调度表/编码类型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from ldf_parser import (LDFFile, LDFSignal, LDFFrame, LDFScheduleTable,
                        LDFEncodingType, LDFNodeAttribute, LDFScheduleEntry)


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

    # 信号需要比较的字段（编码类型不影响协议栈代码生成，不纳入比较）
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
        for name in sorted(set(new_sigs) - set(old_sigs)):
            frame_name = sig_to_frame_new.get(name, "")
            result.signal_changes.append(LDFSignalChange(
                change_type=ChangeType.ADDED,
                frame_name=frame_name,
                signal_name=name,
                new_signal=new_sigs[name],
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
