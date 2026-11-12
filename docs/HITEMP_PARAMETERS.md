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
  limited number of writes (`T12` counts them). Don't let automations change
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

## How Home Assistant shows the codes

- **Names** start with the code and a short name, for example
  `R01 Target water temperature`. The app's own name is kept in the
  `app_name` attribute.
- **Sections** on the device page:
  - **Controls**: the climate entity, `R01`, `R03`, `R04`, `R05`, `R06` and
    `M17`, the settings meant for daily use.
  - **Sensors**: live temperatures, the EEV position, running hours and the
    calculated superheat and water ΔT.
  - **Configuration**: installer settings you can write, disabled by default.
  - **Diagnostic**: settings you can only read, switch inputs, outputs,
    status and faults.
- **Values with labels** read `label (raw)`, for example `Standard (0)`, so
  both the app's text and the raw number are visible. A raw value the app has
  no label for reads like `1 (not listed in the app)`.
- **Attributes** on every parameter: `code`, `app_name`, `level` (password),
  `range` and `app_value` as seen in the app, `confidence`, `description` and
  `guidance`. Labelled values also have `raw_value`. The static attributes
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
  wired to a thermostat or volt-free contact. The cloud never reports `S01`
  itself, but opening the contacts sets `Power` to 0 and closing them sets it
  to 1, so the Power sensor and the climate entity follow them. Each switch is
  written to the controller's memory (see `T21` and `H01`). After stopping, the
  compressor waits 3 minutes before it starts again.
- **Operating modes** (Trianco S300 manual, app names in brackets): Eco (heat
  pump only), Standard (Hybrid: electric heater after `R06` minutes if the
  target isn't reached), High demand (Fast heating: electric heater without
  the delay), Intelligent (chooses between them by ambient temperature) and
  Vacation. `mode_real` holds the chosen mode (0 Intelligent, 2 Eco, 3
  Hybrid, 4 Fast heating) and can be set from Home Assistant. `Mode` shows
  the active mode, 7 while on vacation, when `mode_real` keeps the mode to
  return to.
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
  acceleration) probably starts it without the delay, `M06` is probably the
  app's Electric heating switch, and `O09` counts its hours.
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
- **Fan.** The controller runs the fan while heating (`O29` is probably its
  speed). `M17` sets what it does once the target is reached: low, high or
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
  temperature. It is disabled by default until that is confirmed.
- **T10** (the displayed temperature) always equalled `T03`.
- **Fan:** `M17` changed from 1 to 2 after the climate entity's fan mode was
  set to high. According to the manual that only changes what the fan does
  after the target is reached.
- **R01** was written every few minutes by something other than the app,
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
  (`E04`) within about 20 minutes, when bit 2 of `2050` cleared.

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
rejects are not asked for again until the next restart.

What we know for HiTemp:

- Register `1158` read 23205 for hours in one log, probably while the app was
  open. The integration's own request, sent every 5 minutes, has not changed
  it.
- With the request sent before every poll, the cloud still returned nothing
  for the S and O codes, the fault words or the PCB versions. Only `ModeState`
  had a value. So on HiTemp the request doesn't make these values available
  through the cloud, at least not the way the integration sends it.
- The app shows the S and O values, so it must read them some other way.

The best lead is the scan of an Indol PV300 with the same product ID by
[victor987/hitemp](https://github.com/victor987/hitemp). It found that the S
codes never return data on this product, and that the operating state is in
packed status words, for example register `2050`, where bit 8 followed the
compressor and bit 9 the electric heater. The integration therefore reads
`2050` and shows it, with the compressor and heater bits as binary sensors,
and reads the other codes that scan found (listed at the end of this guide)
for diagnostics.

The bits decoded so far on a Trianco S300:

| Word   | Bit    | Set while                                                  | Confidence |
| ------ | ------ | ---------------------------------------------------------- | ---------- |
| `2050` | 0      | the unit is switched off                                   | observed   |
| `2050` | 2      | the coil is above about -3 °C (`D01`); meaning unconfirmed | uncertain  |
| `2050` | 5      | always, so far                                             | observed   |
| `2050` | 8      | the compressor runs (**Compressor running**)               | observed   |
| `2050` | 9      | the electric heater is on (**Electric heater on**)         | observed   |
| `2050` | 10     | defrosting, probably the 4-way valve                       | observed   |
| `2050` | 11, 12 | the fan runs; which bit is which speed isn't known yet     | uncertain  |
| `2051` | 1      | always, so far                                             | observed   |
| `2051` | 2      | defrosting (**Defrost**)                                   | observed   |

To find out, download the diagnostics of the heat pump while it runs. The
`live_data` section lists the result of the last heartbeat, which codes had a
value and which stayed empty, and any packed switch words as value, hex and
bits. The **Request live data** option in the integration's settings turns
the heartbeat off.

If the S and O codes stay empty, the remaining way to learn how the app reads
them is to capture its traffic while the parameter pages are open, for example
with Proxyman on iOS or HTTP Toolkit on Android, and share the request and
response of `getDataByCode` with the token and password removed.

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
| `R04` | Enable R05 as setpoint of booster?             | NO, YES                       | NO         | `0`             | ENUM, 0 to 1         | select, Controls | observed   |
| `R05` | Setpoint of booster                            | 30.0C to 90.0C, steps of 0.5C | 55.0C      | `55.0`          | TEMP1, 30 to 90      | number, Controls | observed   |
| `R06` | Booster startup delay                          | 0Min to 450Min, steps of 1Min | 200Min     | `200`           | DIGI4, 0 to 90       | number, Controls | documented |

- **R01 Target water temperature**: Target water temperature, the main control. The climate entity sets the same value. Heating starts when the controlling sensor (T02 bottom, or T03 top with R17 = YES) drops R03 below R01, and stops at R01. Each change is probably stored in the controller's memory, which allows a limited number of writes (see T12), so avoid automations that change R01 every few minutes.
- **R03 Start hysteresis (bottom sensor)**: How far below R01 the bottom sensor (T02) must drop before heating restarts. A small value keeps the water closer to R01 but starts the compressor more often; very small values cause short cycling. Your heat pump uses 5.0 °C.
- **R04 Use R05 as booster setpoint**: Whether the booster heats to its own setpoint R05 instead of R01. Values: NO (0), YES (1).
- **R05 Booster setpoint**: Water temperature the booster heats to when R04 = YES.
- **R06 Booster start delay**: How long the heat pump runs before the booster may help. The cloud declares a range of 0-90 for the app's 0-450 minutes, so the heat pump most likely stores it in 5-minute units; Home Assistant writes it in steps of 5.

**R04, R05, R06:** Electric heater logic (Trianco S300 manual): in Standard mode the heater starts if the target isn't reached after R06 minutes; in High demand mode it starts without the delay; in Eco mode it never starts; both decide with the R03 differential. Intelligent mode picks Eco above R10 ambient (T01), Standard between R09 and R10 and High demand between R08 and R09; with R07 = YES the heater presumably replaces the heat pump below R08. The heater output is O02. Only relevant with an electric heater fitted.

### Expansion valve

| Code  | App name                        | App range                      | App value | Raw cloud value | Cloud type and range | Home Assistant                  | Confidence |
| ----- | ------------------------------- | ------------------------------ | --------- | --------------- | -------------------- | ------------------------------- | ---------- |
| `E01` | EEV adjustment mode             | automatic, Manual              | automatic | `1`             | ENUM, 0 to 1         | select, Configuration, disabled | documented |
| `E02` | Target degree of supreheat      | -20.0C to 20.0C, steps of 0.5C | 5.0C      | `5.0`           | TEMP1, -20 to 20     | number, Configuration, disabled | documented |
| `E03` | Original position of EEV        | 0N to 500N                     | 240N      | `240`           | DIGI2, 0 to 500      | number, Configuration, disabled | documented |
| `E04` | Minimal opening position of EEV | 0N to 500N                     | 100N      | `100`           | DIGI2, 0 to 500      | number, Configuration, disabled | documented |

- **E01 EEV control mode**: Whether the electronic expansion valve (EEV) regulates itself (Automatic) or not (Manual). 1 = Automatic is confirmed by the PHNIX PC1001 manual; the app lists the options in a different order. Values: Manual (0), Automatic (1). Keep Automatic. In Manual the valve no longer follows the superheat target E02, which can return liquid refrigerant to the compressor or starve the coil.
- **E02 Target superheat**: Superheat the EEV aims for: suction minus coil temperature (T05 - T04). Compare it with the Superheat sensor. A higher target closes the valve further (less refrigerant, safer for the compressor, less heat); a lower one opens it. Change it only with an installer: too little superheat can return liquid to the compressor.
- **E03 EEV start position**: EEV opening when the compressor starts. The valve starts at E03 (O07 reads 240 at start-up) and then regulates towards E02.
- **E04 EEV minimum position**: Smallest opening the EEV may regulate down to. Your EEV often sits at this minimum because the measured superheat is below E02. Lowering E04 lets it close further and reduces the refrigerant flow; don't change it to chase the superheat reading without an installer.

### Unit settings

| Code  | App name                     | App range  | App value | Raw cloud value | Cloud type and range | Home Assistant                  | Confidence |
| ----- | ---------------------------- | ---------- | --------- | --------------- | -------------------- | ------------------------------- | ---------- |
| `H98` | Model selection              | 0X08, 0X18 | 0X08      | `2`             | ENUM, 2 to 3         | sensor, Diagnostic              | uncertain  |
| `H99` | Compensate to the shown temp | NO, YES    | NO        | `0`             | ENUM, 0 to 1         | select, Configuration, disabled | uncertain  |

- **H98 Model selection**: Hardware model the controller is configured for. Values: 0X08 (2), 0X18 (3). Never change it: it tells the controller which hardware it drives. Your heat pump reports 2, which the app shows as 0X08. The cloud declares a range of 2-3, which supports 3 = 0X18, but that isn't confirmed.
- **H99 Display temperature compensation**: App description: 'Compensate to the shown temp'. Values: NO (0), YES (1). Not documented; it possibly corrects the displayed temperature. Keep NO.

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

- **T01 Ambient temperature**: Air temperature at the heat pump's air inlet. The booster settings R08-R10 and the compressor limit R12 compare against it.
- **T02 Bottom water temperature (return)**: Water temperature at the controller's bottom sensor. The controller is made for a tank with bottom and top sensors; on your installation it is on the return pipe. With R17 = NO this sensor controls heating: it starts when T02 is R03 below R01.
- **T03 Top water temperature (flow)**: Water temperature at the controller's top sensor; on your installation the flow pipe. T03 - T02 is the Water ΔT sensor. T10 showed the same value as T03 throughout your log.
- **T04 Coil temperature**: Temperature of the evaporator coil, the coil the air passes through. Defrost starts and ends on this temperature (D01, D02). It is also the reference for the superheat (T05 - T04).
- **T05 Suction temperature**: Refrigerant temperature in the suction pipe, the gas going from the coil to the compressor. It is not an air temperature. With E01 = Automatic the EEV keeps T05 - T04 (superheat) at E02. When T05 stays well below T04, as in your log (about -13 °C against 0 °C), the superheat is negative and the EEV closes to its minimum E04. The data can't tell whether that comes from the sensor placement or the refrigerant circuit; ask an installer rather than changing E02 or E04.
- **T10 Displayed water temperature**: Water temperature shown on the display and in the app; the climate entity's current temperature. Equal to T03 throughout your log.
- **O07 EEV position**: Current opening of the electronic expansion valve (EEV), 0-500 steps. On your heat pump it reads 480 (E05) while stopped or defrosting, starts at E03 (240) when heating begins, then works down towards E04 (100) as it regulates the superheat. Plot it with the Superheat sensor and E02.

## Codes from the app, password 066 (installer)

These are shown in addition to the codes above.

### Output configuration

The app shows the raw value 1 instead of one of its options for both codes.

| Code  | App name        | App range                                              | App value | Raw cloud value | Cloud type and range | Home Assistant     | Confidence |
| ----- | --------------- | ------------------------------------------------------ | --------- | --------------- | -------------------- | ------------------ | ---------- |
| `/01` | Usage of OUT 05 | Low speed, Solar water pump                            | 1         | `1`             | ENUM, 0 to 2         | sensor, Diagnostic | uncertain  |
| `/02` | Usage of OUT 06 | No output, Solar water pump, Solar water release valve | 1         | `1`             | ENUM, 0 to 3         | sensor, Diagnostic | uncertain  |

- **/01 Use of OUT05**: Function of output OUT05 (O05): fan low speed or solar water pump.
- **/02 Use of OUT06**: Function of output OUT06 (O06): no output, solar water pump or solar water release valve.

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

- **D01 Defrost start temperature**: Coil temperature (T04) below which a defrost can start. Defrost starts when the coil (T04) is below D01 and at least D03 minutes have passed since the last one. It ends when T04 reaches D02 or after D04 minutes, and lasts at least D05 minutes (PHNIX manuals). During a defrost the compressor keeps running and the fan stops (Trianco S300 manual). A lower D01 means fewer, later defrosts. Change it only if the coil ices up or defrosts too often.
- **D02 Defrost end temperature**: Coil temperature (T04) at which a defrost ends. Defrost starts when the coil (T04) is below D01 and at least D03 minutes have passed since the last one. It ends when T04 reaches D02 or after D04 minutes, and lasts at least D05 minutes (PHNIX manuals). During a defrost the compressor keeps running and the fan stops (Trianco S300 manual). A higher D02 clears the ice more thoroughly but lasts longer.
- **D03 Defrost interval**: Minimum time between two defrosts. The app calls it 'Duration of defrosting', but a 30-90 minute range only makes sense as the interval, as in the PHNIX manuals; a Trianco S300 with D03 = 45 defrosted every 45-49 minutes.
- **D04 Maximum defrost time**: Longest a defrost may last.
- **D05 Minimum defrost time**: Shortest a defrost lasts.
- **D06 Defrost method**: How defrosts are started. Values: Standard (0), Economic (1), Intelligent (2). Standard uses D01-D05; Intelligent also uses D07. What Economic changes isn't documented. Your heat pump reports 0 = Standard; 1 and 2 follow the app's order.
- **D07 Intelligent defrost threshold**: Threshold used by intelligent defrosting (D06 = Intelligent). Not documented; it probably compares the ambient and coil temperatures. It only matters with D06 = Intelligent. Leave it unchanged.

**D03, D04, D05:** Defrost starts when the coil (T04) is below D01 and at least D03 minutes have passed since the last one. It ends when T04 reaches D02 or after D04 minutes, and lasts at least D05 minutes (PHNIX manuals). During a defrost the compressor keeps running and the fan stops (Trianco S300 manual).

### Disinfection

| Code  | App name                      | App range                     | App value | Raw cloud value | Cloud type and range | Home Assistant                  | Confidence |
| ----- | ----------------------------- | ----------------------------- | --------- | --------------- | -------------------- | ------------------------------- | ---------- |
| `G01` | Disinfection target temp      | 30.0C to 70.0C, steps of 0.5C | 60.0C     | `60.0`          | TEMP1, 30 to 70      | number, Configuration, disabled | observed   |
| `G02` | Duration of disinfection      | 0Min to 90Min, steps of 1Min  | 0Min      | `0`             | DIGI1, 0 to 90       | number, Configuration, disabled | observed   |
| `G03` | Startup point of disinfection | 0H to 23H, steps of 1H        | 0H        | `0`             | DIGI1, 0 to 23       | number, Configuration, disabled | observed   |
| `G04` | Circle of disinfection        | 1Day to 99Day, steps of 1Day  | 7Day      | `7`             | DIGI1, 1 to 99       | number, Configuration, disabled | observed   |

- **G01 Disinfection temperature**: Water temperature the disinfection cycle heats to.
- **G02 Disinfection duration**: How long the water is held at G01.
- **G03 Disinfection start hour**: Hour of the day the disinfection starts.
- **G04 Disinfection interval**: Days between disinfection cycles.

Disinfection (anti-legionella) heats the water to G01 every G04 days at G03 o'clock and holds it for G02 minutes. G02 = 0, as on your heat pump, most likely means it never runs. Above 60 °C (the limit of R01) the booster is probably needed.

### Expansion valve

| Code  | App name                       | App range  | App value | Raw cloud value | Cloud type and range | Home Assistant     | Confidence |
| ----- | ------------------------------ | ---------- | --------- | --------------- | -------------------- | ------------------ | ---------- |
| `E05` | Position of EEV for defrosting | 0N to 500N | 480N      | `480`           | DIGI2, 0 to 500      | sensor, Diagnostic | documented |

- **E05 EEV defrost position**: EEV opening during defrost. O07 reads this value (480) during defrost and while the compressor is stopped.

### Unit settings

| Code  | App name                                            | App range                         | App value      | Raw cloud value | Cloud type and range | Home Assistant                  | Confidence |
| ----- | --------------------------------------------------- | --------------------------------- | -------------- | --------------- | -------------------- | ------------------------------- | ---------- |
| `H01` | Remember the power status of device when power down | NO, YES                           | YES            | `1`             | ENUM, 0 to 1         | select, Configuration, disabled | observed   |
| `H03` | Heating source                                      | Air source                        | Air source     | `0`             | ENUM, 0 to 0         | sensor, Diagnostic              | observed   |
| `H07` | Temperature unit                                    | Celsius degree, Fahrenheit degree | Celsius degree | `0`             | ENUM, 0 to 1         | sensor, Diagnostic              | observed   |
| `H30` | Device address                                      | 1 to 255, steps of 1              | 1              | `1`             | DIGI1, 1 to 255      | sensor, Diagnostic              | observed   |
| `H31` | Intelligent control mode                            | Centralized control, DTU&WIFI     | DTU&WIFI       | `1`             | ENUM, 0 to 1         | sensor, Diagnostic              | observed   |
| `H32` | Circle of submitting data to Cloud                  | 1Min to 255Min, steps of 1Min     | 1Min           | `1`             | DIGI1, 1 to 255      | number, Configuration, disabled | observed   |

- **H01 Remember power state**: Whether the heat pump returns to its previous on/off state after a power cut. Values: NO (0), YES (1). YES restarts heating after a power cut if it was on before. Keep YES unless it should stay off. On a Trianco S300 every on/off, including from the remote contacts, raised T21 by 4, so with YES each switch is most likely written to the controller's memory.
- **H03 Heating source**: Type of heat source. The app only offers Air source. Values: Air source (0).
- **H07 Temperature unit**: Unit the heat pump reports temperatures in. Values: Celsius degree (0), Fahrenheit degree (1). The Temperature Unit select in Home Assistant must match it. If you change H07 in the app, change the select as well.
- **H30 Device address**: Address of the controller on its communication bus. Read-only: a wrong address can cut the controller off from the Wi-Fi module.
- **H31 Control mode**: Whether a central controller or the DTU/Wi-Fi module controls the heat pump. Values: Centralized control (0), DTU&WIFI (1). Must stay on DTU&WIFI for the app and Home Assistant to work, so it is read-only.
- **H32 Cloud upload interval**: Minutes between the heat pump's own uploads to the cloud. Your heat pump uses 1 minute. Home Assistant reads the cloud every 5 minutes, so a larger value only makes the readings older. Keep 1.

### Solar circuit

Several values are outside the app's own range, which the app shows as they are.

| Code  | App name                                                | App range                     | App value | Raw cloud value | Cloud type and range | Home Assistant               | Confidence |
| ----- | ------------------------------------------------------- | ----------------------------- | --------- | --------------- | -------------------- | ---------------------------- | ---------- |
| `N01` | The sensor to control solar water pump                  | Bottom, Top                   | Bottom    | `0`             | ENUM, 0 to 1         | sensor, Diagnostic, disabled | uncertain  |
| `N02` | Longest running time of solar water pump                | 1Min to 30Min, steps of 1Min  | 10Min     | `10`            | DIGI1, 1 to 30       | sensor, Diagnostic, disabled | uncertain  |
| `N03` | Temp hysteresis of solar water pump                     | 0.0C to 20.0C, steps of 0.5C  | 10.0C     | `10.0`          | TEMP1, 0 to 20       | sensor, Diagnostic, disabled | uncertain  |
| `N04` | Activate the nighttime temp decreases mode              | NO, YES                       | YES       | `1`             | ENUM, 0 to 1         | sensor, Diagnostic, disabled | uncertain  |
| `N05` | Startup point of the nighttime temp decreases mode      | 0H to 23H, steps of 1H        | 2H        | `2`             | DIGI1, 0 to 23       | sensor, Diagnostic, disabled | uncertain  |
| `N06` | Shutdown point of the nighttime temp decreases mode     | 0H to 23H, steps of 1H        | 3H        | `3`             | DIGI1, 0 to 23       | sensor, Diagnostic, disabled | uncertain  |
| `N07` | Startup temp of decreasing solar water temp             | 40.0C to 90.0C, steps of 0.5C | -25.0C    | `-25.0`         | TEMP1, 40 to 90      | sensor, Diagnostic, disabled | uncertain  |
| `N08` | Temp hysteresis of stopping decreasing solar water temp | 1.0C to 40.0C, steps of 0.5C  | -30.0C    | `-30.0`         | TEMP1, 1 to 40       | sensor, Diagnostic, disabled | uncertain  |
| `N09` | Solar water releasing temp                              | 50.0C to 90.0C, steps of 0.5C | -30.0C    | `-30.0`         | TEMP1, 50 to 90      | sensor, Diagnostic, disabled | uncertain  |
| `N10` | Shutdown temp of solar water pump                       | 50.0C to 90.0C, steps of 0.5C | -30.0C    | `-30.0`         | TEMP1, 50 to 90      | sensor, Diagnostic, disabled | uncertain  |
| `N11` | Working mode of solar water pump                        | Dependent, Independent        | Dependent | `0`             | ENUM, 0 to 1         | sensor, Diagnostic, disabled | uncertain  |

- **N01 Solar pump control sensor**: App name: 'The sensor to control solar water pump'. Values: Bottom (0), Top (1).
- **N02 Solar pump maximum run time**: App name: 'Longest running time of solar water pump'.
- **N03 Solar pump hysteresis**: App name: 'Temp hysteresis of solar water pump'.
- **N04 Night temperature reduction**: App name: 'Activate the nighttime temp decreases mode'. Values: NO (0), YES (1).
- **N05 Night reduction start hour**: App name: 'Startup point of the nighttime temp decreases mode'.
- **N06 Night reduction end hour**: App name: 'Shutdown point of the nighttime temp decreases mode'.
- **N07 Solar water cooling start temperature**: App name: 'Startup temp of decreasing solar water temp'.
- **N08 Solar water cooling stop hysteresis**: App name: 'Temp hysteresis of stopping decreasing solar water temp'.
- **N09 Solar water release temperature**: App name: 'Solar water releasing temp'.
- **N10 Solar pump stop temperature**: App name: 'Shutdown temp of solar water pump'.
- **N11 Solar pump working mode**: App name: 'Working mode of solar water pump'. Values: Dependent (0), Independent (1).

**N01, N02, N03, N07, N08, N09, N10, N11:** Solar circuit setting. Your installation has no solar circuit, so the N codes presumably have no effect; several hold values outside the app's own range (for example N07 = -25.0). Read-only.

**N04, N05, N06:** It may lower the target between N05 and N06 o'clock; your heat pump has it set to YES for 02:00-03:00. Whether it applies without a solar circuit isn't known. Read-only.

### Booster and compressor

| Code  | App name                                                         | App range                      | App value | Raw cloud value | Cloud type and range | Home Assistant                  | Confidence |
| ----- | ---------------------------------------------------------------- | ------------------------------ | --------- | --------------- | -------------------- | ------------------------------- | ---------- |
| `R07` | Booster replaces heat pump?                                      | NO, YES                        | YES       | `1`             | ENUM, 0 to 1         | select, Configuration, disabled | documented |
| `R08` | Setpoint of ambient temp to activate booster to replace heatpump | -20.0C to 10.0C, steps of 0.5C | -5.0C     | `-5.0`          | TEMP1, -20 to 10     | number, Configuration, disabled | documented |
| `R09` | Setpoint of ambient temp to activate booster without delay       | 0.0C to 30.0C, steps of 0.5C   | 5.0C      | `5.0`           | TEMP1, 0 to 30       | number, Configuration, disabled | documented |
| `R10` | Setpoint of ambient temp to activate booster with delay          | 10.0C to 40.0C, steps of 0.5C  | 25.0C     | `25.0`          | TEMP1, 10 to 40      | number, Configuration, disabled | documented |
| `R12` | Ambient temp of shutting down compressor compulsively            | -30.0C to -5.0C, steps of 0.5C | -15.0C    | `-15.0`         | TEMP1, -30 to -5     | sensor, Diagnostic              | observed   |
| `R14` | The target temp of second heating source                         | 10.0C to 60.0C, steps of 0.5C  | -10.0C    | `-10.0`         | TEMP1, 38 to 78      | sensor, Diagnostic              | uncertain  |
| `R15` | Maximal ambient temp of working compressor                       | 55.0C to 80.0C, steps of 0.5C  | 78.0C     | `78.0`          | TEMP1, 55 to 80      | sensor, Diagnostic              | uncertain  |
| `R17` | Enable top sensor to control compressor?                         | NO, YES                        | NO        | `0`             | ENUM, 0 to 1         | sensor, Diagnostic              | observed   |
| `R18` | Hysteresis of heat pump startup(top sensor)                      | 1.0C to 20.0C, steps of 0.5C   | 5.0C      | `5.0`           | TEMP1, 1 to 20       | sensor, Diagnostic              | observed   |
| `R19` | Setpoint 1 of ambient temp to stop compressor                    | 30.0C to 90.0C, steps of 0.5C  | 65.0C     | `65.0`          | TEMP1, 30 to 90      | sensor, Diagnostic              | uncertain  |
| `R20` | Setpoint 2 of ambient temp to stop compressor                    | 30.0C to 90.0C, steps of 0.5C  | 55.0C     | `55.0`          | TEMP1, 30 to 90      | sensor, Diagnostic              | uncertain  |

- **R07 Booster replaces heat pump**: Whether the booster takes over from the heat pump below the R08 ambient temperature. Values: NO (0), YES (1). Electric heater logic (Trianco S300 manual): in Standard mode the heater starts if the target isn't reached after R06 minutes; in High demand mode it starts without the delay; in Eco mode it never starts; both decide with the R03 differential. Intelligent mode picks Eco above R10 ambient (T01), Standard between R09 and R10 and High demand between R08 and R09; with R07 = YES the heater presumably replaces the heat pump below R08. The heater output is O02. Only relevant with an electric heater fitted. With YES and no booster fitted, the heat pump presumably stops heating below R08 (-5.0 °C on your unit).
- **R08 Booster-only below ambient**: Lower ambient temperature (T01) limit of the High demand band of Intelligent mode; below it the electric heater presumably replaces the heat pump (R07 = YES).
- **R09 Booster without delay below ambient**: Ambient temperature (T01) between the High demand (below) and Standard (above) bands of Intelligent mode.
- **R10 Booster with delay below ambient**: Ambient temperature (T01) above which Intelligent mode runs as Eco, without the electric heater; below it, Standard.
- **R12 Compressor cut-off ambient temperature**: Ambient temperature (T01) below which the compressor is forced off.
- **R14 Second heat source target temperature**: Target temperature of the second heating source (see S06). Your heat pump holds -10.0, outside the app's own range, which suggests it isn't used.
- **R15 Maximum ambient for compressor**: App name: 'Maximal ambient temp of working compressor'. A 55-80 °C range fits a water or refrigerant limit better than an air temperature.
- **R17 Top sensor controls compressor**: Whether the top sensor (T03) controls the compressor instead of the bottom sensor (T02). Values: NO (0), YES (1).
- **R18 Start hysteresis (top sensor)**: Restart hysteresis of the top sensor, used instead of R03 when R17 = YES.
- **R19 Compressor stop setpoint 1**: App name: 'Setpoint 1 of ambient temp to stop compressor'.
- **R20 Compressor stop setpoint 2**: App name: 'Setpoint 2 of ambient temp to stop compressor'.

**R08, R09, R10:** Electric heater logic (Trianco S300 manual): in Standard mode the heater starts if the target isn't reached after R06 minutes; in High demand mode it starts without the delay; in Eco mode it never starts; both decide with the R03 differential. Intelligent mode picks Eco above R10 ambient (T01), Standard between R09 and R10 and High demand between R08 and R09; with R07 = YES the heater presumably replaces the heat pump below R08. The heater output is O02. Only relevant with an electric heater fitted.

**R19, R20:** Not documented. A 30-90 °C range fits a water temperature better than an air temperature.

### Switch inputs

The app shows `CL` (closed) or `OP` (open).

| Code  | App name                              | App range | App value | Raw cloud value | Cloud type and range | Home Assistant     | Confidence |
| ----- | ------------------------------------- | --------- | --------- | --------------- | -------------------- | ------------------ | ---------- |
| `S01` | Remote ON/OFF switch                  | CL, OP    | CL        | empty           |                      | sensor, Diagnostic | uncertain  |
| `S03` | Low pressure switch                   | CL, OP    | OP        | empty           |                      | sensor, Diagnostic | uncertain  |
| `S04` | High pressure switch                  | CL, OP    | CL        | empty           |                      | sensor, Diagnostic | uncertain  |
| `S05` | Accelerate the running time of heater | CL, OP    | CL        | empty           |                      | sensor, Diagnostic | uncertain  |
| `S06` | Second heating source                 | CL, OP    | OP        | empty           |                      | sensor, Diagnostic | uncertain  |

- **S01 Remote on/off input**: Remote on/off terminals, DI05 and GND in the manual, linked at the factory; a thermostat or volt-free contact there switches the heat pump on and off. Values: Open (0), Closed (1). The cloud never reports S01 itself, but its effect shows in Power and in bit 0 of 2050. On a Trianco S300, opening the remote on/off contacts (S01, DI05 and GND in the manual) set Power to 0 and closing them set it to 1 by the next read, within a minute. The app shows CL (closed) or OP (open); 1 = Closed is assumed for this entity, which stays unavailable.
- **S03 Low pressure switch**: Low pressure switch of the refrigerant circuit. Values: Open (0), Closed (1). The app showed OP while the heat pump ran normally, so Open isn't necessarily a fault. In your log the cloud returned no value for the S and O codes, even while the app was open, so this shows Unavailable until the heat pump reports it. The app shows CL (closed) or OP (open); 1 = Closed is assumed.
- **S04 High pressure switch**: High pressure switch of the refrigerant circuit. Values: Open (0), Closed (1). The app showed CL during normal operation. In your log the cloud returned no value for the S and O codes, even while the app was open, so this shows Unavailable until the heat pump reports it. The app shows CL (closed) or OP (open); 1 = Closed is assumed.
- **S05 Heater acceleration input**: App name: 'Accelerate the running time of heater'. Values: Open (0), Closed (1). Probably the input that starts the booster without the R06 delay. In your log the cloud returned no value for the S and O codes, even while the app was open, so this shows Unavailable until the heat pump reports it. The app shows CL (closed) or OP (open); 1 = Closed is assumed.
- **S06 Second heating source input**: Second heating source input (see R14). Values: Open (0), Closed (1).

**S06:** In your log the cloud returned no value for the S and O codes, even while the app was open, so this shows Unavailable until the heat pump reports it. The app shows CL (closed) or OP (open); 1 = Closed is assumed.

### Outputs and running hours

The app shows `ON` or `OFF` for the outputs.

| Code  | App name                                | App range | App value | Raw cloud value | Cloud type and range | Home Assistant     | Confidence |
| ----- | --------------------------------------- | --------- | --------- | --------------- | -------------------- | ------------------ | ---------- |
| `O01` | Compressor                              | ON, OFF   | ON        | empty           |                      | sensor, Diagnostic | uncertain  |
| `O02` | Electrical heater                       | ON, OFF   | OFF       | empty           |                      | sensor, Diagnostic | uncertain  |
| `O03` | 4-way valve                             | ON, OFF   | ON        | empty           |                      | sensor, Diagnostic | uncertain  |
| `O04` | Fan high speed                          | ON, OFF   | OFF       | empty           |                      | sensor, Diagnostic | uncertain  |
| `O05` | Fan low speed                           | ON, OFF   | OFF       | empty           |                      | sensor, Diagnostic | uncertain  |
| `O06` | Reserve/solar pump/solar valve pump     | ON, OFF   | OFF       | empty           |                      | sensor, Diagnostic | uncertain  |
| `O08` | Accumulative running time of compressor |           | 211H      | `210` to `215`  | DIGI1                | sensor, Sensors    | observed   |
| `O09` | Accumulative running time of booster    |           | 0H        | `0`             | DIGI1                | sensor, Sensors    | observed   |

- **O01 Compressor**: Compressor output. Values: Off (0), On (1).
- **O02 Electric heater (booster)**: Electric heater (booster) output. Values: Off (0), On (1).
- **O03 4-way valve**: Four-way valve output, which reverses the refrigerant flow, for example to defrost. Values: Off (0), On (1).
- **O04 Fan high speed**: Fan high speed output. Values: Off (0), On (1).
- **O05 Fan low speed (OUT05)**: Fan low speed output (OUT05, see /01). Values: Off (0), On (1).
- **O06 Solar pump/valve (OUT06)**: Reserve, solar pump or solar valve output (OUT06, see /02). Values: Off (0), On (1).
- **O08 Compressor running hours**: Total compressor running time.
- **O09 Booster running hours**: Total booster (electric heater) running time.

**O01, O02, O03, O04, O05, O06:** In your log the cloud returned no value for the S and O codes, even while the app was open, so this shows Unavailable until the heat pump reports it. 1 = On is assumed.

**O08, O09:** A statistics graph with the 'change' statistic per day shows the daily running hours.

## App settings

### Mode and ventilation

The app's settings also have an **Electric heating** switch and an **Align the device time** button. The codes behind them don't appear in the cloud data, so they aren't available in Home Assistant. The About page lists the device MAC, the PCB software code and version, and the display software code and version.

| Code        | App name                | App range                                                  | App value | Raw cloud value | Cloud type and range | Home Assistant   | Confidence |
| ----------- | ----------------------- | ---------------------------------------------------------- | --------- | --------------- | -------------------- | ---------------- | ---------- |
| `mode_real` | Select Mode             | Intelligent Mode, Eco Mode, Hybrid Mode, Fast Heating Mode | Eco Mode  | `2`             | ENUM, 0 to 4         | select, Controls | observed   |
| `M17`       | Ventilation / Air Speed | Ventilation ON/OFF, Air Speed Low or High                  |           | `1` to `2`      | ENUM                 | select, Controls | documented |

- **mode_real Operating mode**: Operating mode, as on the app's Select Mode page. Hybrid is the manual's Standard mode and Fast heating its High demand mode. Values: Intelligent (0), Eco (2), Hybrid (3), Fast heating (4). Eco: heat pump only. Hybrid: the electric heater helps if the target isn't reached after R06 minutes. Fast heating: the electric heater runs at once. Intelligent: chooses between them by the ambient temperature (R08-R10). Without an electric heater fitted, Eco is the mode to use. Vacation is set on the app's Timer page and shows as Mode 7 and the Vacation mode sensor. The values were confirmed by switching modes in the app on a Trianco S300.
- **M17 Fan after heating**: What the fan does once the water has reached its target temperature: run at low speed, run at high speed, or stop (Trianco S300 manual). It is the app's Ventilation switch and Air Speed knob. Values: Off (0), Low (1), High (2). A ventilation setting: Low or High keeps air moving through the unit after heating stops, Off lets the fan stop. While heating the controller runs the fan itself, so this doesn't change the fan speed during heating or the efficiency. The climate entity's fan modes write the same code.

## Codes not shown in the app

### Reported by the cloud

Their names come from the vendor's parameter file, translated where it is Chinese.

| Code  | Name in Home Assistant               | Raw cloud value  | Cloud type and range | Home Assistant               | Confidence |
| ----- | ------------------------------------ | ---------------- | -------------------- | ---------------------------- | ---------- |
| `T06` | T06 Discharge temperature            | `40.5` to `87.0` | TEMP1                | sensor, Sensors              | observed   |
| `T11` | T11 Out-of-range protection count    | empty            |                      | sensor, Diagnostic, disabled | uncertain  |
| `T12` | T12 EEPROM write count               | empty            |                      | sensor, Diagnostic, disabled | uncertain  |
| `S02` | S02 Overheat protection switch       | empty            |                      | sensor, Diagnostic, disabled | uncertain  |
| `O10` | O10 3V_DE output                     | empty            |                      | sensor, Diagnostic, disabled | uncertain  |
| `O11` | O11 MV_DE output                     | empty            |                      | sensor, Diagnostic, disabled | uncertain  |
| `O12` | O12 Shutdown output                  | empty            |                      | sensor, Diagnostic, disabled | uncertain  |
| `O13` | O13 DTU/Wi-Fi online                 | empty            |                      | sensor, Diagnostic, disabled | uncertain  |
| `O14` | O14 Defrost                          | empty            |                      | sensor, Diagnostic, disabled | uncertain  |
| `O15` | O15 High-temperature hot water stage | empty            |                      | sensor, Diagnostic, disabled | uncertain  |

- **T06 Discharge temperature**: Not shown in the app. The vendor parameter file calls it the solar temperature. On a Trianco S300 it rises to 60-90 °C while the compressor runs and drops when it stops, while T07 reads -30.0, the value of a missing sensor. That fits the compressor discharge (hot gas) temperature, which the manual's P81/E04 protections watch.
- **T11 Out-of-range protection count**: Not shown in the app. Vendor name: '进入参数超范围保护次数', number of times the out-of-range parameter protection was entered.
- **T12 EEPROM write count**: Not shown in the app. Vendor name: '记忆芯片EEPROM存储次数', number of times the settings memory (EEPROM) was written.
- **S02 Overheat protection switch**: Not shown in the app. Vendor name: 'Over heat protection switch'. Values: Open (0), Closed (1). In your log the cloud returned no value for the S and O codes, even while the app was open, so this shows Unavailable until the heat pump reports it. The app shows CL (closed) or OP (open); 1 = Closed is assumed.
- **O10 3V_DE output**: Not shown in the app. Vendor name: '3V_DE'. Values: Off (0), On (1).
- **O11 MV_DE output**: Not shown in the app. Vendor name: 'MV_DE'. Values: Off (0), On (1).
- **O12 Shutdown output**: Not shown in the app. Vendor name: 'shutDown'. Values: Off (0), On (1).
- **O13 DTU/Wi-Fi online**: Not shown in the app. Vendor name: 'DTU&WIFI是否上线', whether the DTU/Wi-Fi module is online. Values: NO (0), YES (1).
- **O14 Defrost**: Not shown in the app. Vendor name: '除霜Defrost', defrost. Values: NO (0), YES (1).
- **O15 High-temperature hot water stage**: Not shown in the app. Vendor name: '系统是否进入高温热水阶段', whether the system is in the high-temperature hot water stage. Values: NO (0), YES (1).

**T11, T12, O10, O11, O12, O13, O14, O15:** The cloud has returned no value for it so far.

### Timer page

Decoded by changing these settings in the app of a Trianco S300. Read-only.

| Code            | Name in Home Assistant     | Raw cloud value    | Cloud type and range | Home Assistant         | Confidence |
| --------------- | -------------------------- | ------------------ | -------------------- | ---------------------- | ---------- |
| `vacation_mode` | Vacation mode (1129 bit 0) |                    |                      | binary_sensor, Sensors | observed   |
| `vacation_date` | Vacation date (L02-L04)    |                    |                      | sensor, Diagnostic     | observed   |
| `timer1_on`     | Timer 1 on (L06:L07)       |                    |                      | sensor, Diagnostic     | observed   |
| `timer1_off`    | Timer 1 off (L08:L09)      |                    |                      | sensor, Diagnostic     | observed   |
| `timer2_on`     | Timer 2 on (L10:L11)       |                    |                      | sensor, Diagnostic     | observed   |
| `timer2_off`    | Timer 2 off (L12:L13)      |                    |                      | sensor, Diagnostic     | observed   |
| `1133`          | 1133 Timer switches        | `0000000000000000` |                      | sensor, Diagnostic     | observed   |
| `1129`          | 1129 Vacation flags        | `0000000000000000` |                      | sensor, Diagnostic     | observed   |

- **Vacation mode (1129 bit 0)**: On while vacation mode is set on the app's Timer page. Turning vacation mode on in the app set this bit, changed Mode to 7 and stored the date in L02-L04; turning it off cleared the bit. Read-only.
- **Vacation date (L02-L04)**: Date set for vacation mode on the app's Timer page. The app showed 28-05-2010 while L02-L04 read 10, 5 and 28. Read-only.
- **Timer 1 on (L06:L07)**: On time of timer 1 on the app's Timer page. Setting timer 1 to 9:00-13:00 and timer 2 to 17:00-19:00 in the app set the hours in L06, L08, L10 and L12; L07 holds the minutes. Whether the timer is switched on is in 1133. Read-only.
- **Timer 1 off (L08:L09)**: Off time of timer 1 on the app's Timer page. Setting timer 1 to 9:00-13:00 and timer 2 to 17:00-19:00 in the app set the hours in L06, L08, L10 and L12; L09 holds the minutes. Whether the timer is switched on is in 1133. Read-only.
- **Timer 2 on (L10:L11)**: On time of timer 2 on the app's Timer page. Setting timer 1 to 9:00-13:00 and timer 2 to 17:00-19:00 in the app set the hours in L06, L08, L10 and L12; L11 holds the minutes. Whether the timer is switched on is in 1133. Read-only.
- **Timer 2 off (L12:L13)**: Off time of timer 2 on the app's Timer page. Setting timer 1 to 9:00-13:00 and timer 2 to 17:00-19:00 in the app set the hours in L06, L08, L10 and L12; L13 holds the minutes. Whether the timer is switched on is in 1133. Read-only.
- **1133 Timer switches**: The on/off switches of the app's two timers, as bits. Switching on all four timer switches in the app set bits 0-3, switching them off cleared them. Which bit is which switch isn't known yet.
- **1129 Vacation flags**: Flag word whose bit 0 is vacation mode.

### Status and flag words

| Code   | Name in Home Assistant     | Raw cloud value    | Cloud type and range | Home Assistant               | Confidence |
| ------ | -------------------------- | ------------------ | -------------------- | ---------------------------- | ---------- |
| `T21`  | T21 Settings write counter | `3136`             |                      | sensor, Diagnostic           | observed   |
| `2051` | 2051 Status bits           | `0000000000000010` |                      | sensor, Diagnostic           | observed   |
| `1142` | 1142 Flags                 | `0000000000000000` |                      | sensor, Diagnostic, disabled | uncertain  |
| `1151` | 1151 Flags                 | `0000000000000000` |                      | sensor, Diagnostic, disabled | uncertain  |
| `2085` | 2085 Flags                 | `0000000000000000` |                      | sensor, Diagnostic, disabled | uncertain  |
| `T08`  | T08 Flags                  | `0000000000000000` |                      | sensor, Diagnostic, disabled | uncertain  |
| `F03`  | F03 Flags                  | `0000000000000000` |                      | sensor, Diagnostic, disabled | uncertain  |
| `L28`  | L28 Flags                  | `0000000000000000` |                      | sensor, Diagnostic, disabled | uncertain  |

- **T21 Settings write counter**: Counter that rises with every settings change, equal to register 2027. It rose by 4 for a mode change and by 32 for setting both timers, so it most likely counts writes to the controller's settings memory, the vendor's EEPROM storage count (T12). That memory allows a limited number of writes.
- **2051 Status bits**: Packed status word: bit 2 is set during defrost, bit 1 has always been set.
- **1142 Flags**: Flag word, all bits clear so far.
- **1151 Flags**: Flag word. It read 1 after the app's Align the device time.
- **2085 Flags**: Flag word, all bits clear so far.
- **T08 Flags**: Sensor status flags on an Indol PV300 with the same product ID; all clear so far.
- **F03 Flags**: Configuration flags, all clear so far.
- **L28 Flags**: Schedule flags, all clear so far.

### Found by a scan of a related model

These come from the scan of an Indol PV300 with the same product ID. The status bits have since been checked on a Trianco S300; the rest is not confirmed there.

| Code                 | Name in Home Assistant                   | Raw cloud value    | Cloud type and range | Home Assistant               | Confidence |
| -------------------- | ---------------------------------------- | ------------------ | -------------------- | ---------------------------- | ---------- |
| `2050`               | 2050 Operating status bits               | `0001100100100000` |                      | sensor, Diagnostic           | uncertain  |
| `compressor_running` | Compressor running (2050 bit 8)          |                    |                      | binary_sensor, Sensors       | observed   |
| `electric_heater_on` | Electric heater on (2050 bit 9)          |                    |                      | binary_sensor, Sensors       | observed   |
| `defrost`            | Defrost (2051 bit 2)                     |                    |                      | binary_sensor, Sensors       | observed   |
| `M06`                | M06 Electric heating                     | `0`                |                      | sensor, Diagnostic, disabled | uncertain  |
| `O29`                | O29 Fan speed                            | `0`                |                      | sensor, Sensors, disabled    | uncertain  |
| `T07`                | T07 Discharge temperature (unconfirmed)  | `-30.0`            |                      | sensor, Sensors, disabled    | uncertain  |
| `T09`                | T09 Compressor temperature (unconfirmed) | `0`                |                      | sensor, Sensors, disabled    | uncertain  |

- **2050 Operating status bits**: Packed operating status word, shown as its 16 bits (bit 0 is the last). The bits decoded so far are listed under [Live data](#live-data-the-app-heartbeat).
- **Compressor running (2050 bit 8)**: Bit 8 of the operating status word 2050. Confirmed on a Trianco S300 against the app; it also followed the compressor on an Indol PV300 with the same product ID.
- **Electric heater on (2050 bit 9)**: Bit 9 of the operating status word 2050. Confirmed on a Trianco S300: it came on with the app's electric heater (O02) and Electric heating switch in Fast heating mode.
- **Defrost (2051 bit 2)**: Bit 2 of the status word 2051, set while the heat pump defrosts. On a Trianco S300 it was set for about 3 minutes every 45-49 minutes while the EEV moved to its defrost position (E05), the suction temperature jumped to 25-35 °C, the coil warmed up and the fan stopped, as the manual describes for defrost. Defrosts started with the coil (T04) at about D01 and at least D03 minutes after the previous one.
- **M06 Electric heating**: Electric heater request register. Values: Off (0), On (1). On an Indol PV300 with the same product ID (github.com/victor987/hitemp), writing 1 turned the electric heater on and 2 turned it off, after which it read 0. On a Trianco S300 it stayed 0 while the heater ran in Fast heating mode; the app's Electric heating switch followed the heater output (2050 bit 9) instead. Read-only here.
- **O29 Fan speed**: Fan speed in revolutions per minute. On an Indol PV300 with the same product ID (github.com/victor987/hitemp), it read 0 with the fan off and about 570 to 830 rpm when running. On a Trianco S300 it read 0 while the compressor ran, so it is disabled by default.
- **T07 Discharge temperature (unconfirmed)**: Not shown in the app. On an Indol PV300 with the same product ID (github.com/victor987/hitemp), it read 59 °C and was taken to be the compressor discharge temperature. On a Trianco S300 it reads -30.0, the value of a sensor that isn't fitted; T06 there behaves like the discharge temperature.
- **T09 Compressor temperature (unconfirmed)**: Not shown in the app. On an Indol PV300 with the same product ID (github.com/victor987/hitemp), it read 30-40 °C and dropped when the compressor started.

### Calculated by Home Assistant

| Code            | Name in Home Assistant | Raw cloud value | Cloud type and range | Home Assistant  | Confidence |
| --------------- | ---------------------- | --------------- | -------------------- | --------------- | ---------- |
| `superheat`     | Superheat (T05 - T04)  |                 |                      | sensor, Sensors | documented |
| `water_delta_t` | Water ΔT (T03 - T02)   |                 |                      | sensor, Sensors | observed   |

- **Superheat (T05 - T04)**: Suction minus coil temperature (T05 - T04), calculated by Home Assistant. The value E02 targets. Negative values mean the suction pipe reads colder than the coil, which keeps the EEV at E04.
- **Water ΔT (T03 - T02)**: Top minus bottom water temperature (T03 - T02), calculated by Home Assistant. On your installation, how much the water warms up through the heat pump. Heat pumps are usually designed for about 5 °C; a much larger value can mean low water flow.

### Requested without an entity

The climate entity and the Power sensor use some of these; the rest were requested by the original integration and are kept for diagnostics.

| Code            | Name in Home Assistant | Raw cloud value | Cloud type and range | Home Assistant            | Confidence |
| --------------- | ---------------------- | --------------- | -------------------- | ------------------------- | ---------- |
| `Power`         | Power                  | `1`             | ENUM, 0 to 1         | binary_sensor, Diagnostic | observed   |
| `Mode`          | Mode                   | `2`             | ENUM, 0 to 7         | requested, no entity      |            |
| `T20`           | T20                    | `1`             |                      | requested, no entity      |            |
| `L02`           | L02                    | `10`            |                      | requested, no entity      |            |
| `L03`           | L03                    | `5`             |                      | requested, no entity      |            |
| `L04`           | L04                    | `28`            |                      | requested, no entity      |            |
| `L06`           | L06                    | `0`             |                      | requested, no entity      |            |
| `L07`           | L07                    | `0`             |                      | requested, no entity      |            |
| `L08`           | L08                    | `0`             |                      | requested, no entity      |            |
| `L09`           | L09                    | `0`             |                      | requested, no entity      |            |
| `L10`           | L10                    | `0`             |                      | requested, no entity      |            |
| `L11`           | L11                    | `0`             |                      | requested, no entity      |            |
| `L12`           | L12                    | `0`             |                      | requested, no entity      |            |
| `L13`           | L13                    | `0`             |                      | requested, no entity      |            |
| `Manual-mute`   | Manual-mute            | empty           |                      | requested, no entity      |            |
| `Set_Temp`      | Set_Temp               | empty           |                      | requested, no entity      |            |
| `MO6`           | MO6                    | empty           |                      | requested, no entity      |            |
| `2074`          | 2074                   | `0`             | DIGI1                | requested, no entity      |            |
| `2075`          | 2075                   | `0`             | DIGI1                | requested, no entity      |            |
| `2076`          | 2076                   | `0`             | DIGI1                | requested, no entity      |            |
| `2077`          | 2077                   | empty           |                      | requested, no entity      |            |
| `1158`          | 1158                   | `0` to `23205`  | DIGI1                | requested, no entity      |            |
| `1159`          | 1159                   | empty           |                      | requested, no entity      |            |
| `2064`          | 2064                   | `0`             | DIGI1                | requested, no entity      |            |
| `ver`           | Version                | empty           |                      | requested, no entity      |            |
| `software_code` | Software Code          | empty           |                      | requested, no entity      |            |

- **Power**: On/off state of the heat pump (1 = on). The climate entity turns it on and off. On a Trianco S300, opening the remote on/off contacts (S01, DI05 and GND in the manual) set Power to 0 and closing them set it to 1 by the next read, within a minute. The compressor stopped or started about a minute later. Each switch raised T21 by 4: the on/off state is written to the controller's memory, most likely because H01 = YES remembers it. Whether switching on from Home Assistant or the app overrides open contacts isn't known, so avoid switching it from both.
- **Mode**: Active mode: 0 Intelligent, 2 Eco, 3 Hybrid, 4 Fast heating, 7 Vacation (seen in the app on a Trianco S300). In vacation mode_real keeps the mode to return to.
- **T20**: Read 1, equal to register 2026. Possibly the vendor's out-of-range protection count (T11).
- **L02**: Vacation year (20YY), from the app's Timer page.
- **L03**: Vacation month, from the app's Timer page.
- **L04**: Vacation day, from the app's Timer page.
- **L06**: Timer 1 on hour, from the app's Timer page.
- **L07**: Timer 1 on minute, from the app's Timer page.
- **L08**: Timer 1 off hour, from the app's Timer page.
- **L09**: Timer 1 off minute, from the app's Timer page.
- **L10**: Timer 2 on hour, from the app's Timer page.
- **L11**: Timer 2 on minute, from the app's Timer page.
- **L12**: Timer 2 off hour, from the app's Timer page.
- **L13**: Timer 2 off minute, from the app's Timer page.
- **Manual-mute**: Fan mode code of other models, requested for compatibility. Empty on HiTemp.
- **Set_Temp**: Setpoint code of other models, requested for compatibility. Empty on HiTemp.
- **MO6**: Requested by the original integration. Empty on HiTemp, meaning unknown.
- **2074**: Register requested by the original integration, meaning unknown.
- **2075**: Register requested by the original integration, meaning unknown.
- **2076**: Register requested by the original integration, meaning unknown.
- **2077**: Register requested by the original integration, meaning unknown.
- **1158**: Read 23205, the value of the app's live data request (app_heartbeat), for hours in one log, probably while the app was open, and 0 otherwise. The integration's own request has not changed it.
- **1159**: Register requested by the original integration, meaning unknown.
- **2064**: Register requested by the original integration, meaning unknown.
- **Version**: Version code of other models. Empty on HiTemp, see code_version and MainBoard Version.
- **Software Code**: Software code of other models. Empty on HiTemp, see code_version and MainBoard Version.

### Read for diagnostics only

These codes were found by the same scan. They are read in the separate live
data request and appear in the diagnostics, without entities, until their
meaning is known:

`2011`, `2012`, `2013`, `2014`, `2026`, `2027`, `2057`, `2058`, `2059`, `2068`, `2069`, `2070`, `2071`, `O18`, `O19`, `O21`, `O22`, `O23`, `O24`, `O25`, `O26`, `O27`, `O28`, `M07`, `M12`, `M13`, `M14`, `M15`, `M16`, `R02`, `R11`, `R13`, `R16`, `H09`, `H16`, `E06`, `C01`, `C02`, `C03`, `C05`, `C06`, `C07`, `C08`, `C09`, `D10`, `D11`, `D12`, `D13`, `F01`, `F02`, `F04`, `F05`, `F06`, `F07`, `F09`, `F10`, `F11`, `F12`, `F13`, `L29`, `L30`, `L31`, `L32`
