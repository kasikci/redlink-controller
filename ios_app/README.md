# Cheeses HVAC Control Deck (iOS app)

This iPhone app is a lightweight wrapper around the existing web UI. It loads the controller
UI from a server running on your Mac (or another machine on the same network).

## Run the server on your Mac

From the repo root:

```
python -m redlink_controller server --config config.json
```

By default the server binds to `0.0.0.0:8000`, which is reachable from your phone on the same
Wi-Fi network.

Find your Mac's LAN IP (Wi-Fi):

```
ipconfig getifaddr en0
```

You will use that IP in the iOS app, for example: `http://192.168.1.42:8000`.

## Launch in the iOS Simulator (on Mac)

1. Open `ios_app/CheesesHVACControlDeckiOS.xcodeproj` in Xcode.
2. Select an iPhone simulator (e.g. iPhone 15).
3. Run the app (Cmd+R).
4. Tap the gear icon and set the server URL to your Mac's LAN IP.

Optional: set the server URL as an environment variable in the Xcode scheme:

- `REDLINK_IOS_URL=http://192.168.1.42:8000`

## Launch on a physical iPhone

1. Connect the iPhone to your Mac and trust the device.
2. In Xcode, select your device and run the app.
3. Set the server URL using the gear icon if needed.

## Tests

Run from Xcode: `Product > Test` (Cmd+U).

If you have Xcode command line tools configured, you can also run:

```
xcodebuild test -project ios_app/CheesesHVACControlDeckiOS.xcodeproj \
  -scheme CheesesHVACControlDeckiOS \
  -destination "platform=iOS Simulator,name=iPhone 15"
```
