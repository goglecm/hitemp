<!-- Evidence extract. The summary and how it applies to this integration are in HW211_REGISTER_COMPARISON.md. -->

# Research dump: forums / Reddit / blogs / community archives

**Date:** 2026-11-20  
**Scope:** Hunt community sources (HA forum, Reddit, Domoticz/openHAB/Node-RED, Dutch/UK/AU installer forums, Facebook group archives, sjtrny blog, YouTube, Discord indexes) for **HW211 / Trianco Activair / HiTemp / Indol** register and bit explanations **not** already captured as GitHub workbook extracts.  
**Constraint:** Research dump only — does **not** modify `HW211_REGISTER_COMPARISON.md`. No invented mappings. No commit.

**Anchors searched:** chip HW211; Activair schematic CODE `20230302-0005` (AI01–AI06, DI01, OUT/HT/EEV/FM/COMP, RS485 WIFI); app codes O/S/T/R; status words `2050`/`2051`; `mode_real`.

---

## Executive verdict

**No new independent Modbus workbook or full State0/State1 bit table** for HW211 DHW was found outside the already-known EVO270 / `sjtrny` lineage.

Community channels **do** contribute:

1. **Confirmed (matches workbook):** `2050` bit 8 = compressor (`0x0100`); Modbus RTU slave **99**; TEMP1 scaling `(x-60)*0.5`; Wi‑Fi loom colours; iStore/EvoHeat same board family.
2. **Confirmed (manuals, not forums):** Trianco S300 remote on/off = **DI05**+GND (volt-free); do not apply mains.
3. **Anecdotal / partial:** Neptuno HA mode remapping; timer-on-device vs app mismatch; H30≠DTU slave; PC1006 successor rumour; aquatemp #108 bit-range wording is wrong even though live `2050` strings match bit 8/11.
4. **Traps (do not merge into HW211 DHW State0):** Pool PC1004 / Thermotec Node-RED maps; PHNIX WarmLink heating Modbus; Activair R32/R290 space-heating WarmLink manuals; Activair Indoor 5 DI labels (PI3/PI4/PI5).

**Public URL for schematic `20230302-0005`:** still not found.  
**Facebook / ESPHome Discord / YouTube:** no indexed register tables for HW211 Modbus.

---

## Search methods

| Channel | Queries / targets |
| ------- | ----------------- |
| HA community | Aqua Temp, HiTemp, Trianco, Activair, WarmLink, Neptuno, `mode_real`, `2050` bit, HW211, iStore, EVO270 |
| Reddit | r/homeassistant, heatpumps, DIY — Trianco Activair Modbus / HiTemp / iStore / EvoHeat |
| Domoticz / openHAB / Node-RED | PHNIX DHW, AquaTemp Modbus, tashbee Google Doc |
| Dutch/UK/AU | Tweakers GoT, Trianco downloads / Passiv RS485, ManualsLib S300, MEEH Facebook iStore |
| Blogs | sjtrny Wi‑Fi adapter + HW211 component (no public comment thread with new bits) |
| YouTube | HW211 / EvoHeat / iStore Modbus / ESPHome — descriptions only; no table-bearing hits |
| Discord | ESPHome Discord archives — not publicly indexed with HW211 register content |
| Related traps | WarmLink #855025, fleuke PC1004, control.com Oasis/Thermotec PDFs |

---

## Useful threads (priority)

| # | URL | Why useful |
| - | --- | ---------- |
| 1 | https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400 | **Primary.** Origin of local Modbus; spreadsheet link; ESPHome YAML; bit8; wiring; iStore confirm; sjtrny component announce; PC1006 note |
| 1a | …/230400/136 (epayne787) | Posted EVO270-1 HW211 Modbus map (Filebin; later expired → sjtrny workbook) |
| 1b | …/230400?page=8 | Steve61: spreadsheet showed bit8@2050; working `bitmask: 0x0100`; slave 99; iStore 270L works |
| 1c | …/230400/123–135 | tjhowse RS485 attempts; H30=50 ≠ Wi‑Fi slave; points at https://github.com/tjhowse/evoheat_modbus (empty/stub) |
| 1d | …/230400/206 + page 11 | sjtrny ESPHome component; Roving-Ronin: HW211→PC1006 (Chico) rumour + A2/B2 secondary Modbus pads |
| 2 | https://community.home-assistant.io/t/water-boiler-heater-immergas-neptuno-300-sol/999488 | HiTemp Neptuno: mode values 0/2/3/4 + HA Auto/Cool/Heat/FanOnly remapping; product ID pastebin |
| 3 | https://community.home-assistant.io/t/aquatemp-heat-pump-controller-integration-custom-climate-entity/334594 | Cloud integration; HiTemp credential issues; no new Modbus bits |
| 4 | https://community.home-assistant.io/t/warmlink-support/855025 | **Heating** PHNIX/WarmLink Modbus YAML (slave 1, regs 1011/2045–2047/1157) — **trap** |
| 5 | https://docs.google.com/document/d/e/2PACX-1vTeQRtc3AX4VB80hpf8HlfPtUTnXznXPVtW3zGL3Krl7_H51Z1tFqnpi417Iw0vtOvZ7oqZBjtkIbFl/pub | tashbee Node-RED (linked from #230400/107) — **pool Thermotec / PC1004 CN13**, not HW211 DHW |
| 6 | https://sjtrny.com/posts/2026-05-26-heat-pump-hot-water-wi-fi-adapter/ | Hardware install; cable colours; points at HA thread for registers |
| 7 | https://sjtrny.com/posts/2026-06-03-esphome-hw211-component/ | Component overview; `raw_registers`; no new bit table beyond workbook |
| 8 | https://github.com/radical-squared/aquatemp/issues/108 | Community cloud observation: O/S empty in API; packed in `2050` (see § Confirmed / Anecdotal) |
| 9 | https://www.reddit.com/r/homeassistant/comments/1si5mzk/aqua_temp_integration_for_evoheat_evo_2701/ | Cloud-only success story; **no** Modbus/register table |
| 10 | https://www.manualslib.com/manual/3338247/Trianco-S300.html?page=17 | Official DI05+GND volt-free remote (installer doc, not forum) |
| 11 | https://manualspro.net/233207-trianco-s300-wall-hung-air-source-heat-pump-user-manual | Same DI05 wording |
| 12 | https://pstinstallers.zendesk.com/hc/en-gb/articles/47388223959569-Trianco-RS485-connections | Passiv/Activair **space-heating** RS485 terminals 32/33 — **unrelated** to HW211 DHW Wi‑Fi loom |

---

## Confirmed vs anecdotal

### Confirmed (community + consistent with workbook / manuals)

| Fact | Evidence | Confidence |
| ---- | -------- | ---------- |
| Holding `2050` bit **8** (`0x0100`) = compressor running (O01) | HA #230400 p.8 (Steve61: “spreadsheet… bit8”); live use on EvoHeat/iStore; aquatemp #108 live strings flip bit 8 with compressor | **High** |
| Modbus RTU **9600 8N1**, DTU/Wi‑Fi slave address **99** | HA #230400; epayne787 YAML; sjtrny blog/component | **High** |
| Temperatures use TEMP1 `(raw-60)*0.5` °C at 2019–2023 | HA #230400/142 YAML (ambient/bottom/top/coil/suction) | **High** |
| Wi‑Fi connector: Black GND, Red 12V, White 485‑A, Yellow 485‑B; do not feed 12V into bare ESP32 | HA #230400; sjtrny adapter post; echopin664 README | **High** |
| 5th loom wire = earth/chassis; **not** required for RS485 | HA #230400/146 epayne787 | **High** |
| iStore 270L (and likely 180L) shares HW211 / same map | HA #230400 p.8 community reports | **High** (hardware family) |
| Trianco S300 remote on/off = remove link **DI05–GND**, volt-free thermostat; **never** put mains on those pins | ManualsLib / manualspro S300 | **High** (OEM manual) |
| App/cloud modes for HiTemp DHW: `0` Smart/Intelligent, `2` Eco, `3` Hybrid, `4` Fast/Boost; Vacation often `7` | HA Neptuno #999488; matches local S300/`mode_real` docs | **High** for values; remapping to HA HVAC modes is **integration-specific** |
| Named O01–O06 / S01–S06 often **empty** in cloud API; packed into numeric `2050` | aquatemp #108 (spanznet) | **High** (API behaviour) |
| Device-panel timers ≠ app timers (one-way / not synced) | HA #230400/115–117 | **Medium–High** (multiple users) |

### Anecdotal / uncertain (do not promote to workbook without re-check)

| Claim | Source | Notes |
| ----- | ------ | ----- |
| “Bits 5–10 of `2050` are O01–O06” | aquatemp #108 comment | **Miscount.** Same post’s example strings actually show compressor/fan as bits **8** and **11** when bit0=rightmost — matches workbook, not the prose |
| Early guess that RS485 to HiTemp module is “not Modbus” | HA #230400/122 angyp74 | Superseded by successful Modbus at slave 99 |
| Setting panel **H30** to 50 makes the Wi‑Fi Modbus address 50 | tjhowse #230400/123 | Failed to get replies; working community configs use **99**. H30 is bus address parameter; DTU slave 99 is separate in practice |
| Newer iStore uses **PC1006** (Chico) instead of HW211; secondary A2/B2 pads | HA #230400/207 Roving-Ronin | Plausible hardware lead; **no** public Modbus table |
| Wi‑Fi module HTTP login `admin`/`admin` | HA #230400/112–113 | 404 after login; no useful local API found |
| External antenna mod on HiTemp dongle fixes dropouts | HA #230400/103–109 | Hardware anecdote only |
| HA Auto/Cool/Heat/FanOnly ↔ Smart/Eco/Hybrid/Boost | Neptuno #999488 | Useful for aquatemp climate entity; **not** Modbus register semantics |
| Passiv Programmer RS485 A=32 B=33 on Trianco | pstinstallers Zendesk | Activair **heating** wiring centre — not S300/HW211 DHW Wi‑Fi port |

### Explicit traps (wrong product family)

| Source | Why trap |
| ------ | -------- |
| tashbee Node-RED Google Doc + control.com Oasis PDFs | Pool heat pump; CN13 on **PC1004**; mode 0/1/2 cool/heat/auto; target ÷10; slave via **H37** menu | 
| fleuke VBIV/Fairland/Norsup (cited in #230400 p.10–11) | Pool: `2050` = **discharge temp**, not State0 |
| WarmLink HA #855025 Modbus YAML | PHNIX **space heating**: slave **1**, inlet/outlet/DHW at 2045–2047 (×0.1), power 1011 |
| Trianco Activair R290 High Temp / WarmLink app manuals | Space-heating Activair; not HW211 DHW cylinder controller |
| Activair Indoor 5 ManualsLib DI page | PI3=TA thermostat, PI4=E/I, PI5=remote — **different** controller family from S300 DI05 |
| Tweakers GoT Modbus threads | Ecoforest / Midea / Qsilence / Brink — keyword collisions only |

---

## Extracted register / bit / wiring notes

### A. HW211 DHW — community Modbus (aligned with workbook)

From HA #230400 YAML + commentary (epayne787 / Steve61 lineage):

| Addr | Use in community YAML | Notes |
| ---- | --------------------- | ----- |
| 2019 | Ambient | TEMP1 |
| 2020 | Bottom tank | TEMP1 |
| 2021 | Top tank | TEMP1 |
| 2022 | Coil | TEMP1 |
| 2023 | Suction | TEMP1 |
| 2050 | Status word | bit8 compressor confirmed in-thread |

Compressor binary sensor (community-confirmed pattern):

```yaml
binary_sensor:
  - platform: modbus_controller
    modbus_controller_id: device_addr_1
    id: compressor_status
    address: 2050
    register_type: holding
    bitmask: 0x0100
    name: "Compressor Status"
```

**Not newly decoded in forums** (still workbook / local S300 territory): full `2050` S01/S03/S06/O02–O06 map; `2051` bits; `2085` faults; `mode_real` address semantics beyond cloud enum.

### B. Cloud API packing (community)

From aquatemp #108 (EvoHeat270 / HiTemp), example `2050` string values (bit0 = rightmost digit as published):

| Observed value | Interpretation |
| -------------- | -------------- |
| `0000000000110000` | Bits 4+5 set; compressor off |
| `0000100100110000` | Bits 4+5+8+11 set; compressor + fan high on |

→ Diff = bits **8** and **11** → matches workbook O01 / O04. Treat “bits 5–10 = O01–O06” prose as **anecdotal error**.

### C. DI01 vs DI05 (wiring)

| Label source | Remote / thermostat claim |
| ------------ | ------------------------- |
| Activair schematic CODE **20230302-0005** (local) | **DI01** labelled room thermostat on drawing |
| Trianco S300 installation manual | Remote on/off = **DI05** and GND (factory link); volt-free only |
| Local S300 observation (workbook comparison / HITEMP_PARAMETERS) | Opening DI05–GND → Power=0 and `2050` bit0 behaviour |

**Forum hunt result:** No HA/Reddit/Facebook thread independently resolved the silkscreen conflict. Installer manuals uniformly say **DI05**. Treat DI01-on-schematic vs DI05-in-manual as **open conflict** (already flagged in comparison §8); community did not add a third authoritative source.

### D. App codes O/S/T/R — community explanations matching the app

| Topic | Community contribution |
| ----- | ---------------------- |
| O01 compressor | Confirmed via `2050` bit8 (forums) |
| O02–O06 / S0x | Named cloud codes empty; must use packed `2050` (#108) — no new bit indices beyond workbook |
| `mode_real` / Mode 0/2/3/4/7 | Neptuno + aquatemp issues confirm enum; Fast heating ↔ booster/electric heater in app UX |
| R/T parameter prose | Forums mostly cloud/integration UX; deep R/T meanings remain manuals + local docs |
| Timers | Device timers and HiTemp app timers often diverge (#230400) |

### E. Schematic AI / OUT anchors

Public web: **no** hit for `20230302-0005` or a published AI01–AI06 table matching the local Activair drawing. Community wiring posts describe the **Wi‑Fi RS485 loom** and S300 **DI05**, not AI01–AI06 sensor silkscreen.

---

## Channel-by-channel empty / thin results

| Channel | Result |
| ------- | ------ |
| **Reddit** | One EvoHeat + Aqua Temp cloud post (`1si5mzk`); no Trianco Activair Modbus register map |
| **Facebook** | MEEH iStore ownership threads (noise, warranty, Wi‑Fi “coming soon”); Trianco marketing videos; **no** Modbus/bit posts indexed |
| **Domoticz** | Generic Modbus plugins only; no PHNIX HW211 DHW device map found |
| **openHAB** | Generic Modbus binding docs only |
| **Node-RED** | Useful write-up is **pool** (tashbee), not HW211 DHW |
| **Dutch Tweakers** | No Trianco/Indol/HiTemp HW211 hits; other brands only |
| **UK installer** | Trianco downloads + Passiv RS485 for **heating** Activair; S300 manuals for DI05 |
| **AU** | iStore discussion lives inside HA #230400 + MEEH Facebook (no registers) |
| **sjtrny blog comments** | No public comment thread adding bits; posts cite HA #230400 |
| **ESPHome Discord** | Not indexed; no scrapable HW211 register archive found |
| **YouTube** | Trianco wiring/WarmLink marketing; **no** HW211 Modbus register-table videos/transcripts found |

---

## New facts vs known workbook / local docs

| Item | New from this hunt? | Action |
| ---- | ------------------- | ------ |
| Full `2050`/`2051`/`2085` bit tables | **No** — still sjtrny workbook | Prefer workbook |
| Compressor = bit8 | **Reinforced** by HA p.8 + #108 live strings | Already in comparison |
| Cloud O/S empty → use `2050` | **Reinforced** (#108) | Already known |
| Slave 99 / TEMP1 / loom colours | **Reinforced** | Already known |
| DI05 vs DI01 conflict | **No resolution** in forums | Still open |
| `20230302-0005` public URL | **Still missing** | Keep local-only |
| Neptuno HA HVAC remapping table | **Useful for cloud UX** only | Not Modbus |
| PC1006 / Chico successor | **New lead**, no map | Watch |
| H30 ≠ working Wi‑Fi slave 99 | **Practical warning** | Document as anecdote |
| Pool/WarmLink maps with overlapping addresses | **Trap reinforcement** | Do not merge |

**Bottom line for comparison doc (do not edit here):** Community sources corroborate the workbook’s compressor bit and transport settings, and they document cloud packing quirks — they do **not** supply any bit meanings absent from the EVO270 `dtu_wifi` sheet.

---

## Key URLs (quick list)

- https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400
- https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400?page=8
- https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400/136
- https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400/206
- https://community.home-assistant.io/t/water-boiler-heater-immergas-neptuno-300-sol/999488
- https://community.home-assistant.io/t/warmlink-support/855025
- https://docs.google.com/document/d/e/2PACX-1vTeQRtc3AX4VB80hpf8HlfPtUTnXznXPVtW3zGL3Krl7_H51Z1tFqnpi417Iw0vtOvZ7oqZBjtkIbFl/pub
- https://sjtrny.com/posts/2026-05-26-heat-pump-hot-water-wi-fi-adapter/
- https://sjtrny.com/posts/2026-06-03-esphome-hw211-component/
- https://github.com/radical-squared/aquatemp/issues/108
- https://www.reddit.com/r/homeassistant/comments/1si5mzk/aqua_temp_integration_for_evoheat_evo_2701/
- https://www.manualslib.com/manual/3338247/Trianco-S300.html?page=17
- https://chico-future.com (PC1006 OEM lead only)

---

*End of research dump. Comparison doc untouched. Nothing committed.*
