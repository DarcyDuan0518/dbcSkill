# DBC 变更差异报告

- **生成时间**: 2026-04-29 13:48:42
- **旧版本**: `EEA3.0_CAN_Matrix_V10.1.4_20260317_PZCU_CHCAN1.dbc`
- **新版本**: `EEA3.0_CAN_Matrix_V11.1.0_20260415_PZCU_CHCAN1.dbc`

## 变更摘要

| 类别 | 新增 | 删除 | 修改 |
|------|------|------|------|
| 节点 | 0 | 0 | - |
| 报文 | 2 | 0 | 4 |
| 信号 | 3 | 0 | 1 |

## 新增报文

### ✚ PZCU_ChassisCtrl2_Event `0xF4`

- **DLC**: 16 bytes
- **发送节点**: PZCU

**信号列表**:

| 信号名 | 起始位 | 长度(bit) | 字节序 | 类型 | 因子 | 偏移 | 最小值 | 最大值 | 单位 | 接收节点 |
|--------|--------|-----------|--------|------|------|------|--------|--------|------|----------|
| `GameModeHWAForceFb` | 47 | 9 | Motorola(大端) | 无符号 | 0.1 | -22.78 | -22.78 | 22.72 | Nm | Vector_XXX |
| `GameModeInitReq` | 15 | 1 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 1.0 |  | Vector_XXX |
| `GameModeResdSig` | 103 | 32 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 4294967295.0 | NA | Vector_XXX |
| `GameModeSetHWAAng` | 23 | 16 | Motorola(大端) | 无符号 | 0.1 | -780.0 | -780.0 | 779.9000000000001 | deg | Vector_XXX |
| `GameModeSteerFeelMode` | 14 | 2 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 3.0 |  | Vector_XXX |
| `GameModeVehSpd` | 39 | 8 | Motorola(大端) | 无符号 | 1.804 | 0.0 | 0.0 | 458.216 | kph | Vector_XXX |
| `SigGroup_0x0F4_ChkSm_F` | 7 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 | NA | Vector_XXX |
| `SigGroup_0x0F4_RlngCtr_F` | 11 | 4 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 15.0 | NA | Vector_XXX |

### ✚ HWA_Info4_Event `0x2CE`

- **DLC**: 16 bytes
- **发送节点**: Vector_XXX

**信号列表**:

| 信号名 | 起始位 | 长度(bit) | 字节序 | 类型 | 因子 | 偏移 | 最小值 | 最大值 | 单位 | 接收节点 |
|--------|--------|-----------|--------|------|------|------|--------|--------|------|----------|
| `GameModeHWAFbResd` | 103 | 32 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 4294967295.0 | NA | PZCU |
| `GameModeHWAInitErrCode` | 23 | 3 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 7.0 |  | PZCU |
| `GameModeHWAInitSts` | 15 | 3 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 7.0 |  | PZCU |
| `SigGroup_0x2CE_ChkSm_F` | 7 | 8 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 255.0 | NA | PZCU |
| `SigGroup_0x2CE_RlngCtr_F` | 11 | 4 | Motorola(大端) | 无符号 | 1.0 | 0.0 | 0.0 | 15.0 | NA | PZCU |

## 修改报文

### ✎ ESP_SysSts3_10ms `0x76`

**信号变更**:

#### ✎ [修改] `TDiscMaxEstimd_Mod`

| 字段 | 旧值 | 新值 |
|------|------|------|
| 单位 | `K` | `��` |

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
| 接收节点 | PZCU |
| 注释 | VMM Suspension control request
VMM���������ܿ������� |

### ✎ ESP_SysSts3_20ms `0x216`

**信号变更**:

#### ✚ [新增] `ESP_WssCoreMonRob`

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
| 接收节点 | PZCU |
| 注释 | ESP��DPB������У����� |

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
