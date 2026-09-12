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

# TPS62827 - unencrypted PSpice transient model, SLVSEF9 datasheet family.
# Models start-up, steady state, current limit and hiccup, pre-bias, line and
# load transients. Temperature and leakage are NOT modelled.
fetch SLVMCV3 TPS62827 TPS62827_TRANS.LIB

echo
echo "Done. Decks .include these from sim/models/."
