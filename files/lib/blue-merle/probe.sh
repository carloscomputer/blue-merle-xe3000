#!/usr/bin/env ash

# blue-merle probe library for GL-XE3000 (Puli AX)
# Standalone: talks directly to /dev/ttyUSB2 via pyserial, no dependency
# on quectel-5g-tools or GL.iNet's gl_modem. Vanilla OpenWrt's
# mhi_pci_generic driver has no /dev/mhi_DUN (that was GL.iNet's
# proprietary pcie_mhi driver's node).

bm_log() {
    logger -p notice -t blue-merle "$1"
}

# Check if IMEI writes work on this modem (RM520N-GL support is firmware-dependent)
# Caches result in /tmp so we only probe once per boot.
bm_can_write_imei() {
    local cache="/tmp/blue-merle-imei-capable"
    if [ -f "$cache" ]; then
        [ "$(cat "$cache")" = "1" ]
        return $?
    fi

    if [ ! -c /dev/ttyUSB2 ]; then
        echo 0 > "$cache"
        bm_log "IMEI write not supported: /dev/ttyUSB2 not found"
        return 1
    fi

    local resp
    resp=$(python3 /lib/blue-merle/at_send.py --retries 3 'AT+EGMR=0,7' 2>/dev/null)

    if echo "$resp" | grep -qE "EGMR|OK"; then
        echo 1 > "$cache"
        return 0
    fi

    echo 0 > "$cache"
    bm_log "IMEI write not supported on this modem firmware"
    return 1
}
