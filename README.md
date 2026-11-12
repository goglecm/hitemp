# Home Assistant Aqua Temp & HiTemp heat pumps

A Home Assistant integration for PHNIX Aqua Temp / HiTemp compatible heat pumps,
controlled through the manufacturer's cloud.

It controls the HVAC mode, target temperature and fan, writes the device
parameters that are well understood within the ranges of the app, and reports
every other parameter, the online status and faults of the heat pump as
sensors. HiTemp owners: read the [HiTemp guide](#hitemp-guide) and the
[parameter guide](docs/HITEMP_PARAMETERS.md) before changing anything.

This repository, [goglecm/hitemp](https://github.com/goglecm/hitemp), is the
maintained continuation of
[radical-squared/aquatemp](https://github.com/radical-squared/aquatemp). The
cloud protocol is based on the [aquatemp](https://github.com/dst6se/aquatemp)
project. See the [changelog](CHANGELOG.md) for what changed.

## Safety

A heat pump heats or cools water that people use. Before relying on this
integration:

- Check every change from Home Assistant on the unit itself or in the
  manufacturer's app the first time you use it.
- Keep the safety settings of the heat pump (anti-legionella disinfection,
  maximum temperatures, frost protection) configured on the unit. Home
  Assistant only sends what you ask for; it does not replace them.
- Only the parameters listed under [Writable parameters](#writable-parameters)
  can be changed from Home Assistant, within the ranges listed there. Values
  outside the range are rejected before anything is sent.
- When the cloud reports the heat pump as offline, or cannot be reached, its
  controls and readings become unavailable instead of showing old values.

## Requirements

- Home Assistant 2026.11.0 or newer
- An Aqua Temp or HiTemp app account

### Use a separate account

Since app version 1.5.9 only one session per account can be logged in. If the
integration and the app use the same account they keep logging each other out.
Create a second account, share the heat pump with it from the app, and use that
account for Home Assistant. Thanks to [@dodg3r](https://github.com/dodg3r) and
[@kopierschnitte](https://github.com/kopierschnitte) for the suggestion.

## Installation

### HACS [![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/goglecm/hitemp` with the type **Integration**.
3. Install **Aqua Temp** and restart Home Assistant.

### Manual

Copy `custom_components/aqua_temp` into the `custom_components` folder of your
Home Assistant configuration and restart Home Assistant.

## Setup

Go to **Settings → Devices & services → Add integration** and choose
**Aqua Temp**. Every account is a separate entry, and every heat pump of the
account becomes a device.

| Field             | Description                                                                                          |
| ----------------- | ---------------------------------------------------------------------------------------------------- |
| Title             | Name of the entry                                                                                    |
| Username          | Account username                                                                                     |
| Password          | Account password, stored encrypted                                                                   |
| API type          | The app the account was created with: Aqua Temp, HiTemp or Aqua Temp ≤1.5.8                          |
| Request live data | Send the app's live data request before each poll, see [Live data](#live-data)                       |
| Update interval   | Minutes between reads of the cloud (1-60, default 5); the heat pump itself uploads every H32 minutes |

| Error                       | Meaning                                                                      |
| --------------------------- | ---------------------------------------------------------------------------- |
| Invalid credentials         | The cloud rejected the username or password                                  |
| Cannot connect to the cloud | The cloud could not be reached or answered with an error; try again          |
| Corrupted encryption key    | The stored password cannot be decrypted, see [Invalid token](#invalid-token) |
| Already configured          | The account is already set up                                                |

To change the title, credentials or API type later, open the entry and choose
**Configure**. Leave the password empty to keep the current one. The entry
reloads with the new settings.

If the password is changed in the app, Home Assistant stops polling and asks
for the new password. Network or cloud outages do not trigger this; polling
retries until the cloud is back.

## Entities

Every heat pump gets these entities:

| Entity           | Platform      | Description                                                                                   |
| ---------------- | ------------- | --------------------------------------------------------------------------------------------- |
| _(device name)_  | climate       | HVAC mode, target and current temperature, fan mode                                           |
| Temperature Unit | select        | The unit the heat pump reports temperatures in (°C or °F)                                     |
| Fault            | binary_sensor | On while the heat pump reports a fault; `fault` has the detail                                |
| Fault details    | sensor        | `No fault`, or the cloud's description of the fault                                           |
| Status           | binary_sensor | On while the cloud reports the heat pump online                                               |
| API Status       | binary_sensor | On while the integration is logged in and reaching the cloud                                  |
| Cloud status     | sensor        | OK, Session expired, Login rejected, Cannot connect or Cloud error, with the message and time |

Fault, Fault details, Status, API Status and Cloud status stay available while
the heat pump is offline or the cloud cannot be reached, so the reason is
visible. Entities of a parameter the cloud returns no value for are
unavailable, never unknown.

The device page shows the MAC address, serial number, software versions and,
for HiTemp, a link to the parameter guide.

The other entities depend on the product:

| Product                      | Parameters                                                                                                                        | Climate mapping                                                                                             |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Default                      | [entity_description.default.json](custom_components/aqua_temp/parameters/entity_description.default.json)                         | [mapping.default.json](custom_components/aqua_temp/parameters/mapping.default.json)                         |
| HiTemp 1245226668902080512   | [entity_description.1245226668902080512.json](custom_components/aqua_temp/parameters/entity_description.1245226668902080512.json) | [mapping.1245226668902080512.json](custom_components/aqua_temp/parameters/mapping.1245226668902080512.json) |
| AquaTemp 1442284873216843776 | [entity_description.1442284873216843776.json](custom_components/aqua_temp/parameters/entity_description.1442284873216843776.json) | [mapping.1442284873216843776.json](custom_components/aqua_temp/parameters/mapping.1442284873216843776.json) |

Other supported product IDs use the default files.

### Climate

- **Turn on** powers the heat pump up in the mode it was last running in.
  **Turn off** powers it down.
- **Changing the mode** also sets the active setpoint to the target of the
  new mode.
- **Target temperature limits** come from the heat pump for the current mode
  (AquaTemp: R08-R11). Where the device does not report limits, the range of
  the parameter holding the target is used (HiTemp: R01, 38-60 °C in steps
  of 0.5 °C).
- The target temperature can be changed while the heat pump is off, for
  example from an automation.

### Writable parameters

Only parameters that are well understood can be changed, within the range and
step the manufacturer's app allows. Every other parameter is a read-only
sensor.

HiTemp (1245226668902080512):

| Parameters                     | Entities | Enabled by default |
| ------------------------------ | -------- | ------------------ |
| R01, R03, R05, R06             | number   | Yes (Controls)     |
| R04, M17, mode_real (mode)     | select   | Yes (Controls)     |
| E02-E04, D01-D05, D07, G01-G04 | number   | No (Configuration) |
| R08-R10, H32                   | number   | No (Configuration) |
| E01, H99, D06, R07, H01        | select   | No (Configuration) |

The [parameter guide](docs/HITEMP_PARAMETERS.md) lists the range, step and
meaning of each. Settings under **Configuration** have to be enabled on their
entity page before they can be changed. H98 (model selection), H31 (control
mode) and the output configuration /01 and /02 are read-only.

If the heat pump reports in °F, select °F in **Temperature Unit**; ranges are
converted and narrowed to whole degrees.

## HiTemp guide

The [parameter guide](docs/HITEMP_PARAMETERS.md) documents every code the
HiTemp app shows, with the app's names and ranges, what each code does, how
sure we are of it, and how the codes depend on each other. The same
explanation is attached to each entity as attributes (`description`,
`guidance`, `range`, `app_value`, `confidence`), so it is visible in Home
Assistant too.

### What to change and what to leave

- **Daily use:** `R01` (target water temperature, also set by the climate
  entity) and the operating mode `mode_real` (Eco, Hybrid, Fast heating or
  Intelligent, as in the app). Heating is started with the remote on/off input `S01` on the board
  (`DI05` in the Trianco S300 manual). `M17` only sets what the fan does once
  the target is reached: low, high or off.
- **Booster, if one is fitted:** `R04`-`R06` in Controls, `R07`-`R10` in
  Configuration.
- **Installer settings** (expansion valve, defrost, disinfection): disabled by
  default. Change them only with the guide at hand and a reason to.
- **Leave alone:** everything marked `uncertain` in the guide, and the
  read-only codes.
- Avoid automations that change a parameter every few minutes: every change
  is probably written to the controller's memory, which wears out.

Each entity name starts with its code, for example `R01 Target water
temperature`. Values with labels read like the app plus the raw value, for
example `Standard (0)`.

### Graphs and dashboard

Live temperatures, the EEV position (`O07`), superheat (`T05 - T04`) and the
water temperature rise (`T03 - T02`) keep long-term statistics, and the
compressor hours (`O08`) can be shown per day.
[docs/hitemp-dashboard.yaml](docs/hitemp-dashboard.yaml) is a ready dashboard
with the controls, water temperatures against `R01`, superheat against `E02`,
the EEV position, daily compressor hours, and status and faults. To use it,
add a dashboard, open **Edit dashboard → Raw configuration editor**, paste the
file, and replace `heat_pump` in the entity IDs with the start of your heat
pump's entity IDs. Installs from before 4.1.0 keep their old entity IDs; pick
those in the card editors instead.

### Live data

The cloud only keeps some values while the heat pump uploads live data, which
the app requests while it is open. With **Request live data** on (the
default), the integration sends the same request before each poll and reads
further codes in a separate request. On HiTemp the switch inputs `S01`-`S06`
and outputs `O01`-`O06` stay empty, so they show as unavailable.

A full scan of another heat pump with the same product ID found the
operating state in packed status words instead. The integration reads
register `2050` and shows its compressor and electric heater bits as
**Compressor running** and **Electric heater on**, plus the operating mode,
fan speed and a discharge temperature. These are not yet confirmed on every
model: compare them with the app, and attach the diagnostics of the heat pump
to an [issue](https://github.com/goglecm/hitemp/issues) to help confirm
them. The guide explains the details.

### Finding out what a setting changes

The **Code changes** sensor lists, after each read, the codes whose values
changed since the previous read, with the old and new values; live readings
such as temperatures are left out. Change one setting in the app, wait for the
next read (or lower the **Update interval**), and the sensor and the log show
which codes moved. The vacation, timer and clock codes in the guide were found
this way.

## Troubleshooting

### Logs

Add the following to `configuration.yaml`, or use **Enable debug logging** on
the integration page:

```yaml
logger:
  default: warning
  logs:
    custom_components.aqua_temp: debug
```

Passwords, tokens and account identifiers are removed from the logs and from
the diagnostics, which you can download from the integration page with
**Download diagnostics**. Attach both when reporting an
[issue](https://github.com/goglecm/hitemp/issues).

### Data from the mobile app

If the mapping of your heat pump is wrong, collect the following before
reporting an issue:

1. Install a packet sniffer on your phone (for example NetCapture or HTTP
   Toolkit on Android, Proxyman on iOS) and enable it for the app.
2. Open the app, log in and open the heat pump.
3. Open the menu and choose `Parameter Settings`.
4. Enter the user parameter code `002` and take a screenshot of every page.
5. Repeat with the installer parameter code `066`.
6. Export the requests and responses of `login`, `deviceList`,
   `getDataByCode` and `control` from the packet sniffer, after removing your
   password hash and token. On iOS a proxy app such as Proxyman can capture
   them.

Attach the app name and version, the screenshots and the diagnostics.

### Invalid token

The password is stored encrypted with a key kept in
`.storage/aqua_temp.config.json` under `data.key`:

```json
{
  "version": 1,
  "minor_version": 1,
  "key": "aqua_temp.config.json",
  "data": {
    "key": "ox-qQsAiHb67Kz3ypxY19uU2_YwVcSjvdbaBVHZJQFY="
  }
}
```

If the file or the key is missing, please report an issue.

If the key exists but the password cannot be decrypted:

1. Remove the integration.
2. Delete the file.
3. Restart Home Assistant.
4. Add the integration again.

Older versions stored the key under an entry ID, for example
`data.b8fa11c50331d2647b8aa7e37935efeb.key`. Moving it to `data.key` and
restarting Home Assistant fixes that case.

## Development

```shell
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_dev.txt
.venv/bin/pytest --cov
.venv/bin/pre-commit run --all-files
```

The tests run against Home Assistant 2026.11.1 with a fake of the cloud API
built from captured payloads. CI also runs hassfest and the HACS action.

The HiTemp parameter file and its guide are maintained by hand: do not
regenerate the file with `utils/parse-resources.py`, which does not know the
writable parameters or their explanations. Tests check that the guide and the
example dashboard match the parameter file.

## License

MIT, see [LICENSE](LICENSE). The authors of the original project agreed to
the MIT licence for their work; see [NOTICE](NOTICE.md).
