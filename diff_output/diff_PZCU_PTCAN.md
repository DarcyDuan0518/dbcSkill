# DBC 变更差异报告

- **生成时间**: 2026-04-29 13:48:42
- **旧版本**: `EEA3.0_CAN_Matrix_V10.1.6_20260403_PZCU_PTCAN.dbc`
- **新版本**: `EEA3.0_CAN_Matrix_V11.1.0_20260415_PZCU_PTCAN.dbc`

## 变更摘要

| 类别 | 新增 | 删除 | 修改 |
|------|------|------|------|
| 节点 | 0 | 0 | - |
| 报文 | 0 | 0 | 11 |
| 信号 | 12 | 0 | 6 |

## 修改报文

### ✎ ESP_SysSts3_10ms `0x76`

**信号变更**:

#### ✎ [修改] `TDiscMaxEstimd_Mod`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 单位 | `K` | `��` |

### ✎ EMS_SysSts1_10ms `0x123`

**信号变更**:

#### ✚ [新增] `EnPrignTotCnt`

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

### ✎ BMS_SysSts1_10ms `0x140`

**信号变更**:

#### ✚ [新增] `DCChrgPrtVByOGC`

| 属性 | 值 |
|------|----|
| 起始位 | 246 |
| 位长度 | 15 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 0.1 |
| 偏移 | -1500.0 |
| 范围 | [-1500.0, 1500.0] |
| 单位 | V |
| 接收节点 | PZCU |
| 注释 | DC charging port voltage By OGC
  
���׮��ֱ�����˿ڵ�ѹ |

### ✎ PZCU_ACHtMgm_100ms `0x3AA`

**信号变更**:

#### ✚ [新增] `AtuoChrgSts`

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

### ✎ ODU_STS1_100ms `0x3D0`

**信号变更**:

#### ✎ [修改] `ChrgInltLEDSts`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Off', 1: 'White', 2: 'Green', 3: 'Red', 4: 'Blue', 5: 'Breathing Green��Reserved��', 6: 'Breathing Blue��Reserved��', 7: 'Reserved'}` | `{0: 'Off', 1: 'White', 2: 'Green', 3: 'Red', 4: 'Blue', 5: 'Breathing Green��Reserved��', 6: 'Breathing Blue��Reserved��', 7: 'Invalid'}` |

### ✎ ODU_Temp_100ms `0x3D1`

**信号变更**:

#### ✚ [新增] `OBCOverTemp`

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
| 接收节点 | PZCU |
| 注释 | OBC Over Temperature
OBC���±��� |

### ✎ BMS_ChrgInfo2_100ms `0x3E0`

**信号变更**:

#### ✚ [新增] `BMS_ChgEndPwrLowWarning`

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
| 接收节点 | PZCU |
| 注释 | ���ĩ�˵͹������� |

### ✎ ODU_NM `0x400`

**信号变更**:

#### ✎ [修改] `ODU_WakeUpRsn`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Init', 1: 'NM PDU received', 2: 'Hardwire ACC', 3: 'CC WakeUp', 4: 'CC2 WakeUp', 5: 'CP WakeUp', 6: 'A+ WakeUp', 7: 'Reserved'}` | `{0: 'Init', 1: 'NM PDU received', 2: 'Hardwire ACC', 3: 'CC WakeUp', 4: 'CC2 WakeUp', 5: 'CP WakeUp', 6: 'Reserved', 7: 'Reserved'}` |

### ✎ BZCU_BodySts_100ms `0x51A`

**信号变更**:

#### ✎ [修改] `DrEasyEntCfg`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Active', 1: 'Inactive'}` | `{0: 'Inactive', 1: 'Active'}` |

#### ✎ [修改] `SecLEasyEntCfg`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Active', 1: 'Inactive'}` | `{0: 'Inactive', 1: 'Active'}` |

#### ✎ [修改] `SecREasyEntCfg`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Active', 1: 'Inactive'}` | `{0: 'Inactive', 1: 'Active'}` |

### ✎ CCU_VehSts_1000ms `0x5A0`

**信号变更**:

#### ✚ [新增] `OBDDiagDeviceActivated`

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

### ✎ BMS_Fault_1000ms `0x633`

**信号变更**:

#### ✚ [新增] `COMM_PTCAN_H120_FLT`

| 属性 | 值 |
|------|----|
| 起始位 | 483 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | PTCAN_H120���Ĵ��� |

#### ✚ [新增] `COMM_PTCAN_H121_FLT`

| 属性 | 值 |
|------|----|
| 起始位 | 482 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | PTCAN_H121���Ĵ��� |

#### ✚ [新增] `COMM_PTCAN_H3A0_FLT`

| 属性 | 值 |
|------|----|
| 起始位 | 484 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | PTCAN_H3A0���Ĵ��� |

#### ✚ [新增] `ERR_MCUFRollingCounterFlt_ID0X120`

| 属性 | 值 |
|------|----|
| 起始位 | 486 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | MCUF����RollingCounter����(0x120) |

#### ✚ [新增] `ERR_MCURRollingCounterFlt_ID0X121`

| 属性 | 值 |
|------|----|
| 起始位 | 485 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | MCUR����RollingCounter����(0x121) |

#### ✚ [新增] `ERR_PZCURollingCounterFlt_ID0X3A0`

| 属性 | 值 |
|------|----|
| 起始位 | 381 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | PZCURollingCounter����(ID 0X3A0) |
