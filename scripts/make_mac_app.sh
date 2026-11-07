#!/bin/bash
# Builds ~/Applications/Brainy.app (icon in the Dock/Launchpad) that runs Brainy.command.
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP="$HOME/Applications/Brainy.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cat > "$APP/Contents/MacOS/Brainy" <<SH
#!/bin/bash
exec "$REPO/Brainy.command" >> "\$HOME/.brainy/app.log" 2>&1
SH
chmod +x "$APP/Contents/MacOS/Brainy"
mkdir -p "$HOME/.brainy"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Brainy</string>
  <key>CFBundleIdentifier</key><string>ai.brainy.app</string>
  <key>CFBundleExecutable</key><string>Brainy</string>
  <key>CFBundleIconFile</key><string>Brainy</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>NSMicrophoneUsageDescription</key><string>Brainy écoute ta demande.</string>
</dict></plist>
PLIST
ICONSET="$(mktemp -d)/Brainy.iconset"
mkdir -p "$ICONSET"
SRC="$REPO/frontend/public/mascot/icon.png"
for s in 16 32 64 128 256 512; do
  sips -z $s $s "$SRC" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$SRC" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/Brainy.icns"
echo "Brainy.app créé dans ~/Applications — glisse-le dans le Dock."
