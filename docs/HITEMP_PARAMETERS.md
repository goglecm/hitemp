# HiTemp parameter guide

This guide covers the HiTemp heat pump with product ID `1245226668902080512`,
sold for example as the Trianco S300 air source heat pump.
It lists every code the HiTemp app (iOS) showed on 2026-11-12 for the user
password `002` and the installer password `066`, written exactly as the app
shows them, spelling mistakes included. It also gives the raw value the cloud
returned for each code that day, how Home Assistant shows it, and what we
understand it does.

There may be more codes than these. Codes the app doesn't show are listed
where the cloud reports them, but they weren't seen in the app.

## Read this first

Changing the wrong setting can damage the heat pump or stop it from heating.

- Only change a code if this guide explains it and its confidence is
  **documented** or **observed**. Leave **uncertain** codes alone.
- Home Assistant only writes the codes listed as `number` or `select` below,
  and only within the range the app allows. Installer settings start disabled
  and must be enabled on their entity page first.
- Note the current value before you change anything; the `app_value`
  attribute of each entity has the value seen in the app on 2026-11-12.
- Every change is probably stored in the controller's memory, which allows a
  limited number of writes (`T21` counts them). Don't let automations change
  settings every few minutes; your log showed `R01` being written that often.
- If in doubt, ask an installer.

Confidence means:

| Confidence | Meaning                                                                              |
| ---------- | ------------------------------------------------------------------------------------ |
| documented | Stated in the Trianco S300 manual or in PHNIX manuals for the same controller family |
| observed   | Clear from the app's name and seen behaving that way in the app or the log           |
| uncertain  | Not documented and not observed; the meaning is a guess or unknown                   |

Sources:

- the HiTemp app screens and two Home Assistant logs of a Trianco S300 from
  2026-11-12;
- the [Trianco S300 user manual](https://manualspro.net/233207-trianco-s300-wall-hung-air-source-heat-pump-user-manual)
  (modes, fan setting, defrost, fault codes);
- PHNIX controller manuals for the same board family;
- [victor987/hitemp](https://github.com/victor987/hitemp), which scanned every
  code of an Indol PV300 water heater with the same product ID;
- [FoxAir_Control](https://github.com/dosordie/FoxAir_Control), which
  documented the same cloud for a related board.

## Source ids

Findings in this guide and in the parameter file cite these ids.

| Id               | Source                                                                                                                                                                                                   |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `workbook`       | EVO270-1 Modbus workbook, `dtu_wifi` sheet, via [sjtrny/esphome-hw211](https://github.com/sjtrny/esphome-hw211) `protocol/hw211_modbus.json`                                                             |
| `workbook-hw211` | Same workbook, `hw211` sheet. Used only where the `dtu_wifi` sheet is blank                                                                                                                              |
| `darksplat`      | [Darksplat/EVOHeat-EVO270-ESP32-Modbus](https://github.com/Darksplat/EVOHeat-EVO270-ESP32-Modbus) field notes and `data/status_bits.csv`                                                                 |
| `victor`         | [victor987/hitemp](https://github.com/victor987/hitemp) `DEVICE_PARAMETERS.md` cloud scan                                                                                                                |
| `aquatemp-130`   | [radical-squared/aquatemp#130](https://github.com/radical-squared/aquatemp/issues/130) HiTemp iOS capture                                                                                                |
| `aquatemp-108`   | [radical-squared/aquatemp#108](https://github.com/radical-squared/aquatemp/issues/108)                                                                                                                   |
| `trianco-manual` | Trianco ActivAir S300 manual                                                                                                                                                                             |
| `evoheat-manual` | [EvoHeat Evo270 manual](https://evoheat.com.au/wp-content/uploads/2021/07/pdf-manual-Evo270-Manual.pdf) and the [EVO270-E manual](https://evoheat.com.au/wp-content/uploads/2026/10/MANUAL-EVO270-E.pdf) |
| `ha-230400`      | [Home Assistant community thread 230400](https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400)                                                                            |
| `schematic`      | Activair indoor heat pump wiring diagram, code 20230302-0005                                                                                                                                             |
| `app`            | HiTemp app screens on a Trianco S300                                                                                                                                                                     |
| `s300`           | Logs and remote-contact tests from that S300                                                                                                                                                             |

See also:

- [HW211 register comparison](HW211_REGISTER_COMPARISON.md) — official EVO270 /
  HW211 Modbus bitfields for `2050`/`2051`/`2085`, named↔numeric aliases,
  Darksplat field CSVs, OEM OUT1–5≡O01–O05, app poll evidence, FoxAir
  conflicts, and match status vs this integration;
- [HW211 `dtu_wifi` full register map](HW211_REGISTER_MAP_FULL.md) — complete
  226-register workbook extract (appendix);
- [`_research_app_cloud_api.md`](_research_app_cloud_api.md) — HiTemp iOS
  `getDataByCode` poll list (`2050`/`2051`, `appId` 13).

## How Home Assistant shows the codes

- **Names** start with the code and a short name and end with the HW211
  register in brackets, where the `dtu_wifi` workbook gives one. The app's
  own name is kept in the `app_name` attribute.

  | Kind                         | Pattern                                     | Example                                   |
  | ---------------------------- | ------------------------------------------- | ----------------------------------------- |
  | Code with a register         | `{Code} {Meaning} ({register})`             | `T01 Ambient temperature (2019)`          |
  | Code without a register      | `{Code} {Meaning}`                          | `T07 Discharge temperature unconfirmed`   |
  | Register without a code      | `Reg {register} {Meaning}`                  | `Reg 1158 Heartbeat echo`                 |
  | Named bit                    | `{Code} {Meaning} ({register}.{bit})`       | `O01 Compressor running (2050.8)`         |
  | Raw bit                      | `Reg {register} bit {n} ({Code} {meaning})` | `Reg 2050 bit 8 (O01 compressor running)` |
  | Raw bit of a code            | `{Code} bit {n}`                            | `T08 bit 3`                               |
  | Several registers            | `{Code}-{Code} {Meaning} ({first}-{last})`  | `L06-L07 Timer 1 start (1134-1135)`       |
  | Status sensor of a named bit | `{Meaning} ({register}.{bit})`              | `Compressor running (2050.8)`             |

  Running means the compressor, a heater, the fan or a defrost is working;
  on or active means an output or a stage; open or closed is a switch input,
  with the polarity the workbook gives. Where the workbook gives none, the
  name doesn't claim one.

- **Enabled by default:** every sensor and binary sensor, so its value is
  recorded, including diagnostics and codes whose meaning is unknown. Of the
  writable controls, only the daily ones (`mode_real`, `M17`, `R01`, `R03`,
  `R04`, `R05`, `R06`) are enabled; installer settings start disabled.
- **Sections** on the device page:
  - **Controls**: the climate entity, `mode_real`, `R01`, `R03`, `R04`,
    `R05`, `R06` and `M17`, the settings meant for daily use.
  - **Sensors**: live temperatures, the EEV position, running hours,
    whether the compressor, heater and defrost are running, vacation mode,
    and the calculated superheat and water temperature rise.
  - **Configuration**: installer settings you can write, disabled by default.
  - **Diagnostic**: settings you can only read, switch inputs, outputs,
    status and faults, the unconfirmed `T07`, `T09` and `O29`, and the codes
    whose meaning is unknown.
- **Values with labels** read `label (raw)`, for example `Standard (0)`, so
  both the app's text and the raw number are visible. A raw value the app has
  no label for reads like `1 (not listed in the app)`.
- **Attributes** on every parameter: `code`, `app_name`, `level` (password),
  `range` and `app_value` as seen in the app, `confidence`, `description`,
  `guidance`, `register` and `source` (the [source ids](#source-ids) behind
  the meaning). Labelled values also have `raw_value`. The static attributes
  aren't stored in the history database.
- **Unavailable** means the cloud returned no usable value for the code, or
  the heat pump is offline. Code-based entities never show Unknown.

## Day-to-day use

- **Set the water temperature with `R01`** (or the climate entity, which
  writes the same code), 38-60 °C in steps of 0.5 °C.
- **Start and stop heating** with the remote on/off input `S01`, the pair of
  terminals on the board. Closing them asks the heat pump to heat; heating
  then starts once the controlling sensor is `R03` below `R01`.
- **Operating mode `mode_real`**: Eco (heat pump only), Hybrid, Fast heating
  or Intelligent, as on the app's Select Mode page. Without an electric heater
  fitted, use Eco.
- **Fan after heating `M17`**: whether the fan keeps running (low or high) or
  stops once the water is at its target. It doesn't change the fan while
  heating.
- Leave everything else as it is unless you have a reason and understand the
  related codes.

## How the codes work together

- **Start and stop.** With `R17 = NO` the bottom sensor `T02` controls the
  compressor: heating starts when `T02` is `R03` below `R01` and stops at
  `R01`. With `R17 = YES` the top sensor `T03` and `R18` are used instead. On
  your installation the bottom sensor is on the return pipe and the top
  sensor on the flow pipe. `S01` is the remote on/off input, the `DI05` and
  `GND` terminals in the manual, which are linked at the factory and can be
  wired to a thermostat or volt-free contact. The named code `S01` stays
  empty, but bit 0 of `2050` follows the contacts (the S01 Remote switch open
  (2050.0) sensor). Opening them sets `Power` to 0 and closing them sets it to
  1, so the Power sensor and the climate entity follow them. Each switch is
  written to the controller's memory (see `T21` and `H01`). After stopping, the
  compressor waits 3 minutes before it starts again.
- **Operating modes** (Trianco S300 manual, app names in brackets): Eco (heat
  pump only), Standard (Hybrid: electric heater after `R06` minutes if the
  target isn't reached), High demand (Fast heating: electric heater without
  the delay), Intelligent (chooses between them by ambient temperature) and
  Vacation. `mode_real` (1013) holds the chosen mode (0 Intelligent, 2 Eco,
  3 Hybrid, 4 Fast heating) and can be set from Home Assistant. `Mode`
  (1012), which the workbook calls the requested mode, read 7 while on
  vacation on a Trianco S300, when `mode_real` kept the mode to return to.
- **Timer page.** Vacation mode sets bit 0 of `1129` and stores the date in
  `L02`-`L04` (year 20YY, month, day). The two timers keep their on and off
  times in `L06`-`L13` (hour, minute pairs) and their four switches in bits
  0-3 of `1133`. The app's Align the device time writes the clock to
  `M12`-`M16` (minute, hour, day, month, year) and set `1151` to 1. These are
  read-only in Home Assistant.
- **Electric heater (booster, output `O02`).** In Standard mode it starts if
  the target isn't reached after `R06` minutes, in High demand mode without
  the delay, in Eco mode never; it decides with the `R03` differential.
  Intelligent mode uses Eco above `R10` ambient (`T01`), Standard between
  `R09` and `R10` and High demand between `R08` and `R09`. With `R07 = YES`
  the heater presumably replaces the heat pump below `R08` (-5.0 °C on your
  unit); without a heater fitted, that would leave no heating. With `R04 =
YES` the heater heats to `R05` instead of `R01`. `S05` (heater
  acceleration) probably starts it without the delay, bit 9 of `2050` shows
  it running, and `O09` counts its hours. `M06` (1014, booster mode) stayed 0
  on a Trianco S300 while the heater ran, so it isn't the heater state.
- **Expansion valve (EEV).** With `E01 = Automatic` the EEV starts at `E03`
  when the compressor starts, then opens or closes to keep the superheat
  (`T05 - T04`) at `E02`, never closing below `E04`. During defrost it moves
  to `E05`. `O07` is its current position.
- **Defrost.** A defrost can start when the coil `T04` is below `D01` and at
  least `D03` minutes have passed since the last one. It ends when `T04`
  reaches `D02` or after `D04` minutes, and lasts at least `D05` minutes.
  `D06` chooses the method; `D07` is only used by the intelligent method.
  The manual says a defrost takes 2 to 10 minutes, during which the
  compressor keeps running and the fan stops.
- **Disinfection (anti-legionella).** `G01`-`G04`: heat to `G01` every `G04`
  days at `G03` o'clock for `G02` minutes. `G02 = 0` most likely means it
  never runs.
- **Fan.** The controller runs the fan while heating (`O29` may be its
  speed, but it read 0 on a Trianco S300). `M17` sets what it does once the target is reached: low, high or
  off (Trianco S300 manual). `O04` and `O05` are the high and low speed
  outputs, and `/01` sets what `OUT05` drives.
- **Units.** `H07` is the unit the heat pump reports in. Home Assistant's
  **Temperature Unit** select must match it.
- **Cloud connection.** `H31` must stay on `DTU&WIFI`, `H30` is the bus
  address and `H32` how often the heat pump uploads to the cloud.
- **Protection.** `R12` forces the compressor off below that ambient
  temperature. `S03` and `S04` are the low and high pressure switches.
  `R15`, `R19` and `R20` are compressor limits whose exact meaning is
  unknown.
- **Solar circuit.** `N01`-`N11` and outputs `O06` and `/02`. There is no
  solar circuit on your installation.

## What your heat pump showed (log of 2026-11-12)

- **EEV:** `O07` read 480 (the `E05` value) while stopped or defrosting,
  240 (`E03`) when heating started, then worked down to 100 (`E04`) and
  mostly stayed there.
- **Superheat:** `T05` was often far below `T04` (for example -13 °C against
  0.5 °C), so the calculated superheat was negative while `E02` asks for
  +5 °C. That explains why the EEV sat at its minimum `E04`. The data can't
  tell whether this comes from the sensor placement or the refrigerant
  circuit; an installer should check it before anyone changes `E02` or `E04`.
- **T06** isn't shown in the app. The vendor file calls it the solar
  temperature, but it rose from about 63 to 87 °C while the compressor ran
  and fell when it stopped, which fits the compressor discharge (hot gas)
  temperature. The entity keeps the discharge name with confidence
  uncertain until that is confirmed.
- **T10** (the displayed temperature) always equalled `T03`.
- **Fan:** `M17` changed from 1 to 2 after the climate entity's fan mode was
  set to high. According to the manual that only changes what the fan does
  after the target is reached.
- **R01 Target water temperature (1104)** was written every few minutes by something other than the app,
  between 56 and 60 °C.
- **Register 1158** read 23205 from 10:20 to 11:55 and from 14:15 to 15:00,
  probably while the app was open, and 0 otherwise. 23205 is the value of the
  app's live data request (see below).
- **Empty codes:** the cloud returned nothing for `S01`-`S06`, `O01`-`O06`,
  `O10`-`O15`, `T11`, `T12`, `ver` and `software_code`, even while `1158` read 23205.

A fourth log, with one read per minute and no changes in the app (18:44 to
23:13), showed:

- Three defrosts, at 19:12, 20:01 and 20:48, each about 3 minutes long and
  45-49 minutes apart (`D03` = 45). Each started with the coil (`T04`) at
  about -3 °C (`D01`). During each, bit 2 of `2051` was set, bits 11 and 12
  of `2050` cleared and bit 10 set, the EEV moved to 480 (`E05`), the suction
  temperature jumped to 25-36 °C and the coil warmed up.
- The unit was switched off at 21:31:00 and 22:55:06 and on at 22:18:06 with
  the remote on/off contacts (`S01`). `S01` stayed empty, but `Power` changed
  at the next read each time (9 to 54 seconds later), and the compressor
  stopped or started about a minute after that. While off, `2050` held only
  bits 0 and 5 (bit 2 came back 2-3 minutes later) and the EEV sat at 480.
  Each switch raised `T21`/`2027` by 4, so the on/off state is written to the
  controller's memory, most likely because `H01` = YES remembers it.
- After each start the EEV opened at 240 (`E03`) and worked down to 100
  (`E04`) within about 20 minutes, when bit 2 of `2050` cleared (that bit
  tracked roughly with coil temperature in this log, but the official workbook
  names it S03 low-pressure open — treat the coil correlation as unconfirmed).

A third log, while modes, vacation, the timers and the clock were changed in
the app (17:37 to 18:16), showed:

- `Mode`, `mode_real` and `ModeState` followed the app's modes: 2 Eco, 3
  Hybrid, 4 Fast heating, 0 Intelligent. Vacation set `Mode` to 7 only.
- In Fast heating, bit 9 of `2050` was set, the app showed the electric
  heater (O02) on and its Electric heating switch on, while `M06` stayed 0.
- Bits 5, 8, 11 and 12 of `2050` stayed set while the compressor ran.
- The vacation date, timer times and switches, and the clock appeared in the
  `L`, `1129`, `1133` and `M12`-`M16` codes described above.
- `T21` (equal to `2027`) rose with every settings change.
- `2011`-`2014` hold the PCB software version (1.0) and code (679) and the
  display's version (1.0) and code (741), as on the app's About page.
- `T07` read -30.0 and `O29` 0 throughout, so they aren't used on the S300.

A second log, with version 4.1.0 sending the live data request before every
poll (16:45 to 17:01), showed:

- The cloud accepted the request every time, but `1158` stayed 0.
- The cloud accepted all the extra live codes. Only `ModeState` had a value
  (2, the same as `Mode`); the fault words, the PCB version codes and the
  packed switch and output words were empty.
- The S, O, `T11` and `T12` codes stayed empty.
- With each value the cloud also returns its data type and declared range;
  they are listed in the tables below.

## Live data (the app heartbeat)

The official apps send `app_heartbeat = 23205` to the heat pump while they
are open. On the FoxAir boards documented by
[FoxAir_Control](https://github.com/dosordie/FoxAir_Control), the board then
uploads its live block to the cloud: packed switch and output words, raw fault
words `Fault1`-`Fault10`, `ModeState`, and the PCB software code
(`MainBoard Version`) and version (`code_version`).

The integration does the same before each poll (every 5 minutes), waits 2
seconds, then reads the codes. It also asks for those live codes separately,
so a code the heat pump doesn't know can't break the poll; codes the cloud
rejects are not asked for again until the next restart. The FoxAir packed
codes (`O01~023`, `S01~S10` and the shorter forms) are not requested for this
heat pump: on this board register `2019` is the ambient temperature, not a
packed output word. The individual `O` and `S` letters are still requested.

What we know for HiTemp:

- Register `1158` read 23205 for hours in one log, probably while the app was
  open. The integration's own request, sent every 5 minutes, has not changed
  it.
- With the request sent before every poll, the cloud still returned nothing
  for the S and O codes, the fault words or the PCB versions. Only `ModeState`
  had a value. So on HiTemp the heartbeat does **not** fill named S/O through
  the cloud.
- **Why named O/S stay empty (app evidence):** a Proxyman capture of HiTemp
  iOS v1.3.3 ([aquatemp #130](https://github.com/radical-squared/aquatemp/issues/130))
  shows the official app's periodic `getDataByCode` list includes **`2050` and
  `2051`**, and does **not** request named `O01`–`O06` or any `S*` (it does
  poll scalars like `O07`–`O09` and, oddly, lone **`O03`**). The app UI that
  shows compressor / heater / fan therefore almost certainly **unpacks
  `2050`/`2051` on the client**. The named O/S codes staying empty in the
  cloud is expected for this product, not a failed heartbeat.

The scan of an Indol PV300 with the same product ID by
[victor987/hitemp](https://github.com/victor987/hitemp) already found that the
S codes never return data and that operating state lives in packed words such
as `2050` (bit 8 compressor, bit 9 heater). The integration therefore reads
`2050` and `2051` and shows each named O and S code, and every other bit of
those words, as a binary sensor. The other codes that scan found are
diagnostic sensors (see [Read from the probe request](#read-from-the-probe-request)).

The bits decoded so far on a Trianco S300. Official meanings come from the
EVO270 `dtu_wifi` workbook (see [HW211 register comparison](HW211_REGISTER_COMPARISON.md)).
The confidence is that of the entity for the bit.

| Word   | Bit    | Official (`dtu_wifi`)                    | S300 observation                                                                    | Confidence |
| ------ | ------ | ---------------------------------------- | ----------------------------------------------------------------------------------- | ---------- |
| `2050` | 0      | S01 remote on/off (1 = OP, open)         | set while the unit is switched off (contacts open)                                  | observed   |
| `2050` | 2      | S03 low pressure switch (1 = OP, open)   | cleared when the coil fell to about −3 °C in one log; not yet matched to the switch | documented |
| `2050` | 5      | S06 external heat source, polarity blank | often set so far; why on this install is unknown                                    | uncertain  |
| `2050` | 8      | O01 compressor                           | the compressor runs (**Compressor running (2050.8)**)                               | observed   |
| `2050` | 9      | O02 electrical heater                    | the electric heater is on (**Heater running (2050.9)**)                             | observed   |
| `2050` | 10     | O03 4-way valve                          | set while defrosting                                                                | observed   |
| `2050` | 11, 12 | O04 fan high / O05 fan low (or solar)    | the fan runs; which bit is which speed isn't known yet                              | uncertain  |
| `2051` | 1      | O15 DTU&WIFI online (app code O13)       | always set so far while online                                                      | observed   |
| `2051` | 2      | O16 defrost (app code O14)               | defrosting (**Defrost running (2051.2)**)                                           | observed   |

To find out, download the diagnostics of the heat pump while it runs. The
`live_data` section lists the result of the last heartbeat, which codes had a
value and which stayed empty, and any packed switch words as value, hex and
bits. The **Request live data** option in the integration's settings turns
the heartbeat off.

Named S/O emptiness is explained by the #130 poll list above. Further captures
(Android, full response bodies, or JADX of the bit→label map) would still help
explain the lone `O03` poll and confirm Android matches iOS.

## How often values update

The heat pump uploads its values to the cloud every `H32` minutes (1 on your
unit). Home Assistant reads the cloud every 5 minutes by default, counted from
when the integration started; the **Update interval** option in the
integration's settings changes that, down to 1 minute. After a change made
from Home Assistant it reads again straight away, but the heat pump's own
upload can take up to `H32` minutes to show the result.

To find out what a setting in the app changes, watch the **Code changes**
sensor: after each read it lists the codes whose values changed, with the old
and new values, leaving out live readings such as temperatures. The same list
is written to the log at the info level.

## How values are written

- Only the codes listed as `number` or `select` are written, within the app's
  range and step.
- The cloud declares a data type for each code. Codes of the whole-number
  types `DIGI1`, `DIGI2` and `DIGI4` are written as whole numbers (`"2"`),
  the form the heat pump itself reports. Temperatures (`TEMP1`) and `DIGI7`
  codes are written as decimals (`60.0`), as before. Selects send the raw
  value (`"1"`).
- `R06` is declared as `DIGI4` with a range of 0-90 while the app offers
  0-450 minutes and the heat pump holds 200, so it is most likely stored in
  5-minute units. Home Assistant writes it in steps of 5.
- The cloud's declared ranges are wider than the app's for some codes, for
  example 38-75 °C for `R01`. Home Assistant keeps to the app's ranges.
- Right after a change the cloud returns the value that was written, before
  the heat pump has confirmed it. Check the app after a few minutes the first
  time you change a setting from Home Assistant.

## Status and faults

| Entity        | Shows                                                                                                                               |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Status        | Whether the cloud reports the heat pump online                                                                                      |
| API Status    | Whether the integration is logged in and reaching the cloud                                                                         |
| Cloud status  | OK, Session expired, Login rejected, Cannot connect or Cloud error, with the message and the time it started                        |
| Fault         | On while the cloud reports a fault                                                                                                  |
| Fault details | `No fault`, the cloud's description of the fault, or that it gave none; raw fault words as attributes when the heat pump sends them |

The cloud sends the fault description itself. For reference, the Trianco S300
manual lists these fault codes:

| Code  | Fault                                                        | What to check                              |
| ----- | ------------------------------------------------------------ | ------------------------------------------ |
| `P01` | Bottom water temperature sensor failure                      | The bottom sensor                          |
| `P02` | Top tank water temperature sensor failure                    | The top sensor                             |
| `P04` | Ambient temperature sensor failure                           | The ambient sensor                         |
| `P05` | Coil temperature sensor failure                              | The coil sensor                            |
| `P07` | Suction temperature sensor failure                           | The suction sensor                         |
| `P09` | Anti-freeze temperature sensor failure                       | The anti-freeze sensor                     |
| `P81` | Discharge overheating protection                             | Refrigerant leak or blockage               |
| `E01` | High pressure protection                                     | High pressure switch, refrigerant blockage |
| `E02` | Low pressure protection                                      | Low pressure switch, refrigerant leak      |
| `E03` | Water flow failure                                           | Water flow, water pump                     |
| `E04` | Discharge overheating protection                             | Refrigerant leak or blockage               |
| `E07` | Anti-freeze protection                                       | Water flow                                 |
| `E08` | Communication failure between the display and the main board | The display cable                          |
| `E09` | Winter frost protection, ambient too low                     | Drain the water side heat exchanger        |
| `E10` | Discharge overheating three times                            | Refrigerant leak or blockage               |

The cloud's Chinese reply `请重新登录` means "please log in again": the
session expired, and the integration logs in again by itself.

## Codes from the app, password 002 (user)

### Target temperature and booster

| Code  | App name                                       | App range                     | App value  | Raw cloud value | Cloud type and range | Home Assistant   | Confidence |
| ----- | ---------------------------------------------- | ----------------------------- | ---------- | --------------- | -------------------- | ---------------- | ---------- |
| `R01` | Target temp                                    | 38.0C to 60.0C, steps of 0.5C | Set by you | `60.0`          | TEMP1, 38 to 75      | number, Controls | documented |
| `R03` | Hysteresis of heat pump startup(bottom sensor) | 1.0C to 20.0C, steps of 0.5C  | 5.0C       | `5.0`           | TEMP1, 1 to 20       | number, Controls | documented |
| `R04` | Enable R05 as setpoint of booster?             | NO, YES                       | NO         | `0`             | ENUM, 0 to 1         | select, Controls | documented |
| `R05` | Setpoint of booster                            | 30.0C to 90.0C, steps of 0.5C | 55.0C      | `55.0`          | TEMP1, 30 to 90      | number, Controls | documented |
| `R06` | Booster startup delay                          | 0Min to 450Min, steps of 1Min | 200Min     | `200`           | DIGI4, 0 to 90       | number, Controls | documented |

- **R01 Target water temperature (1104)**: Target water temperature, the main control. The climate entity sets the same value. Heating starts when the controlling sensor (T02 bottom, or T03 top with R17 = YES) drops R03 below R01, and stops at R01. Each change is probably stored in the controller's memory, which allows a limited number of writes (see T21), so avoid automations that change R01 every few minutes.
- **R03 Start hysteresis bottom (1106)**: How far below R01 the bottom sensor (T02) must drop before heating restarts. A small value keeps the water closer to R01 but starts the compressor more often; very small values cause short cycling. Your heat pump uses 5.0 °C.
- **R04 Use R05 as booster setpoint (1107)**: Whether the booster heats to its own setpoint R05 instead of R01. Values: NO (0), YES (1).
- **R05 Booster setpoint (1108)**: Water temperature the booster heats to when R04 = YES.
- **R06 Booster start delay (1109)**: How long the heat pump runs before the booster may help. The cloud declares a range of 0-90 for the app's 0-450 minutes, so the heat pump most likely stores it in 5-minute units; Home Assistant writes it in steps of 5.

**R04, R05, R06:** Electric heater logic (Trianco S300 manual): in Standard mode the heater starts if the target isn't reached after R06 minutes; in High demand mode it starts without the delay; in Eco mode it never starts; both decide with the R03 differential. Intelligent mode picks Eco above R10 ambient (T01), Standard between R09 and R10 and High demand between R08 and R09; with R07 = YES the heater presumably replaces the heat pump below R08. The heater output is O02. Only relevant with an electric heater fitted.

### Expansion valve

| Code  | App name                        | App range                      | App value | Raw cloud value | Cloud type and range | Home Assistant                  | Confidence |
| ----- | ------------------------------- | ------------------------------ | --------- | --------------- | -------------------- | ------------------------------- | ---------- |
| `E01` | EEV adjustment mode             | automatic, Manual              | automatic | `1`             | ENUM, 0 to 1         | select, Configuration, disabled | documented |
| `E02` | Target degree of supreheat      | -20.0C to 20.0C, steps of 0.5C | 5.0C      | `5.0`           | TEMP1, -20 to 20     | number, Configuration, disabled | documented |
| `E03` | Original position of EEV        | 0N to 500N                     | 240N      | `240`           | DIGI2, 0 to 500      | number, Configuration, disabled | documented |
| `E04` | Minimal opening position of EEV | 0N to 500N                     | 100N      | `100`           | DIGI2, 0 to 500      | number, Configuration, disabled | documented |

- **E01 EEV control mode (1055)**: Whether the electronic expansion valve (EEV) regulates itself (Automatic) or not (Manual). 1 = Automatic is confirmed by the PHNIX PC1001 manual; the app lists the options in a different order. Values: Manual (0), Automatic (1). Keep Automatic. In Manual the valve no longer follows the superheat target E02, which can return liquid refrigerant to the compressor or starve the coil.
- **E02 Target superheat (1056)**: Superheat the EEV aims for: suction minus coil temperature (T05 - T04). Compare it with T05-T04 Superheat (2023-2022). A higher target closes the valve further (less refrigerant, safer for the compressor, less heat); a lower one opens it. Change it only with an installer: too little superheat can return liquid to the compressor.
- **E03 EEV start position (1057)**: EEV opening when the compressor starts. The valve starts at E03 (O07 reads 240 at start-up) and then regulates towards E02.
- **E04 EEV minimum position (1058)**: Smallest opening the EEV may regulate down to. Your EEV often sits at this minimum because the measured superheat is below E02. Lowering E04 lets it close further and reduces the refrigerant flow; don't change it to chase the superheat reading without an installer.

### Unit settings

| Code  | App name                     | App range  | App value | Raw cloud value | Cloud type and range | Home Assistant                  | Confidence |
| ----- | ---------------------------- | ---------- | --------- | --------------- | -------------------- | ------------------------------- | ---------- |
| `H98` | Model selection              | 0X08, 0X18 | 0X08      | `2`             | ENUM, 2 to 3         | sensor, Diagnostic              | documented |
| `H99` | Compensate to the shown temp | NO, YES    | NO        | `0`             | ENUM, 0 to 1         | select, Configuration, disabled | uncertain  |

- **H98 Model selection (1074)**: Hardware model the controller is configured for. Values: 0X08 (2), 0X18 (3). Never change it: it tells the controller which hardware it drives. Your heat pump reports 2, which the app shows as 0X08. The cloud declares a range of 2-3, which supports 3 = 0X18, but that isn't confirmed.
- **H99 Display temperature compensation (1075)**: App description: 'Compensate to the shown temp'. Values: NO (0), YES (1). Not documented; it possibly corrects the displayed temperature. Keep NO.

### Temperatures and EEV position

The raw values of live readings are the range seen in the log.

| Code  | App name                               | App range               | App value | Raw cloud value   | Cloud type and range | Home Assistant  | Confidence |
| ----- | -------------------------------------- | ----------------------- | --------- | ----------------- | -------------------- | --------------- | ---------- |
| `T01` | Ambient temperature                    | Steps of 0.5C           | 18.0C     | `17.5` to `22.0`  | TEMP1                | sensor, Sensors | observed   |
| `T02` | Bottom temperature                     | Steps of 0.5C           | 33.5C     | `25.5` to `52.0`  | TEMP1                | sensor, Sensors | observed   |
| `T03` | Top temperature                        | Steps of 0.5C           | 37.0C     | `30.0` to `55.5`  | TEMP1                | sensor, Sensors | observed   |
| `T04` | Coil temperature                       | Steps of 0.5C           | 0.5C      | `-5.0` to `8.5`   | TEMP1                | sensor, Sensors | documented |
| `T05` | Suction temperature                    | Steps of 0.5C           | -13.0C    | `-16.0` to `21.5` | TEMP1                | sensor, Sensors | documented |
| `T10` | Temperature value shown on APP/display | Steps of 0.5C           | 37.0C     | `30.0` to `55.5`  | TEMP1                | sensor, Sensors | observed   |
| `O07` | EEV current position                   | 0N to 500N, steps of 1N | 100N      | `100` to `480`    | DIGI1                | sensor, Sensors | observed   |

- **T01 Ambient temperature (2019)**: Air temperature at the heat pump's air inlet. The booster settings R08-R10 and the compressor limit R12 compare against it.
- **T02 Bottom water temperature (2020)**: Water temperature at the controller's bottom sensor. The controller is made for a tank with bottom and top sensors; on your installation it is on the return pipe. With R17 = NO this sensor controls heating: it starts when T02 is R03 below R01.
- **T03 Top water temperature (2021)**: Water temperature at the controller's top sensor; on your installation the flow pipe. T03 - T02 is the T03-T02 Water temperature rise (2021-2020) sensor. T10 showed the same value as T03 throughout your log.
- **T04 Coil temperature (2022)**: Temperature of the evaporator coil, the coil the air passes through. Defrost starts and ends on this temperature (D01, D02). It is also the reference for the superheat (T05 - T04).
- **T05 Suction temperature (2023)**: Refrigerant temperature in the suction pipe, the gas going from the coil to the compressor. It is not an air temperature. With E01 = Automatic the EEV keeps T05 - T04 (superheat) at E02. When T05 stays well below T04, as in your log (about -13 °C against 0 °C), the superheat is negative and the EEV closes to its minimum E04. The data can't tell whether that comes from the sensor placement or the refrigerant circuit; ask an installer rather than changing E02 or E04.
- **T10 Displayed water temperature (2025)**: Water temperature shown on the display and in the app; the climate entity's current temperature. Equal to T03 throughout your log.
- **O07 EEV position (2060)**: Current opening of the electronic expansion valve (EEV), 0-500 steps. On your heat pump it reads 480 (E05) while stopped or defrosting, starts at E03 (240) when heating begins, then works down towards E04 (100) as it regulates the superheat. Plot it with T05-T04 Superheat (2023-2022) and E02.

## Codes from the app, password 066 (installer)

These are shown in addition to the codes above.

### Output configuration

The app shows the raw value 1 instead of one of its options for both codes.

| Code  | App name        | App range                                              | App value | Raw cloud value | Cloud type and range | Home Assistant     | Confidence |
| ----- | --------------- | ------------------------------------------------------ | --------- | --------------- | -------------------- | ------------------ | ---------- |
| `/01` | Usage of OUT 05 | Low speed, Solar water pump                            | 1         | `1`             | ENUM, 0 to 2         | sensor, Diagnostic | uncertain  |
| `/02` | Usage of OUT 06 | No output, Solar water pump, Solar water release valve | 1         | `1`             | ENUM, 0 to 3         | sensor, Diagnostic | uncertain  |

- **/01 OUT05 use (1020)**: Function of output OUT05 (O05): fan low speed or solar water pump. EvoHeat OEM manuals label hardware **OUT1–OUT5** as compressor, electric heater, 4-way valve, fan high, fan low — the same roles as app codes **O01–O05** (bits of `2050`); see [HW211 register comparison](HW211_REGISTER_COMPARISON.md) §8.
- **/02 OUT06 use (1021)**: Function of output OUT06 (O06): no output, solar water pump or solar water release valve.

The heat pump reports 1, which the app can't name either, so the active function isn't known. The cloud declares one more value than the app lists (0-2 for /01, 0-3 for /02), so the app's list may be incomplete. Read-only.

### Defrost

| Code  | App name                         | App range                       | App value | Raw cloud value | Cloud type and range | Home Assistant                  | Confidence |
| ----- | -------------------------------- | ------------------------------- | --------- | --------------- | -------------------- | ------------------------------- | ---------- |
| `D01` | Defrosting startup temp          | -30.0C to 0.0C, steps of 0.5C   | -3.0C     | `-3.0`          | TEMP1, -30 to 0      | number, Configuration, disabled | documented |
| `D02` | Defrosting shutdown temp         | 0.0C to 30.0C, steps of 0.5C    | 13.0C     | `13.0`          | TEMP1, 0 to 30       | number, Configuration, disabled | documented |
| `D03` | Duration of defrosting           | 30Min to 90Min, steps of 1Min   | 45Min     | `45`            | DIGI1, 30 to 90      | number, Configuration, disabled | documented |
| `D04` | Longest duration of defrosting   | 1Min to 20Min, steps of 1Min    | 8Min      | `8.0`           | DIGI7, 1 to 20       | number, Configuration, disabled | documented |
| `D05` | Shortest duration of defrosting  | 1Min to 8Min, steps of 1Min     | 3Min      | `3.0`           | DIGI7, 0 to 8.00     | number, Configuration, disabled | documented |
| `D06` | Defrosting way                   | Standard, Economic, Intelligent | Standard  | `0`             | ENUM, 0 to 2         | select, Configuration, disabled | observed   |
| `D07` | Intelligent defrosting judgement | -10.0C to 20.0C, steps of 0.5C  | 4.0C      | `4.0`           | TEMP1, -10 to 20     | number, Configuration, disabled | uncertain  |

- **D01 Defrost start temperature (1034)**: Coil temperature (T04) below which a defrost can start. Defrost starts when the coil (T04) is below D01 and at least D03 minutes have passed since the last one. It ends when T04 reaches D02 or after D04 minutes, and lasts at least D05 minutes (PHNIX manuals). During a defrost the compressor keeps running and the fan stops (Trianco S300 manual). A lower D01 means fewer, later defrosts. Change it only if the coil ices up or defrosts too often.
- **D02 Defrost end temperature (1035)**: Coil temperature (T04) at which a defrost ends. Defrost starts when the coil (T04) is below D01 and at least D03 minutes have passed since the last one. It ends when T04 reaches D02 or after D04 minutes, and lasts at least D05 minutes (PHNIX manuals). During a defrost the compressor keeps running and the fan stops (Trianco S300 manual). A higher D02 clears the ice more thoroughly but lasts longer.
- **D03 Defrost interval (1036)**: Minimum time between two defrosts. The app calls it 'Duration of defrosting', but a 30-90 minute range only makes sense as the interval, as in the PHNIX manuals; a Trianco S300 with D03 = 45 defrosted every 45-49 minutes.
- **D04 Maximum defrost time (1037)**: Longest a defrost may last.
- **D05 Minimum defrost time (1038)**: Shortest a defrost lasts.
- **D06 Defrost method (1039)**: How defrosts are started. Values: Standard (0), Economic (1), Intelligent (2). Standard uses D01-D05; Intelligent also uses D07. What Economic changes isn't documented. Your heat pump reports 0 = Standard; 1 and 2 follow the app's order.
- **D07 Intelligent defrost threshold (1040)**: Threshold used by intelligent defrosting (D06 = Intelligent). Not documented; it probably compares the ambient and coil temperatures. It only matters with D06 = Intelligent. Leave it unchanged.

**D03, D04, D05:** Defrost starts when the coil (T04) is below D01 and at least D03 minutes have passed since the last one. It ends when T04 reaches D02 or after D04 minutes, and lasts at least D05 minutes (PHNIX manuals). During a defrost the compressor keeps running and the fan stops (Trianco S300 manual).

### Disinfection

| Code  | App name                      | App range                     | App value | Raw cloud value | Cloud type and range | Home Assistant                  | Confidence |
| ----- | ----------------------------- | ----------------------------- | --------- | --------------- | -------------------- | ------------------------------- | ---------- |
| `G01` | Disinfection target temp      | 30.0C to 70.0C, steps of 0.5C | 60.0C     | `60.0`          | TEMP1, 30 to 70      | number, Configuration, disabled | observed   |
| `G02` | Duration of disinfection      | 0Min to 90Min, steps of 1Min  | 0Min      | `0`             | DIGI1, 0 to 90       | number, Configuration, disabled | observed   |
| `G03` | Startup point of disinfection | 0H to 23H, steps of 1H        | 0H        | `0`             | DIGI1, 0 to 23       | number, Configuration, disabled | observed   |
| `G04` | Circle of disinfection        | 1Day to 99Day, steps of 1Day  | 7Day      | `7`             | DIGI1, 1 to 99       | number, Configuration, disabled | observed   |

- **G01 Disinfection temperature (1046)**: Water temperature the disinfection cycle heats to.
- **G02 Disinfection duration (1047)**: How long the water is held at G01.
- **G03 Disinfection start hour (1048)**: Hour of the day the disinfection starts.
- **G04 Disinfection interval (1049)**: Days between disinfection cycles.

Disinfection (anti-legionella) heats the water to G01 every G04 days at G03 o'clock and holds it for G02 minutes. G02 = 0, as on your heat pump, most likely means it never runs. Above 60 °C (the limit of R01) the booster is probably needed.

### Expansion valve

| Code  | App name                       | App range  | App value | Raw cloud value | Cloud type and range | Home Assistant     | Confidence |
| ----- | ------------------------------ | ---------- | --------- | --------------- | -------------------- | ------------------ | ---------- |
| `E05` | Position of EEV for defrosting | 0N to 500N | 480N      | `480`           | DIGI2, 0 to 500      | sensor, Diagnostic | documented |

- **E05 EEV defrost position (1059)**: EEV opening during defrost. O07 reads this value (480) during defrost and while the compressor is stopped.

### Unit settings

| Code  | App name                                            | App range                         | App value      | Raw cloud value | Cloud type and range | Home Assistant                  | Confidence |
| ----- | --------------------------------------------------- | --------------------------------- | -------------- | --------------- | -------------------- | ------------------------------- | ---------- |
| `H01` | Remember the power status of device when power down | NO, YES                           | YES            | `1`             | ENUM, 0 to 1         | select, Configuration, disabled | documented |
| `H03` | Heating source                                      | Air source                        | Air source     | `0`             | ENUM, 0 to 0         | sensor, Diagnostic              | documented |
| `H07` | Temperature unit                                    | Celsius degree, Fahrenheit degree | Celsius degree | `0`             | ENUM, 0 to 1         | sensor, Diagnostic              | documented |
| `H30` | Device address                                      | 1 to 255, steps of 1              | 1              | `1`             | DIGI1, 1 to 255      | sensor, Diagnostic              | documented |
| `H31` | Intelligent control mode                            | Centralized control, DTU&WIFI     | DTU&WIFI       | `1`             | ENUM, 0 to 1         | sensor, Diagnostic              | documented |
| `H32` | Circle of submitting data to Cloud                  | 1Min to 255Min, steps of 1Min     | 1Min           | `1`             | DIGI1, 1 to 255      | number, Configuration, disabled | documented |

- **H01 Remember power state (1067)**: Whether the heat pump returns to its previous on/off state after a power cut. Values: NO (0), YES (1). YES restarts heating after a power cut if it was on before. Keep YES unless it should stay off. On a Trianco S300 every on/off, including from the remote contacts, raised T21 by 4, so with YES each switch is most likely written to the controller's memory.
- **H03 Heating source (1069)**: Type of heat source. The app only offers Air source. Values: Air source (0).
- **H07 Temperature unit (1073)**: Unit the heat pump reports temperatures in. Values: Celsius degree (0), Fahrenheit degree (1). The Temperature Unit select in Home Assistant must match it. If you change H07 in the app, change the select as well.
- **H30 Panel address (1076)**: Address of the controller on its communication bus. Read-only: a wrong address can cut the controller off from the Wi-Fi module.
- **H31 Control mode (1077)**: Whether a central controller or the DTU/Wi-Fi module controls the heat pump. Values: Centralized control (0), DTU&WIFI (1). Must stay on DTU&WIFI for the app and Home Assistant to work, so it is read-only.
- **H32 Cloud upload interval (1066)**: Minutes between the heat pump's own uploads to the cloud. Your heat pump uses 1 minute. Home Assistant reads the cloud every 5 minutes, so a larger value only makes the readings older. Keep 1.

### Solar circuit

Several values are outside the app's own range, which the app shows as they are.

| Code  | App name                                                | App range                     | App value | Raw cloud value | Cloud type and range | Home Assistant     | Confidence |
| ----- | ------------------------------------------------------- | ----------------------------- | --------- | --------------- | -------------------- | ------------------ | ---------- |
| `N01` | The sensor to control solar water pump                  | Bottom, Top                   | Bottom    | `0`             | ENUM, 0 to 1         | sensor, Diagnostic | uncertain  |
| `N02` | Longest running time of solar water pump                | 1Min to 30Min, steps of 1Min  | 10Min     | `10`            | DIGI1, 1 to 30       | sensor, Diagnostic | uncertain  |
| `N03` | Temp hysteresis of solar water pump                     | 0.0C to 20.0C, steps of 0.5C  | 10.0C     | `10.0`          | TEMP1, 0 to 20       | sensor, Diagnostic | uncertain  |
| `N04` | Activate the nighttime temp decreases mode              | NO, YES                       | YES       | `1`             | ENUM, 0 to 1         | sensor, Diagnostic | uncertain  |
| `N05` | Startup point of the nighttime temp decreases mode      | 0H to 23H, steps of 1H        | 2H        | `2`             | DIGI1, 0 to 23       | sensor, Diagnostic | uncertain  |
| `N06` | Shutdown point of the nighttime temp decreases mode     | 0H to 23H, steps of 1H        | 3H        | `3`             | DIGI1, 0 to 23       | sensor, Diagnostic | uncertain  |
| `N07` | Startup temp of decreasing solar water temp             | 40.0C to 90.0C, steps of 0.5C | -25.0C    | `-25.0`         | TEMP1, 40 to 90      | sensor, Diagnostic | uncertain  |
| `N08` | Temp hysteresis of stopping decreasing solar water temp | 1.0C to 40.0C, steps of 0.5C  | -30.0C    | `-30.0`         | TEMP1, 1 to 40       | sensor, Diagnostic | uncertain  |
| `N09` | Solar water releasing temp                              | 50.0C to 90.0C, steps of 0.5C | -30.0C    | `-30.0`         | TEMP1, 50 to 90      | sensor, Diagnostic | uncertain  |
| `N10` | Shutdown temp of solar water pump                       | 50.0C to 90.0C, steps of 0.5C | -30.0C    | `-30.0`         | TEMP1, 50 to 90      | sensor, Diagnostic | uncertain  |
| `N11` | Working mode of solar water pump                        | Dependent, Independent        | Dependent | `0`             | ENUM, 0 to 1         | sensor, Diagnostic | uncertain  |

- **N01 Solar pump control sensor (1080)**: App name: 'The sensor to control solar water pump'. Values: Bottom (0), Top (1).
- **N02 Solar pump maximum run time (1081)**: App name: 'Longest running time of solar water pump'.
- **N03 Solar pump hysteresis (1082)**: App name: 'Temp hysteresis of solar water pump'.
- **N04 Night temperature reduction (1083)**: App name: 'Activate the nighttime temp decreases mode'. Values: NO (0), YES (1).
- **N05 Night reduction start hour (1084)**: App name: 'Startup point of the nighttime temp decreases mode'.
- **N06 Night reduction end hour (1085)**: App name: 'Shutdown point of the nighttime temp decreases mode'.
- **N07 Solar water cooling start temperature (1086)**: App name: 'Startup temp of decreasing solar water temp'.
- **N08 Solar water cooling stop hysteresis (1087)**: App name: 'Temp hysteresis of stopping decreasing solar water temp'.
- **N09 Solar water release temperature (1088)**: App name: 'Solar water releasing temp'.
- **N10 Solar pump stop temperature (1089)**: App name: 'Shutdown temp of solar water pump'.
- **N11 Solar pump working mode (1090)**: App name: 'Working mode of solar water pump'. Values: Dependent (0), Independent (1).

**N01, N02, N03, N07, N08, N09, N10, N11:** Solar circuit setting. Your installation has no solar circuit, so the N codes presumably have no effect; several hold values outside the app's own range (for example N07 = -25.0). Read-only.

**N04, N05, N06:** It may lower the target between N05 and N06 o'clock; your heat pump has it set to YES for 02:00-03:00. Whether it applies without a solar circuit isn't known. Read-only.

### Booster and compressor

| Code  | App name                                                         | App range                      | App value | Raw cloud value | Cloud type and range | Home Assistant                  | Confidence |
| ----- | ---------------------------------------------------------------- | ------------------------------ | --------- | --------------- | -------------------- | ------------------------------- | ---------- |
| `R07` | Booster replaces heat pump?                                      | NO, YES                        | YES       | `1`             | ENUM, 0 to 1         | select, Configuration, disabled | documented |
| `R08` | Setpoint of ambient temp to activate booster to replace heatpump | -20.0C to 10.0C, steps of 0.5C | -5.0C     | `-5.0`          | TEMP1, -20 to 10     | number, Configuration, disabled | documented |
| `R09` | Setpoint of ambient temp to activate booster without delay       | 0.0C to 30.0C, steps of 0.5C   | 5.0C      | `5.0`           | TEMP1, 0 to 30       | number, Configuration, disabled | documented |
| `R10` | Setpoint of ambient temp to activate booster with delay          | 10.0C to 40.0C, steps of 0.5C  | 25.0C     | `25.0`          | TEMP1, 10 to 40      | number, Configuration, disabled | documented |
| `R12` | Ambient temp of shutting down compressor compulsively            | -30.0C to -5.0C, steps of 0.5C | -15.0C    | `-15.0`         | TEMP1, -30 to -5     | sensor, Diagnostic              | documented |
| `R14` | The target temp of second heating source                         | 10.0C to 60.0C, steps of 0.5C  | -10.0C    | `-10.0`         | TEMP1, 38 to 78      | sensor, Diagnostic              | documented |
| `R15` | Maximal ambient temp of working compressor                       | 55.0C to 80.0C, steps of 0.5C  | 78.0C     | `78.0`          | TEMP1, 55 to 80      | sensor, Diagnostic              | documented |
| `R17` | Enable top sensor to control compressor?                         | NO, YES                        | NO        | `0`             | ENUM, 0 to 1         | sensor, Diagnostic              | documented |
| `R18` | Hysteresis of heat pump startup(top sensor)                      | 1.0C to 20.0C, steps of 0.5C   | 5.0C      | `5.0`           | TEMP1, 1 to 20       | sensor, Diagnostic              | documented |
| `R19` | Setpoint 1 of ambient temp to stop compressor                    | 30.0C to 90.0C, steps of 0.5C  | 65.0C     | `65.0`          | TEMP1, 30 to 90      | sensor, Diagnostic              | documented |
| `R20` | Setpoint 2 of ambient temp to stop compressor                    | 30.0C to 90.0C, steps of 0.5C  | 55.0C     | `55.0`          | TEMP1, 30 to 90      | sensor, Diagnostic              | documented |

- **R07 Booster replaces heat pump (1110)**: Whether the booster takes over from the heat pump below the R08 ambient temperature. Values: NO (0), YES (1). Electric heater logic (Trianco S300 manual): in Standard mode the heater starts if the target isn't reached after R06 minutes; in High demand mode it starts without the delay; in Eco mode it never starts; both decide with the R03 differential. Intelligent mode picks Eco above R10 ambient (T01), Standard between R09 and R10 and High demand between R08 and R09; with R07 = YES the heater presumably replaces the heat pump below R08. The heater output is O02. Only relevant with an electric heater fitted. With YES and no booster fitted, the heat pump presumably stops heating below R08 (-5.0 °C on your unit).
- **R08 Booster only below ambient (1111)**: Lower ambient temperature (T01) limit of the High demand band of Intelligent mode; below it the electric heater presumably replaces the heat pump (R07 = YES).
- **R09 Booster without delay below ambient (1112)**: Ambient temperature (T01) between the High demand (below) and Standard (above) bands of Intelligent mode.
- **R10 Booster with delay below ambient (1113)**: Ambient temperature (T01) above which Intelligent mode runs as Eco, without the electric heater; below it, Standard.
- **R12 Compressor cutoff ambient (1115)**: Ambient temperature (T01) below which the compressor is forced off.
- **R14 Second heat source target (1117)**: Target temperature of the second heating source (see S06). Your heat pump holds -10.0, outside the app's own range, which suggests it isn't used.
- **R15 Maximum compressor ambient (1118)**: App name: 'Maximal ambient temp of working compressor'. A 55-80 °C range fits a water or refrigerant limit better than an air temperature.
- **R17 Top sensor controls compressor (1120)**: Whether the top sensor (T03) controls the compressor instead of the bottom sensor (T02). Values: NO (0), YES (1).
- **R18 Start hysteresis top (1121)**: Restart hysteresis of the top sensor, used instead of R03 when R17 = YES.
- **R19 Compressor stop setpoint 1 (1122)**: App name: 'Setpoint 1 of ambient temp to stop compressor'.
- **R20 Compressor stop setpoint 2 (1123)**: App name: 'Setpoint 2 of ambient temp to stop compressor'.

**R08, R09, R10:** Electric heater logic (Trianco S300 manual): in Standard mode the heater starts if the target isn't reached after R06 minutes; in High demand mode it starts without the delay; in Eco mode it never starts; both decide with the R03 differential. Intelligent mode picks Eco above R10 ambient (T01), Standard between R09 and R10 and High demand between R08 and R09; with R07 = YES the heater presumably replaces the heat pump below R08. The heater output is O02. Only relevant with an electric heater fitted.

**R19, R20:** Not documented. A 30-90 °C range fits a water temperature better than an air temperature.

### Switch inputs

The app shows `CL` (closed) or `OP` (open).

| Code  | App name                              | App range | App value | Raw cloud value | Cloud type and range | Home Assistant            | Confidence |
| ----- | ------------------------------------- | --------- | --------- | --------------- | -------------------- | ------------------------- | ---------- |
| `S01` | Remote ON/OFF switch                  | CL, OP    | CL        | bit of 2050     |                      | binary_sensor, Diagnostic | observed   |
| `S03` | Low pressure switch                   | CL, OP    | OP        | bit of 2050     |                      | binary_sensor, Diagnostic | documented |
| `S04` | High pressure switch                  | CL, OP    | CL        | bit of 2050     |                      | binary_sensor, Diagnostic | documented |
| `S05` | Accelerate the running time of heater | CL, OP    | CL        | bit of 2050     |                      | binary_sensor, Diagnostic | documented |
| `S06` | Second heating source                 | CL, OP    | OP        | bit of 2050     |                      | binary_sensor, Diagnostic | uncertain  |

- **S01 Remote switch open (2050.0)**: Remote on/off terminals, DI05 and GND in the manual. The named cloud code stays empty. This sensor reads bit 0 of register 2050. The workbook says 1 = OP (open) and 0 = CL (closed). On a Trianco S300, opening those contacts set Power to 0 and set this bit; closing them set Power to 1 and cleared the bit.
- **S03 Low pressure switch open (2050.2)**: Low pressure switch of the refrigerant circuit, bit 2 of register 2050. The workbook says 1 = OP (open) and 0 = CL (closed). Open is not necessarily a fault; the app showed OP while the heat pump ran normally.
- **S04 High pressure switch open (2050.3)**: High pressure switch of the refrigerant circuit, bit 3 of register 2050. The workbook says 1 = OP (open) and 0 = CL (closed). The app showed CL during normal operation.
- **S05 Heater boost switch open (2050.4)**: App name: 'Accelerate the running time of heater'. Bit 4 of register 2050. The workbook says 1 = OP (open) and 0 = CL (closed). Probably the input that starts the booster without the R06 delay.
- **S06 External heat switch active (2050.5)**: Second heating source input (see R14), bit 5 of register 2050. The workbook does not state whether 1 means open or closed. On this S300 the bit is often set, and why is unknown.

**S01, S03, S04, S05, S06:** The named letter codes are still empty in the cloud. These sensors are the bits, so they show on or off from register 2050. They do not stay unavailable while that word is reported.

### Outputs and running hours

The app shows `ON` or `OFF` for the outputs.

| Code  | App name                                | App range | App value | Raw cloud value | Cloud type and range | Home Assistant            | Confidence |
| ----- | --------------------------------------- | --------- | --------- | --------------- | -------------------- | ------------------------- | ---------- |
| `O01` | Compressor                              | ON, OFF   | ON        | bit of 2050     |                      | binary_sensor, Diagnostic | observed   |
| `O02` | Electrical heater                       | ON, OFF   | OFF       | bit of 2050     |                      | binary_sensor, Diagnostic | observed   |
| `O03` | 4-way valve                             | ON, OFF   | ON        | bit of 2050     |                      | binary_sensor, Diagnostic | observed   |
| `O04` | Fan high speed                          | ON, OFF   | OFF       | bit of 2050     |                      | binary_sensor, Diagnostic | uncertain  |
| `O05` | Fan low speed                           | ON, OFF   | OFF       | bit of 2050     |                      | binary_sensor, Diagnostic | uncertain  |
| `O06` | Reserve/solar pump/solar valve pump     | ON, OFF   | OFF       | bit of 2050     |                      | binary_sensor, Diagnostic | documented |
| `O08` | Accumulative running time of compressor |           | 211H      | `210` to `215`  | DIGI1                | sensor, Sensors           | observed   |
| `O09` | Accumulative running time of booster    |           | 0H        | `0`             | DIGI1                | sensor, Sensors           | observed   |

- **O01 Compressor running (2050.8)**: Compressor output. Values: Off (0), On (1).
- **O02 Heater running (2050.9)**: Electric heater (booster) output. Values: Off (0), On (1).
- **O03 Reversing valve on (2050.10)**: Four-way valve output, which reverses the refrigerant flow, for example to defrost. Values: Off (0), On (1).
- **O04 Fan running high (2050.11)**: Fan high speed output. Values: Off (0), On (1).
- **O05 Fan running low (2050.12)**: Fan low speed output (OUT05, see /01). Values: Off (0), On (1).
- **O06 Spare output on (2050.13)**: Reserve, solar pump or solar valve output (OUT06, see /02). Values: Off (0), On (1).
- **O08 Compressor hours (2061)**: Total compressor running time.
- **O09 Heater hours (2062)**: Total booster (electric heater) running time.

**O01, O02, O03, O04, O05, O06:** The named letter codes stay empty. These binary sensors read bits 8–13 of register 2050, so they show on when the output is on. 1 means on.

**O08, O09:** A statistics graph with the 'change' statistic per day shows the daily running hours.

## App settings

### Mode and ventilation

The app's settings also have an **Electric heating** switch and an **Align the device time** button. The codes behind them don't appear in the cloud data, so they aren't available in Home Assistant. The About page lists the device MAC, the PCB software code and version, and the display software code and version.

| Code        | App name                | App range                                                  | App value | Raw cloud value | Cloud type and range | Home Assistant   | Confidence |
| ----------- | ----------------------- | ---------------------------------------------------------- | --------- | --------------- | -------------------- | ---------------- | ---------- |
| `mode_real` | Select Mode             | Intelligent Mode, Eco Mode, Hybrid Mode, Fast Heating Mode | Eco Mode  | `2`             | ENUM, 0 to 4         | select, Controls | observed   |
| `M17`       | Ventilation / Air Speed | Ventilation ON/OFF, Air Speed Low or High                  |           | `1` to `2`      | ENUM                 | select, Controls | documented |

- **mode_real Operating mode (1013)**: Operating mode, as on the app's Select Mode page. Hybrid is the manual's Standard mode and Fast heating its High demand mode. Values: Intelligent (0), Eco (2), Hybrid (3), Fast heating (4). Eco: heat pump only. Hybrid: the electric heater helps if the target isn't reached after R06 minutes. Fast heating: the electric heater runs at once. Intelligent: chooses between them by the ambient temperature (R08-R10). Without an electric heater fitted, Eco is the mode to use. Vacation is set on the app's Timer page and shows as Mode 7 and the L01 Vacation enabled (1129.0) sensor. The values were confirmed by switching modes in the app on a Trianco S300.
- **M17 Fan after heating (1016)**: What the fan does once the water has reached its target temperature: run at low speed, run at high speed, or stop (Trianco S300 manual). It is the app's Ventilation switch and Air Speed knob. Values: Off (0), Low (1), High (2). A ventilation setting: Low or High keeps air moving through the unit after heating stops, Off lets the fan stop. While heating the controller runs the fan itself, so this doesn't change the fan speed during heating or the efficiency. The climate entity's fan modes write the same code.

## Codes not shown in the app

### Reported by the cloud

Their names come from the vendor's parameter file, translated where it is Chinese.

| Code  | Name in Home Assistant              | Raw cloud value  | Cloud type and range | Home Assistant            | Confidence |
| ----- | ----------------------------------- | ---------------- | -------------------- | ------------------------- | ---------- |
| `T06` | T06 Discharge temperature (2024)    | `40.5` to `87.0` | TEMP1                | sensor, Sensors           | uncertain  |
| `T11` | T11 Out-of-range count empty        | empty            |                      | sensor, Diagnostic        | uncertain  |
| `T12` | T12 EEPROM write count empty        | empty            |                      | sensor, Diagnostic        | uncertain  |
| `S02` | S02 Overheat input (2050.1)         | bit of 2050      |                      | binary_sensor, Diagnostic | uncertain  |
| `O10` | O10 Anode 3V on (2050.14)           | bit of 2050      |                      | binary_sensor, Diagnostic | documented |
| `O11` | O11 Anode MV on (2050.15)           | bit of 2050      |                      | binary_sensor, Diagnostic | documented |
| `O12` | O12 Heating stopped (2051.0)        | bit of 2051      |                      | binary_sensor, Diagnostic | documented |
| `O13` | O13 Wi-Fi link up (2051.1)          | bit of 2051      |                      | binary_sensor, Diagnostic | observed   |
| `O14` | O14 Defrost running (2051.2)        | bit of 2051      |                      | binary_sensor, Diagnostic | observed   |
| `O15` | O15 Hot water stage active (2051.3) | bit of 2051      |                      | binary_sensor, Diagnostic | documented |

- **T06 Discharge temperature (2024)**: Not shown in the app. The vendor parameter file calls it the solar temperature. On a Trianco S300 it rises to 60-90 °C while the compressor runs and drops when it stops, while T07 reads -30.0, the value of a missing sensor. That fits the compressor discharge (hot gas) temperature, which the manual's P81/E04 protections watch.
- **T11 Out-of-range count empty**: Not shown in the app. Vendor name: '进入参数超范围保护次数', number of times the out-of-range parameter protection was entered.
- **T12 EEPROM write count empty**: Not shown in the app. Vendor name: '记忆芯片EEPROM存储次数', number of times the settings memory (EEPROM) was written.
- **S02 Overheat input (2050.1)**: Bit 1 of register 2050. The `dtu_wifi` sheet that applies to this heat pump leaves the bit blank. Another sheet calls a different status word's bit 1 overheat protection, with the opposite polarity, so this sensor does not claim open or closed. It shows on when the bit is 1.
- **O10 Anode 3V on (2050.14)**: Not shown in the app. Vendor name: '3V_DE'. Values: Off (0), On (1). Packed as `2050` bit 14 (workbook label O12, electric anode 3V; this entity keeps the legacy code O10).
- **O11 Anode MV on (2050.15)**: Not shown in the app. Vendor name: 'MV_DE'. Values: Off (0), On (1). Packed as `2050` bit 15 (workbook label O13, anode MV).
- **O12 Heating stopped (2051.0)**: Not shown in the app. Vendor name: 'shutDown'. Values: Off (0), On (1). Packed as `2051` bit 0 (workbook label O14).
- **O13 Wi-Fi link up (2051.1)**: Not shown in the app. Vendor name: 'DTU&WIFI是否上线', whether the DTU/Wi-Fi module is online. Values: NO (0), YES (1). Packed as `2051` bit 1 (workbook label O15).
- **O14 Defrost running (2051.2)**: Not shown in the app. Vendor name: '除霜Defrost', defrost. Values: NO (0), YES (1). Packed as `2051` bit 2 (workbook label O16; also exposed as **Defrost running (2051.2)**).
- **O15 Hot water stage active (2051.3)**: Not shown in the app. Vendor name: '系统是否进入高温热水阶段', whether the system is in the high-temperature hot water stage. Values: NO (0), YES (1). Packed as `2051` bit 3 (workbook label O17).

**T11, T12:** The named codes stay empty on this product. The counts are T20 (2026) and T21 (2027).

**O10–O15:** The named codes stay empty on this product. These binary sensors read bits 14–15 of `2050` and bits 0–3 of `2051`, as O01–O06 and the S codes do. See [Live data](#live-data-the-app-heartbeat).

### Timer page

Decoded by changing these settings in the app of a Trianco S300. Read-only.

| Code            | Name in Home Assistant            | Raw cloud value    | Cloud type and range | Home Assistant         | Confidence |
| --------------- | --------------------------------- | ------------------ | -------------------- | ---------------------- | ---------- |
| `vacation_mode` | L01 Vacation enabled (1129.0)     | bit of 1129        |                      | binary_sensor, Sensors | observed   |
| `vacation_date` | L02-L04 Vacation date (1130-1132) |                    |                      | sensor, Diagnostic     | observed   |
| `timer1_on`     | L06-L07 Timer 1 start (1134-1135) |                    |                      | sensor, Diagnostic     | observed   |
| `timer1_off`    | L08-L09 Timer 1 stop (1136-1137)  |                    |                      | sensor, Diagnostic     | observed   |
| `timer2_on`     | L10-L11 Timer 2 start (1138-1139) |                    |                      | sensor, Diagnostic     | observed   |
| `timer2_off`    | L12-L13 Timer 2 stop (1140-1141)  |                    |                      | sensor, Diagnostic     | observed   |
| `1133`          | L05 Timer enables (1133)          | `0000000000000000` |                      | sensor, Diagnostic     | documented |
| `1129`          | L01 Vacation flags (1129)         | `0000000000000000` |                      | sensor, Diagnostic     | documented |

- **L01 Vacation enabled (1129.0)**: On while vacation mode is set on the app's Timer page. Turning vacation mode on in the app set this bit, changed Mode to 7 and stored the date in L02-L04; turning it off cleared the bit. Read-only.
- **L02-L04 Vacation date (1130-1132)**: Date set for vacation mode on the app's Timer page. The app showed 28-05-2010 while L02-L04 read 10, 5 and 28. Read-only.
- **L06-L07 Timer 1 start (1134-1135)**: On time of timer 1 on the app's Timer page. Setting timer 1 to 9:00-13:00 and timer 2 to 17:00-19:00 in the app set the hours in L06, L08, L10 and L12; L07 holds the minutes. Whether the timer is switched on is in 1133. Read-only.
- **L08-L09 Timer 1 stop (1136-1137)**: Off time of timer 1 on the app's Timer page. Setting timer 1 to 9:00-13:00 and timer 2 to 17:00-19:00 in the app set the hours in L06, L08, L10 and L12; L09 holds the minutes. Whether the timer is switched on is in 1133. Read-only.
- **L10-L11 Timer 2 start (1138-1139)**: On time of timer 2 on the app's Timer page. Setting timer 1 to 9:00-13:00 and timer 2 to 17:00-19:00 in the app set the hours in L06, L08, L10 and L12; L11 holds the minutes. Whether the timer is switched on is in 1133. Read-only.
- **L12-L13 Timer 2 stop (1140-1141)**: Off time of timer 2 on the app's Timer page. Setting timer 1 to 9:00-13:00 and timer 2 to 17:00-19:00 in the app set the hours in L06, L08, L10 and L12; L13 holds the minutes. Whether the timer is switched on is in 1133. Read-only.
- **L05 Timer enables (1133)**: The on/off switches of the app's two timers, as bits. The workbook gives bits 0-3 as timer 1 start, timer 1 stop, timer 2 start and timer 2 stop. Switching on all four timer switches in the app set bits 0-3 and switching them off cleared them, so that order hasn't been checked one switch at a time.
- **L01 Vacation flags (1129)**: Flag word whose bit 0 is vacation mode.

### Status and flag words

| Code   | Name in Home Assistant          | Raw cloud value    | Cloud type and range | Home Assistant     | Confidence |
| ------ | ------------------------------- | ------------------ | -------------------- | ------------------ | ---------- |
| `T21`  | T21 Settings write count (2027) | `3136`             |                      | sensor, Diagnostic | observed   |
| `2051` | State1 Function status (2051)   | `0000000000000010` |                      | sensor, Diagnostic | observed   |
| `1142` | Reg 1142 Flags                  | `0000000000000000` |                      | sensor, Diagnostic | uncertain  |
| `1151` | M11 Clock apply (1151)          | `0000000000000000` |                      | sensor, Diagnostic | documented |
| `2085` | Fault0 Fault bits (2085)        | `0000000000000000` |                      | sensor, Diagnostic | documented |
| `T08`  | T08 Flags                       | `0000000000000000` |                      | sensor, Diagnostic | uncertain  |
| `F03`  | F03 Flags                       | `0000000000000000` |                      | sensor, Diagnostic | uncertain  |
| `L28`  | L28 Flags                       | `0000000000000000` |                      | sensor, Diagnostic | uncertain  |

- **T21 Settings write count (2027)**: Counter that rises with every settings change, equal to register 2027. It rose by 4 for a mode change and by 32 for setting both timers, so it most likely counts writes to the controller's settings memory, the vendor's EEPROM storage count (T12). That memory allows a limited number of writes.
- **State1 Function status (2051)**: Packed status word: bit 2 is set during defrost, bit 1 has always been set.
- **Reg 1142 Flags**: Flag word, all bits clear so far.
- **M11 Clock apply (1151)**: Flag word. It read 1 after the app's Align the device time.
- **Fault0 Fault bits (2085)**: Fault word, all bits clear so far. The workbook's sensor and protection faults for bits 0-5, 8, 9 and 13 are listed under [Added register bits](#added-register-bits).
- **T08 Flags**: Sensor status flags on an Indol PV300 with the same product ID; all clear so far.
- **F03 Flags**: Configuration flags, all clear so far.
- **L28 Flags**: Schedule flags, all clear so far.

### Found by a scan of a related model

These come from the scan of an Indol PV300 with the same product ID. The status bits have since been checked on a Trianco S300; the rest is not confirmed there.

| Code                 | Name in Home Assistant                 | Raw cloud value    | Cloud type and range | Home Assistant         | Confidence |
| -------------------- | -------------------------------------- | ------------------ | -------------------- | ---------------------- | ---------- |
| `2050`               | State0 Operating status (2050)         | `0001100100100000` |                      | sensor, Diagnostic     | observed   |
| `compressor_running` | Compressor running (2050.8)            | bit of 2050        |                      | binary_sensor, Sensors | observed   |
| `electric_heater_on` | Heater running (2050.9)                | bit of 2050        |                      | binary_sensor, Sensors | observed   |
| `defrost`            | Defrost running (2051.2)               | bit of 2051        |                      | binary_sensor, Sensors | observed   |
| `M06`                | M06 Booster mode (1014)                | `0`                |                      | sensor, Diagnostic     | uncertain  |
| `O29`                | O29 Fan speed                          | `0`                |                      | sensor, Diagnostic     | uncertain  |
| `T07`                | T07 Discharge temperature unconfirmed  | `-30.0`            |                      | sensor, Diagnostic     | uncertain  |
| `T09`                | T09 Compressor temperature unconfirmed | `0`                |                      | sensor, Diagnostic     | uncertain  |

- **State0 Operating status (2050)**: Packed operating status word (State0), shown as its 16 bits (bit 0 is the last). Official bit meanings and the S300 observations are listed under [Live data](#live-data-the-app-heartbeat); prefer the workbook for bit 2 (low pressure) and bit 5 (external heat source) over earlier coil/always-on guesses.
- **Compressor running (2050.8)**: Bit 8 of the operating status word 2050. Confirmed on a Trianco S300 against the app; it also followed the compressor on an Indol PV300 with the same product ID. The protocol entity `O01` reads the same bit.
- **Heater running (2050.9)**: Bit 9 of the operating status word 2050. Confirmed on a Trianco S300: it came on with the app's electric heater (O02) and Electric heating switch in Fast heating mode.
- **Defrost running (2051.2)**: Bit 2 of the status word 2051, set while the heat pump defrosts. On a Trianco S300 it was set for about 3 minutes every 45-49 minutes while the EEV moved to its defrost position (E05), the suction temperature jumped to 25-35 °C, the coil warmed up and the fan stopped, as the manual describes for defrost. Defrosts started with the coil (T04) at about D01 and at least D03 minutes after the previous one.
- **M06 Booster mode (1014)**: Workbook register 1014, booster works independently: 1 on, 2 off, 0 instruction complete. On an Indol PV300 with the same product ID (github.com/victor987/hitemp), writing 1 turned the electric heater on and 2 turned it off, after which it read 0. On a Trianco S300 it stayed 0 while the heater ran in Fast heating mode; the app's Electric heating switch followed the heater output (2050 bit 9) instead. Read-only here.
- **O29 Fan speed**: Fan speed in revolutions per minute. On an Indol PV300 with the same product ID (github.com/victor987/hitemp), it read 0 with the fan off and about 570 to 830 rpm when running. On a Trianco S300 it read 0 while the compressor ran, so it isn't confirmed there; it is recorded so the value can be compared.
- **T07 Discharge temperature unconfirmed**: Not shown in the app. On an Indol PV300 with the same product ID (github.com/victor987/hitemp), it read 59 °C and was taken to be the compressor discharge temperature. On a Trianco S300 it reads -30.0, the value of a sensor that isn't fitted; T06 there behaves like the discharge temperature.
- **T09 Compressor temperature unconfirmed**: Not shown in the app. On an Indol PV300 with the same product ID (github.com/victor987/hitemp), it read 30-40 °C and dropped when the compressor started.

### Calculated by Home Assistant

| Code            | Name in Home Assistant                     | Raw cloud value | Cloud type and range | Home Assistant  | Confidence |
| --------------- | ------------------------------------------ | --------------- | -------------------- | --------------- | ---------- |
| `superheat`     | T05-T04 Superheat (2023-2022)              |                 |                      | sensor, Sensors | documented |
| `water_delta_t` | T03-T02 Water temperature rise (2021-2020) |                 |                      | sensor, Sensors | observed   |

- **T05-T04 Superheat (2023-2022)**: Suction minus coil temperature (T05 - T04), calculated by Home Assistant. The value E02 targets. Negative values mean the suction pipe reads colder than the coil, which keeps the EEV at E04.
- **T03-T02 Water temperature rise (2021-2020)**: Top minus bottom water temperature (T03 - T02), calculated by Home Assistant. On your installation, how much the water warms up through the heat pump. Heat pumps are usually designed for about 5 °C; a much larger value can mean low water flow.

### Other requested codes

The climate entity and the Power sensor use some of these. The others were requested by the original integration or found on the app's Timer page, and each is a sensor so its value is recorded. Only `ver` and `software_code` have no entity.

| Code            | Name in Home Assistant          | Raw cloud value | Cloud type and range | Home Assistant            | Confidence |
| --------------- | ------------------------------- | --------------- | -------------------- | ------------------------- | ---------- |
| `Power`         | Power Heat pump on (1011)       | `1`             | ENUM, 0 to 1         | binary_sensor, Diagnostic | observed   |
| `Mode`          | Mode Requested mode (1012)      | `2`             | ENUM, 0 to 7         | sensor, Diagnostic        | uncertain  |
| `T20`           | T20 Out-of-range count (2026)   | `1`             |                      | sensor, Diagnostic        | documented |
| `L02`           | L02 Vacation year (1130)        | `10`            |                      | sensor, Diagnostic        | documented |
| `L03`           | L03 Vacation month (1131)       | `5`             |                      | sensor, Diagnostic        | documented |
| `L04`           | L04 Vacation day (1132)         | `28`            |                      | sensor, Diagnostic        | documented |
| `L06`           | L06 Timer 1 start hour (1134)   | `0`             |                      | sensor, Diagnostic        | documented |
| `L07`           | L07 Timer 1 start minute (1135) | `0`             |                      | sensor, Diagnostic        | documented |
| `L08`           | L08 Timer 1 stop hour (1136)    | `0`             |                      | sensor, Diagnostic        | documented |
| `L09`           | L09 Timer 1 stop minute (1137)  | `0`             |                      | sensor, Diagnostic        | documented |
| `L10`           | L10 Timer 2 start hour (1138)   | `0`             |                      | sensor, Diagnostic        | documented |
| `L11`           | L11 Timer 2 start minute (1139) | `0`             |                      | sensor, Diagnostic        | documented |
| `L12`           | L12 Timer 2 stop hour (1140)    | `0`             |                      | sensor, Diagnostic        | documented |
| `L13`           | L13 Timer 2 stop minute (1141)  | `0`             |                      | sensor, Diagnostic        | documented |
| `Manual-mute`   | Manual-mute Fan mode empty      | empty           |                      | sensor, Diagnostic        | uncertain  |
| `Set_Temp`      | Set_Temp Setpoint empty         | empty           |                      | sensor, Diagnostic        | uncertain  |
| `MO6`           | MO6 Power empty                 | empty           |                      | sensor, Diagnostic        | uncertain  |
| `2074`          | Reg 2074 Unknown                | `0`             | DIGI1                | sensor, Diagnostic        | uncertain  |
| `2075`          | Reg 2075 Unknown                | `0`             | DIGI1                | sensor, Diagnostic        | uncertain  |
| `2076`          | Reg 2076 Unknown                | `0`             | DIGI1                | sensor, Diagnostic        | uncertain  |
| `2077`          | Reg 2077 Unknown                | empty           |                      | sensor, Diagnostic        | uncertain  |
| `1158`          | Reg 1158 Heartbeat echo         | `0` to `23205`  | DIGI1                | sensor, Diagnostic        | observed   |
| `1159`          | Reg 1159 Unknown                | empty           |                      | sensor, Diagnostic        | uncertain  |
| `2064`          | Reg 2064 Unknown                | `0`             | DIGI1                | sensor, Diagnostic        | uncertain  |
| `ver`           | Version                         | empty           |                      | requested, no entity      |            |
| `software_code` | Software Code                   | empty           |                      | requested, no entity      |            |

- **Power Heat pump on (1011)**: On/off state of the heat pump (1 = on). The climate entity turns it on and off. On a Trianco S300, opening the remote on/off contacts (S01, DI05 and GND in the manual) set Power to 0 and closing them set it to 1 by the next read, within a minute. The compressor stopped or started about a minute later. Each switch raised T21 by 4: the on/off state is written to the controller's memory, most likely because H01 = YES remembers it. Whether switching on from Home Assistant or the app overrides open contacts isn't known, so avoid switching it from both.
- **Mode Requested mode (1012)**: Workbook register 1012, which the workbook calls the requested mode: 0 Intelligent, 2 Eco, 3 Hybrid, 4 Fast heating, 7 Vacation (values seen in the app on a Trianco S300). On that S300 it read 7 while on vacation, when mode_real (1013) kept the mode to return to. Read-only; mode changes are written to mode_real.
- **T20 Out-of-range count (2026)**: Read 1, equal to register 2026. Possibly the vendor's out-of-range protection count (T11).
- **L02 Vacation year (1130)**: Vacation year (20YY), from the app's Timer page.
- **L03 Vacation month (1131)**: Vacation month, from the app's Timer page.
- **L04 Vacation day (1132)**: Vacation day, from the app's Timer page.
- **L06 Timer 1 start hour (1134)**: Timer 1 on hour, from the app's Timer page.
- **L07 Timer 1 start minute (1135)**: Timer 1 on minute, from the app's Timer page.
- **L08 Timer 1 stop hour (1136)**: Timer 1 off hour, from the app's Timer page.
- **L09 Timer 1 stop minute (1137)**: Timer 1 off minute, from the app's Timer page.
- **L10 Timer 2 start hour (1138)**: Timer 2 on hour, from the app's Timer page.
- **L11 Timer 2 start minute (1139)**: Timer 2 on minute, from the app's Timer page.
- **L12 Timer 2 stop hour (1140)**: Timer 2 off hour, from the app's Timer page.
- **L13 Timer 2 stop minute (1141)**: Timer 2 off minute, from the app's Timer page.
- **Manual-mute Fan mode empty**: Fan mode code of other models, requested for compatibility. Empty on HiTemp.
- **Set_Temp Setpoint empty**: Setpoint code of other models, requested for compatibility. Empty on HiTemp.
- **MO6 Power empty**: Requested by the original integration. Empty on HiTemp, meaning unknown.
- **Reg 2074 Unknown**: Register requested by the original integration, meaning unknown.
- **Reg 2075 Unknown**: Register requested by the original integration, meaning unknown.
- **Reg 2076 Unknown**: Register requested by the original integration, meaning unknown.
- **Reg 2077 Unknown**: Register requested by the original integration, meaning unknown.
- **Reg 1158 Heartbeat echo**: Read 23205, the value of the app's live data request (app_heartbeat), for hours in one log, probably while the app was open, and 0 otherwise. The integration's own request has not changed it.
- **Reg 1159 Unknown**: Register requested by the original integration, meaning unknown.
- **Reg 2064 Unknown**: Register requested by the original integration, meaning unknown.
- **Version**: Version code of other models. Empty on HiTemp, see code_version and MainBoard Version.
- **Software Code**: Software code of other models. Empty on HiTemp, see code_version and MainBoard Version.

### Controller versions

The About page of the app shows these as the PCB and display software. They are also combined into the device's software version.

| Code   | Name in Home Assistant       | Raw cloud value | Cloud type and range | Home Assistant     | Confidence |
| ------ | ---------------------------- | --------------- | -------------------- | ------------------ | ---------- |
| `2011` | Reg 2011 Main version        | `1.0`           |                      | sensor, Diagnostic | documented |
| `2012` | Reg 2012 Main software code  | `679`           |                      | sensor, Diagnostic | documented |
| `2013` | Reg 2013 Panel version       | `1.0`           |                      | sensor, Diagnostic | documented |
| `2014` | Reg 2014 Panel software code | `741`           |                      | sensor, Diagnostic | documented |

- **Reg 2011 Main version**: Main program version. The workbook stores 11 for V1.1; the cloud already returns the version, for example 1.0.
- **Reg 2012 Main software code**: Software code of the main program. The workbook reads 1234 as software 35005-311234.
- **Reg 2013 Panel version**: Version of the wired panel's program, in the same form as 2011.
- **Reg 2014 Panel software code**: Software code of the wired panel.

### Read from the probe request

These codes were found by Victor's scan or are named in the workbook but not
requested in the main read. They are read in the separate probe request, so a
code the cloud rejects can't break the main read; a rejected code stays
unavailable until a restart. Each is a diagnostic sensor so its history is
recorded, and changes also show in the Code changes sensor. Except for `M07`
and `M12`-`M16`, which the workbook names, no meaning is known on this heat
pump, so the names don't claim one. Victor's numeric aliases are given in the
descriptions only.

| Code        | Name in Home Assistant    | Raw cloud value | Cloud type and range | Home Assistant     | Confidence |
| ----------- | ------------------------- | --------------- | -------------------- | ------------------ | ---------- |
| `2057`      | Reg 2057 Unknown          | `0`             |                      | sensor, Diagnostic | uncertain  |
| `2058`      | Reg 2058 Unknown          | `0`             |                      | sensor, Diagnostic | uncertain  |
| `2059`      | Reg 2059 Unknown          | `0`             |                      | sensor, Diagnostic | uncertain  |
| `2068`      | Reg 2068 Unknown          | `0`             |                      | sensor, Diagnostic | uncertain  |
| `2069`      | Reg 2069 Unknown          | `0`             |                      | sensor, Diagnostic | uncertain  |
| `2070`      | Reg 2070 Unknown          | `0`             |                      | sensor, Diagnostic | uncertain  |
| `2071`      | Reg 2071 Unknown          | `0`             |                      | sensor, Diagnostic | uncertain  |
| `O18`       | O18 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `O19`       | O19 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `O21`       | O21 Unknown               | `-55`           |                      | sensor, Diagnostic | uncertain  |
| `O22`       | O22 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `O23`       | O23 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `O24`       | O24 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `O25`       | O25 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `O26`       | O26 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `O27`       | O27 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `O28`       | O28 Unknown               | `0.0`           |                      | sensor, Diagnostic | uncertain  |
| `M07`       | M07 Forced defrost (1015) | `0`             |                      | sensor, Diagnostic | documented |
| `M12`       | M12 Clock minute (1152)   | `0`             |                      | sensor, Diagnostic | documented |
| `M13`       | M13 Clock hour (1153)     | `0`             |                      | sensor, Diagnostic | documented |
| `M14`       | M14 Clock day (1154)      | `0`             |                      | sensor, Diagnostic | documented |
| `M15`       | M15 Clock month (1155)    | `0`             |                      | sensor, Diagnostic | documented |
| `M16`       | M16 Clock year (1156)     | `0`             |                      | sensor, Diagnostic | documented |
| `R02`       | R02 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `R11`       | R11 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `R13`       | R13 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `R16`       | R16 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `H09`       | H09 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `H16`       | H16 Unknown               | `1`             |                      | sensor, Diagnostic | uncertain  |
| `E06`       | E06 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `C01`       | C01 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `C02`       | C02 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `C03`       | C03 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `C05`       | C05 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `C06`       | C06 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `C07`       | C07 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `C08`       | C08 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `C09`       | C09 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `D10`       | D10 Unknown               | `-30.0`         |                      | sensor, Diagnostic | uncertain  |
| `D11`       | D11 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `D12`       | D12 Unknown               | `-30.0`         |                      | sensor, Diagnostic | uncertain  |
| `D13`       | D13 Unknown               | `-30.0`         |                      | sensor, Diagnostic | uncertain  |
| `F01`       | F01 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `F02`       | F02 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `F04`       | F04 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `F05`       | F05 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `F06`       | F06 Unknown               | `-30.0`         |                      | sensor, Diagnostic | uncertain  |
| `F07`       | F07 Unknown               | `-30.0`         |                      | sensor, Diagnostic | uncertain  |
| `F09`       | F09 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `F10`       | F10 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `F11`       | F11 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `F12`       | F12 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `F13`       | F13 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `L29`       | L29 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `L30`       | L30 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `L31`       | L31 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `L32`       | L32 Unknown               | `0`             |                      | sensor, Diagnostic | uncertain  |
| `ModeState` | ModeState Mode state      | `2`             |                      | sensor, Diagnostic | uncertain  |

- **Reg 2057 Unknown**: Register 2057 has no name in the workbook. Victor's scan read it; it read 0 on a Trianco S300.
- **Reg 2058 Unknown**: Register 2058 has no name in the workbook. Victor's scan read it; it read 0 on a Trianco S300.
- **Reg 2059 Unknown**: Register 2059 has no name in the workbook. Victor's scan read it; it read 0 on a Trianco S300.
- **Reg 2068 Unknown**: Register 2068 has no name in the workbook. Victor's scan read it; it read 0 on a Trianco S300.
- **Reg 2069 Unknown**: Register 2069 has no name in the workbook. Victor's scan read it; it read 0 on a Trianco S300.
- **Reg 2070 Unknown**: Register 2070 has no name in the workbook. Victor's scan read it; it read 0 on a Trianco S300.
- **Reg 2071 Unknown**: Register 2071 has no name in the workbook. Victor's scan read it; it read 0 on a Trianco S300.
- **O18 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 2062, which the workbook gives to O09 heater hours, so that address is not used.
- **O19 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 2063, which the workbook leaves blank.
- **O21 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 2065, which the workbook leaves blank. Victor took it for a temperature sensor. It read -55 on a Trianco S300.
- **O22 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. No address is known.
- **O23 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. No address is known.
- **O24 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. No address is known.
- **O25 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. No address is known.
- **O26 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. No address is known.
- **O27 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. No address is known.
- **O28 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 2066, which the workbook leaves blank.
- **M07 Forced defrost (1015)**: Workbook register 1015, compulsive defrosting (0 off, 1 on). It is a command that starts a defrost.
- **M12 Clock minute (1152)**: Workbook register 1152, system clock minute (0-59).
- **M13 Clock hour (1153)**: Workbook register 1153, system clock hour (0-23).
- **M14 Clock day (1154)**: Workbook register 1154, system clock day (1-31).
- **M15 Clock month (1155)**: Workbook register 1155, system clock month (1-12).
- **M16 Clock year (1156)**: Workbook register 1156, system clock year (0-99).
- **R02 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1105, which the workbook leaves blank. The app doesn't show it.
- **R11 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1114, which the workbook leaves blank. The app doesn't show it.
- **R13 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1116, which the workbook leaves blank. The app doesn't show it.
- **R16 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1119, which the workbook leaves blank. The app doesn't show it.
- **H09 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. No address is known.
- **H16 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1068, which the workbook leaves blank. It read 1 on a Trianco S300.
- **E06 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1060, which the workbook leaves blank.
- **C01 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. No address is known.
- **C02 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1023, which the workbook leaves blank.
- **C03 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1024, which the workbook leaves blank.
- **C05 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1033, which the workbook leaves blank.
- **C06 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1026, which the workbook leaves blank.
- **C07 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1029, which the workbook leaves blank.
- **C08 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1030, which the workbook leaves blank.
- **C09 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1031, which the workbook leaves blank.
- **D10 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1042, which the workbook leaves blank. It read -30.0 on a Trianco S300.
- **D11 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1043, which the workbook leaves blank. It read 0 on a Trianco S300.
- **D12 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1041, which the workbook leaves blank. It read -30.0 on a Trianco S300.
- **D13 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1051, which the workbook leaves blank. It read -30.0 on a Trianco S300.
- **F01 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1160, which is not on the dtu_wifi sheet. It read 0 on a Trianco S300.
- **F02 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1161, which is not on the dtu_wifi sheet. It read 0 on a Trianco S300.
- **F04 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1163, which is not on the dtu_wifi sheet. It read 0 on a Trianco S300.
- **F05 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1164, which is not on the dtu_wifi sheet. It read 0 on a Trianco S300.
- **F06 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1165, which is not on the dtu_wifi sheet. It read -30.0 on a Trianco S300.
- **F07 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1166, which is not on the dtu_wifi sheet. It read -30.0 on a Trianco S300.
- **F09 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1168, which is not on the dtu_wifi sheet. It read 0 on a Trianco S300.
- **F10 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1169, which is not on the dtu_wifi sheet. It read 0 on a Trianco S300.
- **F11 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1170, which is not on the dtu_wifi sheet. It read 0 on a Trianco S300.
- **F12 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1171, which is not on the dtu_wifi sheet. It read 0 on a Trianco S300.
- **F13 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1172, which is not on the dtu_wifi sheet. It read 0 on a Trianco S300.
- **L29 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 1143, which is not on the dtu_wifi sheet.
- **L30 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. No address is known.
- **L31 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 2075, which the workbook leaves blank. Register 2075 is recorded separately.
- **L32 Unknown**: Code found by Victor's scan of an Indol PV300 with the same product ID. Victor matched it to 2076, which the workbook leaves blank. Register 2076 is recorded separately.
- **ModeState Mode state**: Live-data code of the FoxAir boards. On a Trianco S300 it read 2, the same as Mode.

The same request also reads codes that have no entity of their own:

- the named letter codes `O01`-`O06`, `O10`-`O15` and `S01`-`S06`, so a value
  would show up in the diagnostics if the cloud ever filled them; their
  entities read the bits of `2050` and `2051`;
- `2026` and `2027`, which equal `T20` and `T21`;
- the fault words `Fault1`-`Fault10`, shown as attributes of Fault details;
- `MainBoard Version` and `code_version`, shown in the device's software
  version.

## Added register bits

Every bit of the status, fault and flag words is a binary sensor in the
Diagnostic section, enabled by default. It is on when the bit is 1. A
meaning in brackets comes from the workbook or Darksplat; bits without one
are recorded so their pattern can be compared with what the heat pump does.

| Code          | Name                                             | Confidence |
| ------------- | ------------------------------------------------ | ---------- |
| `2050_bit_00` | Reg 2050 bit 0 (S01 remote switch open)          | observed   |
| `2050_bit_01` | Reg 2050 bit 1 (S02 overheat input)              | uncertain  |
| `2050_bit_02` | Reg 2050 bit 2 (S03 low pressure switch open)    | documented |
| `2050_bit_03` | Reg 2050 bit 3 (S04 high pressure switch open)   | documented |
| `2050_bit_04` | Reg 2050 bit 4 (S05 heater boost switch open)    | documented |
| `2050_bit_05` | Reg 2050 bit 5 (S06 external heat switch active) | uncertain  |
| `2050_bit_06` | Reg 2050 bit 6                                   | uncertain  |
| `2050_bit_07` | Reg 2050 bit 7                                   | uncertain  |
| `2050_bit_08` | Reg 2050 bit 8 (O01 compressor running)          | observed   |
| `2050_bit_09` | Reg 2050 bit 9 (O02 heater running)              | observed   |
| `2050_bit_10` | Reg 2050 bit 10 (O03 reversing valve on)         | observed   |
| `2050_bit_11` | Reg 2050 bit 11 (O04 fan running high)           | uncertain  |
| `2050_bit_12` | Reg 2050 bit 12 (O05 fan running low)            | uncertain  |
| `2050_bit_13` | Reg 2050 bit 13 (O06 spare output on)            | documented |
| `2050_bit_14` | Reg 2050 bit 14 (O10 anode 3V on)                | documented |
| `2050_bit_15` | Reg 2050 bit 15 (O11 anode MV on)                | documented |
| `2051_bit_00` | Reg 2051 bit 0 (O12 heating stopped)             | documented |
| `2051_bit_01` | Reg 2051 bit 1 (O13 Wi-Fi link up)               | observed   |
| `2051_bit_02` | Reg 2051 bit 2 (O14 defrost running)             | observed   |
| `2051_bit_03` | Reg 2051 bit 3 (O15 hot water stage active)      | documented |
| `2051_bit_04` | Reg 2051 bit 4                                   | uncertain  |
| `2051_bit_05` | Reg 2051 bit 5                                   | uncertain  |
| `2051_bit_06` | Reg 2051 bit 6                                   | uncertain  |
| `2051_bit_07` | Reg 2051 bit 7                                   | uncertain  |
| `2051_bit_08` | Reg 2051 bit 8                                   | uncertain  |
| `2051_bit_09` | Reg 2051 bit 9                                   | uncertain  |
| `2051_bit_10` | Reg 2051 bit 10                                  | uncertain  |
| `2051_bit_11` | Reg 2051 bit 11                                  | uncertain  |
| `2051_bit_12` | Reg 2051 bit 12                                  | uncertain  |
| `2051_bit_13` | Reg 2051 bit 13                                  | uncertain  |
| `2051_bit_14` | Reg 2051 bit 14                                  | uncertain  |
| `2051_bit_15` | Reg 2051 bit 15                                  | uncertain  |
| `2085_bit_00` | Reg 2085 bit 0 (P04 ambient sensor fault)        | documented |
| `2085_bit_01` | Reg 2085 bit 1 (P01 bottom sensor fault)         | documented |
| `2085_bit_02` | Reg 2085 bit 2 (P02 top sensor fault)            | documented |
| `2085_bit_03` | Reg 2085 bit 3 (P05 coil sensor fault)           | documented |
| `2085_bit_04` | Reg 2085 bit 4 (P07 suction sensor fault)        | documented |
| `2085_bit_05` | Reg 2085 bit 5 (P034 solar sensor fault)         | documented |
| `2085_bit_06` | Reg 2085 bit 6                                   | uncertain  |
| `2085_bit_07` | Reg 2085 bit 7                                   | uncertain  |
| `2085_bit_08` | Reg 2085 bit 8 (E01 high pressure fault)         | documented |
| `2085_bit_09` | Reg 2085 bit 9 (E02 low pressure fault)          | documented |
| `2085_bit_10` | Reg 2085 bit 10                                  | uncertain  |
| `2085_bit_11` | Reg 2085 bit 11                                  | uncertain  |
| `2085_bit_12` | Reg 2085 bit 12                                  | uncertain  |
| `2085_bit_13` | Reg 2085 bit 13 (E09 tank frost protection)      | documented |
| `2085_bit_14` | Reg 2085 bit 14                                  | uncertain  |
| `2085_bit_15` | Reg 2085 bit 15                                  | uncertain  |
| `1142_bit_00` | Reg 1142 bit 0                                   | uncertain  |
| `1142_bit_01` | Reg 1142 bit 1                                   | uncertain  |
| `1142_bit_02` | Reg 1142 bit 2                                   | uncertain  |
| `1142_bit_03` | Reg 1142 bit 3                                   | uncertain  |
| `1142_bit_04` | Reg 1142 bit 4                                   | uncertain  |
| `1142_bit_05` | Reg 1142 bit 5                                   | uncertain  |
| `1142_bit_06` | Reg 1142 bit 6                                   | uncertain  |
| `1142_bit_07` | Reg 1142 bit 7                                   | uncertain  |
| `1142_bit_08` | Reg 1142 bit 8                                   | uncertain  |
| `1142_bit_09` | Reg 1142 bit 9                                   | uncertain  |
| `1142_bit_10` | Reg 1142 bit 10                                  | uncertain  |
| `1142_bit_11` | Reg 1142 bit 11                                  | uncertain  |
| `1142_bit_12` | Reg 1142 bit 12                                  | uncertain  |
| `1142_bit_13` | Reg 1142 bit 13                                  | uncertain  |
| `1142_bit_14` | Reg 1142 bit 14                                  | uncertain  |
| `1142_bit_15` | Reg 1142 bit 15                                  | uncertain  |
| `T08_bit_00`  | T08 bit 0                                        | uncertain  |
| `T08_bit_01`  | T08 bit 1                                        | uncertain  |
| `T08_bit_02`  | T08 bit 2                                        | uncertain  |
| `T08_bit_03`  | T08 bit 3                                        | uncertain  |
| `T08_bit_04`  | T08 bit 4                                        | uncertain  |
| `T08_bit_05`  | T08 bit 5                                        | uncertain  |
| `T08_bit_06`  | T08 bit 6                                        | uncertain  |
| `T08_bit_07`  | T08 bit 7                                        | uncertain  |
| `T08_bit_08`  | T08 bit 8                                        | uncertain  |
| `T08_bit_09`  | T08 bit 9                                        | uncertain  |
| `T08_bit_10`  | T08 bit 10                                       | uncertain  |
| `T08_bit_11`  | T08 bit 11                                       | uncertain  |
| `T08_bit_12`  | T08 bit 12                                       | uncertain  |
| `T08_bit_13`  | T08 bit 13                                       | uncertain  |
| `T08_bit_14`  | T08 bit 14                                       | uncertain  |
| `T08_bit_15`  | T08 bit 15                                       | uncertain  |
| `F03_bit_00`  | F03 bit 0                                        | uncertain  |
| `F03_bit_01`  | F03 bit 1                                        | uncertain  |
| `F03_bit_02`  | F03 bit 2                                        | uncertain  |
| `F03_bit_03`  | F03 bit 3                                        | uncertain  |
| `F03_bit_04`  | F03 bit 4                                        | uncertain  |
| `F03_bit_05`  | F03 bit 5                                        | uncertain  |
| `F03_bit_06`  | F03 bit 6                                        | uncertain  |
| `F03_bit_07`  | F03 bit 7                                        | uncertain  |
| `F03_bit_08`  | F03 bit 8                                        | uncertain  |
| `F03_bit_09`  | F03 bit 9                                        | uncertain  |
| `F03_bit_10`  | F03 bit 10                                       | uncertain  |
| `F03_bit_11`  | F03 bit 11                                       | uncertain  |
| `F03_bit_12`  | F03 bit 12                                       | uncertain  |
| `F03_bit_13`  | F03 bit 13                                       | uncertain  |
| `F03_bit_14`  | F03 bit 14                                       | uncertain  |
| `F03_bit_15`  | F03 bit 15                                       | uncertain  |
| `L28_bit_00`  | L28 bit 0                                        | uncertain  |
| `L28_bit_01`  | L28 bit 1                                        | uncertain  |
| `L28_bit_02`  | L28 bit 2                                        | uncertain  |
| `L28_bit_03`  | L28 bit 3                                        | uncertain  |
| `L28_bit_04`  | L28 bit 4                                        | uncertain  |
| `L28_bit_05`  | L28 bit 5                                        | uncertain  |
| `L28_bit_06`  | L28 bit 6                                        | uncertain  |
| `L28_bit_07`  | L28 bit 7                                        | uncertain  |
| `L28_bit_08`  | L28 bit 8                                        | uncertain  |
| `L28_bit_09`  | L28 bit 9                                        | uncertain  |
| `L28_bit_10`  | L28 bit 10                                       | uncertain  |
| `L28_bit_11`  | L28 bit 11                                       | uncertain  |
| `L28_bit_12`  | L28 bit 12                                       | uncertain  |
| `L28_bit_13`  | L28 bit 13                                       | uncertain  |
| `L28_bit_14`  | L28 bit 14                                       | uncertain  |
| `L28_bit_15`  | L28 bit 15                                       | uncertain  |
| `1133_bit_00` | Reg 1133 bit 0 (L05 timer 1 start enabled)       | documented |
| `1133_bit_01` | Reg 1133 bit 1 (L05 timer 1 stop enabled)        | documented |
| `1133_bit_02` | Reg 1133 bit 2 (L05 timer 2 start enabled)       | documented |
| `1133_bit_03` | Reg 1133 bit 3 (L05 timer 2 stop enabled)        | documented |
| `1129_bit_00` | Reg 1129 bit 0 (L01 vacation enabled)            | observed   |
| `1151_bit_00` | Reg 1151 bit 0 (M11 clock apply requested)       | documented |
