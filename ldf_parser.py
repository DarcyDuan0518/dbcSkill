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

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple


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
