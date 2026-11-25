<!-- Evidence extract. The summary and how it applies to this integration are in HW211_REGISTER_COMPARISON.md. -->

# Research dump: GitHub / web sweep for HW211 DHW register sources

**Date:** 2026-11-20  
**Scope:** Aggressive search for any remaining repos/docs that decode HW211 / Activair / Trianco / Indol / PHNIX **DHW** heat-pump registers or bits that prior research may have missed.  
**Constraint:** Research dump only — does **not** modify `HW211_REGISTER_COMPARISON.md`. No invented mappings.

---

## Executive verdict

No **new independent** Modbus workbook or State0/State1 bit map for HW211 DHW was found outside the already-known `sjtrny/esphome-hw211` lineage.

What _was_ newly surfaced or clarified in this sweep:

1. **`sjtrny/esphome-hw211/datasheets/`** holds more than the JSON extract — also `Evo-270-1_Modbus Map.pdf`, `Parameter and description.doc`, and an older `302020 00000028 communication protocol.xls` (same repo; verify whether comparison doc already scraped these binary files).
2. Several **forks / siblings** of known repos (identical or trimmed; no new bit semantics).
3. Several **heating / pool / WarmLink** PHNIX-family sources that share address numbers like `2050` but mean **different** things (trap / do-not-merge).
4. Community observations that reinforce known `2050` bit 8 = compressor (`aquatemp#108`, HA forum).

---

## Search methods used

| Channel             | Queries / actions                                                                                                                      |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| GitHub code / repos | `HW211`, `dtu_wifi`, `EVO270`, `mode_real`+`2050`, `State0`+`2050`, `20230302-0005`, Activair/Trianco/Indol/PHNIX, `EVO270-1_MODBUS`   |
| GitHub forks API    | forks of sjtrny, echopin664, dosordie, Allthebester, radical-squared, victor987                                                        |
| Web search          | HW211 Modbus/WIFI/DTU; Trianco Activair S300/S200; Indol PV300/EVOSONIC; Chinese OEM; Gitee; `2050`/`2051`/`2085`; State0/State1 bit 8 |
| Local repo          | `docs/`, `CHANGELOG.md`, `README.md` for leftover notes / URLs                                                                         |
| Agent transcripts   | skimmed `github.com` links under `/home/john/.cursor/projects/home-john-repos-hitemp/agent-transcripts/`                               |

**Rate limit note:** GitHub code search returned HTTP 403 mid-sweep for some `xlsx` / filename queries; those were covered via raw file fetches and prior hits instead.

---

## Already-known sources (verified; forks/deltas)

### sjtrny/esphome-hw211 — **HW211 DHW — High**

- **URL:** https://github.com/sjtrny/esphome-hw211
- **Contains:** ESPHome external component; `protocol/hw211_modbus.json` from official EVO270-1 workbook; sheets `dtu_wifi` (slave **99**) and `hw211`; bitfields for `2050`/`2051`/`2085`.
- **Datasheets directory (verify vs prior extract):**
  - `datasheets/EVO270-1_MODBUS communication_protocol_6.5.25.xlsx`
  - `datasheets/Evo-270-1_Modbus Map.pdf`
  - `datasheets/Parameter and description.doc`
  - `datasheets/302020 00000028 communication protocol.xls`
- **Blog:** https://sjtrny.com/posts/2026-06-03-esphome-hw211-component/
- **Forks with no delta:**
  - https://github.com/Mozzie-AU/esphome-hw211 — identical to upstream
  - https://github.com/hydazz/esphome-hw211 — identical to upstream

#### High-value register table (official `dtu_wifi` sheet, from JSON)

**Notable addresses:** `status0`=`2050`, `status1`=`2051`, `fault0`=`2085`, power=`1011`, operation_mode=`1013`, target=`1104`.

**`2050` State0 — Slave component status (Binary)**

| Bit | Code | Meaning (workbook text)                 |
| --- | ---- | --------------------------------------- |
| 0   | S01  | Remote on/off switch (1=OP, 0=CL)       |
| 2   | S03  | Low pressure switch (1=OP, 0=CL)        |
| 3   | S04  | High pressure switch (1=OP, 0=CL)       |
| 4   | S05  | Shortened time signal (1=OP, 0=CL)      |
| 5   | S06  | External heat source switch             |
| 6–7 | —    | Reserve                                 |
| 8   | O01  | Compressor (0=OFF, 1=ON)                |
| 9   | O02  | Electrical heater (0=OFF, 1=ON)         |
| 10  | O03  | 4-way valve (0=OFF, 1=ON)               |
| 11  | O04  | Fan high speed (0=OFF, 1=ON)            |
| 12  | O05  | Fan low speed / solar pump              |
| 13  | O06  | Reserve / solar pump / solar valve pump |
| 14  | O12  | Electric anode 3V_DE                    |
| 15  | O13  | Electric anode MV_DE                    |

**`2051` State1 — Slave function status**

| Bit | Code | Meaning                                 |
| --- | ---- | --------------------------------------- |
| 0   | O14  | Shutdown (0=NO, 1=YES)                  |
| 1   | O15  | DTU & WIFI online (0=NO, 1=YES)         |
| 2   | O16  | Defrost (0=NO, 1=YES)                   |
| 3   | O17  | Hot water function active (0=NO, 1=YES) |

**`2085` Fault0 — Failure (W10)**

| Bit | Fault                            |
| --- | -------------------------------- |
| 0   | Ambient sensor failure P04       |
| 1   | Bottom sensor failure P01        |
| 2   | Top sensor failure P02           |
| 3   | Coil sensor failure P05          |
| 4   | Suction sensor failure P07       |
| 5   | Solar sensor failure P034        |
| 8   | High pressure protection E01     |
| 9   | Low pressure protection E02      |
| 13  | Tank antifreezing protection E09 |

Note: On the **`hw211` sheet**, addresses `2050`/`2051` exist but descriptions are **blank** in the JSON (DTU sheet is the useful one for cloud/DTU naming).

---

### Allthebester/esphome-iStore-R290 — **HW211 DHW sibling — High (same lineage)**

- **URL:** https://github.com/Allthebester/esphome-iStore-R290
- **Parent:** sjtrny/esphome-hw211
- **Delta:** 1 commit ahead / 10 behind; only file change `protocol/hw211_modbus.json`.
- **Difference:** Trimmed JSON — `dtu_wifi` **99** named rows vs upstream **226** total (many blanks removed); State0/State1/Fault0 bit text **shortened**, not expanded. No new bits.
- **iStore / PC1006 note:** README / HA forum discuss newer iStore boards (PC1006 / Chico) as possible successors; **no separate register map** published in this repo beyond the HW211 JSON.

Allthebester shortened excerpt (same bit numbers, less detail):

```
2050 State0: Bit0 Remote ON/OFF; Bit2 LP; Bit3 HP; Bit8 Compressor; Bit9 E-heater;
             Bit10 4-way; Bit11 Fan high; Bit12 Fan low
2051 State1: Bit0 Shutdown; Bit1 DTU/WIFI online; Bit2 Defrost; Bit3 Hot water active
2085 Fault0: Bit0 Ambient; Bit1 Bottom; Bit2 Top; Bit3 Coil; Bit4 Suction; Bit5 Solar;
             Bit8 HP protect; Bit9 LP protect; Bit13 Tank antifreeze
```

---

### echopin664/EVO270-1-HWS — **HW211 DHW hardware — Medium (wiring only)**

- **URL:** https://github.com/echopin664/EVO270-1-HWS
- **Contains:** Atom S3 + RS485 wiring to HW211 Wi‑Fi connector (GND / 12V / A / B); ESPHome YAML; **no** independent register workbook.
- **Fork:** https://github.com/j14s/EVO270-1-HWS — 1 commit ahead (“update for pool hp”); GPIO rename only; **no** new registers.

---

### victor987/hitemp — **HiTemp cloud scan / Indol PV300 same product ID — High (aliases)**

- **URL:** https://github.com/victor987/hitemp
- **Contains:** `DEVICE_PARAMETERS.md` full scan for product `1245226668902080512`; `mode_real`↔`1013`; packed `2050`/`2051`/`2085`.
- **Excerpt (observed, not workbook):**

| Code        | Example / note                                                                            |
| ----------- | ----------------------------------------------------------------------------------------- |
| `mode_real` | alias **1013**; 0 Intelligent, 2 Eco, 3 Hybrid, 4 Fast heating                            |
| `2050`      | bitmask; author notes bit8=compressor, bit9=e-heater; bits 2+5 “always set” in their scan |
| `2051`      | flags word                                                                                |
| `2085`      | flags (often clear)                                                                       |

---

### goglecm/hitemp (this project / maintained aquatemp fork) — **HiTemp — High for product docs**

- **URL:** https://github.com/goglecm/hitemp
- **Contains:** Live Trianco S300 observations; entities for `mode_real` **and** `2050`/`2051`/`2085`; points at comparison doc.
- **Repos that mention both `mode_real` and `2050`:** this repo + victor987 (above). No third independent decoder found.

---

### dosordie/FoxAir_Control — **Heating PHNIX / FoxAir — High for heating; not HW211 DHW**

- **URL:** https://github.com/dosordie/FoxAir_Control
- **Contains:** WarmLink/FoxAir register JSON; packed outputs around **`2019`**, not HW211 State0.
- **Fork:** https://github.com/Gazki/FoxAir_Control — behind upstream; no new map.

---

### radical-squared/aquatemp — **Cloud HA — Medium; #108 useful for 2050**

- **URL:** https://github.com/radical-squared/aquatemp
- **Issue #108:** https://github.com/radical-squared/aquatemp/issues/108
  - Community (EvoHeat270 / HiTemp): O01–O06 empty in cloud API; live in code **`2050`**.
  - Example values: compressor+fan off `0000000000110000`; on `0000100100110000`.
  - Commenter claimed bits 5–10 = O01–O06 (indexing **partially wrong** vs workbook; workbook puts compressor at **bit 8**).
- **Issue #103:** HiTemp mapping / `mode_real` → Mode discussion; no new Modbus bit table.
- **Forks of interest (cloud product mapping, not Modbus workbook):**
  - https://github.com/ip0her/aquatemp (`Custom-component` branch) — HiTemp/Termobrasa fan/mode fixes
  - https://github.com/arthuriansoft/aquatemp (`trianco` branch) — WarmLink/Trianco **heating** product IDs
  - https://github.com/zyznos321/warmlink — WarmLink product IDs
  - https://github.com/dst6se/aquatemp — original cloud protocol basis (known)

---

## NEW / newly catalogued sources

Classification: **NEW** = not in the user’s “already known” list as a named URL, even if related. Confidence and family noted.

### 1. tnako/ha-foxair — **Heating FoxAir/PHNIX Modbus — High for heating; not HW211 DHW**

- **URL:** https://github.com/tnako/ha-foxair
- **Contains:** HA integration over Modbus TCP; register metadata derived from **dosordie/FoxAir_Control** (`foxair_phnix_registers.json`, bitfield tools).
- **Family:** Space-heating FoxAir / PHNIX boards (slave 1, EW11), not HW211 DHW DTU sheet.
- **Confidence:** High as a packaged FoxAir map; **do not** merge bit meanings into S300 State0.

### 2. fleuke/VBIV-Fairland-Norsup-ha — **Pool PC1004 — Medium; address collision trap**

- **URL:** https://github.com/fleuke/VBIV-Fairland-Norsup-ha
- **Contains:** Verified Modbus map for VBIV / Fairland / Norsup **PC1004** pool pumps (AquaTemp WiFi ecosystem, different mainboard).
- **Critical excerpt:**

| Reg  | Meaning on PC1004 (fleuke)     | HW211 DHW `dtu_wifi`     |
| ---- | ------------------------------ | ------------------------ |
| 2019 | Output bits (bit0=comp, …)     | Ambient `T01` on DHW map |
| 2050 | **T06 Discharge gas** (°C×0.1) | **State0** bitfield      |

- **Family:** Pool / PC1004 — **unrelated** to HW211 State0 despite shared AquaTemp branding and overlapping addresses.

### 3. vossim/ha_aquatemp — **Pool AquaTemp BLE — Low for HW211 DHW**

- **URL:** https://github.com/vossim/ha_aquatemp
- **Contains:** `BLE_PROTOCOL_SPEC.md` — Modbus-over-BLE ASCII hex; slave **0x63 (99)**; FC03 read of registers **7–51** (45 regs); cool/heat pool modes; mentions device types including `pc1006`.
- **Does not** document `2050`/`2051`/`2085` State0/State1/Fault0.
- **Family:** Pool / BLE gateway map — adjacent ecosystem, **not** EVO270 DHW workbook.

### 4. WarmLink cloud integrations — **Heating Linked-Go cloud — Medium; not HW211 DHW bits**

| URL                                                           | Notes                                                             |
| ------------------------------------------------------------- | ----------------------------------------------------------------- |
| https://github.com/VAdamec/WarmLink                           | Cloud codes (Power, Mode, Fault*, T*, SG*); no State0             |
| https://github.com/srbjessen/ha-warmlink                      | Large WarmLink sensor set (Zealux/Alsavo/Fairland R290)           |
| https://github.com/00gtw00/homeassistant_warmlink             | Simpler WarmLink cloud climate                                    |
| https://community.home-assistant.io/t/warmlink-support/855025 | Forum thread linking the above + PHNIX Modbus YAML (heating regs) |

### 5. radical-squared/aquatemp#99 + arthuriansoft — **WarmLink/Trianco heating — Medium**

- **URL:** https://github.com/radical-squared/aquatemp/issues/99
- **Contains:** WarmLink API notes; mention of PHNIX GreenTherm **Modbus RTU** technical manual (not attached publicly); community Modbus snippets with **`2019` bit9 = O10 DHW 3-way** (heating family).
- **Fork:** https://github.com/arthuriansoft/aquatemp/tree/trianco — Trianco heating product mapping for aquatemp cloud.
- **Family:** Heating / WarmLink — **not** HW211 DHW State0.

### 6. MelPump / Planet Devices Trianco Activair — **Commercial adapter — Empty for registers**

- **URL:** https://melpump.com/homepage/en/compatibility/trianco
- **Contains:** Claims Modbus hardware adapter support for Trianco Activair; **no public register map**.

### 7. Trianco Activair Indoor 5/7 kW control-panel Modbus — **Different product — Unrelated**

- **URL:** Trianco download “Activair Indoor Heatpump Control Panel” (e.g. manuals on trianco.co.uk)
- **Contains:** PF6 enables Modbus TA; supervisor register **address 10** on/off for heating/cooling call.
- **Family:** Indoor Activair R32-style controller — **not** HW211 HiTemp DHW `dtu_wifi` map.

### 8. HA forum Aqua Temp controller thread — **Community — Medium (confirms known)**

- **URL:** https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400
- **Contains:** Origin story for esphome-hw211; ESPHome bit8/`0x0100` on `2050` compressor examples; PC1006 board photos; wiring discussion.
- **No** independent full State0 table beyond what sjtrny extracted.

### 9. Pool PC1002 sources — **Unrelated**

- https://community.home-assistant.io/t/hayward-oasis-and-other-generic-pool-heatpump-using-pc1002/733827
- https://github.com/vamadou/hayward
- Oasis PC1002 PDF maps — different board family.

### 10. PHNIX Greentherm / Gonzik Modbus forum — **Heating PHNIX — Medium for heating**

- **URL:** https://community.home-assistant.io/t/modbus-heatpump-gonzik/853668
- **Contains:** Heating Modbus addresses (1011 power, 1156+, 207x fans/flow); references a 2021 PHNIX Modbus doc **not published** in-thread.
- **Family:** Heating — not HW211 DHW State0.

### 11. Chico / PC1006 OEM page — **Hardware lead only — Low**

- Mentioned in HA forum: https://chico-future.com (OEM hybrid heat pump PCB / PC1006).
- **No** public Modbus register table found in this sweep.

### 12. Export-record confirmation HW211 is PHNIX DHW controller — **Context only**

- Trade listing: Guangdong Phnix ships “central controller **HW211**” for water-heater production (Rheem Vietnam, etc.). Confirms OEM naming; **no** register map.

---

## Sources searched but empty / no HW211 DHW register decode

| Query / lead                                                      | Result                                                                               |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Gitee `PHNIX` / `HW211` / `dtu_wifi`                              | No PHNIX Modbus xlsx mirror found; generic DTU/Modbus projects only                  |
| `CODE 20230302-0005` on GitHub/web                                | **No public hit**; only local comparison doc (schematic treated as attached/offline) |
| Chinese OEM manuals with `2050`/`2051`/`2085` HW211 text          | No freely indexed PDF/xlsx beyond sjtrny datasheets                                  |
| Indol PV300 / EVOSONIC dedicated Modbus PDF                       | No dedicated public protocol; only victor987 cloud scan                              |
| Trianco Activair **S200** Modbus                                  | No register map found                                                                |
| Repos named `HW211` (vanekKiselev, VerKse, homework clones, etc.) | Unrelated (iOS homework / radio / textures)                                          |
| NTE Electronics “HW211” datasheet                                 | Unrelated resistor part                                                              |
| Climate-model “Phoenix_2050_*.xlsx”                               | Unrelated                                                                            |
| Gebwell / Vaillant / Triple Solar / Daikin Modbus                 | Unrelated heat-pump brands                                                           |
| Fairland/Norsup `2050`                                            | Exists but means **T06**, not State0                                                 |

---

## Local repo leftovers (`/home/john/repos/hitemp`)

| Path                                       | Finding                                                                                                                           |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `docs/HW211_REGISTER_COMPARISON.md`        | Already lists known sources; schematic `20230302-0005` section; **not edited** this sweep                                         |
| `docs/HITEMP_PARAMETERS.md`                | Live `2050`/`2051`/`2085` / `mode_real` notes                                                                                     |
| `CHANGELOG.md`                             | Migration to goglecm/hitemp; aquatemp history; no extra external Modbus URLs                                                      |
| `README.md`                                | Points at HiTemp guide / aquatemp lineage                                                                                         |
| Leftover `_research_*.md` before this file | None other under `docs/`                                                                                                          |
| Agent transcripts                          | URLs already in known set + WarmLink/FoxAir forks (`tnako/ha-foxair`, `VAdamec/WarmLink`, `dst6se/aquatemp`, Mozzie/hydazz forks) |

---

## `mode_real` + `2050` co-occurrence

| Source                                             | Both present?                                             |
| -------------------------------------------------- | --------------------------------------------------------- |
| goglecm/hitemp (this repo)                         | Yes — entities + guide                                    |
| victor987/hitemp                                   | Yes — DEVICE_PARAMETERS scan                              |
| sjtrny JSON                                        | `1013` operation mode + `2050` State0 (named differently) |
| Other GitHub hits for literal `mode_real` + `2050` | Noise / unrelated (WiFi mode scripts, ROS, etc.)          |

---

## High-value register tables discovered

1. **Primary (already known, re-verified):** sjtrny `dtu_wifi` State0/State1/Fault0 — full bit tables above.
2. **Same bits, shorter text:** Allthebester trimmed JSON — no new semantics.
3. **Cloud confirmation:** aquatemp#108 + HA forum bit8/`0x0100` compressor on `2050`.
4. **Trap tables (do not merge into HW211 DHW):**
   - fleuke PC1004: `2050` = discharge temp; `2019` = outputs
   - FoxAir / tnako / WarmLink heating: packed status on **`2019`/`2034`**, not State0
5. **sjtrny binary datasheets** (`pdf` / `doc` / older `xls`) — **highest priority follow-up** if not already transcribed into the comparison doc.

---

## Suggested follow-ups (for later; not done here)

1. Diff/extract `Evo-270-1_Modbus Map.pdf` and `Parameter and description.doc` from sjtrny datasheets against JSON.
2. Keep FoxAir/WarmLink/PC1004 maps in a **separate** “heating/pool” appendix; never overlay onto S300 `2050`.
3. If Activair schematic `20230302-0005` can be published or linked, attach URL in comparison doc (currently offline-only).
4. Watch Chico PC1006 / iStore successor for a **new** workbook; none public yet.

---

## Quick return summary

- **Path written:** `/home/john/repos/hitemp/docs/_research_github_sweep.md`
- **NEW catalogued URLs (bullets):** see section “NEW / newly catalogued sources” (tnako, fleuke, vossim, WarmLink suite, arthuriansoft, MelPump, HA forum, Gonzik, Chico, etc.)
- **No new HW211 DHW State0 workbook** beyond sjtrny lineage
- **Highest-value re-find:** sjtrny `datasheets/` multi-file bundle + full State0/1/Fault0 tables re-copied above
