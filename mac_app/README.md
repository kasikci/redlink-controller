# Cheeses HVAC Control Deck (macOS app)

This is a macOS wrapper for the local web UI. It starts the Python server on launch
and loads the controller UI inside a native window.

## Run (Swift Package)

```
cd mac_app
swift run
```

The app will start the server automatically using:

```
python3 -m redlink_controller server --config <config>
```

## Build a standalone .app

1. Save the logo image as:

```
mac_app/Assets/AppIcon.png
```

Recommended: square PNG, 1024x1024.

2. Build the app bundle:

```
cd mac_app
./scripts/build_app.sh
```

The app bundle will be created at:

```
mac_app/build/Cheeses HVAC Control Deck.app
```

The build script creates a Python virtualenv inside the app bundle and installs
`requirements.txt`, so it needs network access during the build.

## Configuration

By default the app:
- Uses `http://localhost:8000`
- Uses the repo `config.json` if found
- Otherwise uses: `~/Library/Application Support/CheesesHVACControlDeck/config.json`

Override with environment variables:

```
REDLINK_UI_URL="http://localhost:8000"
REDLINK_CONFIG_PATH="/path/to/config.json"
REDLINK_PYTHON="/opt/homebrew/bin/python3"
REDLINK_SERVER_CWD="/path/to/repo"
REDLINK_LOG_PATH="/path/to/server.log"
```

## Logs

The default log path is:

```
~/Library/Application Support/CheesesHVACControlDeck/server.log
```

## Notes

- The standalone app bundles the `redlink_controller` Python package and `web` assets.
- You still need a working Python 3 install.
