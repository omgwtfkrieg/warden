#!/bin/bash
set -e

# --- Directories and ownership ---
sudo chown -R warden:warden /home/warden/.config
sudo rm -rf /home/warden/.config/systemd
mkdir -p /home/warden/.config/systemd/user
sudo mkdir -p /opt/warden/app/bundle

# --- start.sh ---
sudo tee /opt/warden/start.sh > /dev/null << 'SCRIPT'
#!/bin/bash
set -e
APP_DIR="/opt/warden/app"
RELEASES_URL="https://api.github.com/repos/omgwtfkrieg/warden/releases/latest"
mkdir -p "$APP_DIR"
LATEST=$(curl -sf "$RELEASES_URL" | grep '"tag_name"' | cut -d'"' -f4)
CURRENT=""
[ -f "$APP_DIR/version.txt" ] && CURRENT=$(cat "$APP_DIR/version.txt")
if [ "$LATEST" != "$CURRENT" ] && [ -n "$LATEST" ]; then
    ASSET_URL=$(curl -sf "$RELEASES_URL" | grep '"browser_download_url"' | grep 'linux' | cut -d'"' -f4)
    if [ -n "$ASSET_URL" ]; then
        echo "Updating to $LATEST..."
        curl -sfL "$ASSET_URL" -o /tmp/warden-linux.tar.gz
        rm -rf "$APP_DIR/bundle"
        mkdir -p "$APP_DIR/bundle"
        tar -xzf /tmp/warden-linux.tar.gz -C "$APP_DIR/bundle" --strip-components=1
        echo "$LATEST" > "$APP_DIR/version.txt"
        rm -f /tmp/warden-linux.tar.gz
    fi
fi
exec env WLR_BACKENDS=drm WLR_RENDERER=pixman cage -- "$APP_DIR/bundle/warden"
SCRIPT
sudo chmod +x /opt/warden/start.sh

# --- systemd user service ---
cat > /home/warden/.config/systemd/user/warden-kiosk.service << 'UNIT'
[Unit]
Description=Warden Kiosk
After=graphical-session.target

[Service]
Type=simple
ExecStart=/opt/warden/start.sh
Restart=always
RestartSec=3
Environment=XDG_RUNTIME_DIR=/run/user/1000

[Install]
WantedBy=default.target
UNIT

# --- load snd-dummy at boot (virtual audio for WebRTC ADM) ---
echo "snd-dummy" | sudo tee /etc/modules-load.d/snd-dummy.conf > /dev/null

# --- bash profile: enable and start kiosk on tty1 login ---
cat > /home/warden/.bash_profile << 'PROFILE'
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    systemctl --user daemon-reload
    systemctl --user enable pipewire pipewire-pulse wireplumber
    systemctl --user start pipewire pipewire-pulse wireplumber
    systemctl --user enable warden-kiosk.service
    systemctl --user start warden-kiosk.service
fi
PROFILE

# --- autologin on tty1 ---
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
sudo tee /etc/systemd/system/getty@tty1.service.d/autologin.conf > /dev/null << 'AUTOLOGIN'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin warden --noclear %I $TERM
AUTOLOGIN

# --- enable linger so user services persist ---
sudo mkdir -p /var/lib/systemd/linger
sudo touch /var/lib/systemd/linger/warden

# --- fix ownership ---
sudo chown -R warden:warden /opt/warden /home/warden

sudo systemctl daemon-reload || true
echo "Setup complete."
