# Redlink controller scaffolding

This repo provides a small Python 3 scaffolding client for Honeywell Total Connect Comfort / Redlink thermostats.
It mirrors the public web flow used at `mytotalconnectcomfort.com` and follows the gist you linked, but is structured as a library.

## Quick start

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```python
from redlink_controller import RedlinkClient

client = RedlinkClient(
    username="your@email.com",
    password="your_password",
    device_id=10169897,
)

client.login()
status = client.get_status()
print(status.temperature, status.humidity)

client.set_cool_setpoint(78, hold_minutes=120)
client.set_heat_setpoint(68, hold_minutes=240)
client.set_fan_mode("auto")
client.cancel_hold()
```

## CLI

Use environment variables or flags to supply credentials:

```
export REDLINK_USERNAME="your@email.com"
export REDLINK_PASSWORD="your_password"
export REDLINK_DEVICE_ID="10169897"
```

The CLI will also read `config.json` (via `--config`) if present.

Examples:

```
python -m redlink_controller status
python -m redlink_controller cool --setpoint 78 --hold-minutes 120
python -m redlink_controller heat --setpoint 68 --hold-minutes 240
python -m redlink_controller fan --mode auto
python -m redlink_controller cancel
```

Start the local web controller:

```
cp config.example.json config.json
python -m redlink_controller server --config config.json
```

The server binds to `0.0.0.0:8000` by default (LAN-accessible). Open `http://localhost:8000`.

Schedule endpoints must be wired in (see the next section):

```
python -m redlink_controller schedule-get \\
  --schedule-get-path "/portal/Device/YourScheduleEndpoint/{device_id}" \\
  --out schedule.json

python -m redlink_controller schedule-set \\
  --schedule-submit-path "/portal/Device/YourScheduleSubmitEndpoint" \\
  --in schedule.json
```

## Web UI + Hysteresis

The web UI reads/writes `config.json` and runs a background loop that enforces hysteresis:

- Heat turns on at `heat_on_below` and resets to `heat_on_below` at `heat_off_at`.
- Cool turns on at `cool_on_above` and resets to `cool_on_above` at `cool_off_at`.
- The loop polls at `poll_interval_seconds` and refreshes login sessions at `login_refresh_seconds`.


## Schedule scaffolding

The schedule endpoints and payload shapes are not stable across accounts and firmware. The web UI does not include schedule support yet, but the client can be wired in manually:

```python
from redlink_controller import EndpointConfig, RedlinkClient

endpoints = EndpointConfig(
    get_schedule_path="/portal/Device/YourScheduleEndpoint/{device_id}",
    submit_schedule_path="/portal/Device/YourScheduleSubmitEndpoint",
)

client = RedlinkClient(
    username="your@email.com",
    password="your_password",
    device_id=10169897,
    endpoints=endpoints,
)
client.login()

schedule = client.get_schedule()
# capture a payload from the web UI and re-submit it after editing
client.set_schedule(schedule)
```

To find the correct schedule endpoints and payloads:

1. Open the web UI in a browser and open Developer Tools.
2. In the Network tab, filter for XHR requests while changing the schedule.
3. Copy the request URL and JSON payload.
4. Plug the URL path into `EndpointConfig` and pass the payload to `set_schedule`.

## Notes

- The client uses `Device/CheckDataSession/{device_id}` and `Device/SubmitControlScreenChanges`, which are the same endpoints used in the gist.
- Heat/cool setpoints set `SystemSwitch` to the appropriate value (cool = 3, heat = 1). Verify your account if these values differ.
- This is a scaffold only. Expect to adjust headers, endpoints, and payload fields to match your account.
