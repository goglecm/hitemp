# Changelog

## 4.3.1

_Minimum HA Version: 2026.11.0_

### Documentation

- The remote on/off contacts (`S01`) are never reported by the cloud, but a
  test on a Trianco S300 showed `Power` following them by the next read; the
  Power, `S01` and `H01` explanations and the guide now say so
- Each on/off, including from the contacts, raised the settings write counter
  `T21` by 4, so it is most likely written to the controller's memory while
  `H01` = YES

## 4.3.0

_Minimum HA Version: 2026.11.0_

### New

- **Defrost** binary sensor (bit 2 of `2051`): a log of a Trianco S300 at one
  read per minute showed it set during every defrost, with the EEV at its
  defrost position and the fan stopped

### Changes

- **Compressor running** and **Electric heater on** are marked as observed,
  confirmed against the app on a Trianco S300
- The guide lists the status bits decoded so far (unit off, compressor,
  electric heater, defrost, fan) and what the log showed about defrost timing
  (`D01`, `D03`, `D05`) and the on/off state being stored in the controller's
  memory

## 4.2.0

_Minimum HA Version: 2026.11.0_

### New

- **Operating mode select** (`mode_real`): Intelligent, Eco, Hybrid and Fast
  heating, as on the app's Select Mode page, confirmed on a Trianco S300
- **Update interval** option: read the cloud every 1 to 60 minutes (default 5)
- **Code changes** sensor: after each read, the codes whose values changed,
  with old and new values; also logged at the info level
- Read-only, decoded by changing settings in the app: **Vacation mode**
  (`1129` bit 0) and its date (`L02`-`L04`), the two timers' on and off times
  (`L06`-`L13`) and switches (`1133`), the **T21 settings write counter**, and
  further flag words
- The device page shows the display's software code and version too, read
  from `2011`-`2014`

### Changes

- `T06` is shown as the discharge temperature and enabled; on the S300 it
  follows the compressor while `T07` reads -30.0 (no sensor)
- `T07`, `O29` and `M06` are disabled by default: on the S300 they read
  -30.0, 0 and 0 while the compressor and electric heater ran
- The guide explains the modes, the timer page codes, how often values
  update, and what the third log showed

## 4.1.1

_Minimum HA Version: 2026.11.0_

### Safety fixes

- Whole-number parameters (cloud types `DIGI1`, `DIGI2`, `DIGI4`, for example
  `H32`, `E03`, `G04`) are written as `"2"`, the form the heat pump reports,
  instead of `2.0`
- `R06` is written in steps of 5 minutes: the cloud declares it as 0-90 for
  the app's 0-450 minutes
- HiTemp: the climate entity shows the Intelligent, Standard and High demand
  modes as heat, and choosing heat no longer switches them to Eco

### Corrections from the Trianco S300 manual

- `M17` sets what the fan does once the target temperature is reached (low,
  high or off), not the fan speed while heating; it is now called "M17 Fan
  after heating"
- The operating modes, the Intelligent mode bands (`R08`-`R10`), the remote
  on/off terminals and the defrost behaviour are explained from the manual,
  and the guide lists the S300's fault codes

### New readings (unconfirmed on the S300)

- From a full scan of another heat pump with the same product ID: the status
  word `2050` with **Compressor running** (bit 8) and **Electric heater on**
  (bit 9), the operating mode `mode_real`, `M06` electric heating, `O29` fan
  speed and `T07`/`T09` temperatures
- About 80 further codes from that scan are read for the diagnostics, and
  packed status words sent as 16 binary digits are decoded there

### Other changes

- The parameter guide shows each code's cloud data type and declared range,
  and what a second log showed about the live data request

### Upgrading

- If Home Assistant reports that the unit of `O07` can't be converted from
  the previously compiled statistics, open **Developer tools → Statistics** and
  choose to update the unit of the old statistics

## 4.1.0

_Minimum HA Version: 2026.11.0_

### HiTemp parameters

- Every HiTemp code is rebuilt from the app: names start with the code (for
  example `R01 Target water temperature`), ranges and steps match the app
  (0.5 °C for temperatures), and each entity explains itself with the
  attributes `code`, `app_name`, `level`, `range`, `app_value`, `confidence`,
  `description` and `guidance`
- New [parameter guide](docs/HITEMP_PARAMETERS.md) with every code as the app
  shows it, the raw cloud values, how the codes work together and what is
  still uncertain, and an example [dashboard](docs/hitemp-dashboard.yaml)
- Codes with app labels read `label (raw)`, for example `Standard (0)`
- New selects that send the raw value: `M17` fan speed, `R04` (both enabled),
  and `E01`, `H99`, `D06`, `R07`, `H01` (disabled, under Configuration)
- Defrost (`D01`-`D05`, `D07`), disinfection (`G01`-`G04`), booster ambient
  settings (`R08`-`R10`) and `H32` become writable, disabled by default under
  Configuration
- `O07` (EEV position) is a measurement in steps and can be graphed; `O08` and
  `O09` are running hours that keep increasing statistics
- New calculated sensors: superheat (`T05 - T04`) and water ΔT (`T03 - T02`)
- The solar codes, `T06`, `T11`, `T12`, `S02` and `O10`-`O15` are disabled by
  default

### Status and faults

- Last Error is replaced by **Cloud status** (OK, Session expired, Login
  rejected, Cannot connect, Cloud error) and **Fault details** (`No fault` or
  the cloud's description)
- Entities without a value from the cloud are unavailable instead of unknown
- The cloud's Chinese session-expired message is logged with its meaning
- The device page shows the MAC address, serial number, board and Wi-Fi
  versions and a link to the guide

### Live data

- New **Request live data** option, on by default: before each poll the
  integration sends the request the app sends while it is open, then reads
  the fault, version and switch codes related boards provide. Diagnostics show
  which codes returned a value

### Upgrading

- Entities that moved to another platform (for example `E01`, `R04` and `H99`
  from number to select) get new entity IDs; the old entities and Last Error
  are removed. Update automations that use them
- Names of existing entities change to the new code-first names; their entity
  IDs stay the same

## 4.0.0

_Minimum HA Version: 2026.11.0_

The project moved to [goglecm/hitemp](https://github.com/goglecm/hitemp).

### Breaking changes

- Requires Home Assistant 2026.11.0, for the native climate temperature API
- HiTemp: only parameters with ranges confirmed in the app are writable:
  R01 (38-60 °C), R03, R04, R05 and R06 (0-450 min). E01-E04 and H99 are
  writable but disabled by default; existing installs have them disabled by a
  migration. All other parameters, including H98 (model selection), are
  read-only sensors. The old number entities show as "no longer provided" and
  can be removed.
- The climate card of HiTemp is limited to 38-60 °C (was 5-90 °C)
- Turning a climate entity on resumes the heat pump's last mode instead of
  switching to heat

### Home Assistant 2026.11

- Remove the deprecated `CONN_CLASS_LOCAL_POLL` from the config flow
- Use `_attr_native_temperature_unit`, `_attr_native_target_temperature` and
  `_attr_native_current_temperature` in the climate entity
- Use probatio for the config flow schema and drop the undeclared aiofiles
  dependency
- Replace `device_registry.async_get_device` in diagnostics
- Set up the entry in `async_setup_entry` (retried while the cloud is
  unreachable), store the coordinator in `runtime_data`, remove `async_setup`
- Add reauthentication when the cloud rejects the password

### Safety fixes

- The Fault sensor never turned on (the cloud reports a boolean) and Fault and
  Status were only refreshed at login; both now update on every poll
- Entities of an offline heat pump are unavailable and commands to it are
  refused
- Failed data requests no longer leave old values shown as current
- Switching mode wrote the previous mode's target to the active setpoint
- Commands never contain an unmapped protocol code; duplicate writes removed
- Numbers are rounded to their step; temperature ranges follow the unit select
- Accounts no longer share their cloud token; TLS certificate verification is
  enabled again
- Passwords, tokens and account details are removed from logs and diagnostics

### Other fixes

- Editing the options moved the API type out of the entry data, so the wrong
  API was used after a restart; affected entries are repaired
- Device diagnostics failed with a TypeError
- Last Error and API Status stayed unavailable exactly when polling failed
- Changing the temperature unit needed a reload
- Unloading the entry deleted the stored temperature unit
- Concurrent setups could lose the encryption key or preferences
- The same account can no longer be added twice

### Since 3.0.37

- HiTemp: fetch `mode_real`, `M17` and use the product's fan mapping;
  align the mapping with the device
- Number platform for writable parameters, target temperature while off
- Last Error diagnostic sensor

### Development

- Tests for every feature against Home Assistant 2026.11.1, run in CI with
  95% coverage required
- Ruff replaces black, isort, flake8, pyupgrade and autoflake; all
  dependencies, hooks and actions updated

## 3.0.37

- Initialize data using `async_request_refresh` instead of `async_config_entry_first_refresh` to remove warning message

## 3.0.36

- Add support for more products [PR #83](https://github.com/radical-squared/aquatemp/pull/83) by [@Know1](https://github.com/Know1)

## 3.0.35

- Fix minimum / maximum values according to HVAC mode

## 3.0.34

- Fix relative path of config files

## 3.0.33

- Fix "detected blocking call to open inside the event loop by custom integration" error

## 3.0.32

- Fix warning - StrEnum is a deprecated alias which will be removed in HA Core 2025.5. Use enum.StrEnum instead

## 3.0.31

- Disable climate backwards compatibility flag

## 3.0.30

- Fix error message `implicitly supporting turn_on/turn_off` introduced in v2024.2

## 3.0.29

- Replaced soon (2025) to get deprecated SUPPORT\_\* constant with ClimateEntityFeature

## 3.0.28

_Minimum HA Version: 2024.1.0b0_

- Set minimum HA version for component to 2024.1.0b0

## 3.0.27

_Minimum HA Version: 2024.1.0_

- Adjust code to HA 2024.1.0

## v3.0.26

- Change API update from 30 seconds to 5 minutes, will update also when action is being performed
- Redact sensitive details from diagnostic file
- Fix diagnostic file creation process

## v3.0.25

### Breaking Change!

Password store format changed, up until now, password saved as the hash being send to the API,

To allow the enhanced functionality added, to edit Credentials and API Type, the password is now being saved encrypted and decrypted in 2 flows:

1. Edit integration details
2. On startup (hashed and sent to the API)

As result of that process, you need to re-setup the integration.

### Changes

- Add to set up configuration form new field of title to define the name of the integration
- Add edit integration details - Title, Credentials and API Type
- Refactor component initialization code to simplify process
- Fix `UndefinedType._singleton` name for climate entity

## v3.0.24

- Add missing configuration for API param 'error_code'

## v3.0.23

- Fix APIParam class, caused corrupted data on component creation and error code handling

## v3.0.22

- Fix binary sensor state evaluation

## v3.0.21

- Fix vacuum entity name
- Fix add integration (config) error handling

## v3.0.20

- Fix error handling when performing an action
- Optimize components loading

## v3.0.19

- Fix error handling when fetch data failed

## v3.0.18

- Add more parameters to API type configuration
- Extract model for HA DeviceInfo from API
- Add translation key to all components with name ready for translation

## v3.0.17

- Fix logic to extract protocol codes
- Fix mappings of product ID 1442284873216843776

## v3.0.16

- Optimize error handling for fetch device data

## v3.0.15

- Add log to update device

## v3.0.14

- Fix for the new capability of AquaTemp of single app to login, will re-login on every attempt to perform action / refresh
- Add new binary sensor of `API Status` represents whether the API is authenticated (logged in) or not

## v3.0.13

- Add API Type drop-down to configuration (Aqua Temp, Hitemp, Aqua Temp [=<1.5.8])
- Update authentication process

## v3.0.12

- Fix config flow, API manager constructor requires three parameters but only two are passed when creating it

## v3.0.11

- Per device's product ID parameters support

## v3.0.10

- Handling expired token error (401) more gracefully (re-login)

## v3.0.9

- Add support for product ID `1245226668902080512` [#25](https://github.com/radical-squared/aquatemp/issues/25)

## v3.0.8

- Fix missing `Off` mode for climate

## v3.0.7

- Improve support for devices of product ID `1442284873216843776`

## v3.0.6

- Fix device's empty values as `None` handling

## v3.0.5

- Set device's empty values as `None`

## v3.0.4

- Add device discovery for new devices without need to reload integration
- Fix integration reload issue
- Entities code clean up
- API stabilization after timeout
- Fix target temperature parameter mapping (Heat, Cool and Auto)
- Fix parameter mapping for P01 (Water pump mode)

## v3.0.3

- Fix setting HVAC mode
- Support shared devices
- Support multiple product IDs, Solution provided by [sjtrny](https://github.com/sjtrny) for issue [#25](https://github.com/radical-squared/aquatemp/issues/25)

## v3.0.2

- Fix configuration saving, without credentials
- Fix socket timeouts
- Add `suggested_unit_of_measurement=UnitOfElectricPotential.VOLT` to sensors of `SensorDeviceClass.VOLTAGE`
- Fix token clean-up
- Code clean up for entities
- HVAC Mode Mapping in v3.0.1 is mixed up [#29](https://github.com/radical-squared/aquatemp/issues/29)
- Block API operations if initial login failed

## v3.0.1

- Refactor entity's creation (using EntityDescription)
- Mapped all protocol codes to `EntityDescription`
- Add more entities (updated list in README)
- Create [Protocol Codes](https://github.com/radical-squared/aquatemp/blob/master/PROTOCOL_CODES.md) document
- Fix `climate` HVAC Modes

## v3.0.0

- Major refactor to the code - Breaking changes
- Configuration is available only from UI
- Supports multiple accounts (different credentials)
- Supports multiple devices (different devices on the same account)
- Add centralized `DataUpdateCoordinator` to communicate with the API and post updates to HA components
- Set minimum and maximum temperature based on the current HVAC mode relevant for the device (from API)
- Add `diagnostic` component to output data from API and configuration for troubleshooting (replacing the need for extra codes attributes)
- Add `binary_sensor` components for Power (Is on), Status (Is online) and Fault (Has fault)
- Add `select` component for choosing the Temperature Unit (C/F)
- Add `sensor` components for each of the temperature reading (T01-T03)
- Simplified `climate` component to include just its functionality without additional attributes (moved to dedicated components)
- Add mapping of more Protocol Codes (Parameters) for later support of more sensors/binary_sensors
