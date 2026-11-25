<!-- Evidence extract. The summary and how it applies to this integration are in HW211_REGISTER_COMPARISON.md. -->

# FoxAir / WarmLink / PHNIX space-heating register research

**Status:** research extract only. **Do not treat as a write recipe for Trianco S300 / HW211.**  
**Board family:** FoxAir GL9 / PHNIX air-to-water **space-heating** mainboards (WarmLink / Linked-Go product family **644**, firmware 3.x) — **different** from HW211 DHW / Trianco S300 `dtu_wifi`.

Sources mined (cloned or fetched 2026-11-20; no inventions):

| Repo / thread | URL | Role |
| ------------- | --- | ---- |
| **dosordie/FoxAir_Control** (`a98b16c`) | https://github.com/dosordie/FoxAir_Control | Primary: `data/foxair_phnix_registers.json`, cloud resolver, bit decoders, WarmLink docs |
| **tnako/ha-foxair** (`aef9a59`) | https://github.com/tnako/ha-foxair | HA Modbus integration; same register JSON lineage; marks 2019 bits 13–15 reserved |
| **VAdamec/WarmLink** | https://github.com/VAdamec/WarmLink | Linked-Go cloud HA client (`appId=16`, `cloud.linked-go.com`) |
| **radical-squared/aquatemp#99** | https://github.com/radical-squared/aquatemp/issues/99 | Community WarmLink `getDataByCode` code list incl. `O01~023` / `S01~S10` |
| **dosordie/FoxAir_updater** | https://github.com/dosordie/FoxAir_updater | FW tooling for same heating mainboard family (`82400644`); not a register map |
| LogicMachine Phnix fancoil | https://forum.logicmachine.net/showthread.php?tid=5743 | **Fancoil** holding regs **28xxx** (unrelated to heat-pump MAIN 1xxx/2xxx) |
| HA Phnix fancoil ESP | https://community.home-assistant.io/t/phnix-fan-coil-modbus-esp-integration/950947 | Fancoil **28301–28311** write + **46801–46804** read |

Cross-check for HW211 conflicts: local `docs/HW211_REGISTER_COMPARISON.md` (read-only; **not modified**).

---

## Applies to HW211 S300 vs Heating-board only

### Applies to HW211 S300 / Linked-Go cloud mechanics (reusable)

| Item | Evidence | Use on S300 |
| ---- | -------- | ----------- |
| Cloud host `https://cloud.linked-go.com:449/crmservice/api` + `appId` **16** | WarmLink HA, aquatemp#99, FoxAir_Control | Same CRM stack as HiTemp / AquaTemp family |
| Live refresh: `POST app/device/control` with `protocolCode=app_heartbeat`, `value=23205` (**no `appId`**) | FoxAir `docs/warmlink_polling_and_readback.md` (GL9 2026-10-05); `cloud/warmlink_api.py` | Same heartbeat mechanism; still does **not** populate named `O01`/`S01` on S300 |
| Poll pattern: heartbeat → settle (~1 s) → `getDataByCode` for live codes | Same docs + `tests/test_cloud_app_heartbeat.py` | Useful for forcing DTU upload of live words |
| Cloud BINARY bitwords: 16-char string, **MSB leftmost = bit 15**; e.g. `"0000010000000000"` = `0x0400` = bit 10 | FoxAir tests + GL9 live note on `O01~023` | Parsing rule only — **not** the S300 bit layout |
| Named Fault1…Fault10 → MAIN 2081…2090 (heating confirmed) | `CONFIRMED_REGISTER_ALIASES` | On S300 these codes are often **empty**; DHW faults live in workbook **`2085` Fault0** with a **different** bit map |
| Concept: packed status words exposed as tilde codes (`O01~023`, `S01~S10`) | Cloud catalogs | On S300 the **equivalent** packing is workbook **`2050`/`2051`**, not 2019/2034 |

### Heating-board only (do **not** reuse addresses/bit positions on HW211)

| Item | FoxAir / GL9 heating | HW211 `dtu_wifi` / S300 |
| ---- | -------------------- | ------------------------ |
| Packed outputs | Cloud `O01~023` → MAIN **2019** | Named O empty; bits in **2050** bits 8–15; **2019 = T01 ambient** |
| Packed inputs | Cloud `S01~S10` → MAIN **2034** | Named S empty; bits in **2050** bits 0–5 (+ **2051**) |
| Ambient temp `T01` | MAIN **2045** | MAIN / cloud **2019** |
| Manifold / distributor temp | `T14` → **2050** | **2050 = State0** status word |
| Frost plate temp `T06` | **2055** | **2055 blank** in workbook; **not** O03 |
| Compressor output bit | **2019 bit 0** (and app label O01) | **2050 bit 8** (O01) |
| 4-way valve | **2019 bit 6** (O07 / logical 007) | **2050 bit 10** (O03) |
| Electrical heater | **2019 bits 7–8** (stages 1–2) | **2050 bit 9** (single O02) |
| Fault word semantics | ERR01–ERR10 bitfields 2081–2090 (heating) | Workbook Fault0 **2085** DHW sensor/protect bits |
| Fancoil 28xxx / 46xxx | PHNIX **fancoil** products only | Unrelated to S300 heat pump |

---

## Explicit conflict table (packed cloud words vs HW211 `dtu_wifi`)

Focus addresses requested: **2019, 2034, 2050, 2055**.

| Address | FoxAir GL9 / heating MAIN | Cloud code (heating) | HW211 `dtu_wifi` / S300 | Conflict? |
| ------: | ------------------------- | -------------------- | ----------------------- | --------- |
| **2019** | BITFIELD load outputs O001–O023 | **`O01~023`** | **`T01` ambient temperature** (°C×10) | **HARD CONFLICT** — never decode 2019 as O-bits on S300 |
| **2034** | BITFIELD contacts / SG Ready | **`S01~S10`** | Not the DHW S-pack address (S/O live in **2050**) | **HARD CONFLICT** if reused as “S word” |
| **2050** | **`T14` Verteilerrohrtemperatur** (TEMP1) | `T14` | **`State0`** packed S01/S03–S06 + O01–O06 (+ anodes) | **HARD CONFLICT** — temp vs status word |
| **2055** | **`T06` Frostschutztemperatur** (plate HX) | `T06` | Blank / unused; **not** O03 | **CONFLICT** with any “O03=2055” hypothesis; FoxAir meaning ≠ DHW O03 |
| 2045 | `T01` ambient | `T01` | (S300 ambient is 2019) | Same **name**, different address |
| 2048 | `T04` outdoor in use | `T04` | Different T-map on DHW | Heating-only mapping |
| 2085 | Fault1 / ERR01 (heating fault bits) | `Fault5` alias → 2085 in FoxAir aliases | Workbook **Fault0** DHW bit map | Same address number, **different bit meanings** |
| 2060 | (EEV elsewhere on heating: O15→2020) | — | `O07` EEV position | Do not assume O07↔2060 from heating maps alone without S300 check |

### Side-by-side: “compressor on” and “4-way”

| Signal | FoxAir heating | HW211 DHW |
| ------ | -------------- | --------- |
| Compressor running | `2019` **bit 0** (also WarmLink app `O01`) | `2050` **bit 8** (`O01`) |
| 4-way / reversing | `2019` **bit 6** (logical O007 / app `O07`) | `2050` **bit 10** (`O03`) |
| Electric heater | `2019` bits **7** / **8** (stages) | `2050` **bit 9** (`O02`) |
| Remote on/off input | `2034` **bit 4** S05 (active-low) | `2050` **bit 0** S01 (1=OP open) |

---

## Full bit maps — packed output / input words

### MAIN 2019 — cloud `O01~023` (load / output bitfield)

Source: FoxAir_Control `data/foxair_phnix_registers.json` → `"2019"`.  
Type: `BITFIELD`, read-only. Cloud BINARY string MSB-first.

| Bit | Logical O# (board text) | Meaning (FoxAir_Control) | WarmLink 644 app label (when present) |
| --: | ----------------------- | ------------------------ | ------------------------------------- |
| 0 | (compressor run) | Kompressor tatsächlich laufend / Inverter-Istfrequenz ≠ 0 (0=AUS/1=EIN) | `O01` Compressor |
| 1 | — | Reserviert | — |
| 2 | — | Mindestens ein Lüfter tatsächlich aktiv (0=AUS/1=EIN) | `O03` Fan Motor:High Speed |
| 3 | — | Lüfter Niedriggeschwindigkeitsausgang (0=AUS/1=EIN) | `O04` Fan Motor:Low Speed |
| 4 | 005 | Wasserpumpen-Ausgang (0=AUS/1=EIN) | `O05` Main Circulation Pump |
| 5 | 006 | Warmwasserpumpen-Ausgang (0=AUS/1=EIN) | `O06` DHW Pump |
| 6 | 007 | 4-Wege-Ventil 1 (0=AUS/1=EIN) | `O07` 4-Way Valve |
| 7 | 008 | Elektrische Heizstufe 1 (0=AUS/1=EIN) | `O08` Electric Heater Stage 1 |
| 8 | 009 | Elektrische Heizstufe 2 (0=AUS/1=EIN) | `O09` Electric Heater Stage 2 |
| 9 | 010 | 3-Wege-Ventil (0=AUS/1=EIN) | `O10` Hot Water 3-Way Valve |
| 10 | 011 | Alarm-Ausgang (0=AUS/1=EIN) | `O11` Alarm — live: `0x0400` while Sammelstörung active |
| 11 | 012 | Kurbelgehäuseheizung (0=AUS/1=EIN) | `O12` Crankcase Heater |
| 12 | 013 | Wannenheizung (0=AUS/1=EIN) | `O13` Bottom Plate Heater |
| 13 | 021 | Heizungswasserpumpe (0=AUS/1=EIN) | `O21` Air-Conditioning Pump |
| 14 | 022 | Hydraulikmodul Wasserkreislauf Elektroheizung | `O22` Electric Heating of Waterway (Hydraulic Module) |
| 15 | 023 | Hydraulikmodul WW-Tank Elektroheizung | `O23` Electric Heating of Water Tank (Hydraulic Module) |

**ha-foxair caveat:** bits **13–15** labelled “Reserviert — … unbestaetigt” and not expanded as binary sensors; FoxAir_Control still documents them as O021–O023.

**Physical RO vs logical O** (FAQ `relais_ausgaenge.md`, GL9 board):

| Relais | Function | Feedback |
| ------ | -------- | -------- |
| RO01 | Alarm / Sammelstörung | **2019 bit 10** / O011 |
| RO04 / K4 | Main circulation pump | 2019 bit 4 / O005 |
| RO05 / K5 | External / DHW pump (via H40) | 2019 bit 5 / O006 |
| RO06 | 4-way | 2019 bit 6 / O007 |
| RO07 / RO08 | E-heater stage 1 / 2 | bits 7 / 8 |
| RO09 | DHW 3-way | bit 9 |
| RO10 / RO11 | Crankcase / drip-tray heater | bits 11 / 12 |
| RO12–RO15 | Cool 3-way, WW tank heater, zone pumps | mostly **2018** bits (see below) |

### MAIN 2018 — additional outputs (heating)

FoxAir_Control lists 2018 as DIGI1 “025 / Elektrischer Wassertankheizer”.  
**ha-foxair** expands it as BITFIELD:

| Bit | Meaning |
| --: | ------- |
| 0 | 025 Elektroheizer Warmwasserspeicher |
| 8 | Pumpe Zone 1 |
| 9 | Pumpe Zone 2 |
| 10 | 3-Wege-Ventil Kühlung |

### MAIN 2034 — cloud `S01~S10` (contacts / SG)

Source: `foxair_phnix_registers.json` `"2034"` + `CONTACT_BIT_MAP_2034` in `core/foxair_phnix_core.py`.

Polarity:

- **S01–S10 (bits 0–9):** **active-low** — raw `0` = contact “on/closed”, `1` = “off/open” (`0=ein / 1=aus`).
- **SG bits 12–13:** **active-high** — `0=Aus`, `1=Ein`.

| Bit | Name | Polarity / notes |
| --: | ---- | ---------------- |
| 0 | S01 Hochdruckschalter | active-low |
| 1 | S02 Niederdruckschalter | active-low |
| 2 | S03 Wasserflussschalter | active-low |
| 3 | S04 Überhitzungsschalter elektrischer Heizer | active-low |
| 4 | S05 Fern-AN/AUS | active-low |
| 5 | S06 Fernheizung/Kühlung / Remote Heat-Cool | active-low; RE hypothesis re DIN2 / external AT path when 1463=1 — **not confirmed** |
| 6 | S07 Warmwasserschalter | active-low |
| 7 | S08 Reserviert / unbekannt | — |
| 8 | S09 Reserviert / unbekannt | — |
| 9 | S10 Heizen/Kühlen AN/AUS | active-low |
| 10 | S11 Reserviert / unbekannt | — |
| 11 | S12 Reserviert / unbekannt | — |
| 12 | SG Kontakt 1 / AI-DI16 / Fernschalter / Klemme 1–2 | active-high |
| 13 | SG Kontakt 2 / DIN_1 / Heat/Cool On/Off / PV / Klemme 7–8 | active-high |
| 14 | S15 Reserviert / unbekannt | — |
| 15 | S16 Reserviert / unbekannt | — |

GL9 live example (644 catalog doc): `S01~S10` = `0010110000000000` = `0x2C00` = 11264, matching MAIN 2034.

---

## Related heating MAIN bitfields (complete named maps)

Sized from FoxAir_Control register JSON: **29** BITFIELD registers, **184** named bits total. Primary operational maps below.

### Fault words Fault1…Fault10 → MAIN 2081…2090

Confirmed aliases (`cloud/register_resolver.py`):

| Cloud | MAIN |
| ----- | ---: |
| Fault1 | 2081 |
| Fault2 | 2082 |
| Fault3 | 2083 |
| Fault4 | 2084 |
| Fault5 | 2085 |
| Fault6 | 2086 |
| Fault7 | 2087 |
| Fault8 | 2088 |
| Fault9 | 2089 |
| Fault10 | 2090 |

#### 2081 ERR07 (Fehler 7)

| Bit | Text |
| --: | ---- |
| 0 | F00 – IPM-Überstromfehler |
| 1 | F01 – Kompressortreiberfehler |
| 2 | Kompressor Überstrom |
| 3 | Phasenverlust Eingangsspannung |
| 4 | IPM Stromabtastfehler |
| 5 | F26 – IGBT-Überhitzungsfehler |
| 6 | Vorladefehler |
| 7 | DC-Sammelschienen-Überspannung |
| 8 | DC-Sammelschienen-Unterspannung |
| 9 | AC-Eingangsspannung Unterspannung |
| 10 | AC-Eingangs-Überstromabschaltung |
| 11 | Eingangsspannungs-Abtastfehler |
| 12 | DSP ↔ PFC Kommunikationsfehler |
| 13 | F17 – Temperatursensorfehler Kompressortreiber |
| 14 | F11 – Kommunikation DSP ↔ Kompressortreiber gestört |
| 15 | F151 – Kommunikation Kompressortreiber ↔ Hauptplatine gestört |

#### 2082 ERR08

| Bit | Text |
| --: | ---- |
| 0 | IPM Überhitzungsstopp |
| 1 | F14 – Kompressor-Phasenausfall |
| 3 | Eingangsstrom-Abtastfehler |
| 6 | EEPROM-Fehler |
| 7 | F10 – AC-Eingangsüberspannungsfehler |
| 15 | Kompressor-Übergeschwindigkeitsschutz |

#### 2083 ERR09

| Bit | Text |
| --: | ---- |
| 0 | F33 – Frequenzreduzierung wegen Kompressorstrom |
| 1 | F16 – Kompressor-Schwachmagnetisierungsalarm |
| 2 | Leistungseinheit Überhitzung |
| 4 | F22 – Frequenzreduzierung wegen AC-Eingangsstrom |
| 5 | EEPROM-Fehlerwarnung |
| 7 | F24 – EEPROM beschädigt / ungültige Fehlerdaten |

#### 2084 ERR10

| Bit | Text |
| --: | ---- |
| 8 | F120 – Lüftertreiber-Temperatursensorfehler |
| 9 | F108 – Lüftertreiber-IPM Überhitzungsfehler |
| 10 | F105 – Lüftertreiber externer Überstromfehler |
| 11 | F101 – Lüftertreiber Phasenausfall Versorgung |
| 12 | F112 – Lüftertreiber Strommess-/Abtastfehler |
| 13 | F102 – Lüftertreiber Startfehler |
| 14 | F113 – Lüftertreiber interner Überstromfehler |
| 15 | F109 – Lüftertreiber Überdrehzahlschutz |

#### 2085 ERR01 (Fehler 1) — **not** HW211 Fault0 layout

| Bit | Text |
| --: | ---- |
| 2 | Heizungsrücklauftemperatur-Sensorfehler |
| 3 | Heizungsauslasswassertemperatur-Sensorfehler |
| 4 | Hochdruckschutz |
| 5 | TC – Kein Kühlbetrieb bei niedriger Außentemperatur / Schutz |
| 6 | Niederdruckschutz |
| 7 | E030 – Unzureichender Wasserdurchfluss beim Abtauen |
| 8 | E032 – Durchflussschalterfehler |
| 9 | E04 – Elektroheizung Überhitzungsfehler |
| 10 | E19 – Primärer Frostschutzfehler |
| 11 | E29 – Sekundärer Frostschutzfehler |
| 12 | Frostschutz |
| 13 | E035 – Niedriger Wasserdurchfluss – Schutz |
| 14 | P42 – Raumtemperatursensorfehler |

#### 2086 ERR02

| Bit | Text |
| --: | ---- |
| 0 | P182 – Zu hohe Heißgastemperatur |
| 3 | E103 – Lüftermotor 1 Überlastfehler |
| 4 | E203 – Lüftermotor 2 Überlastfehler |
| 5 | Temp.diff. Ein-/Auslasswasser zu groß |
| 6 | E065 – Auslasswassertemperatur zu hoch |
| 7 | Mischwasser-Auslasswassertemperatur-Sensorfehler |
| 8 | Warmwasserrücklauftemperatur-Sensorfehler |
| 9 | Warmwasserauslasswassertemperatur-Sensorfehler |
| 10 | P105 – Zone 1 Raumtemperatursensorfehler |
| 11 | P106 – Zone 2 Raumtemperatursensorfehler |
| 12 | P107 – Zone 2 Mischtemperatursensorfehler |
| 13 | E08g – Kommunikationsfehler Thermostat Zone 1 |
| 14 | E08h – Kommunikationsfehler Thermostat Zone 2 |
| 15 | E122 – Fehlerhafte Regelung des Mischventils |

#### 2087 ERR03 (latch / 3× variants)

| Bit | Text |
| --: | ---- |
| 4 | Hochdruckschutz (3x) |
| 6 | Niederdruckschutz (3x) |
| 8 | E032 – Durchflussschalterfehler (3+) |
| 9 | E04 – Elektroheizung Überhitzungsfehler (3+) |
| 10 | E035 – Niedriger Wasserdurchfluss – Schutz (3+) |
| 12 | Frostschutz (3x) |

#### 2088 ERR04

| Bit | Text |
| --: | ---- |
| 0 | P182 – Zu hohe Heißgastemperatur (3+) |
| 2 | Temp.diff. Ein-/Auslasswasser zu groß (3x) |
| 3 | Auslasswassertemperatur zu niedrig (3x) |
| 4 | Auslasswasser Übertemperaturschutz (3x) |
| 7 | Externer Außentemperaturfühler Fehler |

#### 2089 ERR05

| Bit | Text |
| --: | ---- |
| 0 | Einlasswassertemperaturfehler |
| 1 | Auslasswassertemperaturfehler |
| 2 | Spulentemperaturfehler |
| 3 | Umgebungstemperaturfehler |
| 4 | Sauggastemperaturfehler |
| 5 | Frostschutztemperaturfehler |
| 6 | P152 – Verteilerrohr-Temperatursensorfehler |
| 7 | P03a – Pufferspeicher-Temperatursensorfehler |
| 9 | EVI Einlasstemperaturfehler |
| 10 | EVI Auslasstemperaturfehler |
| 11 | Abgastemperaturfehler |
| 12 | PP12 – Hochdrucksensorfehler |
| 13 | System 1 Drucksensorfehler |
| 14 | Niedrige Umgebungstemperaturfehler |
| 15 | Auslasstemperatur zu niedriger Schutz |

#### 2090 ERR06

| Bit | Text |
| --: | ---- |
| 8 | P03 – WW-Speicher-Temperatursensorfehler |
| 11 | Lüfter 1 Fehler |
| 12 | Lüfter 2 Fehler |
| 13 | Kommunikationsfehler Hauptplatine ↔ Lüfter 1 |
| 14 | E08c – Kommunikationsfehler Hydraulikmodul |
| 15 | Kommunikationsfehler Hauptplatine ↔ Lüfter 2 |

### MAIN 2139 — Schutz-/Frequenzbegrenzungs-Status

| Bit | Text |
| --: | ---- |
| 0 | Thermischer Regelzustand 1 (T30 hold) |
| 1 | Wasserspreizung (A24) |
| 2 | Thermischer Regelzustand 2 |
| 3 | Temperaturdifferenz (A27) |
| 4 | Niederdruck (A38) → may force pump 100% |
| 5 | AC-Eingangsstrom (T35) |
| 6 | Heißgastemperatur (T12) |
| 8 | SG-/Zusatzheizung |
| 9 | Remote-/WarmLink Mode 4 |
| 10 | 3-phasiger Stromlimiter |

### MAIN 2146 — System-/I/O status / capability

| Bit | Text |
| --: | ---- |
| 1 | HYD61:2049 Bit1 (H30=3) |
| 2,3,5 | Basis-/Capability (fixed) |
| 4 | Heiz-/Sommerabschaltung aktiv (1464/1465) |
| 6 | H07=2 / S10-Hardwaresteuerpfad aktiv |
| 8 | Service-/Engineering-Qualifizierung (ENG:A:5036) |
| 9 | V3.5 Capability bit (fixed) |

Baseline: V3.3/3.4 `0x002C`; V3.5 `0x022C`.

### MAIN 1016 — manual / silent status

Bits 0–2 named in register JSON (manual control / silent flags); firmware-gated in ha-foxair.

---

## Named code lists and aliases

### Explicit confirmed cloud → MAIN aliases (FoxAir)

From `cloud/register_resolver.py` `CONFIRMED_REGISTER_ALIASES`:

| Cloud code | MAIN |
| ---------- | ---: |
| `O01~023` | **2019** |
| `O15` | 2020 (EEV steps) |
| `O17` | 2022 (EVI EEV) |
| `S01~S10` | **2034** |
| `Power` | 1011 |
| `Mode` | 1012 |
| `ModeState` | 2012 |
| `code_version` | 2104 |
| `MainBoard Version` | 2105 |
| `Fault1`…`Fault10` | 2081…2090 |
| `Timer_Mute_On_En`…`TimerMuteOffMinute` | 1244…1249 |
| `compensate_slope` / `compensate_offset` | 1234 / 1235 |
| `2014` | 2014 |
| `2146` | 2146 |
| `CP1-1`…`CP1-7` / `1250` | 1250…1255 |
| `T57` | 2023 |

Plus hundreds of per-register `code` / `cloud_aliases` fields in `foxair_phnix_registers.json` (≈322 code keys indexed). Examples of **heating T-map** (not HW211):

| Code | MAIN | Notes |
| ---- | ---: | ----- |
| T01 | 2045 | **≠** HW211 2019 |
| T02 | 2046 | |
| T04 | 2048 | outdoor in use |
| T05 | 2051 | |
| T06 | **2055** | frost plate |
| T07 | 2052 | |
| T08 | 2047 | DHW tank |
| T14 | **2050** | manifold — **≠** HW211 State0 |
| SG Status | 2133 | |

### WarmLink 644 individual O app labels (aliases for bits inside 2019)

See table under MAIN 2019. Individual `O11` often unsupported in `getDataByCode`; alarm seen via packed `O01~023` bit 10.

### Legacy / candidate pack code

- `O01~014` — listed in aquatemp#99 and FoxAir codes as **candidate / not confirmed**; prefer `O01~023`.

### Product ID list

FoxAir `WARMLINK_PRODUCT_IDS` contains **31** Linked-Go product snowflake IDs used for `deviceList` discovery (same CRM as WarmLink app). Not copied here in full; see `cloud/warmlink_codes.py`.

---

## Heartbeat / live-data mechanics (all Linked-Go products)

Documented in FoxAir `docs/warmlink_polling_and_readback.md` from WarmLink Android 3.0.5 reverse engineering on GL9 / family **644** (2026-10-05):

1. App sends control write:
   - Endpoint: `POST …/app/device/control`
   - Body: `{ "param": [ { "deviceCode": "<id>", "protocolCode": "app_heartbeat", "value": "23205" } ] }`
   - **No `appId`** on this payload (unlike normal reads/writes that use `appId: "16"`).
2. Observed on bus after heartbeat: Mainboard traffic; FC16 live block covering roughly **2001–2090**.
3. Client settle: `WARMLINK_APP_HEARTBEAT_SETTLE_S = 1.0` then `getDataByCode` for `live_codes` only.
4. Heartbeat is **not** sent for: initial config scan, discovery-only, API debugger, single-read/write workers.
5. Heartbeat IoT errors: log once, still attempt live read without settle; auth errors use normal re-login.

**Reusable for HiTemp / S300:** same CRM endpoints and heartbeat can refresh DTU-uploaded registers. **Not reusable:** assuming the uploaded map is the FoxAir O/S packing — S300 still exposes DHW `dtu_wifi` addresses (e.g. `T01`=2019, State0=2050).

Normal data read (aquatemp#99 / WarmLink):

```text
POST …/device/getDataByCode?lang=en
{ "deviceCode", "appId": "16", "protocalCodes": [ … ] }
```

Write path (FoxAir confirmed): `app/device/control?lang=en` with `param[]` of `{deviceCode, protocolCode, value}` (and usually `appId` for non-heartbeat commands).

---

## PHNIX fancoil Modbus (28xxx / 46xxx) — separate family

Unrelated to FoxAir GL9 MAIN heat-pump maps and to HW211. Documented for completeness so they are not confused with heating/DHW addresses.

### Holding (write with FC16 / `write_multiple`)

| Address | Role | Values |
| ------: | ---- | ------ |
| 28301 | On/Off | 0/1 |
| 28302 | Mode | 0 Auto, 1 Cool, 2 Dehumidify, 3 Fan, 4 Heat |
| 28303 | Fan speed set | 2…6 (HA ESP example) |
| 28310 | Cool setpoint | °C×10 |
| 28311 | Heat setpoint | °C×10 |

LogicMachine: require `"writable": true, "write_multiple": true` for 28302.

### Input / read

| Address | Role |
| ------: | ---- |
| 46801 | Air temperature (°C×10) |
| 46802 | Coil temperature (°C×10) |
| 46803 | Fan speed status (0 Off … 6 Auto) |
| 46804 | Fan RPM |

Sources: HA community thread + LogicMachine tid=5743 (attachment “Modbus protocol.xls” referenced there; not re-hosted here).

---

## Size summary (bit maps extracted)

| Map | Named bits extracted |
| --- | -------------------: |
| 2019 `O01~023` | **16** |
| 2034 `S01~S10` (+ SG) | **16** |
| 2018 (ha-foxair expansion) | **4** |
| Fault 2081–2090 | **95** (16+6+6+8+13+14+6+5+15+6) |
| 2139 limiter | **10** |
| 2146 I/O status | **8** |
| 1016 manual/silent | **3** |
| Other BITFIELDs in JSON (2080, 2106, 2109, 2152, 6073–6080, …) | remaining of **184** total named bits across **29** BITFIELD registers |
| Confirmed cloud↔MAIN aliases (resolver table) | **~40** explicit + ~322 code keys in register JSON |

---

## Reusable-for-HW211 takeaways

1. **Do reuse:** Linked-Go heartbeat `app_heartbeat=23205`, `appId=16`, BINARY MSB packing rules, and the idea that live O/S may be packed into a status word rather than named codes.
2. **Do not reuse:** FoxAir addresses **2019 / 2034 / 2050 / 2055** bit meanings or T/O code→register tables on Trianco S300 — they collide with `dtu_wifi` (ambient, State0, blank/frost).
3. **S300 O/S truth remains** workbook **`2050`/`2051`** (and Fault0 **`2085`**), as in `HW211_REGISTER_COMPARISON.md`. FoxAir proves why cloud probes for `O01~023` / `S01~S10` return empty on DHW: those codes target a different board map.
4. **Reject** `O03 ↔ 2055`: heating 2055 is frost temp `T06`; DHW O03 is **2050 bit 10**.
5. Fancoil **28xxx/46xxx** maps are a third PHNIX product line — ignore for S300 heat-pump work.

---

## Provenance notes

- Primary JSON: `/tmp` clone of FoxAir_Control `data/foxair_phnix_registers.json` (240 545 bytes, 6874 lines) at commit `a98b16c` (2026-11-19).
- Bit polarity for 2034 from `CONTACT_BIT_MAP_2034` (authoritative for decoder UI).
- No HW211 workbook rows were altered; this file is additive research only.
- No git commit was created for this documentation.
`)