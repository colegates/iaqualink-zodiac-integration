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
5. Enter your iAquaLink email, password, and the heat pump serial number
   printed on the unit (e.g. `LB18475932`).

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

## Notes / limitations

- This integration controls **power on/off**, **setpoint**, and **mode**
  (Boost/Silent). Pump-control / scheduling are not exposed.
- Tested with one Z400iQ (firmware `V71R54` / `V71E5`). Other Zodiac heat
  pumps that report under `equipment.hp_0` should work, but are untested.
