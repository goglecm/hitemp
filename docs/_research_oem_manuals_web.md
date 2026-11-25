<!-- Evidence extract. The summary and how it applies to this integration are in HW211_REGISTER_COMPARISON.md. -->

# Research dump: OEM manuals / datasheets / vendor docs (web, not only GitHub)

**Date:** 2026-11-20  
**Scope:** Online OEM manuals, datasheets, ManualsLib/manufacturer PDFs, Chinese vendor pages, Gitee/gitcode/CSDN for **HW211 / Trianco Activair / PHNIX DHW** register knowledge.  
**Constraint:** Research dump only — does **not** modify `HW211_REGISTER_COMPARISON.md`. No invented Modbus addresses.  
**Known baseline:** `sjtrny/esphome-hw211` EVO270-1 workbook (`dtu_wifi` sheet) already maps Power / Mode / T01–T06 / R… / O… / S… / D/E/G/H/L/M/N / packed `2050`/`2051` / `2085`.

---

## Executive verdict

**No new independent Modbus register workbook or State0/State1 bit map was found online beyond the already-known `sjtrny` EVO270-1 xlsx lineage.**

What *is* newly useful from OEM/web sources:

1. **Physical DI / OUT / T labelling** from EvoHeat DHW manuals that **align with** workbook O01–O05 / T01–T05 / S04 (high pressure) — hardware names, not new Modbus addresses.
2. **Display fault-code lists** (Pxx / Exx) and **installer parameter ranges** (r04–r10 Hydro Power, g01–g04 Sanitech) that match the app’s named R/G families — still no address tables in those PDFs.
3. **Hard family splits:** older Trianco ActivAir S300 wall-hung (codes 01–09), Trianco Activair Indoor 5/7 (European PF + Modbus reg 10), FoxAir/WarmLink heating boards, and pool `302020-00000028` are **not** HW211 DHW Modbus maps.
4. **Empty:** schematic `20230302-0005`, Gitee/gitcode/CSDN hits for `2050`/`2051`/`2085` + HW211, Termobrasa/Indol public Modbus tables, Chico PC1006 protocol PDF on the public support site.

---

## Search methods

| Channel | Queries / targets |
| ------- | ----------------- |
| Web | `EVO270` Modbus/HW211; Trianco Activair S300; PHNIX/`芬尼`/`派尼尔` O01 T01; Termobrasa BI GOLD; iStore R290 PC1006; Chico Future; `302020`; `20230302-0005` |
| Manual hosts | ManualsLib, manualspro/manuzoid/manualsnet, evoheat.com.au, trianco.co.uk, heatpumps.istore.net.au, termobrasa.com, chico-future.com |
| CN platforms | Gitee, gitcode/AtomGit, CSDN for `2050` `2051` `2085` 热泵 / HW211 / 302020 |
| Cross-check | Prior local dumps `_research_github_sweep.md`, `_research_foxair_phnix.md`, `_research_hw211_esphome.md` |

---

## New / confirmed OEM sources (with URLs)

### A. HW211-family DHW — useful (manuals, not Modbus workbooks)

| Source | URL | Family | What it adds |
| ------ | --- | ------ | ------------ |
| EvoHeat **Evo270** Hot Water Heat Pump Manual | https://evoheat.com.au/wp-content/uploads/2021/07/pdf-manual-Evo270-Manual.pdf | **HW211 DHW** (EVO270) | PCB OUT1–OUT5, T1–T5, DI04; fault P/E; r04–r10 + g01–g04 ranges |
| Same on ManualsLib | https://www.manualslib.com/manual/1890396/Evoheat-Evo270.html | HW211 DHW | Same content; troubleshooting page mirrors PDF |
| EvoHeat **EVO270-E** Manual | https://evoheat.com.au/wp-content/uploads/2026/10/MANUAL-EVO270-E.pdf (also `/2024/09/MANUAL-Evo270-E.pdf`) | HW211 DHW (R290 gen) | Expanded error list: P03/P08, anode E13–E19, E43–E45 |
| Evo270-E tech support | https://evoheat.com.au/tech_support/evo270-e/ | HW211 DHW | Error table (includes P034 solar in one listing) |
| EvoHeat **EVO270-1** Manual | https://e8n3kui9abp.exactdn.com/wp-content/uploads/2022/02/MANUAL-Evo270-1.pdf | HW211 DHW | Sanitech g01–g04; PCB silkscreen labels (COMP/HT/HP/TTT/BTT/AT/SUT/OUT…) |
| manua.ls EVO270-E | https://www.manua.ls/evoheat/evo270-e/manual | HW211 DHW | Mirror / FAQ extract of E01 etc. |
| iStore manuals hub | https://heatpumps.istore.net.au/downloads-2/ | HW211 / PC1006 DHW | Owner + install PDFs for PASHW015-270LD-FL02-R290; **no Modbus register table** |
| Chico Future (OEM) home | https://chico-future.com/ | PC1006 OEM | Confirms Chico as heat-pump controller OEM; **no public PC1006 Modbus map** |
| Chico support / download centre | https://chico-future.com/support | Thermostats | Published manuals are thermostats (TP/CCST/HP6xxx); **not** All-in-One PC1006 protocol |
| HA forum (PC1006 sighting) | https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400?page=11 | HW211→PC1006 | Community: newer iStore boards labelled **PC1006** (Guangdong Chico); RS485 A2/B2 still present |

### B. Same OEM stack / cloud — already known lineage (listed for completeness)

| Source | URL | Note |
| ------ | --- | ---- |
| sjtrny ESPHome HW211 blog | https://sjtrny.com/posts/2026-06-03-esphome-hw211-component/ | Points at EVO270-1 xlsx → JSON |
| sjtrny/esphome-hw211 | https://github.com/sjtrny/esphome-hw211 | **Canonical** Modbus workbook + `dtu_wifi` |
| Dropbox `302020-00000028-communication-protocol.xls` | https://www.dropbox.com/scl/fi/x1e84b0s252kjkmh3zsu2/302020-00000028-communication-protocol.xls | Circulates as “302020”; used for **pool PC1002/PC1004**, also shipped beside HW211 datasheets in sjtrny — **do not merge as DHW `dtu_wifi`** |
| HA pool thread citing that xls | https://community.home-assistant.io/t/hayward-oasis-and-other-generic-pool-heatpump-using-pc1002/733827 | PC1002 CN13 RS485; register mismatches vs sheet |

### C. Other families — do **not** merge into HW211 DHW

| Source | URL | Why not HW211 DHW |
| ------ | --- | ----------------- |
| Trianco ActivAir **S300 & S500** install (archived) | https://trianco.co.uk/index.php?filename=224511-ActivAir-S300-S500.pdf… (also https://www.dhsspares.co.uk/userfiles/boiler_manuals/TRI035.pdf, ManualsLib S500) | **~2010 wall-hung ASHP**, R417a; programmer codes **01–09** — different product from modern Linked-Go DHW S300 / product `1245226668902080512` |
| Trianco Activair **Indoor 5/7 kW** control panel | https://trianco.co.uk/…Activair-Indoor-Heatpump-Control-Panel.pdf… ; ManualsLib page 44 | European PF1–PF11 params; Modbus **TA via register address 10** (PF6) — **not** slave-99 `dtu_wifi` |
| Trianco Activair HT / High Temperature error codes | https://www.manualslib.com/manual/3053727/Trianco-Activair.html?page=28 | Space-heating E01–E29 / inverter faults — heating board family |
| Trianco wall-hung WarmLink commissioning | https://trianco.co.uk/…Activair-Wall-Hung-3.2kW-Manual.pdf… | H07/H25/G01–G05 — **FoxAir/WarmLink heating** parameter names |
| Termobrasa Gold catalogues | https://termobrasa.com/wp-content/uploads/2025/03/Catalogo_Termobrasa_2025.pdf ; EN: `/2025/07/EN_termobrasa_catalogo_2025.pdf` | Wi-Fi + app only; **no Modbus / register table** |
| Indol EcoSave PV300 productblatt | https://www.vvsbutiken.nu/dokument/EcoSave%20produktblad%20v1.pdf | Specs + Wi-Fi; **no Modbus** |
| PHNIX commercial BMS blog | https://www.phnix-e.com/commercial-heat-pump-bms-integration-monitoring-points.html | Generic “ask for points list”; no DHW HW211 map |
| PHNIX PC4001 board notes | https://www.bestcontactor.com/product/phnix-pc4001/ | Commercial board; T1=supply / T2=return — **different** T-map; Modbus addr param P29 default 1 |
| 科特时控 芬尼克兹 PC4001/PC8001 gateway | https://www.ketetech.com/ProductShow_460.html | Gateway product page; no register table |
| manualspro Trianco Activair 3 kW Wi-Fi module | https://manualspro.net/233411-trianco-activair-3kw-indoor-air-source-heat-pump-user-manual | DTU/Wi-Fi pairing for WarmLink-style module; **no register map** |
| Flotide/Hydro Pro spare parts (PC1004 + 302020) | Azure CDN spare-parts PDFs (e.g. swfile…7028288…) | Confirms `302020-00000028` pairs with **pool** PC1004 — not HW211 DHW |

---

## Extracted facts (OEM manuals)

### 1. PCB DI / OUT / T labelling ↔ app O / S / T names — **HW211 DHW**

From Evo270 Manual §8.2 PCB Description  
(https://evoheat.com.au/wp-content/uploads/2021/07/pdf-manual-Evo270-Manual.pdf):

| PCB symbol | Manual meaning | Correlation to known `dtu_wifi` / cloud names |
| ---------- | -------------- | --------------------------------------------- |
| **OUT1** | Compressor | **O01** (2050 bit 8) |
| **OUT2** | Electric heater | **O02** (2050 bit 9) |
| **OUT3** | 4-way valve | **O03** (2050 bit 10) |
| **OUT4** | Fan high speed | **O04** (2050 bit 11) |
| **OUT5** | Fan low speed | **O05** (2050 bit 12) |
| OUT6–OUT8 | Not used | Aligns with reserve / model-specific O06+ |
| **DI04** | High pressure protection | **S04** (2050 bit 3) |
| DI03 / DI05 | Not used | — |
| **T1** | Ambient temperature | App/cloud **T01** (workbook ambient @ **2019** on DHW — *not* heating’s 2045) |
| **T2** | Bottom temperature | **T02** (tank bottom) |
| **T3** | Top temperature | **T03** (tank top) |
| **T4** | Coil temperature | **T04** |
| **T5** | Suction temperature | **T05** |
| T6–T9 | Not used | — |
| CN2 | Electronic expansion valve | Relates to **O07** EEV position telemetry in workbook |

**Marking:** Hardware naming only. Manuals do **not** publish Modbus holding addresses. Address/bit positions remain those of the sjtrny EVO270-1 workbook.

EVO270-1 silkscreen abbreviations (same PDF family) reinforce: COMP, HT (heater), HP, TTT (top tank), BTT (bottom), AT (ambient), SUT (suction), EEV, OUT1/3/4/5, DI01–DI06, NET/12V Wi-Fi header.

### 2. Display fault codes — **HW211 DHW** (not Modbus bit positions)

**Evo270 (classic)** — same PDF / ManualsLib p.18:

| Display | Meaning |
| ------- | ------- |
| P01 | Bottom water temp sensor open/short |
| P02 | Top tank water temp sensor open/short |
| P04 | Ambient temp sensor open/short |
| P05 | Coil / pipe temp sensor open/short |
| P07 | Refrigerant absorb / evaporator (suction) sensor open/short |
| P09 | Anti-freeze temp sensor open/short |
| E01 | High pressure protection |
| E02 | Low pressure protection |
| E03 | Water flow / no water |
| E04 | Electric-heater overheat / flow issue |
| E07 | Anti-freeze protection (flow) |
| E19 / E29 | Anti-freeze protect level 1 / 2 (ambient too low) |

**EVO270-E** — https://evoheat.com.au/wp-content/uploads/2026/10/MANUAL-EVO270-E.pdf — adds / renames:

| Display | Meaning |
| ------- | ------- |
| P03 | Discharge temperature sensor failure |
| P08 | Solar temperature sensor failure |
| P82 | Discharge overheating protection |
| E08 | Wired remote ↔ motherboard communication failure |
| E09 | Winter frost protection |
| E11 | DC motor stalling |
| E13 / E14 | Electronic anode 1 short / open |
| E18 / E19 | Electronic anode 2 short / open (*note:* E19 meaning differs from classic E19 antifreeze) |
| E43 / E44 / E45 | HP / LP / discharge overheat triggered thrice |

**Use:** Correlates with workbook **Fault0 `2085`** sensor/protect themes and **O12/O13** electric-anode bits; **do not** treat display codes as Modbus addresses. Classic vs -E lists differ — model-specific.

### 3. Installer parameter ranges (r / g) — **HW211 DHW**

Evo270 / EVO270-1 manuals (service menu password **066**):

| Code | Meaning | Default | Range |
| ---- | ------- | ------- | ----- |
| r04 | Enable Hydro Power set-point adjust | 0 | 0/1 |
| r05 | Hydro Power set point | 55 °C | 30–90 |
| r06 | Hydro Power startup delay | 200 min | 0–450 |
| r07 | Hydro Power replaces heat pump | 0 | 0/1 |
| r08 | Ambient when Hydro replaces HP | −5 °C | −20…10 |
| r09 | Ambient for Hydro start without delay | 10 °C | 0–30 |
| r10 | Ambient for Hydro start with delay | 25 °C | 10–40 |
| g01 | Sanitech / legionella target | 70 °C | 30–70 |
| g02 | Sanitech hold time | 30 min | 0–90 |
| g03 | Sanitech start hour | 0 | 0–23 |
| g04 | Sanitech cycle days | 7 | 7–99 |

These are the **same letter families** as cloud/app codes **R** / **G**; Modbus addresses still come only from the EVO270-1 workbook / JSON.

### 4. Explicitly **not** HW211 DHW register facts

#### Older Trianco ActivAir S300/S500 (wall-hung ASHP)

Operating parameter codes **01–09** (cylinder sensor, compressor sensor, pressure cutouts…). Different era/product; **not** P01/E01 DHW display set and **not** `dtu_wifi`.

#### Trianco Activair Indoor 5/7 (European)

- Digital inputs: PI5 OFF, PI4 E/I, PI3 TA; RS+/RS− Modbus.
- PF6 enables “TA via Modbus”; supervisor uses **register address 10** (1=call, 0=off).
- **Other family** — do not map to slave 99 / 2050.

#### Pool protocol `302020-00000028`

Tied to PC1002/PC1004 pool heat pumps (Hayward/Oasis/Flotide). Same filename appears in sjtrny `datasheets/` next to the DHW workbook — treat as **adjacent OEM archive**, not as Trianco S300 DHW map.

#### PHNIX / FoxAir heating

T01 ambient @ **2045**, packed O @ **2019**, etc. — already documented in `_research_foxair_phnix.md`. Hard conflicts with DHW (e.g. DHW **2019 = T01**, **2050 = State0**).

---

## Empty / negative searches

| Query / target | Result |
| -------------- | ------ |
| Schematic / CODE **`20230302-0005`** | **No** public hit (wiring diagrams found were unrelated brands) |
| **`HW211` datasheet** (controller) | Collisions with MV cable “HW211”, metal resistors, audio SAMS — **no** OEM heat-pump PCB datasheet |
| Gitee: HW211 / 2050 2051 2085 热泵 | Only generic Modbus libraries / unrelated student projects |
| gitcode / AtomGit: same | MATLAB heat-pump sims, EVCC/Daikin — **no** register maps |
| CSDN: 2050 2051 HW211 / 302020 热泵 | Generic Modbus addressing tutorials; **no** PHNIX/HW211 DHW table |
| Termobrasa BI GOLD Modbus | Catalogues: Wi-Fi only |
| Indol PV300 Modbus PDF | Spec sheets + Wi-Fi; Modbus not published |
| PHNIX / 芬尼 / 派尼尔 public O01+T01 **DHW** parameter PDF | Commercial BMS prose + PC4001 hardware notes only |
| Chico Future download centre for **PC1006** / All-in-One Modbus | Thermostat manuals only |
| ManualsLib HW211 / Modbus register table | EVO270 PCB + faults only; **no** holding-register list |
| Trianco current downloads “S300 installer Modbus” | Current site lists R290/R32 Activair manuals; archived S300 is old wall-hung ASHP |

---

## Bottom line vs sjtrny xlsx

| Kind of knowledge | Beyond sjtrny workbook? |
| ----------------- | ----------------------- |
| New Modbus addresses / 2050–2051 / 2085 bit definitions | **No** |
| Physical OUT/DI/T → O/S/T name crosswalk | **Yes** (OEM manuals) |
| Display P/E fault lists + r/g ranges | **Yes** (OEM manuals; semantics align with known codes) |
| Competing full protocol xlsx from manufacturer sites | **No** (only pool `302020` and heating-family maps) |

**Path written:** `/home/john/repos/hitemp/docs/_research_oem_manuals_web.md`
