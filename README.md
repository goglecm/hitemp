# Home Assistant Aqua Temp & HiTemp heat pumps

A Home Assistant integration for PHNIX Aqua Temp / HiTemp compatible heat pumps,
controlled through the manufacturer's cloud.

It controls the HVAC mode, target temperature and fan, writes the device
parameters whose ranges are known, and reports every other parameter, the
online status and faults of the heat pump as sensors.

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

| Field    | Description                                                                 |
| -------- | --------------------------------------------------------------------------- |
| Title    | Name of the entry                                                           |
| Username | Account username                                                            |
| Password | Account password, stored encrypted                                          |
| API type | The app the account was created with: Aqua Temp, HiTemp or Aqua Temp ≤1.5.8 |

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

| Entity           | Platform      | Description                                                    |
| ---------------- | ------------- | -------------------------------------------------------------- |
| _(device name)_  | climate       | HVAC mode, target and current temperature, fan mode            |
| Temperature Unit | select        | The unit the heat pump reports temperatures in (°C or °F)      |
| Fault            | binary_sensor | On while the heat pump reports a fault; `fault` has the detail |
| Status           | binary_sensor | On while the cloud reports the heat pump online                |
| API Status       | binary_sensor | On while the integration is logged in and reaching the cloud   |
| Last Error       | sensor        | The error of the last failed update, empty after a success     |

Fault, Status, API Status and Last Error stay available while the heat pump is
offline or the cloud cannot be reached, so the reason is visible.

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
  the parameter holding the target is used (HiTemp: R01, 38-60 °C in whole
  degrees).
- The target temperature can be changed while the heat pump is off, for
  example from an automation.

### Writable parameters

Only parameters whose range was confirmed on the device can be changed. Every
other parameter is a read-only diagnostic sensor.

HiTemp (1245226668902080512):

| Parameter                                     | Range     | Enabled by default |
| --------------------------------------------- | --------- | ------------------ |
| R01 Target temperature                        | 38-60 °C  | Yes                |
| R03 Hysteresis of heat pump start (bottom)    | 1-20 °C   | Yes                |
| R04 Use R05 as booster setpoint               | 0-1       | Yes                |
| R05 Booster setpoint                          | 30-90 °C  | Yes                |
| R06 Booster start delay                       | 0-450 min | Yes                |
| E01 EEV adjustment mode                       | 0-1       | No                 |
| E02 Target superheat                          | -20-20 °C | No                 |
| E03 Initial EEV position                      | 0-500     | No                 |
| E04 Minimum EEV opening                       | 0-500     | No                 |
| H99 Compensation of the displayed temperature | 0-1       | No                 |

The E parameters and H99 are installer settings. They are filed under
**Configuration** and have to be enabled on the entity page before they can be
changed. H98 (model selection) is read-only.

If the heat pump reports in °F, select °F in **Temperature Unit**; ranges are
converted and narrowed to whole degrees.

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

1. Install a packet sniffer on your phone (for example NetCapture on Android)
   and enable it for the app.
2. Open the app, log in and open the heat pump.
3. Open the menu and choose `Parameter Settings`.
4. Enter the user parameter code `022` and take a screenshot of every page.
5. Repeat with the factory parameter code `066`.
6. Export the requests and responses of `login`, `deviceList` and
   `getDataByCode` from the packet sniffer, after removing your password hash
   and token.

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

The HiTemp parameter file is maintained by hand: do not regenerate it with
`utils/parse-resources.py`, which does not know the writable parameters.

## License

MIT, see [LICENSE](LICENSE). The authors of the original project agreed to
the MIT licence for their work; see [NOTICE](NOTICE.md).
