# HiTemp parameter guide

This guide covers the HiTemp heat pump with product ID `1245226668902080512`.
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

| Confidence | Meaning                                                                    |
| ---------- | -------------------------------------------------------------------------- |
| documented | Confirmed by PHNIX manuals for the same controller family                  |
| observed   | Clear from the app's name and seen behaving that way in the app or the log |
| uncertain  | Not documented and not observed; the meaning is a guess or unknown         |

Sources: the HiTemp app screens, a Home Assistant log of the heat pump from
2026-11-12, PHNIX controller manuals for the same board family, and the
[FoxAir_Control](https://github.com/dosordie/FoxAir_Control) project, which
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
- **Fan speed `M17`**: High usually helps in cold weather (see below).
- Leave everything else as it is unless you have a reason and understand the
  related codes.

## How the codes work together

- **Start and stop.** With `R17 = NO` the bottom sensor `T02` controls the
  compressor: heating starts when `T02` is `R03` below `R01` and stops at
  `R01`. With `R17 = YES` the top sensor `T03` and `R18` are used instead. On
  your installation the bottom sensor is on the return pipe and the top
  sensor on the flow pipe. `S01` is the remote on/off input.
- **Booster (electric heater, output `O02`).** `R04`-`R10`: with `R07 = YES`
  the booster replaces the heat pump when the ambient temperature `T01` is
  below `R08`; below `R09` it starts together with the heat pump; below `R10`
  it starts after the heat pump has run `R06` minutes; above `R10` only the
  heat pump heats. With `R04 = YES` the booster heats to `R05` instead of
  `R01`. `S05` (heater acceleration) probably starts it without the delay,
  and `O09` counts its hours. The controller expects an electric water
  heater; a heater at the air intake will behave differently. With `R07 =
YES` and no booster fitted, the heat pump presumably stops heating below
  `R08` (-5.0 °C on your unit).
- **Expansion valve (EEV).** With `E01 = Automatic` the EEV starts at `E03`
  when the compressor starts, then opens or closes to keep the superheat
  (`T05 - T04`) at `E02`, never closing below `E04`. During defrost it moves
  to `E05`. `O07` is its current position.
- **Defrost.** A defrost can start when the coil `T04` is below `D01` and at
  least `D03` minutes have passed since the last one. It ends when `T04`
  reaches `D02` or after `D04` minutes, and lasts at least `D05` minutes.
  `D06` chooses the method; `D07` is only used by the intelligent method.
- **Disinfection (anti-legionella).** `G01`-`G04`: heat to `G01` every `G04`
  days at `G03` o'clock for `G02` minutes. `G02 = 0` most likely means it
  never runs.
- **Fan.** `M17` sets the speed; `O04` and `O05` are the high and low speed
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
- **Fan:** `M17` changed from 1 to 2 when High was chosen in the app.
- **R01** was written every few minutes by something other than the app,
  between 56 and 60 °C.
- **Register 1158** read 23205 while the app was open and 0 otherwise. 23205
  is the value of the app's live data request (see below), so the board does
  receive it.
- **Empty codes:** the cloud returned nothing for `S01`-`S06`, `O01`-`O06`,
  `O10`-`O15`, `T11`, `T12`, `ver` and `software_code`, even while the app was
  open.

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

- Register `1158` shows 23205 while the app is open, so the heat pump receives
  the request.
- The S and O codes stayed empty in the log even while the app was open, so
  the heartbeat alone doesn't fill them. The app may read them under other
  names; the live codes above are the best guess.
- Whether the HiTemp board answers with any live codes is not known yet.

To find out, download the diagnostics of the heat pump while it runs. The
`live_data` section lists the result of the last heartbeat, which codes had a
value and which stayed empty, and any packed switch words as value, hex and
bits. The **Request live data** option in the integration's settings turns
the heartbeat off.

If the S and O codes stay empty, the remaining way to learn how the app reads
them is to capture its traffic while the parameter pages are open, for example
with Proxyman on iOS or HTTP Toolkit on Android, and share the request and
response of `getDataByCode` with the token and password removed.

## Status and faults

| Entity        | Shows                                                                                                                               |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Status        | Whether the cloud reports the heat pump online                                                                                      |
| API Status    | Whether the integration is logged in and reaching the cloud                                                                         |
| Cloud status  | OK, Session expired, Login rejected, Cannot connect or Cloud error, with the message and the time it started                        |
| Fault         | On while the cloud reports a fault                                                                                                  |
| Fault details | `No fault`, the cloud's description of the fault, or that it gave none; raw fault words as attributes when the heat pump sends them |

The cloud sends the fault description itself, so Home Assistant doesn't need
its own fault table. For reference, the manual of the related PHNIX PC4001
controller lists, among others: `P01` water inlet sensor failure, `P02` water
outlet sensor failure, `P04` ambient sensor failure, `E03` water flow
protection, `E04` overheat protection of the electric heater, `E06` too large
a difference between inlet and outlet water, and `E08` communication failure
between the display and the main board. The HiTemp controller may number its
faults differently.

The cloud's Chinese reply `请重新登录` means "please log in again": the
session expired, and the integration logs in again by itself.

## Codes from the app, password 002 (user)

### Target temperature and booster

| Code  | App name                                       | App range                     | App value  | Raw cloud value | Home Assistant   | Confidence |
| ----- | ---------------------------------------------- | ----------------------------- | ---------- | --------------- | ---------------- | ---------- |
| `R01` | Target temp                                    | 38.0C to 60.0C, steps of 0.5C | Set by you | `60.0`          | number, Controls | documented |
| `R03` | Hysteresis of heat pump startup(bottom sensor) | 1.0C to 20.0C, steps of 0.5C  | 5.0C       | `5.0`           | number, Controls | documented |
| `R04` | Enable R05 as setpoint of booster?             | NO, YES                       | NO         | `0`             | select, Controls | observed   |
| `R05` | Setpoint of booster                            | 30.0C to 90.0C, steps of 0.5C | 55.0C      | `55.0`          | number, Controls | observed   |
| `R06` | Booster startup delay                          | 0Min to 450Min, steps of 1Min | 200Min     | `200`           | number, Controls | documented |

- **R01 Target water temperature**: Target water temperature, the main control. The climate entity sets the same value. Heating starts when the controlling sensor (T02 bottom, or T03 top with R17 = YES) drops R03 below R01, and stops at R01. Each change is probably stored in the controller's memory, which allows a limited number of writes (see T12), so avoid automations that change R01 every few minutes.
- **R03 Start hysteresis (bottom sensor)**: How far below R01 the bottom sensor (T02) must drop before heating restarts. A small value keeps the water closer to R01 but starts the compressor more often; very small values cause short cycling. Your heat pump uses 5.0 °C.
- **R04 Use R05 as booster setpoint**: Whether the booster heats to its own setpoint R05 instead of R01. Values: NO (0), YES (1).
- **R05 Booster setpoint**: Water temperature the booster heats to when R04 = YES.
- **R06 Booster start delay**: How long the heat pump runs before the booster may help.

**R04, R05, R06:** Booster logic (PHNIX manuals): with R07 = YES the booster replaces the heat pump below R08 ambient; below R09 it starts together with the heat pump; below R10 it starts after the heat pump has run R06 minutes; above R10 only the heat pump heats. The booster output (O02) is meant for an electric water heater. Only relevant with a booster connected.

### Expansion valve

| Code  | App name                        | App range                      | App value | Raw cloud value | Home Assistant                  | Confidence |
| ----- | ------------------------------- | ------------------------------ | --------- | --------------- | ------------------------------- | ---------- |
| `E01` | EEV adjustment mode             | automatic, Manual              | automatic | `1`             | select, Configuration, disabled | documented |
| `E02` | Target degree of supreheat      | -20.0C to 20.0C, steps of 0.5C | 5.0C      | `5.0`           | number, Configuration, disabled | documented |
| `E03` | Original position of EEV        | 0N to 500N                     | 240N      | `240`           | number, Configuration, disabled | documented |
| `E04` | Minimal opening position of EEV | 0N to 500N                     | 100N      | `100`           | number, Configuration, disabled | documented |

- **E01 EEV control mode**: Whether the electronic expansion valve (EEV) regulates itself (Automatic) or not (Manual). 1 = Automatic is confirmed by the PHNIX PC1001 manual; the app lists the options in a different order. Values: Manual (0), Automatic (1). Keep Automatic. In Manual the valve no longer follows the superheat target E02, which can return liquid refrigerant to the compressor or starve the coil.
- **E02 Target superheat**: Superheat the EEV aims for: suction minus coil temperature (T05 - T04). Compare it with the Superheat sensor. A higher target closes the valve further (less refrigerant, safer for the compressor, less heat); a lower one opens it. Change it only with an installer: too little superheat can return liquid to the compressor.
- **E03 EEV start position**: EEV opening when the compressor starts. The valve starts at E03 (O07 reads 240 at start-up) and then regulates towards E02.
- **E04 EEV minimum position**: Smallest opening the EEV may regulate down to. Your EEV often sits at this minimum because the measured superheat is below E02. Lowering E04 lets it close further and reduces the refrigerant flow; don't change it to chase the superheat reading without an installer.

### Unit settings

| Code  | App name                     | App range  | App value | Raw cloud value | Home Assistant                  | Confidence |
| ----- | ---------------------------- | ---------- | --------- | --------------- | ------------------------------- | ---------- |
| `H98` | Model selection              | 0X08, 0X18 | 0X08      | `2`             | sensor, Diagnostic              | uncertain  |
| `H99` | Compensate to the shown temp | NO, YES    | NO        | `0`             | select, Configuration, disabled | uncertain  |

- **H98 Model selection**: Hardware model the controller is configured for. Values: 0X08 (2), 0X18 (3). Never change it: it tells the controller which hardware it drives. Your heat pump reports 2, which the app shows as 0X08. 3 = 0X18 follows from the original 2-3 range and isn't confirmed.
- **H99 Display temperature compensation**: App description: 'Compensate to the shown temp'. Values: NO (0), YES (1). Not documented; it possibly corrects the displayed temperature. Keep NO.

### Temperatures and EEV position

The raw values of live readings are the range seen in the log.

| Code  | App name                               | App range               | App value | Raw cloud value   | Home Assistant  | Confidence |
| ----- | -------------------------------------- | ----------------------- | --------- | ----------------- | --------------- | ---------- |
| `T01` | Ambient temperature                    | Steps of 0.5C           | 18.0C     | `17.5` to `22.0`  | sensor, Sensors | observed   |
| `T02` | Bottom temperature                     | Steps of 0.5C           | 33.5C     | `25.5` to `52.0`  | sensor, Sensors | observed   |
| `T03` | Top temperature                        | Steps of 0.5C           | 37.0C     | `30.0` to `55.5`  | sensor, Sensors | observed   |
| `T04` | Coil temperature                       | Steps of 0.5C           | 0.5C      | `-5.0` to `8.5`   | sensor, Sensors | documented |
| `T05` | Suction temperature                    | Steps of 0.5C           | -13.0C    | `-16.0` to `21.5` | sensor, Sensors | documented |
| `T10` | Temperature value shown on APP/display | Steps of 0.5C           | 37.0C     | `30.0` to `55.5`  | sensor, Sensors | observed   |
| `O07` | EEV current position                   | 0N to 500N, steps of 1N | 100N      | `100` to `480`    | sensor, Sensors | observed   |

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

| Code  | App name        | App range                                              | App value | Raw cloud value | Home Assistant     | Confidence |
| ----- | --------------- | ------------------------------------------------------ | --------- | --------------- | ------------------ | ---------- |
| `/01` | Usage of OUT 05 | Low speed, Solar water pump                            | 1         | `1`             | sensor, Diagnostic | uncertain  |
| `/02` | Usage of OUT 06 | No output, Solar water pump, Solar water release valve | 1         | `1`             | sensor, Diagnostic | uncertain  |

- **/01 Use of OUT05**: Function of output OUT05 (O05): fan low speed or solar water pump.
- **/02 Use of OUT06**: Function of output OUT06 (O06): no output, solar water pump or solar water release valve.

The heat pump reports 1, which the app can't name either, so the active function isn't known. Read-only.

### Defrost

| Code  | App name                         | App range                       | App value | Raw cloud value | Home Assistant                  | Confidence |
| ----- | -------------------------------- | ------------------------------- | --------- | --------------- | ------------------------------- | ---------- |
| `D01` | Defrosting startup temp          | -30.0C to 0.0C, steps of 0.5C   | -3.0C     | `-3.0`          | number, Configuration, disabled | documented |
| `D02` | Defrosting shutdown temp         | 0.0C to 30.0C, steps of 0.5C    | 13.0C     | `13.0`          | number, Configuration, disabled | documented |
| `D03` | Duration of defrosting           | 30Min to 90Min, steps of 1Min   | 45Min     | `45`            | number, Configuration, disabled | documented |
| `D04` | Longest duration of defrosting   | 1Min to 20Min, steps of 1Min    | 8Min      | `8.0`           | number, Configuration, disabled | documented |
| `D05` | Shortest duration of defrosting  | 1Min to 8Min, steps of 1Min     | 3Min      | `3.0`           | number, Configuration, disabled | documented |
| `D06` | Defrosting way                   | Standard, Economic, Intelligent | Standard  | `0`             | select, Configuration, disabled | observed   |
| `D07` | Intelligent defrosting judgement | -10.0C to 20.0C, steps of 0.5C  | 4.0C      | `4.0`           | number, Configuration, disabled | uncertain  |

- **D01 Defrost start temperature**: Coil temperature (T04) below which a defrost can start. Defrost starts when the coil (T04) is below D01 and at least D03 minutes have passed since the last one. It ends when T04 reaches D02 or after D04 minutes, and lasts at least D05 minutes (PHNIX manuals). A lower D01 means fewer, later defrosts. Change it only if the coil ices up or defrosts too often.
- **D02 Defrost end temperature**: Coil temperature (T04) at which a defrost ends. Defrost starts when the coil (T04) is below D01 and at least D03 minutes have passed since the last one. It ends when T04 reaches D02 or after D04 minutes, and lasts at least D05 minutes (PHNIX manuals). A higher D02 clears the ice more thoroughly but lasts longer.
- **D03 Defrost interval**: Minimum time between two defrosts. The app calls it 'Duration of defrosting', but a 30-90 minute range only makes sense as the interval, as in the PHNIX manuals.
- **D04 Maximum defrost time**: Longest a defrost may last.
- **D05 Minimum defrost time**: Shortest a defrost lasts.
- **D06 Defrost method**: How defrosts are started. Values: Standard (0), Economic (1), Intelligent (2). Standard uses D01-D05; Intelligent also uses D07. What Economic changes isn't documented. Your heat pump reports 0 = Standard; 1 and 2 follow the app's order.
- **D07 Intelligent defrost threshold**: Threshold used by intelligent defrosting (D06 = Intelligent). Not documented; it probably compares the ambient and coil temperatures. It only matters with D06 = Intelligent. Leave it unchanged.

**D03, D04, D05:** Defrost starts when the coil (T04) is below D01 and at least D03 minutes have passed since the last one. It ends when T04 reaches D02 or after D04 minutes, and lasts at least D05 minutes (PHNIX manuals).

### Disinfection

| Code  | App name                      | App range                     | App value | Raw cloud value | Home Assistant                  | Confidence |
| ----- | ----------------------------- | ----------------------------- | --------- | --------------- | ------------------------------- | ---------- |
| `G01` | Disinfection target temp      | 30.0C to 70.0C, steps of 0.5C | 60.0C     | `60.0`          | number, Configuration, disabled | observed   |
| `G02` | Duration of disinfection      | 0Min to 90Min, steps of 1Min  | 0Min      | `0`             | number, Configuration, disabled | observed   |
| `G03` | Startup point of disinfection | 0H to 23H, steps of 1H        | 0H        | `0`             | number, Configuration, disabled | observed   |
| `G04` | Circle of disinfection        | 1Day to 99Day, steps of 1Day  | 7Day      | `7`             | number, Configuration, disabled | observed   |

- **G01 Disinfection temperature**: Water temperature the disinfection cycle heats to.
- **G02 Disinfection duration**: How long the water is held at G01.
- **G03 Disinfection start hour**: Hour of the day the disinfection starts.
- **G04 Disinfection interval**: Days between disinfection cycles.

Disinfection (anti-legionella) heats the water to G01 every G04 days at G03 o'clock and holds it for G02 minutes. G02 = 0, as on your heat pump, most likely means it never runs. Above 60 °C (the limit of R01) the booster is probably needed.

### Expansion valve

| Code  | App name                       | App range  | App value | Raw cloud value | Home Assistant     | Confidence |
| ----- | ------------------------------ | ---------- | --------- | --------------- | ------------------ | ---------- |
| `E05` | Position of EEV for defrosting | 0N to 500N | 480N      | `480`           | sensor, Diagnostic | documented |

- **E05 EEV defrost position**: EEV opening during defrost. O07 reads this value (480) during defrost and while the compressor is stopped.

### Unit settings

| Code  | App name                                            | App range                         | App value      | Raw cloud value | Home Assistant                  | Confidence |
| ----- | --------------------------------------------------- | --------------------------------- | -------------- | --------------- | ------------------------------- | ---------- |
| `H01` | Remember the power status of device when power down | NO, YES                           | YES            | `1`             | select, Configuration, disabled | observed   |
| `H03` | Heating source                                      | Air source                        | Air source     | `0`             | sensor, Diagnostic              | observed   |
| `H07` | Temperature unit                                    | Celsius degree, Fahrenheit degree | Celsius degree | `0`             | sensor, Diagnostic              | observed   |
| `H30` | Device address                                      | 1 to 255, steps of 1              | 1              | `1`             | sensor, Diagnostic              | observed   |
| `H31` | Intelligent control mode                            | Centralized control, DTU&WIFI     | DTU&WIFI       | `1`             | sensor, Diagnostic              | observed   |
| `H32` | Circle of submitting data to Cloud                  | 1Min to 255Min, steps of 1Min     | 1Min           | `1`             | number, Configuration, disabled | observed   |

- **H01 Remember power state**: Whether the heat pump returns to its previous on/off state after a power cut. Values: NO (0), YES (1). YES restarts heating after a power cut if it was on before. Keep YES unless it should stay off.
- **H03 Heating source**: Type of heat source. The app only offers Air source. Values: Air source (0).
- **H07 Temperature unit**: Unit the heat pump reports temperatures in. Values: Celsius degree (0), Fahrenheit degree (1). The Temperature Unit select in Home Assistant must match it. If you change H07 in the app, change the select as well.
- **H30 Device address**: Address of the controller on its communication bus. Read-only: a wrong address can cut the controller off from the Wi-Fi module.
- **H31 Control mode**: Whether a central controller or the DTU/Wi-Fi module controls the heat pump. Values: Centralized control (0), DTU&WIFI (1). Must stay on DTU&WIFI for the app and Home Assistant to work, so it is read-only.
- **H32 Cloud upload interval**: Minutes between the heat pump's own uploads to the cloud. Your heat pump uses 1 minute. Home Assistant reads the cloud every 5 minutes, so a larger value only makes the readings older. Keep 1.

### Solar circuit

Several values are outside the app's own range, which the app shows as they are.

| Code  | App name                                                | App range                     | App value | Raw cloud value | Home Assistant               | Confidence |
| ----- | ------------------------------------------------------- | ----------------------------- | --------- | --------------- | ---------------------------- | ---------- |
| `N01` | The sensor to control solar water pump                  | Bottom, Top                   | Bottom    | `0`             | sensor, Diagnostic, disabled | uncertain  |
| `N02` | Longest running time of solar water pump                | 1Min to 30Min, steps of 1Min  | 10Min     | `10`            | sensor, Diagnostic, disabled | uncertain  |
| `N03` | Temp hysteresis of solar water pump                     | 0.0C to 20.0C, steps of 0.5C  | 10.0C     | `10.0`          | sensor, Diagnostic, disabled | uncertain  |
| `N04` | Activate the nighttime temp decreases mode              | NO, YES                       | YES       | `1`             | sensor, Diagnostic, disabled | uncertain  |
| `N05` | Startup point of the nighttime temp decreases mode      | 0H to 23H, steps of 1H        | 2H        | `2`             | sensor, Diagnostic, disabled | uncertain  |
| `N06` | Shutdown point of the nighttime temp decreases mode     | 0H to 23H, steps of 1H        | 3H        | `3`             | sensor, Diagnostic, disabled | uncertain  |
| `N07` | Startup temp of decreasing solar water temp             | 40.0C to 90.0C, steps of 0.5C | -25.0C    | `-25.0`         | sensor, Diagnostic, disabled | uncertain  |
| `N08` | Temp hysteresis of stopping decreasing solar water temp | 1.0C to 40.0C, steps of 0.5C  | -30.0C    | `-30.0`         | sensor, Diagnostic, disabled | uncertain  |
| `N09` | Solar water releasing temp                              | 50.0C to 90.0C, steps of 0.5C | -30.0C    | `-30.0`         | sensor, Diagnostic, disabled | uncertain  |
| `N10` | Shutdown temp of solar water pump                       | 50.0C to 90.0C, steps of 0.5C | -30.0C    | `-30.0`         | sensor, Diagnostic, disabled | uncertain  |
| `N11` | Working mode of solar water pump                        | Dependent, Independent        | Dependent | `0`             | sensor, Diagnostic, disabled | uncertain  |

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

| Code  | App name                                                         | App range                      | App value | Raw cloud value | Home Assistant                  | Confidence |
| ----- | ---------------------------------------------------------------- | ------------------------------ | --------- | --------------- | ------------------------------- | ---------- |
| `R07` | Booster replaces heat pump?                                      | NO, YES                        | YES       | `1`             | select, Configuration, disabled | documented |
| `R08` | Setpoint of ambient temp to activate booster to replace heatpump | -20.0C to 10.0C, steps of 0.5C | -5.0C     | `-5.0`          | number, Configuration, disabled | documented |
| `R09` | Setpoint of ambient temp to activate booster without delay       | 0.0C to 30.0C, steps of 0.5C   | 5.0C      | `5.0`           | number, Configuration, disabled | documented |
| `R10` | Setpoint of ambient temp to activate booster with delay          | 10.0C to 40.0C, steps of 0.5C  | 25.0C     | `25.0`          | number, Configuration, disabled | documented |
| `R12` | Ambient temp of shutting down compressor compulsively            | -30.0C to -5.0C, steps of 0.5C | -15.0C    | `-15.0`         | sensor, Diagnostic              | observed   |
| `R14` | The target temp of second heating source                         | 10.0C to 60.0C, steps of 0.5C  | -10.0C    | `-10.0`         | sensor, Diagnostic              | uncertain  |
| `R15` | Maximal ambient temp of working compressor                       | 55.0C to 80.0C, steps of 0.5C  | 78.0C     | `78.0`          | sensor, Diagnostic              | uncertain  |
| `R17` | Enable top sensor to control compressor?                         | NO, YES                        | NO        | `0`             | sensor, Diagnostic              | observed   |
| `R18` | Hysteresis of heat pump startup(top sensor)                      | 1.0C to 20.0C, steps of 0.5C   | 5.0C      | `5.0`           | sensor, Diagnostic              | observed   |
| `R19` | Setpoint 1 of ambient temp to stop compressor                    | 30.0C to 90.0C, steps of 0.5C  | 65.0C     | `65.0`          | sensor, Diagnostic              | uncertain  |
| `R20` | Setpoint 2 of ambient temp to stop compressor                    | 30.0C to 90.0C, steps of 0.5C  | 55.0C     | `55.0`          | sensor, Diagnostic              | uncertain  |

- **R07 Booster replaces heat pump**: Whether the booster takes over from the heat pump below the R08 ambient temperature. Values: NO (0), YES (1). Booster logic (PHNIX manuals): with R07 = YES the booster replaces the heat pump below R08 ambient; below R09 it starts together with the heat pump; below R10 it starts after the heat pump has run R06 minutes; above R10 only the heat pump heats. The booster output (O02) is meant for an electric water heater. Only relevant with a booster connected. With YES and no booster fitted, the heat pump presumably stops heating below R08 (-5.0 °C on your unit).
- **R08 Booster-only below ambient**: Ambient temperature (T01) below which the booster replaces the heat pump (R07 = YES).
- **R09 Booster without delay below ambient**: Ambient temperature (T01) below which the booster starts together with the heat pump.
- **R10 Booster with delay below ambient**: Ambient temperature (T01) below which the booster starts after the R06 delay.
- **R12 Compressor cut-off ambient temperature**: Ambient temperature (T01) below which the compressor is forced off.
- **R14 Second heat source target temperature**: Target temperature of the second heating source (see S06). Your heat pump holds -10.0, outside the app's own range, which suggests it isn't used.
- **R15 Maximum ambient for compressor**: App name: 'Maximal ambient temp of working compressor'. A 55-80 °C range fits a water or refrigerant limit better than an air temperature.
- **R17 Top sensor controls compressor**: Whether the top sensor (T03) controls the compressor instead of the bottom sensor (T02). Values: NO (0), YES (1).
- **R18 Start hysteresis (top sensor)**: Restart hysteresis of the top sensor, used instead of R03 when R17 = YES.
- **R19 Compressor stop setpoint 1**: App name: 'Setpoint 1 of ambient temp to stop compressor'.
- **R20 Compressor stop setpoint 2**: App name: 'Setpoint 2 of ambient temp to stop compressor'.

**R08, R09, R10:** Booster logic (PHNIX manuals): with R07 = YES the booster replaces the heat pump below R08 ambient; below R09 it starts together with the heat pump; below R10 it starts after the heat pump has run R06 minutes; above R10 only the heat pump heats. The booster output (O02) is meant for an electric water heater. Only relevant with a booster connected.

**R19, R20:** Not documented. A 30-90 °C range fits a water temperature better than an air temperature.

### Switch inputs

The app shows `CL` (closed) or `OP` (open).

| Code  | App name                              | App range | App value | Raw cloud value | Home Assistant     | Confidence |
| ----- | ------------------------------------- | --------- | --------- | --------------- | ------------------ | ---------- |
| `S01` | Remote ON/OFF switch                  | CL, OP    | CL        | empty           | sensor, Diagnostic | uncertain  |
| `S03` | Low pressure switch                   | CL, OP    | OP        | empty           | sensor, Diagnostic | uncertain  |
| `S04` | High pressure switch                  | CL, OP    | CL        | empty           | sensor, Diagnostic | uncertain  |
| `S05` | Accelerate the running time of heater | CL, OP    | CL        | empty           | sensor, Diagnostic | uncertain  |
| `S06` | Second heating source                 | CL, OP    | OP        | empty           | sensor, Diagnostic | uncertain  |

- **S01 Remote on/off input**: Remote on/off terminals; on your installation, closing them asks the heat pump to heat. Values: Open (0), Closed (1).
- **S03 Low pressure switch**: Low pressure switch of the refrigerant circuit. Values: Open (0), Closed (1). The app showed OP while the heat pump ran normally, so Open isn't necessarily a fault. In your log the cloud returned no value for the S and O codes, even while the app was open, so this shows Unavailable until the heat pump reports it. The app shows CL (closed) or OP (open); 1 = Closed is assumed.
- **S04 High pressure switch**: High pressure switch of the refrigerant circuit. Values: Open (0), Closed (1). The app showed CL during normal operation. In your log the cloud returned no value for the S and O codes, even while the app was open, so this shows Unavailable until the heat pump reports it. The app shows CL (closed) or OP (open); 1 = Closed is assumed.
- **S05 Heater acceleration input**: App name: 'Accelerate the running time of heater'. Values: Open (0), Closed (1). Probably the input that starts the booster without the R06 delay. In your log the cloud returned no value for the S and O codes, even while the app was open, so this shows Unavailable until the heat pump reports it. The app shows CL (closed) or OP (open); 1 = Closed is assumed.
- **S06 Second heating source input**: Second heating source input (see R14). Values: Open (0), Closed (1).

**S01, S06:** In your log the cloud returned no value for the S and O codes, even while the app was open, so this shows Unavailable until the heat pump reports it. The app shows CL (closed) or OP (open); 1 = Closed is assumed.

### Outputs and running hours

The app shows `ON` or `OFF` for the outputs.

| Code  | App name                                | App range | App value | Raw cloud value | Home Assistant     | Confidence |
| ----- | --------------------------------------- | --------- | --------- | --------------- | ------------------ | ---------- |
| `O01` | Compressor                              | ON, OFF   | ON        | empty           | sensor, Diagnostic | uncertain  |
| `O02` | Electrical heater                       | ON, OFF   | OFF       | empty           | sensor, Diagnostic | uncertain  |
| `O03` | 4-way valve                             | ON, OFF   | ON        | empty           | sensor, Diagnostic | uncertain  |
| `O04` | Fan high speed                          | ON, OFF   | OFF       | empty           | sensor, Diagnostic | uncertain  |
| `O05` | Fan low speed                           | ON, OFF   | OFF       | empty           | sensor, Diagnostic | uncertain  |
| `O06` | Reserve/solar pump/solar valve pump     | ON, OFF   | OFF       | empty           | sensor, Diagnostic | uncertain  |
| `O08` | Accumulative running time of compressor |           | 211H      | `210` to `215`  | sensor, Sensors    | observed   |
| `O09` | Accumulative running time of booster    |           | 0H        | `0`             | sensor, Sensors    | observed   |

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

### Ventilation

The app's settings also have an **Electric heating** switch and an **Align the device time** button. The codes behind them don't appear in the cloud data, so they aren't available in Home Assistant. The About page lists the device MAC, the PCB software code and version, and the display software code and version.

| Code  | App name                | App range                                 | App value                  | Raw cloud value | Home Assistant   | Confidence |
| ----- | ----------------------- | ----------------------------------------- | -------------------------- | --------------- | ---------------- | ---------- |
| `M17` | Ventilation / Air Speed | Ventilation ON/OFF, Air Speed Low or High | Low, later changed to High | `1` to `2`      | select, Controls | observed   |

- **M17 Fan speed**: Fan speed chosen with the app's Ventilation switch and Air Speed knob. Values: Off (0), Low (1), High (2). Your log shows 1 (Low), then 2 (High) right after you chose High in the app. A high fan speed moves more air over the coil, which usually helps efficiency and defrosting in cold weather. Off (0) is assumed to be the app's Ventilation switch turned off; what the fan does then while heating isn't confirmed. The climate entity's fan modes write the same code.

## Codes not shown in the app

### Reported by the cloud

Their names come from the vendor's parameter file, translated where it is Chinese.

| Code  | Name in Home Assistant                        | Raw cloud value  | Home Assistant               | Confidence |
| ----- | --------------------------------------------- | ---------------- | ---------------------------- | ---------- |
| `T06` | T06 Solar/discharge temperature (unconfirmed) | `40.5` to `87.0` | sensor, Sensors, disabled    | uncertain  |
| `T11` | T11 Out-of-range protection count             | empty            | sensor, Diagnostic, disabled | uncertain  |
| `T12` | T12 EEPROM write count                        | empty            | sensor, Diagnostic, disabled | uncertain  |
| `S02` | S02 Overheat protection switch                | empty            | sensor, Diagnostic, disabled | uncertain  |
| `O10` | O10 3V_DE output                              | empty            | sensor, Diagnostic, disabled | uncertain  |
| `O11` | O11 MV_DE output                              | empty            | sensor, Diagnostic, disabled | uncertain  |
| `O12` | O12 Shutdown output                           | empty            | sensor, Diagnostic, disabled | uncertain  |
| `O13` | O13 DTU/Wi-Fi online                          | empty            | sensor, Diagnostic, disabled | uncertain  |
| `O14` | O14 Defrost                                   | empty            | sensor, Diagnostic, disabled | uncertain  |
| `O15` | O15 High-temperature hot water stage          | empty            | sensor, Diagnostic, disabled | uncertain  |

- **T06 Solar/discharge temperature (unconfirmed)**: Not shown in the app. The vendor parameter file calls it the solar temperature. Your installation has no solar circuit, yet T06 rose from about 63 to 87 °C while the compressor ran and dropped when it stopped. That fits the compressor discharge (hot gas) temperature, but it isn't confirmed.
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

### Calculated by Home Assistant

| Code            | Name in Home Assistant | Raw cloud value | Home Assistant  | Confidence |
| --------------- | ---------------------- | --------------- | --------------- | ---------- |
| `superheat`     | Superheat (T05 - T04)  |                 | sensor, Sensors | documented |
| `water_delta_t` | Water ΔT (T03 - T02)   |                 | sensor, Sensors | observed   |

- **Superheat (T05 - T04)**: Suction minus coil temperature (T05 - T04), calculated by Home Assistant. The value E02 targets. Negative values mean the suction pipe reads colder than the coil, which keeps the EEV at E04.
- **Water ΔT (T03 - T02)**: Top minus bottom water temperature (T03 - T02), calculated by Home Assistant. On your installation, how much the water warms up through the heat pump. Heat pumps are usually designed for about 5 °C; a much larger value can mean low water flow.

### Requested without an entity

The climate entity and the Power sensor use some of these; the rest were requested by the original integration and are kept for diagnostics.

| Code            | Name in Home Assistant | Raw cloud value | Home Assistant            | Confidence |
| --------------- | ---------------------- | --------------- | ------------------------- | ---------- |
| `Power`         | Power                  | `1`             | binary_sensor, Diagnostic | observed   |
| `Mode`          | Mode                   | `2`             | requested, no entity      |            |
| `mode_real`     | mode_real              | `2`             | requested, no entity      |            |
| `Manual-mute`   | Manual-mute            | empty           | requested, no entity      |            |
| `Set_Temp`      | Set_Temp               | empty           | requested, no entity      |            |
| `MO6`           | MO6                    | empty           | requested, no entity      |            |
| `2074`          | 2074                   | `0`             | requested, no entity      |            |
| `2075`          | 2075                   | `0`             | requested, no entity      |            |
| `2076`          | 2076                   | `0`             | requested, no entity      |            |
| `2077`          | 2077                   | empty           | requested, no entity      |            |
| `1158`          | 1158                   | `0` to `23205`  | requested, no entity      |            |
| `1159`          | 1159                   | empty           | requested, no entity      |            |
| `2064`          | 2064                   | `0`             | requested, no entity      |            |
| `ver`           | Version                | empty           | requested, no entity      |            |
| `software_code` | Software Code          | empty           | requested, no entity      |            |

- **Power**: On/off state of the heat pump (1 = on). The climate entity turns it on and off.
- **Mode**: Mode written by the climate entity, 2 = heat.
- **mode_real**: Mode the heat pump reports, read by the climate entity (2 = heat).
- **Manual-mute**: Fan mode code of other models, requested for compatibility. Empty on HiTemp.
- **Set_Temp**: Setpoint code of other models, requested for compatibility. Empty on HiTemp.
- **MO6**: Requested by the original integration. Empty on HiTemp, meaning unknown.
- **2074**: Register requested by the original integration, meaning unknown.
- **2075**: Register requested by the original integration, meaning unknown.
- **2076**: Register requested by the original integration, meaning unknown.
- **2077**: Register requested by the original integration, meaning unknown.
- **1158**: Reads 23205 while the app's live data request (app_heartbeat) is active, 0 otherwise.
- **1159**: Register requested by the original integration, meaning unknown.
- **2064**: Register requested by the original integration, meaning unknown.
- **Version**: Version code of other models. Empty on HiTemp, see code_version and MainBoard Version.
- **Software Code**: Software code of other models. Empty on HiTemp, see code_version and MainBoard Version.
