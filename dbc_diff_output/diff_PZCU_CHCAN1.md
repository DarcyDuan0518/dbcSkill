# DBC 变更差异报告

- **生成时间**: 2026-04-30 17:28:30
- **旧版本**: `EEA3.0_CAN_Matrix_V10.1.4_20260317_PZCU_CHCAN1.dbc`
- **新版本**: `EEA3.0_CAN_Matrix_V11.1.0_20260415_PZCU_CHCAN1.dbc`

## 变更摘要

| 类别 | 新增 | 删除 | 修改 |
|------|------|------|------|
| 节点 | 0 | 0 | - |
| 报文ID变更 | - | - | 0 |
| 报文 | 2 | 0 | 3 |
| 信号 | 3 | 0 | 0 |

## 新增报文

### [+] PZCU_ChassisCtrl2_Event `0xF4`

- **DLC**: 16 bytes
- **发送节点**: PZCU

**信号列表**:

| 信号名 | 起始位 | 长度(bit) |
|--------|--------|-----------|
| `GameModeHWAForceFb` | 47 | 9 |
| `GameModeInitReq` | 15 | 1 |
| `GameModeResdSig` | 103 | 32 |
| `GameModeSetHWAAng` | 23 | 16 |
| `GameModeSteerFeelMode` | 14 | 2 |
| `GameModeVehSpd` | 39 | 8 |
| `SigGroup_0x0F4_ChkSm_F` | 7 | 8 |
| `SigGroup_0x0F4_RlngCtr_F` | 11 | 4 |

### [+] HWA_Info4_Event `0x2CE`

- **DLC**: 16 bytes
- **发送节点**: Vector_XXX

**信号列表**:

| 信号名 | 起始位 | 长度(bit) |
|--------|--------|-----------|
| `GameModeHWAFbResd` | 103 | 32 |
| `GameModeHWAInitErrCode` | 23 | 3 |
| `GameModeHWAInitSts` | 15 | 3 |
| `SigGroup_0x2CE_ChkSm_F` | 7 | 8 |
| `SigGroup_0x2CE_RlngCtr_F` | 11 | 4 |

## 修改报文

### [~] CCU_ChassisInfo1_10ms `0x196`

**信号变更**:

#### [+] [新增] `VMM_SusBrkCtrlReq`

| 属性 | 值 |
|------|----|
| 起始位 | 248 |
| 位长度 | 1 |

### [~] ESP_SysSts3_20ms `0x216`

**信号变更**:

#### [+] [新增] `ESP_WssCoreMonRob`

| 属性 | 值 |
|------|----|
| 起始位 | 127 |
| 位长度 | 8 |

### [~] PZCU_ACHtMgm_100ms `0x3AA`

**信号变更**:

#### [+] [新增] `AtuoChrgSts`

| 属性 | 值 |
|------|----|
| 起始位 | 205 |
| 位长度 | 2 |
