# Warden Kiosk — Debian 12 Automated Install

## What the preseed does

1. Installs Debian 12 Bookworm minimal (no desktop environment)
2. Creates a `warden` user with sudo access
3. Installs only what is needed: SSH, Wayland/Weston, EGL/GL libs, fonts
4. Configures autologin on tty1
5. Installs a systemd user service that:
   - On every boot, checks GitHub Releases for a new Flutter Linux build
   - Downloads and extracts it if newer than the current version
   - Launches the app via `cage` (single-app Wayland compositor)

## Before using

### 1. Set the warden user password

Generate a hashed password to replace `CHANGEME_RUN_MKPASSWD`:

```sh
printf 'yourpassword' | mkpasswd -s -m sha-512
```

Paste the output into `debian-preseed.cfg` at the `passwd/user-password-crypted` line.

### 2. Set your timezone

Change `UTC` in the `time/zone` line to your local timezone, e.g.:

```
d-i time/zone string America/New_York
```

### 3. Confirm the GitHub Release asset name

The update script looks for a release asset URL containing `linux`. When you publish
a Flutter Linux build as a GitHub Release, name the archive something like
`warden-linux-x64.tar.gz`. The archive should extract to a directory containing
the `warden` binary plus `lib/`, `data/` folders (standard Flutter Linux bundle layout).

## How to use the preseed with a VM

### Proxmox

1. Download the [Debian 12 netinstall ISO](https://www.debian.org/CD/netinst/)
2. Upload to Proxmox: **Datacenter → Storage → ISO Images → Upload**
3. Create a VM:
   - OS: Linux, Debian ISO
   - Disk: 16GB minimum
   - RAM: 2–4 GB
   - CPU: 2–4 cores
4. Mount the preseed via boot parameters (see below) **or** serve it over HTTP

### Serving preseed over HTTP (simplest)

On any machine on the same LAN as the VM:

```sh
cd /path/to/kiosk/
python3 -m http.server 8000
```

Then at the Debian installer boot menu, press `e` or `Tab` to edit boot parameters and add:

```
auto=true priority=critical url=http://192.168.1.100:8000/debian-preseed.cfg
```

Replace `192.168.1.100` with your machine's LAN IP.

### Embedding preseed in a custom ISO

```sh
# Install tools
sudo apt install xorriso isolinux

# Unpack ISO, embed preseed, repack
# (advanced — look up debian-cd preseed embedding docs)
```

## Post-install

After the VM boots:

1. SSH in as `warden` (or use the Proxmox console)
2. Confirm the kiosk service status:
   ```sh
   systemctl --user status warden-kiosk.service
   journalctl --user -u warden-kiosk.service -f
   ```
3. If the GitHub Release does not exist yet, place the Flutter Linux bundle manually:
   ```sh
   mkdir -p /opt/warden/app/bundle
   # scp or rsync your Flutter build/linux/x64/release/bundle/ here
   echo "v0.0.0-local" > /opt/warden/app/version.txt
   ```

## Updating the app

Push a new GitHub Release with a Linux bundle asset. On next reboot the kiosk
will download and switch to the new version automatically.

To force an immediate update without rebooting:

```sh
systemctl --user restart warden-kiosk.service
```
