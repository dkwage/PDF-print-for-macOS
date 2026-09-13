#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p vendor build ghostscript
ARCHIVE=vendor/ghostscript-10.07.1.tar.xz
if [[ ! -f "$ARCHIVE" ]]; then
  curl -fL https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10071/ghostscript-10.07.1.tar.xz -o "$ARCHIVE"
fi
shasum -a 256 -c vendor/ghostscript.sha256
if [[ ! -d build/ghostscript-10.07.1 ]]; then
  tar -xf "$ARCHIVE" -C build
fi
cd build/ghostscript-10.07.1
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export MACOSX_DEPLOYMENT_TARGET=14.0
export CFLAGS='-O2 -mmacosx-version-min=14.0'
export LDFLAGS=-mmacosx-version-min=14.0
./configure --prefix=/ghostscript --disable-cups --disable-gtk --disable-fontconfig --disable-dbus --without-tesseract --without-libidn --without-libpaper --without-ijs --without-urf --without-so --without-cal --with-drivers=PS --with-fontpath= --disable-contrib
make -j"$(sysctl -n hw.ncpu)"
cp bin/gs ../../ghostscript/gs
