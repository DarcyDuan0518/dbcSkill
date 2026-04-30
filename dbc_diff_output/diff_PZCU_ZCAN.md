# DBC 变更差异报告

- **生成时间**: 2026-04-30 16:15:34
- **旧版本**: `EEA3.0_CAN_Matrix_V10.1.6_20260403_PZCU_ZCAN.dbc`
- **新版本**: `EEA3.0_CAN_Matrix_V11.1.0_20260415_PZCU_ZCAN.dbc`

## 变更摘要

| 类别 | 新增 | 删除 | 修改 |
|------|------|------|------|
| 节点 | 0 | 0 | - |
| 报文ID变更 | - | - | 0 |
| 报文 | 3 | 0 | 22 |
| 信号 | 15 | 0 | 15 |

## 新增报文

### [+] DZCU_BodySts7_20ms `0x20B`

- **DLC**: 8 bytes
- **发送节点**: Vector_XXX

**信号列表**:

| 信号名 | 起始位 | 长度(bit) | 字节序 | 类型 | 因子 | 偏移 | 最小值 | 最大值 | 单位 | 接收节点 |
|--------|--------|-----------|--------|------|------|------|--------|--------|------|----------|
| `RRDoorHadlLghtBrghtSts` | 25 | 7 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 100.0 |  | PZCU |

### [+] PZCU_LIN_VerNum6 `0x67B`

- **DLC**: 64 bytes
- **发送节点**: PZCU

**信号列表**:

| 信号名 | 起始位 | 长度(bit) | 字节序 | 类型 | 因子 | 偏移 | 最小值 | 最大值 | 单位 | 接收节点 |
|--------|--------|-----------|--------|------|------|------|--------|--------|------|----------|
| `ESAM10_BTVerNum` | 71 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM10_HWVerNum` | 87 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM10_PreBTVerNum` | 79 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM10_SWID` | 119 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM10_SWVerNum` | 103 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM11_BTVerNum` | 135 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM11_HWVerNum` | 151 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM11_PreBTVerNum` | 143 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM11_SWID` | 183 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM11_SWVerNum` | 167 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM12_BTVerNum` | 199 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM12_HWVerNum` | 215 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM12_PreBTVerNum` | 207 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM12_SWID` | 247 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM12_SWVerNum` | 231 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM13_BTVerNum` | 263 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM13_HWVerNum` | 279 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM13_PreBTVerNum` | 271 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM13_SWID` | 311 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM13_SWVerNum` | 295 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM14_BTVerNum` | 327 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM14_HWVerNum` | 343 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM14_PreBTVerNum` | 335 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM14_SWID` | 375 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM14_SWVerNum` | 359 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM15_BTVerNum` | 391 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM15_HWVerNum` | 407 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM15_PreBTVerNum` | 399 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM15_SWID` | 439 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM15_SWVerNum` | 423 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM16_BTVerNum` | 455 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM16_HWVerNum` | 471 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM16_PreBTVerNum` | 463 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM16_SWID` | 503 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM16_SWVerNum` | 487 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM9_BTVerNum` | 7 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM9_HWVerNum` | 23 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM9_PreBTVerNum` | 15 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 |  | Vector_XXX |
| `ESAM9_SWID` | 55 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |
| `ESAM9_SWVerNum` | 39 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | Vector_XXX |

### [+] BZCU_LIN_VerNum `0x6CA`

- **DLC**: 64 bytes
- **发送节点**: Vector_XXX

**信号列表**:

| 信号名 | 起始位 | 长度(bit) | 字节序 | 类型 | 因子 | 偏移 | 最小值 | 最大值 | 单位 | 接收节点 |
|--------|--------|-----------|--------|------|------|------|--------|--------|------|----------|
| `APTC_SWID` | 247 | 16 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 65535.0 |  | PZCU |

## 修改报文

### [~] EMS_SysSts1_10ms `0x123`

**信号变更**:

#### [+] [新增] `EnPrignTotCnt`

| 属性 | 值 |
|------|----|
| 起始位 | 71 |
| 位长度 | 8 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 255.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | Engine Preignition Total Count 
��ȼ�ܼ��� |

### [~] ESP_SysSts3_20ms `0x216`

**信号变更**:

#### [+] [新增] `ESP_WssCoreMonRob`

| 属性 | 值 |
|------|----|
| 起始位 | 127 |
| 位长度 | 8 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 255.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | ESP��DPB������У����� |

### [~] DZCU_PSDCmd_20ms_GW `0x21B`

**信号变更**:

#### [~] [修改] `LPSDCtrlCmdSour`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Init', 1: 'inside front', 2: 'inside rear', 3: 'outside with smart unlock', 4: 'outside without smart unlock'}` | `{0: 'Init', 1: 'inside front', 2: 'inside rear', 3: 'outside with smart unlock', 4: 'outside without smart unlock', 5: 'inside rear manual handle', 6: 'outside manual handle'}` |

#### [~] [修改] `RPSDCtrlCmdSour`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Init', 1: 'inside front', 2: 'inside rear', 3: 'outside with smart unlock', 4: 'outside without smart unlock'}` | `{0: 'Init', 1: 'inside front', 2: 'inside rear', 3: 'outside with smart unlock', 4: 'outside without smart unlock', 5: 'inside rear manual handle', 6: 'outside manual handle'}` |

### [~] PZCU_BodySts_20ms `0x259`

**信号变更**:

#### [+] [新增] `PZCU_LChildProtnLckSts`

| 属性 | 值 |
|------|----|
| 起始位 | 72 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | Left Child Protection Lock Status
 ����ͯ��״̬ |

#### [+] [新增] `PZCU_RLDoorLckSts`

| 属性 | 值 |
|------|----|
| 起始位 | 87 |
| 位长度 | 2 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 3.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | Rear Left Door Lock Status
 �������״̬�ź� |

#### [+] [新增] `PZCU_RLDoorSts`

| 属性 | 值 |
|------|----|
| 起始位 | 74 |
| 位长度 | 2 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 3.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | Rear Left Door Status
 �����״̬�ź� |

### [~] PZCU_OTASts_Event `0x28A`

**信号变更**:

#### [+] [新增] `OBDKeepWakeupReq`

| 属性 | 值 |
|------|----|
| 起始位 | 1 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | OBD�ŷ���ϱ��ֻ�������
OBD keep wake up request |

#### [+] [新增] `QuitOBDKeepWakeupReq`

| 属性 | 值 |
|------|----|
| 起始位 | 0 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | �˳�OBD�ŷ���ϱ��ֻ�������
Quit OBD keep wake up request |

### [~] BZCU_SeatCtrl_100ms `0x39A`

**信号变更**:

#### [~] [修改] `BZCU_DrSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

#### [~] [修改] `BZCU_PsngSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

#### [~] [修改] `PsngEasyEntCfg`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Active', 1: 'Inactive'}` | `{0: 'Inactive', 1: 'Active'}` |

### [~] HU_RemoteCtrl_100ms `0x39D`

**信号变更**:

#### [+] [新增] `AtuoChrgReq`

| 属性 | 值 |
|------|----|
| 起始位 | 204 |
| 位长度 | 2 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 3.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | �Զ����ģʽ���� |

#### [+] [新增] `AtuoChrgVehParkNum`

| 属性 | 值 |
|------|----|
| 起始位 | 202 |
| 位长度 | 5 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 31.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | �Զ���糵�����ڳ�λ��� |

#### [+] [新增] `HuRLWdwshdPosiCtrl`

| 属性 | 值 |
|------|----|
| 起始位 | 19 |
| 位长度 | 2 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 3.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | HuRLWdwshdPosiCtrl
��󳵴����������� |

### [~] PZCU_ACHtMgm_100ms `0x3AA`

**信号变更**:

#### [+] [新增] `AtuoChrgSts`

| 属性 | 值 |
|------|----|
| 起始位 | 205 |
| 位长度 | 2 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 3.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | �Զ����ģʽ״̬ |

### [~] RRSCU_Sts1_100ms_GW `0x3AC`

**BA_属性变更**:

| 属性名 | 旧值 | 新值 |
|--------|------|------|
| GenMsgStartDelayTime | `0.0` | `30.0` |

**信号变更**:

#### [~] [修改] `RRSCU_SecRSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

### [~] ODU_STS1_100ms `0x3D0`

**信号变更**:

#### [~] [修改] `ChrgInltLEDSts`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Off', 1: 'White', 2: 'Green', 3: 'Red', 4: 'Blue', 5: 'Breathing Green��Reserved��', 6: 'Breathing Blue��Reserved��', 7: 'Reserved'}` | `{0: 'Off', 1: 'White', 2: 'Green', 3: 'Red', 4: 'Blue', 5: 'Breathing Green��Reserved��', 6: 'Breathing Blue��Reserved��', 7: 'Invalid'}` |

### [~] ODU_Temp_100ms `0x3D1`

**信号变更**:

#### [+] [新增] `OBCOverTemp`

| 属性 | 值 |
|------|----|
| 起始位 | 74 |
| 位长度 | 2 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 3.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | OBC Over Temperature
OBC���±��� |

### [~] BMS_ChrgInfo2_100ms `0x3E0`

**信号变更**:

#### [+] [新增] `BMS_ChgEndPwrLowWarning`

| 属性 | 值 |
|------|----|
| 起始位 | 149 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | ���ĩ�˵͹������� |

### [~] BZCU_SecSeatSts_100ms `0x3EC`

**信号变更**:

#### [~] [修改] `SecLSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

#### [~] [修改] `SecRSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

### [~] PSCU_Sts2_100ms_GW `0x3FA`

**信号变更**:

#### [~] [修改] `PsngSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

### [~] PZCU_BodySts5_100ms `0x505`

**信号变更**:

#### [~] [修改] `PZCU_PsngSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

### [~] BZCU_BodySts_100ms `0x51A`

**信号变更**:

#### [~] [修改] `DrEasyEntCfg`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Active', 1: 'Inactive'}` | `{0: 'Inactive', 1: 'Active'}` |

#### [~] [修改] `SecLEasyEntCfg`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Active', 1: 'Inactive'}` | `{0: 'Inactive', 1: 'Active'}` |

#### [~] [修改] `SecREasyEntCfg`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Active', 1: 'Inactive'}` | `{0: 'Inactive', 1: 'Active'}` |

### [~] RRSCU_Sts11_100ms_GW `0x522`

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
| 接收节点 | PZCU |
| 注释 | ���������������� |

### [~] TM_SysSts_100ms_GW `0x531`

**BA_属性变更**:

| 属性名 | 旧值 | 新值 |
|--------|------|------|
| GenMsgStartDelayTime | `0.0` | `80.0` |

### [~] PZCU_LIN_100ms `0x53C`

**信号变更**:

#### [~] [修改] `PsngSeatTableSwSts`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Normal', 1: 'Open', 2: 'Retract', 3: 'valid'}` | `{0: 'Normal', 1: 'short press', 2: 'long press', 3: 'Invalid'}` |

### [~] RRSCU_Sts6_100ms_GW `0x557`

**BA_属性变更**:

| 属性名 | 旧值 | 新值 |
|--------|------|------|
| GenMsgStartDelayTime | `0.0` | `75.0` |

### [~] RLSCU_Sts6_100ms_GW `0x565`

**BA_属性变更**:

| 属性名 | 旧值 | 新值 |
|--------|------|------|
| GenMsgStartDelayTime | `0.0` | `75.0` |

### [~] CCU_VehSts_1000ms `0x5A0`

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
| 接收节点 | PZCU |
| 注释 | OBD diagnostic device activate OBD
������豸���� |
