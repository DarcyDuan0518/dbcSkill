# DBC 变更差异报告

- **生成时间**: 2026-04-30 08:55:10
- **旧版本**: `EEA3.0_CAN_Matrix_V10.1.6_20260403_PZCU_BDCAN1.dbc`
- **新版本**: `EEA3.0_CAN_Matrix_V11.1.0_20260415_PZCU_BDCAN1.dbc`

## 变更摘要

| 类别 | 新增 | 删除 | 修改 |
|------|------|------|------|
| 节点 | 0 | 0 | - |
| 报文ID变更 | - | - | 0 |
| 报文 | 0 | 0 | 11 |
| 信号 | 13 | 0 | 6 |

## 修改报文

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

### ✎ CCU_ChassisInfo1_10ms `0x196`

**信号变更**:

#### ✚ [新增] `VMM_SusBrkCtrlReq`

| 属性 | 值 |
|------|----|
| 起始位 | 248 |
| 位长度 | 1 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 1.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | VMM Suspension control request
VMM���������ܿ������� |

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
| 接收节点 | PZCU |
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
| 接收节点 | PZCU |
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
| 接收节点 | PZCU |
| 注释 | Rear Right Door Status
 �Һ���״̬�ź� |

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

### ✎ CCU_Info3_50ms `0x342`

**信号变更**:

#### ✚ [新增] `AtuoChrgRobarmMoveSts`

| 属性 | 值 |
|------|----|
| 起始位 | 102 |
| 位长度 | 3 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 7.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | �Զ�����е�۶���״̬ |

#### ✚ [新增] `RoadClass`

| 属性 | 值 |
|------|----|
| 起始位 | 99 |
| 位长度 | 4 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 15.0] |
| 单位 |  |
| 接收节点 | Vector_XXX |
| 注释 | ��·�ȼ� |

### ✎ DZCU_BodyCtrl_100ms `0x399`

**信号变更**:

#### ✚ [新增] `RLWndPcntMvCmd`

| 属性 | 值 |
|------|----|
| 起始位 | 44 |
| 位长度 | 7 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 102.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | Rear left Window Percentage Move Command
��󳵴��˶��ٷֱ� |

### ✎ BZCU_SeatCtrl_100ms `0x39A`

**信号变更**:

#### ✎ [修改] `BZCU_DrSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

#### ✎ [修改] `BZCU_PsngSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

#### ✎ [修改] `PsngEasyEntCfg`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'Active', 1: 'Inactive'}` | `{0: 'Inactive', 1: 'Active'}` |

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

### ✎ PZCU_BodySts5_100ms `0x505`

**信号变更**:

#### ✎ [修改] `PZCU_PsngSeatPosChng`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 值表 | `{0: 'No Command', 1: 'No change', 2: 'Changed', 3: 'Invalid'}` | `{0: 'No change', 1: 'Changed', 2: 'Reserved', 3: 'Reserved'}` |

### ✎ RRSCU_Sts11_100ms_GW `0x522`

**BA_属性变更**:

| 属性名 | 旧值 | 新值 |
|--------|------|------|
| GenMsgStartDelayTime | `0.0` | `65.0` |

**信号变更**:

#### ✚ [新增] `PsngSeatMovReq`

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

### ✎ DZCU_BodySts4_100ms `0x52C`

**信号变更**:

#### ✚ [新增] `BLEHoodCtrlReq`

| 属性 | 值 |
|------|----|
| 起始位 | 300 |
| 位长度 | 2 |
| 字节序 | Motorola(大端) |
| 数值类型 | 无符号 |
| 因子 | 1.0 |
| 偏移 | 0.0 |
| 范围 | [0.0, 3.0] |
| 单位 |  |
| 接收节点 | PZCU |
| 注释 | Ble Hood Contrl Request
����ǰ������� |
