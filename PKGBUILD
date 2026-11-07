# SPDX-License-Identifier: GPL-2.0-or-later
# Independent Arch Linux packaging of the Goodix USB 27c6:5125 libfprint driver
# from https://github.com/sorguido/goodix-27c6-5125 (upstream targets Fedora KDE only).
# Upstream source is built UNMODIFIED at a pinned commit. Not affiliated with upstream.

pkgname=libfprint-goodix-5125
_upstream_commit=4bc1f308071768b4f8045e58b4d12937bfa8ada2
pkgver=1.94.100.r4bc1f30
pkgrel=1
pkgdesc="libfprint with the Goodix USB 27c6:5125 driver (Huawei MateBook D15 / Honor MagicBook, firmware APP12508/APP12509)"
arch=(x86_64)
url="https://github.com/sorguido/goodix-27c6-5125"
license=('LGPL-2.1-or-later' 'GPL-2.0-or-later')
depends=(glib2 glibc libgcc libgudev libgusb openssl pixman)
makedepends=(gcc git meson ninja pkgconf)
optdepends=('fprintd: fingerprint enrollment and PAM authentication'
            'python-pyusb: read-only diagnostics (goodix-5125-diagnose)')
provides=("libfprint=1.94.100" "libfprint-2.so=2-64")
conflicts=(libfprint)
install=libfprint-goodix-5125.install
options=(!lto !debug)
source=("goodix-27c6-5125::git+https://github.com/sorguido/goodix-27c6-5125.git#commit=${_upstream_commit}"
        "goodix-5125-diagnose.py")
sha256sums=('SKIP'
            'SKIP')

_native() {
  # Same steps as upstream production/build-chicago-native.py (pinned, self-contained sources).
  local native_src="$srcdir/goodix-27c6-5125/production/chicago-native"
  local out="$srcdir/native"
  rm -rf "$out" && mkdir -p "$out"
  local i=0 f
  for f in $(ls "$native_src"/chicago/*.c | sort) $(ls "$native_src"/common/*.c | sort); do
    cc -std=c11 -O2 -g -fPIC -w -I "$native_src/chicago" -I "$native_src/common" \
       $(pkg-config --cflags gio-2.0) -c "$f" -o "$(printf '%s/%02d.o' "$out" "$i")"
    i=$((i + 1))
  done
  ar rcsD "$out/libgoodix-chicago-native.a" "$out"/*.o
}

build() {
  _native
  # Same meson options as upstream production/build-public.py, minus its Fedora-only checks.
  arch-meson "$srcdir/goodix-27c6-5125/reference/libfprint-fedora44-1.94.100/source" build \
    -Ddrivers=goodix_27c6_5125 \
    -Dintrospection=false -Ddoc=false -Dinstalled-tests=false \
    -Dudev_rules=disabled -Dudev_hwdb=disabled -Dgtk-examples=false \
    -Dgoodix_chicago=true -Dgoodix_production_minimal=true \
    -Dgoodix_chicago_native_archive="$srcdir/native/libgoodix-chicago-native.a" \
    -Dgoodix_chicago_native_include="$srcdir/goodix-27c6-5125/production/chicago-native/chicago"
  meson compile -C build
}

check() {
  # Upstream's nine offline, hardware-free regression suites (normal + ASan/UBSan builds).
  # Run exactly as upstream documents them: no arguments (several runners reject any).
  local t
  for t in "$srcdir"/goodix-27c6-5125/libfprint-driver/tests/run_goodix_*_test.sh; do
    echo "==> $(basename "$t" .sh)"
    sh "$t"
  done
}

package() {
  meson install -C build --destdir "$pkgdir"
  install -Dm755 "$srcdir/goodix-5125-diagnose.py" "$pkgdir/usr/bin/goodix-5125-diagnose"
  install -Dm644 "$srcdir/goodix-27c6-5125/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE.upstream"
}
