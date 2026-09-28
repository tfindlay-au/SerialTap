#!/bin/sh
# Fetch the vendor SPICE models the decks need, and convert them for LTspice.
#
#     ./fetch-models.sh
#
# Vendor models are NOT committed to this repo. TI ships them "as an aid for
# customers of Texas Instruments" with no redistribution grant, so the repo
# carries the fetch step and the conversion script instead of the file itself.
# Everything this produces is listed in sim/.gitignore.
#
# That is the one exception to the project's "carry your own library" rule
# (CLAUDE.md), and it is a licensing exception, not a convenience one. The
# KiCad symbols, footprints, 3D models and datasheets in lib/ are still
# committed.

set -eu
cd "$(dirname "$0")"

fetch() {
    lit=$1; part=$2; want=$3
    echo "==> $part ($lit)"
    if [ ! -f "vendor/$want" ]; then
        curl -sSL -o "vendor/$lit.zip" "https://www.ti.com/lit/zip/$lit"
        unzip -o -q -j "vendor/$lit.zip" "*/$want" -d vendor/
        rm -f "vendor/$lit.zip"
    fi
    ./pspice2ltspice.py "vendor/$want" "$(echo "$part" | tr 'A-Z' 'a-z').lib"
}

mkdir -p vendor

# TPS62162 - the 3.3 V fixed member of the TPS6216x family, and the buck this
# board uses. TI's model header declares itself $UNENCRYPTED_LIB.
#
# Checked and rejected on the way here, recorded so nobody repeats it:
#   TPS6282533  fixed 3.3 V, but TI publishes no SPICE model for it at all
#   TPS62901    newer and nominally more efficient, but its model is 74%
#               Cadence-encrypted ($CDNENCSTART_ADV2) - PSpice-only, useless
#               in LTspice
fetch SLVM430B TPS62162 TPS62162_TRANS.lib


# --- Coilcraft XGL4020 inductor: MANUAL step -------------------------------
# Coilcraft's site rejects scripted downloads (HTTP 403), so this one cannot
# be automated. Get the "Coilcraft LTspice Advanced Library" from
#   https://www.coilcraft.com/en-us/models/spice/
# and unpack it to  sim/models/vendor/CoilcraftLTAdvLib/  so that both
# XGL4020.lib and CoilcraftTemplates.lib sit in that directory.
#
# The _sat variants carry DCR, winding capacitance and a real saturation
# curve, not an L + Rser stand-in. XGL4020-222_sat was checked against the
# datasheet before use: 19.5 mOhm DCR and 2.17 uH, both matching.
if [ -f vendor/CoilcraftLTAdvLib/XGL4020.lib ]; then
    echo "==> Coilcraft XGL4020 library present"
else
    echo "==> MISSING: vendor/CoilcraftLTAdvLib/XGL4020.lib"
    echo "    buck-load-step needs it; see the comment in this script."
fi


# --- Nichicon PCL1A471MCL1GS bulk capacitor: MANUAL step --------------------
# rail-sag and inrush model C4 with Nichicon's own 7-element RC-ladder model,
# PCL1A471MCL1GS_v100.lib, supplied by Nichicon's Fukui engineering department
# on request (their report FTR26-041, 2026-09-28). It was sent to the project,
# not published for redistribution, so like TI's it is not committed. Request
# it from Nichicon and place it at  sim/models/vendor/PCL1A471MCL1GS_v100.lib
# The part page (https://www.nichicon.com/en-us/part/pcl1a471mcl1gs/680/) also
# lists a model; it has not been compared with this one.
#
# The model is plain PSpice (L, R and C only), so the only conversion is the
# CRLF line endings. Checked against the datasheet before use: 475 uF total,
# 2.79 ohm at 120 Hz, ESR 8.6 mOhm at 100 kHz (typical; datasheet max 17).
if [ -f vendor/PCL1A471MCL1GS_v100.lib ]; then
    echo "==> Nichicon PCL1A471MCL1GS model present"
    tr -d '\r' < vendor/PCL1A471MCL1GS_v100.lib > pcl1a471mcl1gs.lib
else
    echo "==> MISSING: vendor/PCL1A471MCL1GS_v100.lib"
    echo "    rail-sag and inrush need it; see the comment in this script."
fi

echo
echo "Done. Decks .include these from sim/models/."
