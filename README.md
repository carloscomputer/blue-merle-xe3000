# blue-merle (GL-XE3000 / Puli AX)

This fork of *blue-merle* is an OpenWrt package for the **GL.iNet GL-XE3000 “Puli AX”** 5G mobile router. It aims to reduce forensic traceability by automating a set of privacy-related hygiene steps on every boot and providing a small LuCI UI + CLI for modem actions.

Standalone fork: talks to the modem directly via `/dev/ttyUSB2` (pyserial), with no dependency on GL.iNet's SDK or on `quectel-5g-tools`.

Features:

1.  IMEI management (only if supported by the modem firmware)
2.  Volatile (RAM-only) storage for connected-client MAC history (where supported)
3.  BSSID randomization (WiFi AP MACs) on boot
4.  WAN MAC address randomization on boot

## Compatibility

This fork targets **GL.iNet GL-XE3000 (Puli AX)** running **vanilla OpenWrt** (not GL.iNet's stock SDK firmware).

The package installer checks `/tmp/sysinfo/model` and will warn/prompt if you try to install it on a different model.

IMEI writes are **modem/firmware-dependent** on Puli AX (Quectel RM520N-GL). This fork will keep read-only functionality (read IMEI/IMSI, RF off, shutdown) even when IMEI writes are not available.

Some original features from the upstream Mudi package have no equivalent on a vanilla-OpenWrt Puli AX and are inert no-ops here: the `gl_clients` client-database wipe (GL.iNet's proprietary client-tracking daemon isn't present on vanilla builds) and `glconfig.general.macclone_addr` (GL.iNet-proprietary UCI section). Both are guarded so they don't fail, they just do nothing.

## Installation

Build (or obtain) an `ipk` for your GL-XE3000 firmware/architecture, copy it to the router (for example to `/tmp`), then install it:

```sh
apk add /tmp/blue-merle_*.apk
```

(Or `opkg install` if your build predates the switch to `apk`.)

## Usage

You can use *blue-merle* via:

1. **LuCI web UI** (recommended), or
2. **CLI** over SSH (`blue-merle`).

If IMEI writes are not supported on your modem firmware, the UI/CLI will only offer read-only and power/RF actions.

### CLI

Connect to the router via SSH and run:

```sh
blue-merle
```

The CLI can guide you through an RF-off / SIM swap / (optional) IMEI update flow. On Puli AX, IMEI updates are only attempted when the modem firmware allows IMEI writes.

**After a successful IMEI write, reboot the router** (not just the modem) to fully apply the change. See "Implementation details" below for why.

### Web

Open GL.iNet “Advanced Settings” (LuCI) and find **Blue Merle** under the **Network** menu.

The page displays the current IMEI/IMSI and offers actions depending on device capabilities:

1. Read IMEI / IMSI
2. Randomize IMEI (only if supported)
3. Disable modem RF (CFUN=4)
4. Shutdown router

## Hardware Button / Switch Integration

If your firmware exposes a GL.iNet “switch button” configuration (`switch-button.@main[0]`), the package will set it to `func='sim'` at install time, and a two-stage flow is available via `/etc/gl-switch.d/sim.sh`.

On GL-XE3000, there is no OLED display; any user prompts are via LuCI/SSH output and logs.

## Building

This repository is an OpenWrt “package feed” style project (no compiled code). You can build an `ipk`/`apk` using an OpenWrt buildroot pointed at OpenWrt 25.12 (mediatek/filogic).

```sh
git clone https://github.com/openwrt/openwrt
cd openwrt
git checkout openwrt-25.12
git clone <your-fork-url> package/blue-merle
./scripts/feeds update -a && ./scripts/feeds install -a
make distclean && make clean
make menuconfig
	# Select the target matching your GL-XE3000 build environment
	# In Utilities, select <M> for blue-merle package
make
make package/blue-merle/compile
```

The resulting package will be in `./bin/packages/` under your target architecture.

## Implementation details

### Modem actions / IMEI management

GL-XE3000 (Puli AX) uses a Quectel **RM520N-GL** 5G modem on **PCIe/MHI** (not USB data path). This fork talks to the modem directly over `/dev/ttyUSB2` using pyserial and standard AT commands (for example `AT+GSN` for IMEI and `AT+CIMI` for IMSI) — no GL.iNet SDK helper, no dependency on `quectel-5g-tools`.

**Important PCIe/MHI caveat:** on this hardware, a full modem reboot (`AT+CFUN=1,1`) while the PCIe link is active can wedge the host's PCIe port into an unrecoverable error state (`CmpltTO` cascade), recoverable only by a full host reboot. This fork therefore never issues `AT+CFUN=1,1`. IMEI writes bracket `AT+EGMR` with `AT+CFUN=0` / `AT+CFUN=1` (functionality-mode toggle, not a modem reboot) instead, and stopping/restarting ModemManager around the write. If the new IMEI can't be verified immediately after the write, the tooling asks you to reboot the *router* rather than retrying with any kind of modem-level reset.

Whether IMEI writes work at all is firmware-dependent. When IMEI writes are not supported, *blue-merle* will not attempt to change IMEI and will instead expose read-only + RF/shutdown functionality.

Changing modem RF state and (if supported) IMEI will disrupt connectivity. Plan operations accordingly.

### Basic Service Set Identifier (BSSID) randomization

On boot, *blue-merle* writes randomized MAC addresses into `wireless.@wifi-iface[*].macaddr` and commits the change, so the AP BSSIDs change after each reboot.

Note: the current implementation assumes two `wifi-iface` sections (`[0]` and `[1]`).

### MAC address log wiping

If the firmware stores connected-client history under `/etc/oui-tertf`, *blue-merle* will shred the on-flash database and mount a `tmpfs` over that directory so the client DB is RAM-only while keeping the UI functional. On vanilla OpenWrt (no `gl_clients`/`/etc/oui-tertf`), this is a no-op.

### MAC Address Randomization

*Blue-merle* sets a randomized MAC address for the WAN device on boot (`network.@device[1].macaddr`). If you use repeater mode or upstream MAC filtering, this may disrupt connectivity until you adjust your upstream configuration.

## Origin

- Original *blue-merle* for the GL.iNet Mudi: [SR Labs](https://github.com/srlabs/blue-merle) (Matthias, BSD-3-Clause)
- Ported to GL-XE3000 (Puli AX): [sureserverman/blue-merle-xe3000](https://github.com/sureserverman/blue-merle-xe3000)
- This fork: replaces GL.iNet's `gl_modem` helper and `/dev/mhi_DUN` with a standalone pyserial-based AT layer (`/dev/ttyUSB2`) for vanilla OpenWrt 25.12, with PCIe/MHI-safe IMEI write handling. No dependency on GL.iNet's SDK or on `quectel-5g-tools`.

## Name origin: blue merle

The original upstream project targeted GL.iNet’s “Mudi” router (a Hungarian dog breed). “Blue merle” is a coat color pattern; the mottled appearance inspired the name.
