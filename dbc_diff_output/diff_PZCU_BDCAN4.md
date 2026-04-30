# DBC 变更差异报告

- **生成时间**: 2026-04-30 16:15:34
- **旧版本**: `EEA3.0_CAN_Matrix_V10.1.4_20260317_PZCU_BDCAN4.dbc`
- **新版本**: `EEA3.0_CAN_Matrix_V11.1.0_20260415_PZCU_BDCAN4.dbc`

## 变更摘要

| 类别 | 新增 | 删除 | 修改 |
|------|------|------|------|
| 节点 | 0 | 0 | - |
| 报文ID变更 | - | - | 0 |
| 报文 | 3 | 0 | 10 |
| 信号 | 8 | 0 | 7 |

## 新增报文

### [+] ETC_Info3_Event `0x19F`

- **DLC**: 8 bytes
- **发送节点**: Vector_XXX

**信号列表**:

| 信号名 | 起始位 | 长度(bit) | 字节序 | 类型 | 因子 | 偏移 | 最小值 | 最大值 | 单位 | 接收节点 |
|--------|--------|-----------|--------|------|------|------|--------|--------|------|----------|
| `ETC_TradeStage1` | 7 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | PZCU |
| `ETC_TradeStage2` | 15 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | PZCU |
| `ETC_TradeStage3` | 23 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | PZCU |
| `ETC_TradeStage4` | 31 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | PZCU |
| `ETC_TradeStage5` | 39 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | PZCU |

### [+] EMS_STS2_100ms_GW2 `0x3E2`

- **DLC**: 8 bytes
- **发送节点**: Vector_XXX
- **注释**: X04C

**信号列表**:

| 信号名 | 起始位 | 长度(bit) | 字节序 | 类型 | 因子 | 偏移 | 最小值 | 最大值 | 单位 | 接收节点 |
|--------|--------|-----------|--------|------|------|------|--------|--------|------|----------|
| `EnMsfrTotCtr` | 47 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | PZCU |

### [+] ETC_OBUCardID_1000ms `0x62D`

- **DLC**: 8 bytes
- **发送节点**: Vector_XXX

**信号列表**:

| 信号名 | 起始位 | 长度(bit) | 字节序 | 类型 | 因子 | 偏移 | 最小值 | 最大值 | 单位 | 接收节点 |
|--------|--------|-----------|--------|------|------|------|--------|--------|------|----------|
| `OBU_CardID` | 7 | 64 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 0.0 |  | PZCU |

## 修改报文

### [~] EMS_SysSts1_10ms_GW2 `0x134`

**信号变更**:

#### [+] [新增] `EnPrignTotCnt`

| 属性 | 值 |
|------|----|
| 起始位 | 7 |
| 位长度 | 8 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 255.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | Engine Preignition Total Count 
��ȼ�ܼ��� |

### [~] ETC_Info2_Event `0x1B9`

**信号变更**:

#### [~] [修改] `ETC_TradeAmou`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 起始位 | `3` | `15` |

#### [~] [修改] `ETC_TradeSts`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 起始位 | `7` | `3` |
| 位长度 | `2` | `3` |
| 最大值 | `3.0` | `7.0` |
| 值表 | `{0: 'Trade success', 1: 'Trade fail', 2: 'Please contact the operator', 3: 'No card'}` | `{0: 'Invalid', 1: 'Trade success', 2: 'Trade fail', 3: 'Please contact the operator', 4: 'No card'}` |

### [~] DZCU_PSDCmd_20ms `0x21B`

**信号变更**:

#### [~] [修改] `LPSDCtrlCmdSour`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Init', 1: 'inside front', 2: 'inside rear', 3: 'outside with smart unlock', 4: 'outside without smart unlock'}` | `{0: 'Init', 1: 'inside front', 2: 'inside rear', 3: 'outside with smart unlock', 4: 'outside without smart unlock', 5: 'inside rear manual handle', 6: 'outside manual handle'}` |

#### [~] [修改] `RPSDCtrlCmdSour`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Init', 1: 'inside front', 2: 'inside rear', 3: 'outside with smart unlock', 4: 'outside without smart unlock'}` | `{0: 'Init', 1: 'inside front', 2: 'inside rear', 3: 'outside with smart unlock', 4: 'outside without smart unlock', 5: 'inside rear manual handle', 6: 'outside manual handle'}` |

### [~] PZCU_Sig3RTBD4_20ms `0x2B8`

**信号变更**:

#### [+] [新增] `LatGrd`

| 属性 | 值 |
|------|----|
| 起始位 | 31 |
| 位长度 | 8 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 0.01 |
| 偏移 | -1.0 |
| 范围 | [-1.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | Lateral Gradient
�����¶� |

#### [+] [新增] `LongtGrd`

| 属性 | 值 |
|------|----|
| 起始位 | 39 |
| 位长度 | 8 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 0.01 |
| 偏移 | -1.0 |
| 范围 | [-1.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | Longitudinal Gradient
�����¶� |

### [~] RRSCU_Sts1_100ms `0x3AC`

**BA_属性变更**:

| 属性名 | 旧值 | 新值 |
|--------|------|------|
| GenMsgStartDelayTime | `0.0` | `30.0` |

**信号变更**:

#### [~] [修改] `RRSCU_SecRSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

### [~] EMS_STS2_100ms_GW1 `0x3E1`

**信号变更**:

#### [+] [新增] `EnBstPre`

| 属性 | 值 |
|------|----|
| 起始位 | 55 |
| 位长度 | 9 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 300.0] |
| 单位 | kPa |
| 接收节点 | PZCU |
| 注释 | Engine Boost Pressure
 ��������ѹѹ�� |

### [~] PSCU_Sts2_100ms `0x3FA`

**信号变更**:

#### [~] [修改] `PsngSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

### [~] RRSCU_Sts11_100ms `0x522`

**BA_属性变更**:

| 属性名 | 旧值 | 新值 |
|--------|------|------|
| GenMsgStartDelayTime | `0.0` | `65.0` |

**信号变更**:

#### [+] [新增] `PsngSeatMovReq`

| 属性 | 值 |
|------|----|
| 起始位 | 63 |
| 位长度 | 4 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 15.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | ���������������� |

### [~] CCU_VehSts_1000ms_GW `0x5A0`

**信号变更**:

#### [+] [新增] `OBDDiagDeviceActivated`

| 属性 | 值 |
|------|----|
| 起始位 | 13 |
| 位长度 | 2 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 3.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | OBD diagnostic device activate OBD
������豸���� |

### [~] ETC_Info1_1000ms `0x5FB`

**信号变更**:

#### [+] [新增] `ETC_EmsnIntnst`

| 属性 | 值 |
|------|----|
| 起始位 | 63 |
| 位长度 | 8 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 255.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | ETC emission intensity
ETC ����ǿ�� |

#### [+] [新增] `ETC_WkupSnstvt`

| 属性 | 值 |
|------|----|
| 起始位 | 55 |
| 位长度 | 8 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 255.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | ETC Wakeup sensitivity
ETC���������� |

#### [~] [修改] `ETC_DisasSts`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 起始位 | `3` | `13` |
| 位长度 | `2` | `3` |
| 最大值 | `3.0` | `7.0` |
| 值表 | `{0: 'Invalid', 1: 'ETC not actived/disassembled', 2: 'ETC actived, anti disassembly verification is normal', 3: 'ETC actived, anti disassembly verification overtime'}` | `{0: 'Invalid', 1: 'ETC not actived', 2: 'ETC actived, anti disassembly verification is normal', 3: 'ETC actived, anti disassembly verification overtime', 4: 'disassembled'}` |
