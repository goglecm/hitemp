# HW211 register comparison (Trianco S300 / HiTemp)

As of integration 4.4.3, the HiTemp entities follow this `dtu_wifi` map.
Sensor names end with the register, named outputs and switches read the
`2050`/`2051` bits, and every bit of those words is a diagnostic entity.
Writable controls were not added. Findings below cite the workbook, Darksplat,
victor987, the HiTemp app captures and the S300 logs listed in
[HITEMP_PARAMETERS.md](HITEMP_PARAMETERS.md#source-ids).

Comparison of reverse-engineered HW211 / PHNIX-family register maps against
this repository’s HiTemp / Aqua Temp Home Assistant integration for product
`1245226668902080512` (Trianco S300 and related Activair / Indol / EVO270 /
Termobrasa BI\*GOLD units).

**Do not treat this as a write recipe.** Several families share Linked-Go cloud
code names but use different Modbus layouts. Evidence is labelled; where
sources disagree, the conflict is called out instead of inventing a winner.

Detailed research extracts (not edited in place of this doc) live in:

- [`_research_hw211_esphome.md`](_research_hw211_esphome.md) — 449 regs, 76 bits, sjtrny + forks
- [`_research_hitemp_cloud.md`](_research_hitemp_cloud.md) — victor aliases, aquatemp issues, gaps
- [`_research_foxair_phnix.md`](_research_foxair_phnix.md) — FoxAir/WarmLink heating maps + conflicts
- [`_research_github_sweep.md`](_research_github_sweep.md) — broad sweep, adjacent sources
- [`_research_github_deeper.md`](_research_github_deeper.md) — **Darksplat** EVO270 Modbus (NEW), midas, Fairland traps, WarmLink
- [`_research_app_cloud_api.md`](_research_app_cloud_api.md) — HiTemp iOS poll `2050`/`2051`, `appId` 13/14/16
- [`_research_oem_manuals_web.md`](_research_oem_manuals_web.md) — EvoHeat OUT/DI/T labelling (no new workbook)
- [`_research_forums_community.md`](_research_forums_community.md) — HA #230400 reinforcement, traps

Full 226-row `dtu_wifi` register table:
[`HW211_REGISTER_MAP_FULL.md`](HW211_REGISTER_MAP_FULL.md).

---

## 1. Executive summary

### Scorecard (product `1245226668902080512` vs official `dtu_wifi`)

| Bucket                  | Count (approx.)                                                                                                | What it covers                                                                                                            |
| ----------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **match**               | ~40+ core codes/bits                                                                                           | Power/Mode/R/T/O07–O09, `2050` bits 0/8–13, `2051` bits 0–3 roles, aliases = workbook; Darksplat field-confirms same bits |
| **empty-in-cloud**      | Named O01–O06, S01–S06, O10–O15, FoxAir `O01~*`/`S01~*`, Fault1–10                                             | **By design:** app polls `2050`/`2051` and unpacks client-side (aquatemp #130); HA entities read the bits                 |
| **alias-of**            | R↔1104+, T↔2019+, O07↔2060; legacy Aqua Temp O10–O15 ↔ workbook O12–O17                                        | victor + workbook + Darksplat CSV                                                                                         |
| **conflict**            | `2050` bit2 (S300 “coil” guess), `2050` bit5 (“always set”), T06 name, M06 behaviour, victor O18→2062          | Prefer workbook until re-verified                                                                                         |
| **uncertain**           | AI06↔T?, fan speed split 11/12, Darksplat S02@bit1 vs blank `dtu_wifi`, lone app poll of `O03`, some C/F codes | Marked in tables                                                                                                          |
| **only-in-repo**        | Darksplat clock mailbox notes, `hw211`-sheet-only regs, FoxAir heating                                         | Not HA entities or wrong family; the `2050`/`2051`/`2085` bits are HA entities since 4.4.0                                |
| **only-in-integration** | Computed superheat / ΔT, climate orchestration, live probe lists                                               | App/HA layer                                                                                                              |

### Key verdicts

1. **Best HW211 source:** [sjtrny/esphome-hw211](https://github.com/sjtrny/esphome-hw211)
   `protocol/hw211_modbus.json` from the official EVO270-1 workbook. Use the
   **`dtu_wifi` sheet** (slave 99) for HiTemp/S300 cloud addresses. The parallel
   **`hw211` sheet** is a different layout — do not mix.
   **Strong field companion:** [Darksplat/EVOHeat-EVO270-ESP32-Modbus](https://github.com/Darksplat/EVOHeat-EVO270-ESP32-Modbus)
   (Arduino + MQTT; credits sjtrny; full `2050`/`2051` bit CSVs + legacy O-code aliases).

2. **Named `O01`–`O06` / `S01`–`S06` are empty in the cloud** on this product —
   **by design**, not a missing second API. HiTemp iOS (aquatemp #130) polls
   **`2050` + `2051`** in `getDataByCode` and does **not** request named
   `O01`–`O06` / `S*` (lone unexplained exception: `O03`). The app UI unpacks
   those words client-side. Official map packs bits into **`2050` (State0)** /
   **`2051` (State1)**; faults **`2085` (Fault0)**. Hypothesis **`O03` ↔ `2055`
   is false** — O03 is **`2050` bit 10**.

3. **S300 live bits largely match the workbook** (compressor bit 8, heater 9,
   4-way 10, defrost `2051` bit 2, remote-off bit 0). Treat earlier S300 guesses
   for **bit 2 = “coil warm”** and **bit 5 = unknown always-on** as **uncertain /
   likely wrong** vs workbook S03 LP and S06 external heat source.

4. **FoxAir / WarmLink / pool PC1004 / Fairland / midas** share address _numbers_
   or product IDs with **different meanings**. Reuse cloud mechanics
   (`app_heartbeat=23205`; the HiTemp app's `appId` **13** is noted, not
   sent by this integration); never reuse their O/S bit maps on S300.

5. **EvoHeat OEM manuals** label PCB **OUT1–OUT5** as compressor / heater /
   4-way / fan high / fan low — same functions as workbook **O01–O05**
   (`2050` bits 8–12). That partially resolves schematic OUT-index vs O-code
   confusion for those five; Activair `20230302-0005` DI01 vs Trianco **DI05**
   remote labelling remains an open conflict — see §8.

---

## 2. Complete source catalog

Applicability: **HW211 DHW** = this product / EVO270 workbook · **Heating** =
FoxAir/PHNIX space-heating · **Pool** = PC100x pool · **Cloud-only** = Linked-Go
API without Modbus workbook · **Unrelated**.

| Source                                                    | URL                                                                       | Applicability                     | Confidence                   | Notes                                                                                                                                   |
| --------------------------------------------------------- | ------------------------------------------------------------------------- | --------------------------------- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **sjtrny/esphome-hw211**                                  | https://github.com/sjtrny/esphome-hw211                                   | **HW211 DHW**                     | **High** (vendor xlsx)       | Full JSON; `2050`/`2051`/`2085`; MIT code, workbook OEM                                                                                 |
| Workbook xlsx                                             | `datasheets/EVO270-1_MODBUS communication_protocol_6.5.25.xlsx`           | HW211 DHW                         | High                         | Origin of JSON                                                                                                                          |
| Other sjtrny datasheets                                   | `Evo-270-1_Modbus Map.pdf`, `Parameter and description.doc`, `302020…xls` | HW211 DHW                         | Medium                       | Not fully re-diffed vs JSON                                                                                                             |
| sjtrny blog                                               | https://sjtrny.com/posts/2026-06-03-esphome-hw211-component/              | HW211 DHW                         | Medium                       | Context / sheet choice                                                                                                                  |
| **hydazz/esphome-hw211**                                  | https://github.com/hydazz/esphome-hw211                                   | HW211 DHW                         | Same as sjtrny               | Fork; protocol JSON **identical**                                                                                                       |
| **Mozzie-AU/esphome-hw211**                               | https://github.com/Mozzie-AU/esphome-hw211                                | HW211 DHW                         | Same                         | Fork; identical JSON                                                                                                                    |
| **Allthebester/esphome-iStore-R290**                      | https://github.com/Allthebester/esphome-iStore-R290                       | HW211 DHW sibling                 | High (same lineage)          | Pruned JSON (99/106 rows); iStore/PC1006 naming                                                                                         |
| **echopin664/EVO270-1-HWS**                               | https://github.com/echopin664/EVO270-1-HWS                                | HW211 DHW hardware                | Medium                       | Atom S3 + RS485 pinout; hand YAML on `dtu_wifi`                                                                                         |
| j14s/EVO270-1-HWS                                         | https://github.com/j14s/EVO270-1-HWS                                      | HW211 DHW                         | Low                          | Fork; GPIO rename only                                                                                                                  |
| **Darksplat/EVOHeat-EVO270-ESP32-Modbus**                 | https://github.com/Darksplat/EVOHeat-EVO270-ESP32-Modbus                  | **HW211 DHW**                     | **High** (field + CSV)       | **NEW:** Arduino/MQTT slave 99; `status_bits.csv` / `core_registers.csv`; legacy O10–O15 aliases; 1012 vs 1013; clock mailbox 1151–1156 |
| **victor987/hitemp**                                      | https://github.com/victor987/hitemp                                       | Cloud + same product ID           | **High** aliases / emptiness | Indol PV300 scan; `DEVICE_PARAMETERS.md`                                                                                                |
| **goglecm/hitemp** (this tree)                            | https://github.com/goglecm/hitemp                                         | Cloud + S300 obs                  | High for docs                | Maintained aquatemp fork                                                                                                                |
| **radical-squared/aquatemp**                              | https://github.com/radical-squared/aquatemp                               | Cloud HA                          | Medium–High                  | #108 O/S→2050; **#130** HiTemp iOS poll + `appId` 13; #103/#123 Power/Mode                                                              |
| aquatemp forks (ip0her, arthuriansoft, zyznos321, …)      | various                                                                   | Cloud mapping                     | Low–Med                      | Mostly product IDs / HiTemp fixes; no new workbook                                                                                      |
| **dosordie/FoxAir_Control**                               | https://github.com/dosordie/FoxAir_Control                                | **Heating** (+ cloud mechanics)   | High heating                 | `O01~023`@2019; heartbeat JSON                                                                                                          |
| **tnako/ha-foxair**                                       | https://github.com/tnako/ha-foxair                                        | **Heating**                       | High heating                 | Modbus HA; same FoxAir JSON lineage                                                                                                     |
| **VAdamec/WarmLink**                                      | https://github.com/VAdamec/WarmLink                                       | Heating cloud                     | Medium                       | `appId=16`; no State0                                                                                                                   |
| **srbjessen/ha-warmlink**, 00gtw00/homeassistant_warmlink | GitHub                                                                    | Heating cloud                     | Medium                       | Larger WarmLink code catalog; still no DHW State0                                                                                       |
| **MiRo1310/ioBroker.midas-aquatemp**                      | https://github.com/MiRo1310/ioBroker.midas-aquatemp                       | Pool cloud (lists DHW product ID) | Low for DHW                  | Polls named O/S + 2074+; **no** `2050`/`2051` — do not treat as State0 map                                                              |
| **rogrun/openhab-addons** AquaTemp binding                | GitHub Release-AquaTemp-Binding…                                          | Pool cloud hosts                  | Medium hosts                 | `appId` **14** + `cloud.go-heating.com`; **not** HiTemp DHW                                                                             |
| **fleuke/VBIV-Fairland-Norsup-ha**                        | https://github.com/fleuke/VBIV-Fairland-Norsup-ha                         | **Pool PC1004**                   | High pool                    | **Trap:** `2050`=discharge temp, `2019`=outputs                                                                                         |
| King007t / rstcologne / spdr870 Fairland ESPHome          | GitHub                                                                    | Pool Modbus                       | Low for DHW                  | TEMP1 formula only; low IR addresses ≠ HW211                                                                                            |
| **vossim/ha_aquatemp**                                    | https://github.com/vossim/ha_aquatemp                                     | Pool BLE                          | Low for DHW                  | Slave 99; regs 7–51; no State0                                                                                                          |
| HA #230400 Aqua Temp                                      | community.home-assistant.io                                               | HW211 DHW                         | Medium–High                  | bit8/`0x0100` compressor; slave 99; TEMP1 YAML; PC1006 rumour                                                                           |
| HA #999488 Neptuno/HiTemp                                 | community                                                                 | Cloud modes                       | Medium                       | Mode remapping strategy                                                                                                                 |
| HA #855025 WarmLink                                       | community                                                                 | Heating                           | Medium                       | Links WarmLink integrations                                                                                                             |
| EvoHeat Evo270 / EVO270-1 / EVO270-E manuals              | evoheat.com.au PDFs / ManualsLib                                          | HW211 DHW hardware                | High for OUT/T/DI labels     | **OUT1–5 ≡ O01–O05** functions; DI04≡S04; no Modbus addresses                                                                           |
| Activair schematic                                        | CODE **20230302-0005** (local/offline)                                    | HW211 hardware                    | Medium                       | AI/DI/OUT; public URL not found                                                                                                         |
| Trianco S300 manual                                       | manualspro / ManualsLib                                                   | S300 docs                         | High for DI05/modes          |                                                                                                                                         |
| MelPump Trianco page                                      | melpump.com                                                               | Commercial adapter                | Empty                        | No public register map                                                                                                                  |
| Trianco Activair Indoor R32 panel                         | trianco.co.uk manuals                                                     | **Unrelated**                     | —                            | Supervisor addr 10, not HW211 DHW                                                                                                       |
| Sibotherm Modbus-R290.pdf                                 | sibotherm.com                                                             | Heating BMS                       | —                            | PLC 40001+; **not** MAIN 2050                                                                                                           |
| PHNIX fancoil (LogicMachine / HA)                         | 28xxx / 46xxx                                                             | **Unrelated**                     | —                            | Fancoil only                                                                                                                            |
| Chico / PC1006 OEM                                        | chico-future.com                                                          | Hardware lead                     | Low                          | No public Modbus table yet                                                                                                              |

### Cloud `appId` map (Linked-Go family)

| `appId` | App / stack                | Host (typical)                           | Relevance to product `1245…`                |
| ------: | -------------------------- | ---------------------------------------- | ------------------------------------------- |
|  **13** | **HiTemp** (iOS MITM #130) | `cloud.linked-go.com:449/crmservice/api` | **Use for HiTemp DHW**                      |
|  **14** | AquaTemp Flutter (openHAB) | `cloud.go-heating.com/crmservice/api`    | Pool accounts; **not** shown for HiTemp DHW |
|  **16** | WarmLink / FoxAir heating  | linked-go `:449` CRM                     | Heating only                                |

### Repos / OEM searches empty or trap-only (no new HW211 DHW State0 workbook)

Gitee/GitCode PHNIX mirrors, Indol/Termobrasa Modbus PDFs, Trianco S200 Modbus,
bare `20230302-0005` web hits, unrelated GitHub “HW211” names, Fairland/Midas/
Sibotherm address spaces — see
[`_research_github_sweep.md`](_research_github_sweep.md),
[`_research_github_deeper.md`](_research_github_deeper.md),
[`_research_oem_manuals_web.md`](_research_oem_manuals_web.md).

---

## 3. Complete `dtu_wifi` register map (highlights)

Full 226-row table + data-type formulas:
**[`HW211_REGISTER_MAP_FULL.md`](HW211_REGISTER_MAP_FULL.md)**.

Transport: Modbus RTU 9600 8N1, slave **99**, FC 03/06/16. TEMP1 =
`(x - 60) * 0.5` °C.

### 3.1 Core controls / telemetry

| Addr        | Code         | Workbook name                                                                       |
| ----------- | ------------ | ----------------------------------------------------------------------------------- |
| 1011        | Power        | Power on/off                                                                        |
| 1012        | Mode         | Mode / **requested** operation mode (0/2/3/4/7 Vacation) — Darksplat verified-write |
| 1013        | Mode_REAL    | **Actual** operation mode (read-only on bus; cloud `mode_real`)                     |
| 1014        | M06          | Booster works independently                                                         |
| 1015        | M07          | Compulsive defrosting                                                               |
| 1016        | M17          | Ventilation mode                                                                    |
| 1020 / 1021 | /01 / /02    | Usage of O05 / O06                                                                  |
| 1034–1040   | D01–D07      | Defrost                                                                             |
| 1046–1049   | G01–G04      | Disinfection                                                                        |
| 1055–1059   | E01–E05      | EEV                                                                                 |
| 1066–1077   | H\*          | Cloud interval, memory, units, address, control mode                                |
| 1080–1090   | N01–N11      | Solar                                                                               |
| 1104        | R01          | Target temp                                                                         |
| 1106–1123   | R03–R20      | Heating / booster / limits (gaps empty)                                             |
| 1129        | L01          | Vacation enable (bit 0)                                                             |
| 1130–1132   | L02–L04      | Vacation date                                                                       |
| 1133        | L05          | Timer enables (bits 0–3)                                                            |
| 1134–1141   | L06–L13      | Timer times                                                                         |
| 1151–1156   | M11–M16      | Clock                                                                               |
| 1158        | —            | APP Online Heartbeat Package (`0x5AA5` / observed `23205`)                          |
| 2011–2014   | —            | Main/controller program version + software codes                                    |
| 2019–2025   | T01–T06, T10 | Ambient, bottom, top, coil, suction, solar, display                                 |
| 2026–2027   | T20 / T21    | Out-of-range count / EEPROM write count                                             |
| **2050**    | **State0**   | **Slave component status**                                                          |
| **2051**    | **State1**   | **Slave function status**                                                           |
| 2060        | O07          | EEV current position                                                                |
| 2061        | O08          | Compressor run hours                                                                |
| 2062        | O09          | Booster run hours                                                                   |
| **2085**    | **Fault0**   | **Failure (W10)**                                                                   |

### 3.2 `2050` State0 — full workbook bits

Access W, FC16, Binary. **Bit 0 = LSB** (rightmost char of cloud `"000…"` string).

| Bit | Workbook text                                |
| --- | -------------------------------------------- |
| 0   | (S01) Remote on/off switch (**1=OP, 0=CL**)  |
| 2   | (S03) low pressure switch (**1=OP, 0=CL**)   |
| 3   | (S04) High pressure switch (**1=OP, 0=CL**)  |
| 4   | (S05) Shortened time signal (**1=OP, 0=CL**) |
| 5   | (S06) External heat source switch            |
| 6–7 | Reserve                                      |
| 8   | (O01) Compressor (**0=OFF, 1=ON**)           |
| 9   | (O02) Electrical heater (**0=OFF, 1=ON**)    |
| 10  | (O03) 4-way valve (**0=OFF, 1=ON**)          |
| 11  | (O04) Fan high speed                         |
| 12  | (O05) Fan low speed / solar pump             |
| 13  | (O06) Reserve / solar pump / solar valve     |
| 14  | O12 Electric anode 3V_DE                     |
| 15  | O13 Electric anode MV_DE                     |

_(Bit 1 absent on `dtu_wifi` text; present as S02 heater overload on `hw211` sheet State0. Darksplat CSV fills bit 1 as legacy **S02** “Over heat protection switch” — treat as field/legacy until xlsx re-check.)_

### 3.3 `2051` State1 — full workbook bits

| Bit | Workbook text                                         |
| --- | ----------------------------------------------------- |
| 0   | O14 shutDown (**0=NO, 1=YES**) — thermostat satisfied |
| 1   | O15 DTU&WIFI online (**0=NO, 1=YES**)                 |
| 2   | O16 Defrost (**0=NO, 1=YES**)                         |
| 3   | O17 Whether the system enters the hot water function  |

### 3.3a Legacy Aqua Temp O-codes vs workbook (Darksplat) — **same bits**

[Darksplat `status_bits.csv`](https://github.com/Darksplat/EVOHeat-EVO270-ESP32-Modbus)
preserves **legacy Aqua Temp / app-style** code numbers on the same bit
positions. CSV notes: numbering is alias, not a second physical layout.
**Prefer workbook labels in this comparison; keep Darksplat as alias + field
confirmation.**

| Word / bit      | Darksplat legacy code | Workbook / `dtu_wifi` label                   | Function (agree)                          |
| --------------- | --------------------- | --------------------------------------------- | ----------------------------------------- |
| 2050 bit 0      | S01                   | S01                                           | Remote ON/OFF                             |
| 2050 bit 1      | **S02**               | _(blank on `dtu_wifi`; S02 on `hw211` sheet)_ | Over-heat protection (legacy)             |
| 2050 bits 2–5   | S03–S06               | S03–S06                                       | LP / HP / shortened time / external heat  |
| 2050 bits 8–13  | O01–O06               | O01–O06                                       | Comp / heater / 4-way / fan H/L / reserve |
| 2050 bits 14–15 | Legacy **O10 / O11**  | Workbook **O12 / O13**                        | 3V_DE / MV_DE anodes                      |
| 2051 bit 0      | Legacy **O12**        | Workbook **O14**                              | Shutdown / satisfied                      |
| 2051 bit 1      | Legacy **O13**        | Workbook **O15**                              | DTU/Wi-Fi online                          |
| 2051 bit 2      | Legacy **O14**        | Workbook **O16**                              | Defrost                                   |
| 2051 bit 3      | Legacy **O15**        | Workbook **O17**                              | Hot-water stage / function active         |

HiTemp entity names `O10`–`O15` in this repo follow the **legacy/app**
numbering (same as Darksplat), not workbook O12–O17. Prefer **bit index +
function** when integrating.

### 3.4 `2085` Fault0 — full workbook bits (`dtu_wifi`)

| Bit | Fault                                    |
| --- | ---------------------------------------- |
| 0   | Ambient sensor failure P04               |
| 1   | Bottom sensor failure P01                |
| 2   | Top sensor failure P02                   |
| 3   | Coil sensor failure P05                  |
| 4   | Suction sensor failure P07               |
| 5   | Solar sensor failure P034                |
| 8   | High pressure protection E01             |
| 9   | Low pressure protection E02              |
| 13  | Antifreezing protection (water tank) E09 |

### 3.5 Named ↔ numeric aliases (workbook + victor)

**Workbook** supplies the address when the JSON “number” field matches the
named code. **Victor** ([DEVICE_PARAMETERS.md](https://github.com/victor987/hitemp/blob/main/DEVICE_PARAMETERS.md))
established **observation** aliases by equal values on Indol PV300 (same
product ID). Author claims ~95 pairs; enumerated Alt cells in research: **109**
(discrepancy unresolved). Full Alt list:
[`_research_hitemp_cloud.md`](_research_hitemp_cloud.md) §3.

| Named                       | Numeric                          | How established                          |
| --------------------------- | -------------------------------- | ---------------------------------------- |
| Power                       | 1011                             | Workbook + victor write                  |
| Mode                        | 1012                             | Workbook + victor                        |
| mode_real                   | 1013                             | Workbook Mode_REAL + victor              |
| M06                         | 1014                             | Workbook + victor                        |
| M17                         | 1016                             | Workbook + victor                        |
| /01, /02                    | 1020, 1021                       | Workbook                                 |
| D01–D07                     | 1034–1040                        | Both                                     |
| G01–G04                     | 1046–1049                        | Both                                     |
| E01–E05                     | 1055–1059                        | Both                                     |
| H32                         | 1066                             | Both                                     |
| H01                         | 1067                             | Workbook (victor unnamed)                |
| H03                         | 1069                             | Both                                     |
| H07 / H98 / H99 / H30 / H31 | 1073 / 1074 / 1075 / 1076 / 1077 | Workbook (± victor)                      |
| N02–N11                     | 1081–1090                        | Both                                     |
| R01; R03–R20                | 1104; 1106–1123                  | Pattern R(n)=1103+n                      |
| L02–L04; L06–L13            | 1130–1132; 1134–1141             | Workbook (+ victor L02–04)               |
| M12–M16                     | 1152–1156                        | Both                                     |
| T01–T06, T10                | 2019–2024, 2025                  | Both                                     |
| T20 / T21                   | 2026 / 2027                      | Workbook                                 |
| O07 / O08 / O09             | 2060 / 2061 / 2062               | Workbook (+ victor O07/O08)              |
| O01–O06, S01–S06            | _bits of 2050_                   | Workbook State0 — **not** solo registers |
| Defrost / online / …        | _bits of 2051_                   | Workbook State1                          |

**Suspect victor rows:** `O18`→`2062` (workbook **O09**); `T09`→`2030`
(`dtu_wifi` blank; `hw211` State0). **O29**→`2067` (victor observation; fan RPM).

Letters empty on this product (victor): entire **S\*** range, plus A/B/I/J/K/P/Q/U–Z.

---

## 4. `hw211` sheet vs `dtu_wifi` (do not mix)

| Topic                    | `dtu_wifi`                               | `hw211`                                              |
| ------------------------ | ---------------------------------------- | ---------------------------------------------------- |
| Workbook sheet           | Visible DTU&WIFI                         | Hidden HW211                                         |
| Register count (sjtrny)  | 226                                      | 223                                                  |
| Default slave            | **99**                                   | Centralized / H30 address                            |
| Ambient                  | **2019**                                 | **2011**                                             |
| Tank bottom / top        | **2020 / 2021**                          | **2012 / 2013**                                      |
| Coil / suction / solar   | 2022–2024                                | 2014–2016                                            |
| Display water temp       | **2025** T10                             | _(no named T10)_                                     |
| EEV position             | **2060** O07                             | **2019** O07                                         |
| Comp / heater hours      | **2061 / 2062**                          | **2020 / 2021**                                      |
| Firmware                 | 2011–2014                                | 2077–2080                                            |
| State0 / State1 / Fault0 | **2050 / 2051 / 2085**                   | **2030 / 2031 / 2060**                               |
| State0 bit5              | External heat source                     | Water flow switch                                    |
| State0 bit1              | _(absent)_                               | Heater overload switch                               |
| State0 bits 14–15        | Electronic anodes                        | _(absent)_                                           |
| State1 bit1              | DTU&WIFI online                          | Online control mode (集控 vs DTU)                    |
| State1 bit3              | Hot water function                       | _(absent)_                                           |
| Fault extras             | —                                        | E04 overheat, E03 flow, E07 frost, senior antifreeze |
| Clock order              | 1151 enable, min, hour, day, month, year | Different field order + weekday                      |
| Address / control params | 1076 / 1077                              | 1157 / 1158                                          |

**Hard collisions** (same number, different meaning): 2011–2014, 2019–2021,
2050/2051 vs empty on other sheet, 2060 EEV vs Fault0, clock 1151–1156.

**HiTemp / S300 cloud follows `dtu_wifi` addresses.**

---

## 5. Cross-repo comparison

### Where sources agree (S300 / HW211 DHW)

| Claim                                     | Agreeing sources                                                               |
| ----------------------------------------- | ------------------------------------------------------------------------------ |
| `2050` bit 8 = compressor                 | Workbook, Darksplat CSV, victor, S300 logs, aquatemp #108, HA #230400 `0x0100` |
| `2050` bit 9 = electric heater            | Workbook, Darksplat, victor, S300 Fast-heating log                             |
| `2050` bits 10–13 = 4-way / fans / O06    | Workbook + Darksplat (same positions)                                          |
| `2051` bit 2 = defrost                    | Workbook, Darksplat O14/O16 alias, ESPHome, S300                               |
| Named O/S empty; live in `2050`/`2051`    | victor, #108, **#130 poll list**, goglecm guide                                |
| App unpacks packed words client-side      | #130 (requests `2050`/`2051`, not O01–O06/S*)                                  |
| `R01`=`1104`, `T01`=`2019`, Power=`1011`  | Workbook + Darksplat + victor + integration                                    |
| Mode **1012** requested / **1013** actual | Workbook + Darksplat field write notes; cloud `mode_real`↔1013                 |
| Heartbeat value **23205**                 | FoxAir docs/tests + local `1158` observation                                   |
| O03 ≠ 2055                                | Workbook + FoxAir (2055 = frost _temp_ on heating)                             |
| PCB OUT1–5 = O01–O05 functions            | EvoHeat Evo270 manual + workbook bits 8–12                                     |

### Where they differ or are wrong for S300

| Claim                             | Wrong / conflicting for S300                       | Prefer                                               |
| --------------------------------- | -------------------------------------------------- | ---------------------------------------------------- |
| O bits on `2050` are “bits 5–10”  | aquatemp #108 prose                                | Workbook bits **8–13**                               |
| `2050` bit 2 = coil > D01         | Local S300 guess                                   | Workbook **S03 LP**; re-verify                       |
| `2050` bit 5 always = mystery     | Local / victor “always set”                        | Workbook **S06**; why set unknown                    |
| FoxAir `O01~023` @ 2019           | Heating map                                        | On DHW **2019 = T01**                                |
| FoxAir `S01~S10` @ 2034           | Heating                                            | DHW S-pack in **2050**                               |
| FoxAir `T14` @ 2050               | Heating manifold temp                              | DHW **State0**                                       |
| fleuke pool `2050` = discharge    | PC1004                                             | DHW **State0**                                       |
| Upstream aquatemp `power: MO6`    | #103/#123/#130                                     | App writes **`Power`**; use Power/Mode               |
| M06 controls heater on S300       | Indol victor behaviour                             | S300: heater via **bit 9** / Fast mode; M06 stayed 0 |
| M17 range 0–5                     | Indol                                              | S300 app **0–2**                                     |
| victor O18 = 2062                 | Equal-value scan                                   | Workbook **2062 = O09**                              |
| Trianco product ID always `1245…` | PR #105 Activair HT uses **`1501438265440362496`** | Different map                                        |

### sjtrny forks / Darksplat

| Source            | Delta                                                                                                                                |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| hydazz, Mozzie-AU | Identical protocol JSON                                                                                                              |
| Allthebester      | Trimmed rows + English/data_type fills; **same** bit numbers                                                                         |
| echopin664        | No JSON; YAML matches `dtu_wifi` bits 0,2–5,8–15                                                                                     |
| **Darksplat**     | Independent firmware; **same** bit positions; legacy O10–O15 names; additive 1012/1013 + clock mailbox docs; no new Fault0 bit table |

---

## 6. Integration applicability

Match status: `match` | `conflict` | `only-in-repo` | `only-in-integration` |
`empty-in-cloud` | `alias-of`.

HA exposure from
`custom_components/aqua_temp/parameters/entity_description.1245226668902080512.json`
and probes in `common/consts.py` (`LIVE_PROBE_CODES`, `HITEMP_DISCOVERY_CODES`,
`BITWORD_CODES`).

### Status / fault bits

Every bit of `2050`, `2051` and `2085` is also a raw diagnostic binary sensor
(`Reg 2050 bit 0` … `Reg 2085 bit 15`), enabled by default.

| Code / bit                        | HA exposure                                                      | Confidence | Match                    | Notes                                                  |
| --------------------------------- | ---------------------------------------------------------------- | ---------- | ------------------------ | ------------------------------------------------------ |
| `2050` word                       | `State0 Operating status (2050)` sensor                          | observed   | **match** (role)         | App polls this (#130)                                  |
| `2050` bit 0                      | `S01 Remote switch open (2050.0)`                                | observed   | **match**                | 1 = OP; set while the contacts are open and Power is 0 |
| `2050` bit 1                      | `S02 Overheat input (2050.1)`                                    | uncertain  | **uncertain**            | Blank on `dtu_wifi`; polarity not claimed              |
| `2050` bit 2                      | `S03 Low pressure switch open (2050.2)`                          | documented | **match** (workbook)     | Earlier S300 coil guess dropped                        |
| `2050` bits 3–4                   | `S04 …(2050.3)`, `S05 …(2050.4)`                                 | documented | **match**                | 1 = OP                                                 |
| `2050` bit 5                      | `S06 External heat switch active (2050.5)`                       | uncertain  | **conflict / uncertain** | Often set on the S300; workbook gives no polarity      |
| `2050` bit 8                      | `O01 Compressor running (2050.8)`, `Compressor running (2050.8)` | observed   | **match**                |                                                        |
| `2050` bit 9                      | `O02 Heater running (2050.9)`, `Heater running (2050.9)`         | observed   | **match**                |                                                        |
| `2050` bit 10                     | `O03 Reversing valve on (2050.10)`                               | observed   | **match**                | Set during defrost                                     |
| `2050` bits 11–12                 | `O04 Fan running high`, `O05 Fan running low`                    | uncertain  | **match** (role)         | Which speed is which isn't confirmed                   |
| `2050` bit 13                     | `O06 Spare output on (2050.13)`                                  | documented | **match**                |                                                        |
| `2050` bits 14–15                 | `O10 Anode 3V on`, `O11 Anode MV on`                             | documented | **alias-of**             | Legacy O10/O11 = workbook O12/O13                      |
| `2051` bit 0                      | `O12 Heating stopped (2051.0)`                                   | documented | **alias-of**             | Workbook O14 shutDown                                  |
| `2051` bit 1                      | `O13 Wi-Fi link up (2051.1)`                                     | observed   | **alias-of**             | Workbook O15; always set while online                  |
| `2051` bit 2                      | `O14 Defrost running (2051.2)`, `Defrost running (2051.2)`       | observed   | **alias-of**             | Workbook O16                                           |
| `2051` bit 3                      | `O15 Hot water stage active (2051.3)`                            | documented | **alias-of**             | Workbook O17                                           |
| `2085`                            | `Fault0 Fault bits (2085)` sensor and its 16 bits                | documented | **match**                | Bits 0–5, 8, 9, 13 named from the workbook (§3.4)      |
| `Fault1`–`Fault10`                | live probe                                                       | —          | **empty-in-cloud**       | FoxAir-style                                           |
| `O01~015` / `O01~023` / `S01~S10` | not probed on HiTemp                                             | —          | **empty-in-cloud**       | Wrong family; `2019` is ambient temperature            |

### Named O / S codes

The named cloud codes stay empty on this product, by design. The entities
with those codes read the bits above instead. The named codes are still
probed, so diagnostics would show a value if the cloud ever filled them.

| Code              | HA                                 | Match                                           | Packed / numeric                   |
| ----------------- | ---------------------------------- | ----------------------------------------------- | ---------------------------------- |
| `O01`–`O06`       | binary sensors, Diagnostic         | **empty-in-cloud** + **alias-of** bits          | `2050` bits 8–13                   |
| `O03`             | binary sensor                      | empty named; app still polls `O03` alone (#130) | bit 10 — unexplained lone poll     |
| `O07`/`O08`/`O09` | sensors                            | **alias-of**                                    | 2060 / 2061 / 2062                 |
| `O10`–`O15`       | binary sensors, Diagnostic         | empty + alias-of (legacy ≡ workbook O12–O17)    | `2050` bits 14–15, `2051` bits 0–3 |
| `O29`             | `O29 Fan speed` sensor, Diagnostic | victor alias 2067 (blank in workbook)           | 0 on S300 while heating            |
| `S01`–`S06`       | binary sensors, Diagnostic         | **empty-in-cloud** + **alias-of** bits          | `2050` bits 0–5                    |
| `2055`            | unused                             | **only-in-repo** (heating frost T)              | Not O03                            |

### Integration decisions

1. The `2050`/`2051` bits the official app paints are binary sensors, and so
   is every other bit of those words and of `2085`.
2. The named O/S entities read those bits, so they are no longer empty.
3. Writes keep using `Power` and `mode_real` without `appId`. The HiTemp app
   sends `appId: "13"` (#130); this integration does not, and nothing so far
   shows the cloud requires it. Heartbeat **`23205`** is sent;
   `go-heating` / `appId` 14 does not fill the DHW O/S codes.
4. Entity names keep the app's legacy O10–O15 numbers; descriptions give the
   workbook O12–O17 numbers (Darksplat table §3.3a).

### Core T / R / Mode / Power / L / M / H

| Code                | Alt                | HA                                    | Match                                                           |
| ------------------- | ------------------ | ------------------------------------- | --------------------------------------------------------------- |
| T01–T05, T10        | 2019–2023, 2025    | sensors                               | **match** + **alias-of**                                        |
| T06                 | 2024               | `T06 Discharge temperature (2024)`    | **conflict** (workbook solar vs S300 discharge-like), uncertain |
| R01                 | 1104               | number, Controls                      | **match**                                                       |
| Power               | 1011               | binary_sensor                         | **match**                                                       |
| mode_real / Mode    | 1013 / 1012        | select (written) / sensor (read-only) | **match** by address; on the S300 1012 read 7 during vacation   |
| M17                 | 1016               | select                                | **match** (range model-dependent)                               |
| M06                 | 1014               | `M06 Booster mode (1014)` sensor      | **conflict** (Indol writable vs S300 stuck 0), uncertain        |
| H01 / H07 / H31     | 1067 / 1073 / 1077 | config / sensors                      | **alias-of**                                                    |
| L02–L13, 1129, 1133 | timers/vacation    | sensors and bits, Diagnostic          | **match**                                                       |
| M07, M12–M16        | 1015, 1152–1156    | probe sensors, Diagnostic             | **match**                                                       |
| 1158                | heartbeat echo     | `Reg 1158 Heartbeat echo` sensor      | **match** (role)                                                |
| 2011–2014           | versions           | `Reg 2011` … `Reg 2014` sensors       | **match**                                                       |
| T20 / T21           | 2026 / 2027        | sensors                               | **match**                                                       |

### Discovery / probes only-in-integration or only-in-repo

- **only-in-integration:** `superheat`, `water_delta_t`, climate entity, `LIVE_PROBE_CODES` / `HITEMP_DISCOVERY_CODES`. Since 4.4.3 the probed codes from Victor's scan (C/D10–13/F/H09/H16/E06/O18–28/R02/R11/R13/R16/L29–32/2057–2059/2068–2071, ModeState) are diagnostic sensors named `{Code} Unknown` or `Reg {address} Unknown`; Victor's aliases are in their descriptions only.
- **only-in-repo:** M07 forced defrost as a control (it is read, never written), `hw211` manual word `1149`, ESPHome derived Operating state.

### Other integrations footnote (aquatemp upstream)

radical-squared mapping historically used `"power": "MO6"` and sometimes
`mode_real` where diagnostics lack it (#123/#130). App MITM writes
`protocolCode: "Power"` with `appId: "13"`. This fork’s entity_description
already uses **Power** / **mode_real** appropriately; do not “fix” by
importing FoxAir bit maps.

---

## 7. FoxAir / heating conflict table

Board family: FoxAir GL9 / PHNIX space-heating (WarmLink product family 644).
Sources: FoxAir_Control, tnako/ha-foxair, VAdamec/WarmLink. Full heating bit
maps: [`_research_foxair_phnix.md`](_research_foxair_phnix.md).

|  Address | FoxAir / heating         | Cloud (heating) | HW211 `dtu_wifi` / S300       | Conflict                   |
| -------: | ------------------------ | --------------- | ----------------------------- | -------------------------- |
| **2019** | Packed outputs O001–O023 | `O01~023`       | **T01 ambient**               | **HARD**                   |
| **2034** | Packed inputs / SG       | `S01~S10`       | Not DHW S-pack                | **HARD**                   |
| **2050** | T14 manifold temp        | `T14`           | **State0**                    | **HARD**                   |
| **2055** | T06 frost plate temp     | `T06`           | Blank; **≠ O03**              | **CONFLICT**               |
|     2045 | T01 ambient              | `T01`           | Ambient is **2019**           | Same name, different addr  |
|     2085 | ERR01 heating fault bits | Fault5 alias    | DHW **Fault0** different bits | Same number, different map |

### Side-by-side signals

| Signal          | FoxAir heating            | HW211 DHW               |
| --------------- | ------------------------- | ----------------------- |
| Compressor      | `2019` **bit 0**          | `2050` **bit 8**        |
| 4-way           | `2019` **bit 6**          | `2050` **bit 10**       |
| Electric heater | `2019` bits 7–8 (stages)  | `2050` **bit 9**        |
| Remote on/off   | `2034` bit 4 (active-low) | `2050` **bit 0** (1=OP) |

### Reusable vs not

| Reuse on S300                                                   | Do **not** reuse                             |
| --------------------------------------------------------------- | -------------------------------------------- |
| Host `cloud.linked-go.com:449/crmservice/api`                   | Any FoxAir bit position                      |
| `app_heartbeat` = `23205` (control write, often **no** `appId`) | `O01~023` / `S01~S10` addresses              |
| Poll: heartbeat → settle → `getDataByCode`                      | Heating T-map (T01@2045, T06@2055, T14@2050) |
| BINARY string MSB-left = bit 15                                 | Fault1–10 bit meanings from heating ERR maps |
| Idea that O/S may be packed                                     | fleuke PC1004 `2050`=discharge               |

Heartbeat payload (FoxAir confirmed):

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

---

## 8. Hardware / schematic notes (Activair 20230302-0005)

Activair indoor heat pump, controller **HW211**, document **20230302-0005**.
Protocol codes use **`dtu_wifi` / HiTemp** naming.

### Sensors (AI → T)

| Schematic | Legend         | Likely protocol | Notes                                                  |
| --------- | -------------- | --------------- | ------------------------------------------------------ |
| AI01      | AT ambient     | `T01` / 2019    | Match                                                  |
| AI02      | BTT bottom     | `T02` / 2020    | Match                                                  |
| AI03      | TTT top        | `T03` / 2021    | Match                                                  |
| AI04      | CT coil        | `T04` / 2022    | Match                                                  |
| AI05      | SUT suction    | `T05` / 2023    | Match                                                  |
| AI06      | AFT antifreeze | **Uncertain**   | Not proven as T06/T07; S300 T06 behaves discharge-like |

### Digital inputs — labelling conflict

| Schematic              | Trianco S300 manual   | `2050` protocol    | Reconciliation                                                         |
| ---------------------- | --------------------- | ------------------ | ---------------------------------------------------------------------- |
| DI01 “room thermostat” | Remote = **DI05**+GND | Bit 0 = S01        | **Conflict** silkscreen vs Trianco; trust Trianco + Power/bit0 on S300 |
| DI03 labelled HP       | —                     | Bit 2 = **S03 LP** | Possible mismatch; do not invent                                       |
| DI04 → HP              | —                     | Bit 3 = S04 HP     | Plausible                                                              |
| DI05 unused on drawing | **DI05** remote       | S01                | Matches Trianco                                                        |

### Outputs — OEM EvoHeat manuals vs workbook / schematic

EvoHeat **Evo270** PCB description (OEM manuals; no Modbus addresses) labels
hardware **OUT1–OUT5** with the **same functions** as workbook **O01–O05**:

| PCB (EvoHeat manual) | Manual meaning  | Protocol                                  | `2050` bit |
| -------------------- | --------------- | ----------------------------------------- | ---------: |
| **OUT1**             | Compressor      | **O01**                                   |          8 |
| **OUT2**             | Electric heater | **O02**                                   |          9 |
| **OUT3**             | 4-way valve     | **O03**                                   |         10 |
| **OUT4**             | Fan high speed  | **O04**                                   |         11 |
| **OUT5**             | Fan low speed   | **O05**                                   |         12 |
| OUT6–OUT8            | Not used        | Aligns with reserve / model-specific O06+ |          — |
| **DI04**             | High pressure   | **S04**                                   |          3 |
| CN2 / EEV            | Expansion valve | **O07** @ 2060                            |          — |

That **OEM OUT1–5 ≡ O01–O05** alignment is stronger than the Activair schematic
alone (where OUT index vs O-code was partially mismatched). Schematic candidates
below remain useful for silkscreen cross-check:

| Protocol   | Workbook        | Schematic candidate                  | Match                                            |
| ---------- | --------------- | ------------------------------------ | ------------------------------------------------ |
| bit8 O01   | Compressor      | OUT1 COMP                            | **Match** (OEM + schematic)                      |
| bit9 O02   | Heater          | HT / OUT2 (OEM: heater)              | **Match** function                               |
| bit10 O03  | 4-way           | OEM OUT3; schematic OUT4→4V          | Function match; schematic index may differ       |
| bit11 O04  | Fan high        | OEM OUT4; schematic OUT3 FM          | Function match                                   |
| bit12 O05  | Fan low / solar | OEM OUT5; schematic OUT5 P           | **Match** OEM; solar via `/01`                   |
| O07 / 2060 | EEV steps       | CN5 / EEV                            | Match telemetry                                  |
| Cycle pump | —               | schematic OUT2 PUMP on some drawings | **Gap** if present — no dedicated DHW State0 bit |

### Communications

485-A/B → WIFI (DTU / ESPHome); CN2 display; CN1 transformer.

---

## 9. Gaps and recommended experiments

1. **Full `2050`/`2051` bit sensors** on live S300 — toggle remote, defrost, heater, fan; resolve bit2/bit5 vs workbook. _(Every bit is a binary sensor since 4.4.0; bit 2 and bit 5 still need checking.)_
2. **Proxy HiTemp app** — **partially closed:** #130 shows the app requests `2050`/`2051` (not named O01–O06/S*). Still open: why lone `O03` is polled; no JADX of the bit→UI map.
3. **`2085` vs Fault1–10** when a real fault appears (Darksplat only flags non-zero; workbook has P/E bits).
4. **Photograph S300 remote terminals** vs Activair DI01/DI05 silkscreen (forums did not resolve).
5. **Pump / unused OUT** — OEM says OUT6–8 unused; schematic pump labelling still a gap if present on a given board.
6. **Diff sjtrny PDF/DOC/older XLS** against JSON (not fully done); re-check Darksplat **S02@bit1** vs `dtu_wifi` blank.
7. **Local Modbus** — Darksplat already field-verified slave 99; ESPHome `sheet: dtu_wifi` still useful for HA native path.
8. **Never** automate from FoxAir `2019` / Fairland / midas `2074+` maps on this product.
9. Watch **PC1006 / iStore** for a _new_ workbook (Allthebester still uses EVO270 extract).
10. Catalog victor orphans (1015, 1020, …, 2057–2074, L31/L32) once meanings appear.
11. Confirm whether any HiTemp account uses **`go-heating.com` / `appId` 14** (no public DHW capture yet).

---

## 10. Document history

| Date       | Note                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-11-20 | Initial comparison from esphome-hw211, victor987/hitemp, FoxAir_Control, Activair 20230302-0005, HiTemp guide.                                                                                                                                                                                                                                                                                                         |
| 2026-11-20 | **Multi-repo expansion:** merged `_research_hw211_esphome.md`, `_research_hitemp_cloud.md`, `_research_foxair_phnix.md`, `_research_github_sweep.md`. Added scorecard, full source catalog (hydazz, Mozzie-AU, tnako, VAdamec, fleuke trap, …), full 2050/2051/2085 workbook tables, sheet-diff, FoxAir conflict table, integration match matrix, appendix [`HW211_REGISTER_MAP_FULL.md`](HW211_REGISTER_MAP_FULL.md). |
| 2026-11-20 | **Second-round online merge:** `_research_github_deeper.md` (**Darksplat** bit CSVs + legacy O10–O15↔O12–O17), `_research_app_cloud_api.md` (HiTemp iOS polls `2050`/`2051`; `appId` 13/14/16), `_research_oem_manuals_web.md` (OUT1–5≡O01–O05), `_research_forums_community.md` (HA #230400 reinforcement). Strengthened bit-sensor / hide-empty-O/S recommendations.                                                 |
| 2026-11-25 | §6 updated to the 4.4.2 entities: every `2050`/`2051`/`2085` bit is a binary sensor and the named O/S entities read those bits. The `appId` 13 recommendation was replaced by the decision not to send it.                                                                                                                                                                                                             |

---

## Quick links

| Doc                                                              | Role                                   |
| ---------------------------------------------------------------- | -------------------------------------- |
| [HITEMP_PARAMETERS.md](HITEMP_PARAMETERS.md)                     | End-user / S300 observation guide      |
| [HW211_REGISTER_MAP_FULL.md](HW211_REGISTER_MAP_FULL.md)         | Full `dtu_wifi` register appendix      |
| [`_research_github_deeper.md`](_research_github_deeper.md)       | Darksplat + adjacent GitHub (round 2)  |
| [`_research_app_cloud_api.md`](_research_app_cloud_api.md)       | HiTemp poll map / appId                |
| [`_research_oem_manuals_web.md`](_research_oem_manuals_web.md)   | OEM OUT/DI/T labelling                 |
| [`_research_forums_community.md`](_research_forums_community.md) | Forums / HA #230400                    |
| Other `_research_*.md`                                           | Round-1 raw extracts; keep as evidence |
