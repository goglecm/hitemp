<!-- Evidence extract. The summary and how it applies to this integration are in HW211_REGISTER_COMPARISON.md. -->

# Research dump: HiTemp / AquaTemp / Linked-Go cloud reverse-engineering

**Status:** research only — do **not** treat this as a write recipe; do not merge into
`HW211_REGISTER_COMPARISON.md` until reviewed.

**Product ID of interest:** `1245226668902080512` (Trianco S300 / Indol PV300 /
Activair DHW / EvoHeat EVO270 / Termobrasa BI*GOLD family on HiTemp app).

**Written:** 2026-11-20
**Method:** GitHub raw docs + issues/PRs + HA community threads + local docs for gap notes only.
**Rule followed:** no invented mappings; observation vs vendor labelled.

---

## 1. Repos / issues / threads mined

| Source                                                                  | What was mined                                                                                                                                                                                                                                                                                                                                                                                                                    | Product relevance                                                   |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [victor987/hitemp](https://github.com/victor987/hitemp)                 | `DEVICE_PARAMETERS.md`, `HITEMP_API_FINDINGS.md`, `BUG_ANALYSIS.md`, `BUG_M06_M17.md`, `ENTITIES.md`, `README.md`, `custom_components/hitemp/{const,binary_sensor}.py`                                                                                                                                                                                                                                                            | **Same product ID** (Indol PV300)                                   |
| [radical-squared/aquatemp](https://github.com/radical-squared/aquatemp) | Issues **#103, #108, #123, #130**; PRs **#41, #105, #110**; upstream `mapping`/`entity_description` for `1245226668902080512`                                                                                                                                                                                                                                                                                                     | Same product ID / HiTemp mapping bugs                               |
| [goglecm/hitemp](https://github.com/goglecm/hitemp)                     | README (fork of radical-squared; maintained continuation; documents empty O/S + `2050` bits)                                                                                                                                                                                                                                                                                                                                      | Same product ID (this local tree’s lineage)                         |
| [dosordie/FoxAir_Control](https://github.com/dosordie/FoxAir_Control)   | `cloud/warmlink_codes.py`, `cloud/warmlink_api.py`, `docs/warmlink_polling_and_readback.md`, `docs/warmlink_644_app_catalog.md`, `tests/test_cloud_app_heartbeat.py`                                                                                                                                                                                                                                                              | **Same Linked-Go cloud**; **different** board map (GL9/644 heating) |
| [sjtrny/esphome-hw211](https://github.com/sjtrny/esphome-hw211)         | `protocol/hw211_modbus.json` `dtu_wifi` sheet addresses **2050/2051/2085** bit descriptions                                                                                                                                                                                                                                                                                                                                       | **Vendor workbook** for HW211 DHW (high confidence bits)            |
| HA community                                                            | [Aqua Temp controller #230400 p.8](https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400?page=8) (Modbus 2050 bit8); [AquaTemp climate #334594](https://community.home-assistant.io/t/aquatemp-heat-pump-controller-integration-custom-climate-entity/334594); [Immergas Neptuno / HiTemp modes #999488](https://community.home-assistant.io/t/water-boiler-heater-immergas-neptuno-300-sol/999488) | HW211 / HiTemp mode notes                                           |
| Local (gap reference only)                                              | `docs/HW211_REGISTER_COMPARISON.md`, `docs/HITEMP_PARAMETERS.md`, `entity_description.1245226668902080512.json`                                                                                                                                                                                                                                                                                                                   | Not re-extracted as primary evidence                                |

### Forks noted (not all deep-read)

`radical-squared/aquatemp` forks include among others: `goglecm/hitemp`, `victor987/aquatemp`,
`ip0her/aquatemp`, `dmkent/aquatemp`, `arthuriansoft/aquatemp`, `zyznos321/warmlink`,
`PavelD/ha-aquatemp`, plus ~40 others. Deep register content is concentrated in
**victor987/hitemp**, **FoxAir_Control**, and **sjtrny/esphome-hw211**, not in most aquatemp forks.

### Not found / thin

- `api_explore/` scan dumps referenced by victor987 are **not** in the public repo tree (404).
- radical-squared **Discussions**: empty.
- No dedicated public “Linked-Go API documentation” beyond reverse-engineering READMEs.
- Web search for bare strings `1245226668902080512` / `app_heartbeat` / `getDataByCode` outside these repos mostly hit unrelated projects.

### Counts (this dump)

| Item                                                         | Count                                                                                                                                                                |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Named↔numeric aliases (victor Alt Code column)               | **109** enumerated pairs below; author prose claims **95** (79+16) — discrepancy unresolved                                                                          |
| Documented `2050` bit interpretations (distinct bit indices) | **bits 0, 2–5, 8–15** (vendor); community confirms bit 8                                                                                                             |
| Documented `2051` bit interpretations                        | **bits 0–3** (vendor)                                                                                                                                                |
| Documented `2085` Fault0 bits (`dtu_wifi`)                   | **0–5, 8–9, 13**; `hw211` sheet Fault0 adds more at different address                                                                                                |
| Newly emphasised sources vs local comparison alone           | aquatemp **#123/#130** (Power vs MO6 MITM); FoxAir **exact** `app_heartbeat=23205` payload + poll order; HA Neptuno mode table; PR **#105** other Trianco product ID |

---

## 2. API surface (Linked-Go / HiTemp)

### Endpoints (victor987 + FoxAir + aquatemp lineage)

| Operation                   | Endpoint                                           | Notes                                                 |
| --------------------------- | -------------------------------------------------- | ----------------------------------------------------- |
| Login                       | `POST …/app/user/login`                            | Password MD5; returns `x-token`                       |
| Shared device list (HiTemp) | `POST …/app/device/getMyAppectDeviceShareDataList` | Filter `productIds: ["1245226668902080512"]`          |
| Read                        | `POST …/app/device/getDataByCode`                  | Body field **`protocalCodes`** (typo retained by API) |
| Write                       | `POST …/app/device/control`                        | `param[]` of `{deviceCode, protocolCode, value}`      |
| Status / faults             | `getDeviceStatus`, `getFaultDataByDeviceCode`      | Used by integrations; not fully re-dumped here        |

**Base URLs seen:**

- HiTemp / crmservice: `https://cloud.linked-go.com:449/crmservice/api` (victor987)
- Older aquatemp script: `https://cloud.linked-go.com/cloudservice/api/...` (legacy path)

**Case:** protocol codes case-insensitive (`R01` ≡ `r01`) — victor987.

**Session:** ~24 h token life; one active login location (app XOR HA) — multiple sources.

### Live-data heartbeat (FoxAir confirmed; local guide agrees)

FoxAir `send_app_heartbeat` (tested in `tests/test_cloud_app_heartbeat.py`):

```json
{
  "param": [
    {
      "deviceCode": "<device>",
      "protocolCode": "app_heartbeat",
      "value": "23205"
    }
  ]
}
```

- Endpoint: `app/device/control` (same as writes).
- Poll order on live refresh: **heartbeat → settle → getDataByCode(live codes) → status**.
- On HiTemp DHW product, named `O01`–`O06` / `S01`–`S06` still return **empty** even when heartbeat is active (local `HITEMP_PARAMETERS.md`; aquatemp #108; goglecm README). Register **`1158`** has been observed to read **`23205`** while the app was open (local guide / entity_description).

---

## 3. Complete named ↔ numeric alias table (victor987)

**Source:** [victor987/hitemp `DEVICE_PARAMETERS.md`](https://github.com/victor987/hitemp/blob/main/DEVICE_PARAMETERS.md)
**Device:** Indol PV300, product `1245226668902080512`, scan 2026-03-23
**Evidence class:** **observation** (equal values when querying letter code and numeric `0–9999`).
**Author claim:** 95 aliases (79 writable + 16 read-only). **Enumerated Alt Code cells in named sections: 109.** Pattern **R(n) = 1103+n** for R01–R20.

### Special / control

| Named     | Alt  | Sample value | Notes (victor)                                   |
| --------- | ---- | ------------ | ------------------------------------------------ |
| Power     | 1011 | 1            | On/off; CONFIRMED writable                       |
| Mode      | 1012 | 2            | Mirrors mode_real; range 0–7                     |
| mode_real | 1013 | 2            | 0 Intelligent, 1 unused, 2 Eco, 3 Hybrid, 4 Fast |
| M06       | 1014 | 0            | Booster; write 1=on, 2=off→settles 0             |
| M17       | 1016 | 0            | Fan 0–5 on Indol (see conflicts)                 |

### C / D / E / F / G

| Named | Alt  | Named | Alt  | Named | Alt  |
| ----- | ---- | ----- | ---- | ----- | ---- |
| C02   | 1023 | C03   | 1024 | C05   | 1033 |
| C06   | 1026 | C07   | 1029 | C08   | 1030 |
| C09   | 1031 | D01   | 1034 | D02   | 1035 |
| D03   | 1036 | D04   | 1037 | D05   | 1038 |
| D06   | 1039 | D07   | 1040 | D10   | 1042 |
| D11   | 1043 | D12   | 1041 | D13   | 1051 |
| E01   | 1055 | E02   | 1056 | E03   | 1057 |
| E04   | 1058 | E05   | 1059 | E06   | 1060 |
| F01   | 1160 | F02   | 1161 | F03   | 1162 |
| F04   | 1163 | F05   | 1164 | F06   | 1165 |
| F07   | 1166 | F09   | 1168 | F10   | 1169 |
| F11   | 1170 | F12   | 1171 | F13   | 1172 |
| G01   | 1046 | G02   | 1047 | G03   | 1048 |
| G04   | 1049 |       |      |       |      |

### H / L / M / N

| Named | Alt  | Named | Alt  | Named | Alt  |
| ----- | ---- | ----- | ---- | ----- | ---- |
| H03   | 1069 | H16   | 1068 | H30   | 1076 |
| H32   | 1066 | H98   | 1074 | L02   | 1130 |
| L03   | 1131 | L04   | 1132 | L29   | 1143 |
| L31   | 2075 | L32   | 2076 | M12   | 1152 |
| M13   | 1153 | M14   | 1154 | M15   | 1155 |
| M16   | 1156 | N02   | 1081 | N03   | 1082 |
| N04   | 1083 | N05   | 1084 | N06   | 1085 |
| N07   | 1086 | N08   | 1087 | N09   | 1088 |
| N10   | 1089 | N11   | 1090 |       |      |

**No Alt listed by victor for:** H01, H07, H09, H31, H99, C01, M07, L06–L13, L28, L30, N01, /01, /02.

### O (only those with numeric Alt)

| Named | Alt  | Victor purpose     | Conflict risk                                     |
| ----- | ---- | ------------------ | ------------------------------------------------- |
| O07   | 2060 | EEV position       | Aligns with workbook                              |
| O08   | 2061 | Compressor hours   | Aligns                                            |
| O18   | 2062 | “Status”           | **Conflict:** workbook `2062` = O09 booster hours |
| O19   | 2063 | Status             | Uncertain                                         |
| O20   | 2064 | Status             | Uncertain                                         |
| O21   | 2065 | Temp sensor? (−55) | Uncertain                                         |
| O28   | 2066 | Unknown            | User-confirmed present                            |
| O29   | 2067 | Fan RPM            | Confirmed on Indol (570/700/830)                  |

**O01–O06, O09–O15:** named codes empty or no Alt in scan; O09 value 0 without Alt.

### R / T

| Named | Alt  | Named | Alt  |
| ----- | ---- | ----- | ---- |
| R01   | 1104 | R02   | 1105 |
| R03   | 1106 | R04   | 1107 |
| R05   | 1108 | R06   | 1109 |
| R07   | 1110 | R08   | 1111 |
| R09   | 1112 | R10   | 1113 |
| R11   | 1114 | R12   | 1115 |
| R13   | 1116 | R14   | 1117 |
| R15   | 1118 | R16   | 1119 |
| R17   | 1120 | R18   | 1121 |
| R19   | 1122 | R20   | 1123 |
| T01   | 2019 | T02   | 2020 |
| T03   | 2021 | T04   | 2022 |
| T05   | 2023 | T06   | 2024 |
| T07   | 2028 | T08   | 2029 |
| T09   | 2030 | T10   | 2025 |

**Suspect vs `dtu_wifi` workbook:** `T09`→`2030` (on dtu_wifi `2030` blank; on `hw211` sheet `2030` is State0). Treat as **uncertain**.

### Numeric-only codes (no named twin identified)

| Code                                                       | Value (scan)        | Notes                                                                                |
| ---------------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------ |
| 1015, 1020, 1021, 1025, 1067, 1070, 1073, 1075, 1077, 1080 | various             | Likely writable orphans                                                              |
| 1134–1141                                                  | timer-like ranges   | Likely numeric twins of L06–L13 (not proven by equal-value match in published table) |
| 1129, 1133, 1142, 1151                                     | bitmasks            | Vacation / timer enables (see §6)                                                    |
| **1158**                                                   | **23205** (at scan) | Heartbeat echo / live flag (local + this scan)                                       |
| 2011–2014                                                  | floats/ints         | Uncertain                                                                            |
| 2026, 2027                                                 | 0                   | Uncertain                                                                            |
| **2050, 2051**                                             | bitmasks            | Status words — §4                                                                    |
| 2057–2059, 2068–2071, 2074                                 | 0                   | Uncertain                                                                            |
| **2085**                                                   | all-zero bitmask    | Fault0                                                                               |

### Letters with **no** data on this product (victor)

`A, B, I, J, K, P, Q, S, U, V, W, X, Y, Z` — entire letter ranges empty.
**S*** empty is critical: remote switch / pressure inputs are **not** available as named cloud codes.

---

## 4. Bit interpretations for 2050 / 2051 / 2085

Bit index **0 = LSB** (rightmost char of the 16-char `"000…0010"` cloud string).

### 4.1 Official vendor (`dtu_wifi` workbook via sjtrny)

**Source:** `sjtrny/esphome-hw211` → `protocol/hw211_modbus.json` address **2050/2051/2085**, sheet `dtu_wifi`.
**Class:** **vendor**.

#### 2050 State0 — Slave component status

| Bit | Label                                                      | Polarity       |
| --- | ---------------------------------------------------------- | -------------- |
| 0   | S01 Remote on/off                                          | **1=OP, 0=CL** |
| 1   | _(absent on dtu_wifi text; present as S02 on hw211 sheet)_ | —              |
| 2   | S03 low pressure                                           | 1=OP, 0=CL     |
| 3   | S04 high pressure                                          | 1=OP, 0=CL     |
| 4   | S05 shortened time / heater accel                          | 1=OP, 0=CL     |
| 5   | S06 external heat source                                   | (workbook)     |
| 6–7 | Reserve                                                    |                |
| 8   | O01 Compressor                                             | 0=OFF, 1=ON    |
| 9   | O02 Electrical heater                                      | 0=OFF, 1=ON    |
| 10  | O03 4-way valve                                            | 0=OFF, 1=ON    |
| 11  | O04 Fan high                                               | 0=OFF, 1=ON    |
| 12  | O05 Fan low / solar pump                                   | 0=OFF, 1=ON    |
| 13  | O06 Reserve / solar                                        | 0=OFF, 1=ON    |
| 14  | “O12” Electric anode 3V_DE                                 |                |
| 15  | “O13” Electric anode MV_DE                                 |                |

#### 2051 State1 — Slave function status

| Bit | Workbook label                                    |
| --- | ------------------------------------------------- |
| 0   | “O14” shutDown (thermostat satisfied) 0=NO, 1=YES |
| 1   | “O15” DTU&WIFI online 0=NO, 1=YES                 |
| 2   | “O16” Defrost 0=NO, 1=YES                         |
| 3   | “O17” Hot water function active 0=NO, 1=YES       |

**Naming conflict:** workbook uses O12–O17 for bits that the **app** names O10–O15. Prefer **bit index + function**, not O-number.

#### 2085 Fault0 (`dtu_wifi`)

| Bit | Fault                 |
| --- | --------------------- |
| 0   | Ambient sensor P04    |
| 1   | Bottom sensor P01     |
| 2   | Top sensor P02        |
| 3   | Coil sensor P05       |
| 4   | Suction sensor P07    |
| 5   | Solar sensor P034     |
| 8   | High pressure E01     |
| 9   | Low pressure E02      |
| 13  | Antifreeze (tank) E09 |

(`hw211` sheet Fault0 at **2060** adds overheat/flow/antifreeze bits — **do not mix sheets**.)

### 4.2 victor987 observation (same product ID)

**Source:** `DEVICE_PARAMETERS.md` numeric row for `2050`.
**Class:** **observation**.

> Operating status: **bit8=compressor, bit9=e-heater, bits2+5=always set**

Sample idle-ish word: `0000000000100100` → bits **2** and **5** set (matches “always set” note; **not** a vendor meaning).

`2051` sample: `0000000000000001` → bit **0** set (workbook: shutDown) — **not** interpreted further by victor.
`2085`: all zeros in scan.

Victor’s HA code (`BINARY_STATUS_PARAMS = []`) no longer exposes O01–O06 as binary sensors (they stay empty); README still lists compressor/heater/defrost conceptually.

### 4.3 aquatemp #108 — spanznet (EvoHeat270 / HiTemp)

**Class:** **observation** (bit indexing partially wrong vs workbook).

Empty named keys: `O01`–`O06`, `S01`, `S03`–`S06` (and notes S keys empty).

Examples:

| State              | `2050` value       |
| ------------------ | ------------------ |
| compressor+fan off | `0000000000110000` |
| compressor+fan on  | `0000100100110000` |

Author claim: “bits 5 to 10 are O01–O06”.
**Conflict with vendor:** workbook puts O01–O06 on **bits 8–13**. The on-example actually shows **bits 4,5,8,11** (LSB-right): bits 4–5 look “sticky”; bit 8 ≈ compressor; bit 11 ≈ fan high — consistent with vendor **if** the author’s bit-range statement is ignored.

### 4.4 Local Trianco S300 observations (already in local docs; listed for conflict matrix)

**Class:** **observation** (this repo’s guide / comparison).

| Word | Bit   | Local reading                  | Vs workbook                       |
| ---- | ----- | ------------------------------ | --------------------------------- |
| 2050 | 0     | set when remote off / Power=0  | **match** S01 OP                  |
| 2050 | 2     | “coil warm > D01” guess        | **conflict** (workbook S03 LP)    |
| 2050 | 5     | always set                     | **uncertain** (workbook S06)      |
| 2050 | 8     | compressor                     | **match**                         |
| 2050 | 9     | electric heater / Fast heating | **match**                         |
| 2050 | 10    | during defrost (4-way)         | **match** O03                     |
| 2050 | 11–12 | fan while heating              | **match** role; speed split fuzzy |
| 2051 | 1     | always set while online        | **likely** DTU online             |
| 2051 | 2     | defrost                        | **match**                         |

### 4.5 HA community Modbus (HW211 family)

**Source:** [community.home-assistant.io #230400](https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400?page=8).
**Class:** **observation** against manufacturer spreadsheet.

ESPHome binary sensor: holding register **2050**, bitmask **`0x0100`** → **bit 8 = compressor**. Aligns with vendor + victor + local.

### 4.6 FoxAir packed words — **not** HW211 DHW map

| Cloud code | FoxAir Modbus | Meaning                            | On product `1245…`                                 |
| ---------- | ------------- | ---------------------------------- | -------------------------------------------------- |
| `O01~023`  | **2019**      | packed outputs (e.g. alarm bit 10) | **Must not use:** 2019 is **T01 ambient** on HW211 |
| `S01~S10`  | **2034**      | packed inputs                      | Empty / different on DHW cloud                     |
| `T14`      | **2050**      | pipe temp on GL9                   | **Must not use:** 2050 is State0 on HW211          |

FoxAir is authoritative for **`app_heartbeat=23205`** mechanics only.

---

## 5. Empty vs populated codes on product `1245226668902080512`

### Consistently **empty** (multiple sources)

| Codes                                                    | Sources                                                 |
| -------------------------------------------------------- | ------------------------------------------------------- |
| `S01`–`S06` (all S*)                                     | victor, aquatemp #108, local guide, goglecm README      |
| `O01`–`O06`                                              | same                                                    |
| `O10`–`O15`                                              | local guide; victor lists as empty/removed entities     |
| `T11`, `T12`                                             | victor BUG_ANALYSIS + local                             |
| `ver`, `software_code`, `Manual-mute`, `Set_Temp`, `MO6` | local entity_description / guide                        |
| FoxAir group codes `O01~023`, `S01~S10`, `O01~014`       | empty / wrong family on this product (local comparison) |

### Populated status path

| Code                                                                          | Role                                      |
| ----------------------------------------------------------------------------- | ----------------------------------------- |
| `2050`                                                                        | packed S/O component bits                 |
| `2051`                                                                        | packed function bits (defrost, online, …) |
| `2085`                                                                        | Fault0 bitmask (often zero)               |
| `Power` / `1011`                                                              | on/off                                    |
| `Mode` / `1012`, `mode_real` / `1013`                                         | mode                                      |
| `O07`/`2060`, `O08`/`2061`, `O29`/`2067`, temps `T01`–`T10`, settings R/D/E/… | normal scalars                            |

### Heartbeat-related

| Code                            | Behaviour                                         |
| ------------------------------- | ------------------------------------------------- |
| Write `app_heartbeat` = `23205` | Official live trigger (FoxAir)                    |
| Read `1158`                     | Observed `23205` while app open, else `0` (local) |
| Named O/S after heartbeat       | Still empty on this product                       |

---

## 6. Power / S01 / H01 / Mode / mode_real / timers / vacation

### Power ↔ S01 ↔ H01

| Finding                                                                                                              | Attribution                            | Class                                               |
| -------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | --------------------------------------------------- |
| Named `S01` empty; effect visible via **`Power`** and **`2050` bit 0**                                               | local + workbook + #108                | obs + vendor                                        |
| Opening remote contacts → Power `0`, bit0 set; close → Power `1`                                                     | local S300                             | observation                                         |
| Each on/off raises `T21` by 4 when `H01=YES` (remember power)                                                        | local                                  | observation                                         |
| App power write uses **`protocolCode":"Power"`** (value 0/1), **`appId":"13"`**                                      | aquatemp **#130** MITM of HiTemp iOS   | observation                                         |
| Upstream radical-squared mapping still uses `"power": "MO6"` (typo/wrong)                                            | mapping JSON + #103/#123/#130          | bug                                                 |
| Correct climate mapping: `"power": "Power"` (and mode often via `Mode`)                                              | PR #110, #103 comments, #123           | observation                                         |
| `MO6` empty; real booster toggle is **`M06`** (1=on, 2=off)                                                          | victor BUG_M06_M17 + DEVICE_PARAMETERS | observation                                         |
| On Trianco S300, `M06` stayed 0 while heater ran in Fast mode; heater followed **2050 bit 9** / app Electric heating | local guide                            | observation (**conflict** with Indol M06 behaviour) |

### Mode / mode_real / Vacation

| Code              | Values                                                  | Sources                                  |
| ----------------- | ------------------------------------------------------- | ---------------------------------------- |
| `mode_real`       | 0 Intelligent, **1 unused**, 2 Eco, 3 Hybrid, 4 Fast    | victor CONFIRMED; local S300             |
| `Mode`            | mirrors mode_real; **7 = Vacation**                     | local; Mode range 0–7 victor             |
| Vacation          | `1129` bit 0; date in `L02`–`L04`                       | local guide                              |
| HA Neptuno thread | maps HA Auto/Cool/Heat/FanOnly ↔ Smart/Eco/Hybrid/Boost | community (different remapping strategy) |

**Upstream bug:** mapping `"mode": "mode_real"` while some EVO270 diagnostics lack `mode_real` but have `Mode` (#123). App capture (#130) does not write `mode_real` for simple on/off. PR #110 switches climate mode key to **`Mode`**.

### Timers (cloud codes)

| Codes                               | Role (victor / local)                                      |
| ----------------------------------- | ---------------------------------------------------------- |
| L06–L13                             | Timer 1/2 start/end h/min                                  |
| L28 bitmask, L29 config, L30 status | schedule                                                   |
| L02–L04                             | vacation (and timer date fields)                           |
| 1129 / 1133 bitmasks                | vacation enable / timer enables (workbook L01/L05)         |
| C06–C09                             | “timer settings” minutes (uncertain purpose)               |
| FoxAir KG* / 1256–1269              | **different** family timer packing — do not import blindly |

### M17 fan

| Device                  | M17 range / meaning                                               |
| ----------------------- | ----------------------------------------------------------------- |
| Indol (victor)          | 0–5 speeds; CONFIRMED writable; compressor overrides physical fan |
| Trianco S300 (local)    | 0 Off / 1 Low / 2 High (app Ventilation)                          |
| radical-squared mapping | fan modes 0/1/2                                                   |

Treat M17 max as **model-dependent**.

---

## 7. Conflicts between sources (summary)

1. **O/S bit positions:** vendor bits **8–13** vs spanznet “bits 5–10” claim → prefer vendor; examples still support bit8 compressor.
2. **2050 bit 2 / bit 5:** local S300 guesses vs workbook S03/S06 → mark **uncertain**; workbook wins until re-verified.
3. **O-numbering on 2050/2051 high bits:** workbook O12–O17 vs app O10–O15.
4. **victor O18→2062** vs workbook **2062=O09**.
5. **victor T09→2030** vs dtu_wifi blank / hw211 State0.
6. **T06 name:** workbook Solar vs S300 discharge-like behaviour (local).
7. **M06 heater control:** works on Indol; ineffective indicator on S300 Fast heating.
8. **M17 range:** 0–5 Indol vs 0–2 S300 app.
9. **Climate power/mode codes:** `MO6`/`mode_real` vs `Power`/`Mode` (aquatemp bugs #103/#123/#130).
10. **FoxAir `O01~023`@2019 / `S01~S10`@2034 / `T14`@2050** vs HW211 DHW meanings — **different product family**.
11. **PR #105 Trianco Activair High Temp 9 kW** uses product ID **`1501438265440362496`** (Warmlink, DHW+CH) — **not** `1245…` DHW-only map.
12. **dtu_wifi vs hw211 sheets:** status at 2050/2051 vs 2030/2031 — cloud follows **dtu_wifi**.

---

## 8. Aquatemp / community narrative (HiTemp-specific)

| ID           | Title                    | Register-relevant takeaway                                             |
| ------------ | ------------------------ | ---------------------------------------------------------------------- |
| #108         | O/S unknown              | Named O/S empty; live in `2050`                                        |
| #103         | Mapping incorrect        | Termobrasa BI200GOLD; fan/mode broken; forks map Power/Mode            |
| #110 (PR)    | Fix HiTemp mapping       | `power: Power`, `mode: Mode`, add auto HVAC set=`2`                    |
| #123         | EVO270 always OFF        | Diagnostics have Power/Mode/R01; lack MO6/mode_real                    |
| #130         | Can’t control EVO270     | MITM: app writes `Power`; integration wrote `mo6`; app uses `appId:13` |
| #41 (merged) | Add product 1245…        | Initial HiTemp product support                                         |
| #105 (PR)    | Trianco Activair HT 9 kW | **Different** product ID 1501…                                         |
| HA #230400   | Modbus compressor        | 2050 bit8 / 0x0100                                                     |
| HA #999488   | Neptuno / HiTemp         | Mode value table; second account for HA                                |

---

## 9. Gaps vs local docs

Compared only to:

- `docs/HW211_REGISTER_COMPARISON.md`
- `docs/HITEMP_PARAMETERS.md`
- `custom_components/aqua_temp/parameters/entity_description.1245226668902080512.json`

### Already well covered locally

- Empty O/S; 2050/2051 packing; vendor bit table; compressor/heater/defrost entities; Power↔S01; vacation 1129; heartbeat 23205 / 1158; FoxAir family warning; victor alias highlights; M06 Indol vs S300.

### Gaps / under-documented in local docs (candidates for later merge)

1. **Full 95-alias table** — comparison has a selection only; this dump has the complete Alt Code list from victor.
2. **Aquatemp #123 / #130 packet evidence** — app writes `Power` + `appId:13`; upstream still maps `MO6`; some units omit `mode_real` in diagnostics. Local entity_description already uses Power/`mode_real` correctly for goglecm lineage, but the **radical-squared upstream** failure mode is worth a short “other integrations” note.
3. **FoxAir exact heartbeat payload + poll ordering** — local mentions 23205; FoxAir documents control JSON and settle-before-read.
4. **victor numeric orphans** (1015, 1020, 1021, 1025, 1067, …, 1134–1141, 2011–2014, 2026–2027, 2057–2074) — not catalogued in local comparison.
5. **victor BITMASK_PARAMS** only `{T08,F03,L28}` in code; cloud also returns bitmasks for 1129/1133/1142/1151/2050/2051/2085 — local handles 2050/2051/1129; **1142/1151** meaning still thin.
6. **O18–O28 / L31–L32 aliases** (2062–2066, 2075–2076) — local notes O18 conflict; little entity guidance for L31/L32 beyond “requested registers”.
7. **Indol M17 0–5 vs S300 0–2** — local documents S300; Indol multi-speed less emphasised.
8. **HA community compressor bitmask `0x0100`** — aligns; not cited in comparison sources table.
9. **PR #105 product `1501438265440362496`** — Trianco name collision risk if someone assumes all “Trianco Activair” share `1245…`.
10. **Workbook Fault0 bit list** — comparison mentions 2085 role; full bit→P/E code table could be copied from sjtrny into comparison when editing.
11. **`ModeState` / `hanControl` / `compensate_*`** — appear in FoxAir code lists; emptiness on S300 not systematically recorded in local entity JSON.
12. **goglecm/hitemp is public** and is the maintained aquatemp fork — comparison sources table lists radical-squared #108 but not goglecm as a primary cloud-integration source (optional citation).

### Not a gap (do not “fix” local with FoxAir bits)

Importing FoxAir `O01~023` bit maps onto this product would be a regression.

---

## 10. Practical extraction checklist for later comparison-doc edits

When editing `HW211_REGISTER_COMPARISON.md` (not done in this task):

- [ ] Paste full victor Alt Code table (or link to this dump).
- [ ] Keep vendor 2050/2051/2085 bits as primary; demote spanznet indexing.
- [ ] Add #123/#130 Power/`appId` footnote under climate mapping history.
- [ ] Cite FoxAir heartbeat JSON once under live-data.
- [ ] Flag Trianco product-ID fork (`1501…` vs `1245…`).
- [ ] Leave bit2/bit5 as unresolved conflicts.

---

## 11. Source URL quick index

- https://github.com/victor987/hitemp/blob/main/DEVICE_PARAMETERS.md
- https://github.com/victor987/hitemp/blob/main/HITEMP_API_FINDINGS.md
- https://github.com/victor987/hitemp/blob/main/BUG_M06_M17.md
- https://github.com/radical-squared/aquatemp/issues/108
- https://github.com/radical-squared/aquatemp/issues/103
- https://github.com/radical-squared/aquatemp/issues/123
- https://github.com/radical-squared/aquatemp/issues/130
- https://github.com/radical-squared/aquatemp/pull/110
- https://github.com/goglecm/hitemp
- https://github.com/dosordie/FoxAir_Control/blob/main/docs/warmlink_polling_and_readback.md
- https://github.com/dosordie/FoxAir_Control/blob/main/tests/test_cloud_app_heartbeat.py
- https://github.com/sjtrny/esphome-hw211/blob/main/protocol/hw211_modbus.json
- https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400?page=8
