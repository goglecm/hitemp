<!-- Evidence extract. The summary and how it applies to this integration are in HW211_REGISTER_COMPARISON.md. -->

# Research dump: deeper GitHub / code-host search (additive only)

**Date:** 2026-11-20  
**Scope:** Second-pass host search for **any remaining** HW211 / HiTemp / Activair / Linked-Go **DHW register maps** beyond the known set and beyond prior dumps in `docs/_research_*.md`.  
**Constraint:** Research only — does **not** modify `HW211_REGISTER_COMPARISON.md`. No inventing mappings.  
**Rule:** List **NEW / additive** finds; known set verified for deltas only.

---

## Known set (delta check only)

| Source                                             | Delta vs prior dumps                                                                                                      |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| sjtrny/esphome-hw211 (+ hydazz, Mozzie-AU)         | Forks still identical lineage; `COMPONENT_BIT_NAMES` / `hw211_modbus.json` still **only** this tree on GitHub code search |
| Allthebester/esphome-iStore-R290                   | Known trimmed JSON; no new bits this pass                                                                                 |
| echopin664/EVO270-1-HWS                            | Known wiring; still no independent workbook                                                                               |
| victor987/hitemp, goglecm/hitemp                   | Known cloud scans / entities                                                                                              |
| radical-squared/aquatemp (+ issues #103/#108/#99)  | Known; no new Modbus workbook in issues/PRs this pass                                                                     |
| dosordie/FoxAir_Control, tnako/ha-foxair           | Known heating `2019`/`2034` maps                                                                                          |
| VAdamec/WarmLink (+ forks)                         | Known cloud codes                                                                                                         |
| fleuke/VBIV-Fairland-Norsup-ha, vossim/ha_aquatemp | Known pool traps                                                                                                          |

**Prior dumps skimmed (do not re-copy):** `_research_github_sweep.md`, `_research_hw211_esphome.md`, `_research_foxair_phnix.md`, `_research_hitemp_cloud.md`.

---

## Executive verdict

**One major NEW HW211 DHW implementation** was found that was missing from the known URL list:

1. **`Darksplat/EVOHeat-EVO270-ESP32-Modbus`** — field-verified Arduino + MQTT local control of EVO270-1 / HW211 (slave **99**), with explicit `2050`/`2051`/`2085` bit tables and allow-listed writes. Credits sjtrny JSON; adds commissioning protocol notes (clock mailbox, 1012 vs 1013) and documents **legacy Aqua Temp O-code renumbering** vs workbook labels.

No second independent OEM workbook (xlsx/PDF) beyond the sjtrny datasheets lineage appeared on GitHub, Gitee, GitCode, GitLab, or Bitbucket.

Several **additive adjacent** repos/docs (pool Fairland, ioBroker Midas, Sibotherm R290 BMS PDF, richer WarmLink HA) share Linked-Go / TEMP1 / address-number collisions but are **not** HW211 DHW `dtu_wifi` maps.

---

## Search methods (this pass)

| Channel                 | Queries / actions                                                                                                                                                                                                                                                             |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `gh search code` / REST | `dtu_wifi`, `hw211_modbus.json`, `COMPONENT_BIT_NAMES`, `mode_real`, `1245226668902080512`, `app_heartbeat`, `23205`, `150143`, `EVO270`, `HW211`, `State0`/`State1`, `O01`+compressor, `cloud.linked-go.com`, `getDataByCode`, `protocalCodes`, Fairland/Alsavo/PC1006, etc. |
| `gh` / REST repo search | `HW211 OR EVO270 OR esphome-hw211`; aquatemp / warmlink / foxair / midas / fairland names                                                                                                                                                                                     |
| Forks API               | sjtrny (3 forks), radical-squared/aquatemp (~38), echopin664                                                                                                                                                                                                                  |
| Web                     | Gitee/GitCode/GitLab/Bitbucket HW211/EVO270; Sibotherm Modbus-R290; ioBroker midas; Fairland ESPHome lineage                                                                                                                                                                  |
| Raw GitHub              | Full extract of Darksplat CSVs/docs; MiRo1310 `axiosParameter.ts`; King007t Fairland README                                                                                                                                                                                   |

**Rate limit:** Mid-pass GitHub code-search 403; covered via raw fetches + repo search + web.

---

## NEW / additive sources

### 1. Darksplat/EVOHeat-EVO270-ESP32-Modbus — **HW211 DHW — High (NEW primary)**

- **URL:** https://github.com/Darksplat/EVOHeat-EVO270-ESP32-Modbus
- **Applicability:** **HW211 DHW** (EVOHeat EVO270-1), local Modbus RTU slave **99**, Waveshare ESP32-S3-RS485-CAN, Arduino firmware + MQTT HA (not ESPHome production).
- **Relation to known set:** Credits `sjtrny/esphome-hw211` + `echopin664/EVO270-1-HWS`; **not** a fork of either. Independent firmware with field-verified writes on two units.
- **Updated:** 2026-10-29 (main). Tip files include `data/status_bits.csv`, `data/core_registers.csv`, `data/evo270_legacy_entity_map.csv`, `docs/MODBUS_PROTOCOL.md`, `docs/REGISTER_MAP.md`.

#### Transport (matches `dtu_wifi`)

| Parameter  | Value                                                            |
| ---------- | ---------------------------------------------------------------- |
| Modbus RTU | 9600 8N1                                                         |
| Slave      | 99 (`0x63`)                                                      |
| FC         | 03 read, 06 allow-listed write, 16 clock mailbox                 |
| Decode     | RAW / TEMP / TEMP1 `(x-60)*0.5` / DIGI2×10 / DIGI4×5 / DIGI7×0.5 |

#### Core registers (`data/core_registers.csv`)

|       Reg | Meaning                                            | Access in project                                                               |
| --------: | -------------------------------------------------- | ------------------------------------------------------------------------------- |
|      1011 | Power                                              | verified-write                                                                  |
|  **1012** | **Requested** operation mode                       | verified-write — 0 Intelligent, 2 Economic, 3 Hybrid, 4 High Demand, 7 Vacation |
|  **1013** | **Actual** operation mode                          | read-only (same value set)                                                      |
|      1104 | Target temp R01                                    | verified-write                                                                  |
| 1129–1141 | Vacation + Timer 1/2                               | verified-write                                                                  |
| 1151–1156 | Clock **command/apply mailbox** (not live clock)   | verified-command                                                                |
| 2019–2025 | T01–T06, T10                                       | read-only                                                                       |
|  **2050** | Status0 bitfield                                   | read-only                                                                       |
|  **2051** | Status1 bitfield                                   | read-only                                                                       |
|  **2085** | Fault0 bitfield                                    | read-only (non-zero ⇒ fault active; **no per-bit fault table** in CSV)          |
| 2060–2062 | O07 EEV / O08 compressor hours / O09 booster hours | read-only                                                                       |

**Cloud conflict note:** HiTemp cloud `mode_real` aliases **1013** (actual). Darksplat separates **1012 requested** vs **1013 actual** — additive protocol clarity vs workbook/cloud naming.

#### Status bits (`data/status_bits.csv`) — full table

**`2050` Status0**

| Bit | Legacy code | Legacy name                           |
| --: | ----------- | ------------------------------------- |
|   0 | S01         | Remote ON/OFF switch                  |
|   1 | S02         | Over heat protection switch           |
|   2 | S03         | Low pressure switch                   |
|   3 | S04         | High pressure switch                  |
|   4 | S05         | Accelerate the running time of heater |
|   5 | S06         | Second heating source                 |
|   8 | O01         | Compressor                            |
|   9 | O02         | Electrical heater                     |
|  10 | O03         | 4-way valve                           |
|  11 | O04         | Fan high speed                        |
|  12 | O05         | Fan low speed                         |
|  13 | O06         | Reserve/solar pump/solar valve pump   |
|  14 | O10         | 3V_DE                                 |
|  15 | O11         | MV_DE                                 |

**`2051` Status1**

| Bit | Legacy code | Legacy name                      |
| --: | ----------- | -------------------------------- |
|   0 | O12         | Shutdown                         |
|   1 | O13         | DTU/Wi-Fi online                 |
|   2 | O14         | Defrost                          |
|   3 | O15         | High-temperature hot-water stage |

#### Conflicts / deltas vs sjtrny `dtu_wifi` workbook labels

Bit **positions** for compressor/heater/4-way/fans and S01/S03–S06 match the workbook. Naming differs:

| Topic           | Darksplat (legacy Aqua Temp codes) | sjtrny `dtu_wifi` workbook                                                |
| --------------- | ---------------------------------- | ------------------------------------------------------------------------- |
| 2050 bit 1      | **S02** Over heat protection       | Often blank / reserve in JSON extract                                     |
| 2050 bits 14–15 | Legacy **O10/O11** (3V_DE / MV_DE) | Workbook **O12/O13** electric anodes                                      |
| 2051 bits 0–3   | Legacy **O12–O15**                 | Workbook **O14–O17** (shutdown / DTU online / defrost / hot-water active) |
| 2051 bit 3 text | “High-temperature hot-water stage” | “Hot water function active” (same bit)                                    |
| Fault0 `2085`   | Presence only (non-zero)           | Full P/E bit table in workbook                                            |

CSV notes explicitly: _“Legacy Aqua Temp numbering preserved; HW211 protocol calls this … O12/O14 …”_ — so Darksplat is documenting **cloud/legacy code aliases**, not a second physical bit layout.

#### Other additive protocol notes (not in prior known-list extracts)

- Clock: **1151 = M11 apply**; **1152–1156** minute/hour/day/month/year — mailbox, not readable live clock; NTP push used instead.
- Solar block **1080–1090 / N01–N11** = solar-thermal, not PV.
- ESPHome 2026.8.1 on this Waveshare path: partial `FE` then timeout; Arduino + GPIO21 DE/RE succeeded (`docs/ESPHOME_FAILURE.md`).
- Known-good FC03 T01@2019: `TX 63 03 07 E3 00 01 7C CA` → raw 97 → 18.5 °C TEMP1.

---

### 2. MiRo1310/ioBroker.midas-aquatemp — **Pool Linked-Go cloud — Medium; no State0 map**

- **URL:** https://github.com/MiRo1310/ioBroker.midas-aquatemp
- **Applicability:** **Pool** Midas/Poolsana via Linked-Go cloud (API levels 1–3). Confirmed devices are pool heaters, not Trianco S300.
- **Why listed:** Discovery product-ID list **includes** `1245226668902080512` (HiTemp DHW) alongside pool IDs — useful as a cloud client cross-check, **not** a Modbus workbook.
- **Codes polled** (`src/lib/axiosParameter.ts`): Power, Mode, Manual-mute, Set_Temp, R01–R03, R08–R11, T01–T07/T14/T17, S3/S03, **1158/1159**, **2074–2077** (pool-style fault words — cf. Fairland/PC1004 family), F17, H02/H03.
- **Missing:** no `2050`/`2051`/`2085`, no `mode_real`, no `app_heartbeat`/`23205`, no bit tables.
- **Conflict with `dtu_wifi`:** none direct; do **not** treat midas `2074+` or pool `T06` semantics as HW211 State0.

Forum precursor: https://forum.iobroker.net/topic/54765/javascript-midas-aquatemp-poolheizung (same product-ID list).

---

### 3. Fairland / InverX pool Modbus lineage — **Pool — Low for HW211; TEMP1 trap**

| URL                                                         | Role                                                       |
| ----------------------------------------------------------- | ---------------------------------------------------------- |
| https://github.com/King007t/esphome-fairland-heatpump       | Packaged ESPHome; MWH216/MWH298; full coil/DI/IR/HR tables |
| https://github.com/rstcologne/ESP-Home-Fairland-Heatpump    | Earlier ESPHome Fairland                                   |
| https://github.com/spdr870/fairland_iphcr45_modbus          | IPHCR45 HA Modbus YAML                                     |
| https://github.com/Locodice67/Pool-Heat-Pump-IPHCR45-Modbus | HA custom component wrapping same map                      |

**Applicability:** Pool boards (slave **1**, low coil/IR addresses). **Unrelated** to HW211 `dtu_wifi` addresses 1011/2050/….

**Shared OEM scaling (trap, not merge):** temperatures use **type 1** `°C = (raw − 60) / 2` — same formula as HW211 **TEMP1**, different address space. King007t EEV is **IR 13**, not HW211 `2060`.

Does **not** conflict with fleuke’s PC1004 `2050=T06` trap; this lineage mostly uses **IR 3–5** for temps, not MAIN 2050.

---

### 4. Sibotherm Modbus-R290 PDF — **Heating BMS / wired controller — Medium heating; not HW211 DHW**

- **URL:** https://www.sibotherm.com/wp-content/uploads/Modbus-R290.pdf
- **Applicability:** R290 **space-heating** wired-controller Modbus (RS-485, 9600 8N1); PLC-style addresses **40001+** (power bitfield, mode, zone/DHW setpoints, SG, etc.).
- **Conflict with `dtu_wifi`:** **hard** if anyone overlays 4000x ↔ MAIN 1xxx/2xxx. No `2050` State0. Adjacent to WarmLink/PHNIX heating community (Gonzik / Greentherm threads), not EVO270 DHW.

---

### 5. srbjessen/ha-warmlink — **Heating WarmLink cloud — Medium; no HW211 bits**

- **URL:** https://github.com/srbjessen/ha-warmlink
- **Applicability:** Zealux / WarmLink / WarmFlow Zeno cloud; **391** named codes (`codes.json`); fault E001–E045 style.
- **vs known VAdamec/WarmLink / 00gtw00:** larger catalog; still **no** `2050`/`2051`/`2085` State0 decode, no Modbus MAIN map.
- **Conflict:** heating cloud O/S packing ≠ HW211 DHW packed `2050` (same story as FoxAir).

---

### 6. Other aquatemp forks surfaced (cloud only; no new Modbus workbook)

Forks API (~38) includes many mirrors. **Not** deep-read unless they publish register JSON. Notable names already in prior dumps: goglecm/hitemp, victor987/aquatemp, ip0her, dmkent, arthuriansoft, zyznos321/warmlink, PavelD/ha-aquatemp, sjtrny/aquatemp, dst6se (upstream lineage).

No fork in this pass published a new `hw211_modbus.json` or State0 bit workbook.

---

## Targeted query results (empty / noise)

| Query                                                                          | Result                                                                                                                                                             |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `protocol/hw211_modbus.json` / `COMPONENT_BIT_NAMES` / `BIT_NAMES["dtu_wifi"]` | **Only** sjtrny (+ forks via clone, not separate trees)                                                                                                            |
| `1245226668902080512`                                                          | radical-squared/aquatemp + MiRo1310 midas (+ known hitemp forks)                                                                                                   |
| `150143` Trianco product                                                       | **No** heat-pump repo hit                                                                                                                                          |
| `app_heartbeat` + `23205`                                                      | No clean public code hit beyond prior FoxAir docs this pass (search noisy / rate-limited); midas/WarmLink HA trees do **not** expose it in indexed sources checked |
| `State0`/`State1` + EEV ESPHome                                                | Hits are Darksplat Status0 naming + unrelated brands; EEV@2060 only in HW211 lineage                                                                               |
| Gitee / GitCode                                                                | No EVO270/HW211/`dtu_wifi` Modbus xlsx mirror                                                                                                                      |
| GitLab / Bitbucket                                                             | No HW211/EVO270 register repos                                                                                                                                     |
| Repo name `HW211`                                                              | Mostly unrelated homework (vanekKiselev, VerKse, …)                                                                                                                |
| Mosibi Midea / Samsung MIM / LG / Lambda / Immergas Magis                      | Unrelated brand maps                                                                                                                                               |

---

## aquatemp issues/PRs mentioning HiTemp registers (skim)

Already covered in prior dumps; no **new** Modbus bit workbook:

| Issue/PR | Note                                                |
| -------- | --------------------------------------------------- |
| #108     | `2050` binary string; O01–O06 empty in API — known  |
| #103     | HiTemp mapping / mode_real — known                  |
| #123     | EVO270-1 power/mode OFF bug — mapping, not new bits |
| #99      | WarmLink heating — known                            |
| PR #110  | HiTemp mapping fix — known                          |

---

## Register-extract summary (NEW only)

| Source                | Family        | Extract worth keeping                                                                                                                              |
| --------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Darksplat**         | HW211 DHW     | Full **2050/2051** bit table; core regs; **1012 vs 1013**; clock mailbox **1151–1156**; TEMP1/DIGI formulas; legacy O-code ↔ workbook O12–O17 note |
| MiRo1310 midas        | Pool cloud    | Product-ID list + cloud code list (incl. 1158, 2074–2077); **no** State0                                                                           |
| King007t Fairland     | Pool Modbus   | Low-address coil/DI/IR/HR + TEMP1 formula; **not** 2050 State0                                                                                     |
| Sibotherm R290 PDF    | Heating BMS   | PLC 40001+ map; **not** MAIN 2050                                                                                                                  |
| srbjessen ha-warmlink | Heating cloud | Large named-code set; **not** HW211 bits                                                                                                           |

---

## Conflicts with `dtu_wifi` (additive emphasis)

1. **Darksplat legacy O10–O15 labels ≠ workbook O12–O17** — same bits, different code numbers; prefer workbook labels for comparison doc; keep Darksplat as alias/field confirmation.
2. **Darksplat S02 @ bit 1** — fills a slot often blank in JSON extract; treat as **field/legacy**, verify against xlsx before promoting.
3. **Fairland/Midas/Sibotherm/WarmLink** — do not merge addresses or packed words into S300 State0 (reinforces prior FoxAir/PC1004 traps).
4. **1012 vs 1013** — requested vs actual mode; cloud `mode_real` aligns with **1013**.

---

## Quick return

- **Path:** `/home/john/repos/hitemp/docs/_research_github_deeper.md`
- **NEW repos/files:**
  - **Darksplat/EVOHeat-EVO270-ESP32-Modbus** (`data/status_bits.csv`, `data/core_registers.csv`, `data/evo270_legacy_entity_map.csv`, `docs/*`)
  - MiRo1310/ioBroker.midas-aquatemp (`axiosParameter.ts` product IDs + codes)
  - King007t / rstcologne / spdr870 / Locodice67 Fairland pool maps
  - Sibotherm `Modbus-R290.pdf`
  - srbjessen/ha-warmlink (expanded WarmLink cloud)
- **Register extracts:** Darksplat full State0/State1 bits + core/control regs summarized above; no new OEM Fault0 bit table beyond sjtrny workbook.
- **Bottom line:** Still **one** public workbook lineage (sjtrny); Darksplat is the important **new field-verified** HW211 DHW implementation with explicit bit CSVs and protocol deltas.
