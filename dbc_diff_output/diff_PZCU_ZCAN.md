# DBC 变更差异报告

- **生成时间**: 2026-04-30 17:28:30
- **旧版本**: `EEA3.0_CAN_Matrix_V10.1.6_20260403_PZCU_ZCAN.dbc`
- **新版本**: `EEA3.0_CAN_Matrix_V11.1.0_20260415_PZCU_ZCAN.dbc`

## 变更摘要

| 类别 | 新增 | 删除 | 修改 |
|------|------|------|------|
| 节点 | 0 | 0 | - |
| 报文ID变更 | - | - | 0 |
| 报文 | 3 | 0 | 14 |
| 信号 | 15 | 0 | 0 |

## 新增报文

### [+] DZCU_BodySts7_20ms `0x20B`

- **DLC**: 8 bytes
- **发送节点**: Vector_XXX

**信号列表**:

| 信号名 | 起始位 | 长度(bit) |
|--------|--------|-----------|
| `RRDoorHadlLghtBrghtSts` | 25 | 7 |

### [+] PZCU_LIN_VerNum6 `0x67B`

- **DLC**: 64 bytes
- **发送节点**: PZCU

**信号列表**:

| 信号名 | 起始位 | 长度(bit) |
|--------|--------|-----------|
| `ESAM10_BTVerNum` | 71 | 8 |
| `ESAM10_HWVerNum` | 87 | 16 |
| `ESAM10_PreBTVerNum` | 79 | 8 |
| `ESAM10_SWID` | 119 | 16 |
| `ESAM10_SWVerNum` | 103 | 16 |
| `ESAM11_BTVerNum` | 135 | 8 |
| `ESAM11_HWVerNum` | 151 | 16 |
| `ESAM11_PreBTVerNum` | 143 | 8 |
| `ESAM11_SWID` | 183 | 16 |
| `ESAM11_SWVerNum` | 167 | 16 |
| `ESAM12_BTVerNum` | 199 | 8 |
| `ESAM12_HWVerNum` | 215 | 16 |
| `ESAM12_PreBTVerNum` | 207 | 8 |
| `ESAM12_SWID` | 247 | 16 |
| `ESAM12_SWVerNum` | 231 | 16 |
| `ESAM13_BTVerNum` | 263 | 8 |
| `ESAM13_HWVerNum` | 279 | 16 |
| `ESAM13_PreBTVerNum` | 271 | 8 |
| `ESAM13_SWID` | 311 | 16 |
| `ESAM13_SWVerNum` | 295 | 16 |
| `ESAM14_BTVerNum` | 327 | 8 |
| `ESAM14_HWVerNum` | 343 | 16 |
| `ESAM14_PreBTVerNum` | 335 | 8 |
| `ESAM14_SWID` | 375 | 16 |
| `ESAM14_SWVerNum` | 359 | 16 |
| `ESAM15_BTVerNum` | 391 | 8 |
| `ESAM15_HWVerNum` | 407 | 16 |
| `ESAM15_PreBTVerNum` | 399 | 8 |
| `ESAM15_SWID` | 439 | 16 |
| `ESAM15_SWVerNum` | 423 | 16 |
| `ESAM16_BTVerNum` | 455 | 8 |
| `ESAM16_HWVerNum` | 471 | 16 |
| `ESAM16_PreBTVerNum` | 463 | 8 |
| `ESAM16_SWID` | 503 | 16 |
| `ESAM16_SWVerNum` | 487 | 16 |
| `ESAM9_BTVerNum` | 7 | 8 |
| `ESAM9_HWVerNum` | 23 | 16 |
| `ESAM9_PreBTVerNum` | 15 | 8 |
| `ESAM9_SWID` | 55 | 16 |
| `ESAM9_SWVerNum` | 39 | 16 |

### [+] BZCU_LIN_VerNum `0x6CA`

- **DLC**: 64 bytes
- **发送节点**: Vector_XXX

**信号列表**:

| 信号名 | 起始位 | 长度(bit) |
|--------|--------|-----------|
| `APTC_SWID` | 247 | 16 |

## 修改报文

### [~] EMS_SysSts1_10ms `0x123`

**信号变更**:

#### [+] [新增] `EnPrignTotCnt`

| 属性 | 值 |
|------|----|
| 起始位 | 71 |
| 位长度 | 8 |

### [~] ESP_SysSts3_20ms `0x216`

**信号变更**:

#### [+] [新增] `ESP_WssCoreMonRob`

| 属性 | 值 |
|------|----|
| 起始位 | 127 |
| 位长度 | 8 |

### [~] PZCU_BodySts_20ms `0x259`

**信号变更**:

#### [+] [新增] `PZCU_LChildProtnLckSts`

| 属性 | 值 |
|------|----|
| 起始位 | 72 |
| 位长度 | 1 |

#### [+] [新增] `PZCU_RLDoorLckSts`

| 属性 | 值 |
|------|----|
| 起始位 | 87 |
| 位长度 | 2 |

#### [+] [新增] `PZCU_RLDoorSts`

| 属性 | 值 |
|------|----|
| 起始位 | 74 |
| 位长度 | 2 |

### [~] PZCU_OTASts_Event `0x28A`

**信号变更**:

#### [+] [新增] `OBDKeepWakeupReq`

| 属性 | 值 |
|------|----|
| 起始位 | 1 |
| 位长度 | 1 |

#### [+] [新增] `QuitOBDKeepWakeupReq`

| 属性 | 值 |
|------|----|
| 起始位 | 0 |
| 位长度 | 1 |

### [~] HU_RemoteCtrl_100ms `0x39D`

**信号变更**:

#### [+] [新增] `AtuoChrgReq`

| 属性 | 值 |
|------|----|
| 起始位 | 204 |
| 位长度 | 2 |

#### [+] [新增] `AtuoChrgVehParkNum`

| 属性 | 值 |
|------|----|
| 起始位 | 202 |
| 位长度 | 5 |

#### [+] [新增] `HuRLWdwshdPosiCtrl`

| 属性 | 值 |
|------|----|
| 起始位 | 19 |
| 位长度 | 2 |

### [~] PZCU_ACHtMgm_100ms `0x3AA`

**信号变更**:

#### [+] [新增] `AtuoChrgSts`

| 属性 | 值 |
|------|----|
| 起始位 | 205 |
| 位长度 | 2 |

### [~] RRSCU_Sts1_100ms_GW `0x3AC`

**BA_属性变更**:

| 属性名 | 旧值 | 新值 |
|--------|------|------|
| GenMsgStartDelayTime | `0.0` | `30.0` |

### [~] ODU_Temp_100ms `0x3D1`

**信号变更**:

#### [+] [新增] `OBCOverTemp`

| 属性 | 值 |
|------|----|
| 起始位 | 74 |
| 位长度 | 2 |

### [~] BMS_ChrgInfo2_100ms `0x3E0`

**信号变更**:

#### [+] [新增] `BMS_ChgEndPwrLowWarning`

| 属性 | 值 |
|------|----|
| 起始位 | 149 |
| 位长度 | 1 |

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

### [~] TM_SysSts_100ms_GW `0x531`

**BA_属性变更**:

| 属性名 | 旧值 | 新值 |
|--------|------|------|
| GenMsgStartDelayTime | `0.0` | `80.0` |

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
