# DBC 变更差异报告

- **生成时间**: 2026-04-30 08:55:10
- **旧版本**: `EEA3.0_CAN_Matrix_V10.1.6_20260403_PZCU_BDCAN6.dbc`
- **新版本**: `EEA3.0_CAN_Matrix_V11.1.0_20260415_PZCU_BDCAN6.dbc`

## 变更摘要

| 类别 | 新增 | 删除 | 修改 |
|------|------|------|------|
| 节点 | 0 | 0 | - |
| 报文ID变更 | - | - | 0 |
| 报文 | 0 | 0 | 8 |
| 信号 | 16 | 0 | 5 |

## 修改报文

### ✎ DZCU_DrLockCtrl_20ms `0x219`

**信号变更**:

#### ✚ [新增] `DZCU_RChildProtnLckSts`

| 属性 | 值 |
|------|----|
| 起始位 | 252 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | Right Child Protection Lock Status
 �Ҳ��ͯ��״̬ |

#### ✚ [新增] `DZCU_RRDoorLckSts`

| 属性 | 值 |
|------|----|
| 起始位 | 249 |
| 位长度 | 2 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 3.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | Rear Right Door Lock Status
 �Һ�����״̬�ź� |

#### ✚ [新增] `DZCU_RRDoorSts`

| 属性 | 值 |
|------|----|
| 起始位 | 251 |
| 位长度 | 2 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 3.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | Rear Right Door Status
 �Һ���״̬�ź� |

### ✎ PZCU_ECGMCmd_20ms `0x247`

**信号变更**:

#### ✚ [新增] `ECPrivacySts`

| 属性 | 值 |
|------|----|
| 起始位 | 41 |
| 位长度 | 2 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 3.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | ȫ����˽������˽״̬ |

#### ✚ [新增] `RLECProtnSts`

| 属性 | 值 |
|------|----|
| 起始位 | 24 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | RLEC Protection Status
�����EC����״̬ |

#### ✚ [新增] `RLTempECCtrlCmd`

| 属性 | 值 |
|------|----|
| 起始位 | 37 |
| 位长度 | 4 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 15.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | ����¶ȵ���EC���� |

#### ✚ [新增] `RRECProtnSts`

| 属性 | 值 |
|------|----|
| 起始位 | 54 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | RREC Protection Status
�Һ���EC����״̬ |

#### ✚ [新增] `RRTempECCtrlCmd`

| 属性 | 值 |
|------|----|
| 起始位 | 33 |
| 位长度 | 4 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 15.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | �Һ��¶ȵ���EC���� |

#### ✚ [新增] `TailDoorECProtnSts`

| 属性 | 值 |
|------|----|
| 起始位 | 52 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | TailDoorEC Protection Status
����EC����״̬ |

#### ✚ [新增] `TaildoorTempECCtrlCmd`

| 属性 | 值 |
|------|----|
| 起始位 | 45 |
| 位长度 | 4 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 15.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | �����¶ȵ���EC���� |

#### ✚ [新增] `ThirdLECProtnSts`

| 属性 | 值 |
|------|----|
| 起始位 | 55 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | ThirdLEC Protection Status
�������EC����״̬ |

#### ✚ [新增] `ThirdRECProtnSts`

| 属性 | 值 |
|------|----|
| 起始位 | 53 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | ThirdREC Protection Status
�����Ҳ�EC����״̬ |

### ✎ PZCU_BodySts_20ms `0x259`

**信号变更**:

#### ✚ [新增] `PZCU_LChildProtnLckSts`

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

#### ✚ [新增] `PZCU_RLDoorLckSts`

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

#### ✚ [新增] `PZCU_RLDoorSts`

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

### ✎ LECGM_Sts1_100msMixed `0x3A1`

**报文字段变更**:

| 字段 | 旧值 | 新值 |
|------|------|------|
| 报文名称 | `LECGM_Sts1_100ms` | `LECGM_Sts1_100msMixed` |

**BA_属性变更**:

| 属性名 | 旧值 | 新值 |
|--------|------|------|
| GenMsgDelayTime | `<不存在>` | `20.0` |
| GenMsgSendType | `0` | `5` |

### ✎ RECGM_Sts1_100msMixed `0x3A2`

**报文字段变更**:

| 字段 | 旧值 | 新值 |
|------|------|------|
| 报文名称 | `RECGM_Sts1_100ms` | `RECGM_Sts1_100msMixed` |

**BA_属性变更**:

| 属性名 | 旧值 | 新值 |
|--------|------|------|
| GenMsgDelayTime | `<不存在>` | `20.0` |
| GenMsgSendType | `0` | `5` |

### ✎ BZCU_SecSeatSts_100ms `0x3EC`

**信号变更**:

#### ✎ [修改] `SecLSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

#### ✎ [修改] `SecRSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

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
