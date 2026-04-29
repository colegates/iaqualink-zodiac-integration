# Zodiac iAquaLink Heat Pump (HACS custom integration)

A Home Assistant custom integration for the **Zodiac Z400iQ** pool heat pump,
spoken to via the Fluidra / iAquaLink cloud (`prod.zodiac-io.com`).

The official Home Assistant `iaqualink` integration and the HACS `exo_pool`
integration cover other devices on the same cloud but do not surface this
heat pump's data. This integration adds:

- A **climate** entity (current water temperature, target setpoint, on/off
  via HVAC mode HEAT/OFF, and heating status mapped to HVAC action).
- **Sensors**: water temperature, air temperature, setpoint, heater status
  (`off` / `temp_buffer` / `heating`), heater mode (`boost` / `silent`),
  reason code.
- A **select** entity to switch between **Boost** and **Silent** mode.

## Installation (HACS)

1. In HACS → *Integrations* → ⋮ → *Custom repositories*.
2. Add `https://github.com/colegates/iaqualink-zodiac-integration` as type
   *Integration*.
3. Install **Zodiac iAquaLink Heat Pump** and restart Home Assistant.
4. *Settings* → *Devices & Services* → *Add Integration* → search for
   "Zodiac iAquaLink Heat Pump".
5. Enter your iAquaLink email, password, and the heat pump serial number.

   **To find your heat pump serial:** log in at <https://iaqualink.net>, open
   the location/site for your pool, then click **Device Status**. The serial
   is also printed on the sticker on the unit and looks like `LB18475932`.

## How it talks to the cloud

| Operation        | Method | URL                                                        |
|------------------|--------|-------------------------------------------------------------|
| Login            | POST   | `https://prod.zodiac-io.com/users/v1/login`                |
| Read state       | GET    | `https://prod.zodiac-io.com/devices/v1/{serial}/shadow`    |
| Write desired    | POST   | `https://prod.zodiac-io.com/devices/v1/{serial}/shadow`    |

Writes use the standard AWS-IoT-style desired-state shape:

```json
{ "state": { "desired": { "equipment": { "hp_0": { "tsp": 28 } } } } }
```

Shadow keys we use under `equipment.hp_0`:

- `state` — power command/report. `1` = on, `0` = off. Writing this is what
  the iAquaLink app does when you toggle the heater.
- `tsp` — target setpoint in °C (8–32).
- `st` — mode. `0` = Boost, `1` = Silent.
- `status` — operational status (read-only). `0` Off, `1` Temperature buffer
  (at/near target), `2` Actively heating.
- `fan` — fan running indicator (read-only).

## Polling

The integration polls every 120 seconds. The cloud rate-limits aggressively
(returning HTTP 429 if you go too fast); please don't shorten the interval
without good reason.

## Branding (iAquaLink logo on the integration tile)

Each entity gets a Material Design icon via `icons.json`. The integration's
**tile/logo** in Home Assistant and HACS, however, is sourced from the
[`home-assistant/brands`](https://github.com/home-assistant/brands)
repository at runtime — there is no manifest field that overrides this.

The existing iAquaLink logo from that repo is bundled in
[`brands/zodiac_iaqualink/`](brands/zodiac_iaqualink) ready to be submitted
as a brands PR (instructions in [`brands/README.md`](brands/README.md)).
Once merged into `home-assistant/brands`, the iAquaLink logo will appear on
the integration tile. Until then HA shows a generic puzzle icon next to
"Zodiac iAquaLink Heat Pump".

## Logs, errors, and diagnostics

The integration follows Home Assistant's standard error-reporting paths:

- All log lines go to HA's normal log under
  `custom_components.zodiac_iaqualink.*`. To turn on debug logging add this
  to `configuration.yaml`:
  ```yaml
  logger:
    default: warning
    logs:
      custom_components.zodiac_iaqualink: debug
  ```
  (or use *Settings → System → Logs → Debug logging* on the integration's
  card; `loggers` is registered in `manifest.json` so HA will recognise it).
- **Authentication failures** trigger HA's standard re-auth notification
  with a button to re-enter the password — no need to delete and re-add the
  integration.
- **Connection / API errors** during polling are reported via
  `DataUpdateCoordinator.UpdateFailed`, which shows up in the HA UI as
  "integration not loading" with the error inline.
- **User-triggered command failures** (changing setpoint, mode, power) are
  raised as `HomeAssistantError`, which HA renders as a red toast in the
  frontend.
- **Diagnostics**: from the integration's *...* menu in
  *Settings → Devices & Services*, choose *Download diagnostics*. The dump
  contains the parsed coordinator data with email, password, and serial
  number redacted — safe to attach to a GitHub issue.

## Releases & updates in HACS

HACS watches the GitHub releases on this repo. Once installed, when a new
release is published HACS shows an *Update available* badge on the
integration card and on the HACS dashboard.

For maintainers, the release flow is:

1. Bump `custom_components/zodiac_iaqualink/manifest.json` `version`.
2. Commit, then `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. The `Release` workflow validates that the tag matches the manifest
   version, bundles the integration as a zip, and creates the GitHub
   Release. HACS picks it up on its next refresh.

The `Validate` workflow runs HACS's own action and Home Assistant's
`hassfest` on every push and PR, so manifest / structural problems are
caught before they ship.

## Notes / limitations

- This integration controls **power on/off**, **setpoint**, and **mode**
  (Boost/Silent). Pump-control / scheduling are not exposed.
- Tested with one Z400iQ (firmware `V71R54` / `V71E5`). Other Zodiac heat
  pumps that report under `equipment.hp_0` should work, but are untested.
