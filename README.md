<!-- SPDX-License-Identifier: GPL-2.0-or-later -->
# Goodix 27c6:5125 fingerprint reader on Arch Linux

Arch Linux packaging of the Goodix USB `27c6:5125` libfprint driver by
[sorguido/goodix-27c6-5125](https://github.com/sorguido/goodix-27c6-5125). It lets
`fprintd` (and through it login, `sudo` and screen lockers) use the fingerprint reader found
in Huawei MateBook D14/D15-family and Honor MagicBook laptops.

**This is an independent port, not affiliated with upstream.** Upstream maintains the driver for
Fedora KDE only and does not accept other-distribution changes
([contributing policy](https://github.com/sorguido/goodix-27c6-5125/blob/main/.github/CONTRIBUTING.md)).
Report Arch problems **here**, not upstream. All driver code is upstream's, built **unmodified**
at a pinned commit; this repository only adds packaging, a read-only diagnostic tool and
documentation.

## Supported hardware

| Item | Value |
| --- | --- |
| USB ID | `27c6:5125` (`lsusb` shows "Shenzhen Goodix Technology Co.,Ltd. Goodix Fingerprint Device") |
| Reader firmware | `GF_ST411SEC_APP_12509` or `GF_ST411SEC_APP_12508` (upstream refuses anything else) |
| Upstream commit | [`4bc1f30`](https://github.com/sorguido/goodix-27c6-5125/commit/4bc1f308071768b4f8045e58b4d12937bfa8ada2) (2026-11-05) |
| libfprint base | 1.94.100 (bundled by upstream; same version as Arch's `libfprint`) |

Other Goodix readers (`27c6:5110`, `5117`, `55a4`, …) are **not** supported by this package.

## Tested environment and results

One live test on one machine. This is evidence that it can work on Arch, not a broad
qualification.

| Item | Value |
| --- | --- |
| Laptop | Huawei MateBook, product `BoDE-WXX9`, dual boot with Windows |
| Reader | `27c6:5125`, firmware `GF_ST411SEC_APP_12509` |
| OS | Arch Linux, kernel 7.2.14-arch1-1, Hyprland 0.57.1 (Wayland) |
| Stack | `fprintd` 1.94.5, OpenSSL 3.6.5, glib2 2.90.1 |

| Test | Result |
| --- | --- |
| Driver build (upstream tree, driver-only) | builds; `fprint-list-supported-devices` lists `27c6:5125` |
| libfprint `enroll` example, right index finger | 12/12 stages, 0 retries; first run wrote the Linux host pairing once (`pairing_writes=1`) |
| libfprint `verify` example | `MATCH!` (~6 s); pairing reused (`pairing_writes=0`) |
| `fprintd-enroll -f right-index-finger` | `enroll-completed` (3 `enroll-retry-scan` along the way, normal) |
| `fprintd-verify` | `verify-match` |
| Package built from this PKGBUILD (upstream unmodified) | all 9 upstream offline suites pass in `check()` (21 checks, incl. ASan/UBSan); `fprintd-verify` → `verify-match` with the existing enrollment (no re-enrollment needed) |
| Windows Hello on the same reader afterwards | not re-tested yet (upstream reports coexistence works) |
| PAM integration (`sudo`, lock screen, login) | not covered by this port yet |

## What the package does (and does not do)

- Replaces Arch's `libfprint` with upstream's libfprint 1.94.100 tree containing **only** the
  `goodix_27c6_5125` driver. Other fingerprint readers will not be recognised while it is installed.
- Builds upstream's pinned sources **without patches** and runs upstream's offline regression
  suites (normal + ASan/UBSan, no hardware) in `check()`.
- Creates `/var/lib/fprint/goodix-5125-state-v2` (`root:root`, mode `0700`). The driver stores its
  Linux host-pairing state there and refuses any other owner or mode.
- Installs `goodix-5125-diagnose`, a **read-only** health check.
- It does **not** flash firmware, write factory data or touch the reader during installation. The
  only write to the reader is the one the driver itself makes on first use (its bounded Linux
  pairing step, as designed upstream).

## Before installing: check your reader

```sh
lsusb | grep 27c6:5125
sudo pacman -S --needed python-pyusb
sudo systemctl stop fprintd 2>/dev/null
sudo python3 goodix-5125-diagnose.py          # from this repository; read-only
```

All four lines should say `OK`. If not, read [Troubleshooting](#troubleshooting) **before** installing.

## Install

```sh
git clone <this repository> && cd goodix-5125-arch
makepkg -si          # answer "y" when asked to replace libfprint
sudo systemctl restart fprintd
```

`makepkg` downloads upstream at the pinned commit, builds the matching engine and libfprint, and
runs upstream's offline tests (about two minutes). Use `makepkg -si --nocheck` to skip the tests.

## Enroll and verify

```sh
fprintd-enroll -f right-index-finger     # touch, lift, shift slightly; repeat until enroll-completed
fprintd-verify                           # expect: verify-match
```

The first use pairs Linux with the reader (one write by the driver). Keep password login available.

## Troubleshooting

Run `sudo systemctl stop fprintd; sudo goodix-5125-diagnose` first; its output contains no secrets
and is safe to paste into an issue.

### `live preflight response failed its target boundary`

The driver checks every reply from the reader and stops at anything unexpected (by design).
Compare with `goodix-5125-diagnose`:

| Diagnose shows | Meaning | Fix |
| --- | --- | --- |
| `ACK status: 0x05` and slot `0xbb010002 … status 0x01, no data` | The reader's host-pairing record is missing. Seen on a reader that had earlier been given the 51x0/51x7 community key by [goodix-fp-dump](https://github.com/goodix-fp-linux-dev/goodix-fp-dump) or its `goodixtls` libfprint fork. | Let the official Windows driver pair the reader again (below). |
| firmware other than APP12508/APP12509 | Unsupported firmware | No fix here. Do not flash firmware. |

**Recovery with Windows** (verified on the test machine):

1. Boot Windows (dual boot, or a Windows VM with the reader passed through over USB).
2. Settings → Accounts → Sign-in options → Fingerprint recognition: **Remove** any old
   fingerprint, then **Set up** a new one. If the reader is missing, update or reinstall the
   fingerprint driver from Huawei PC Manager.
3. Boot back into Linux and run `goodix-5125-diagnose`: slot `0xbb010002` must now show
   `status 0x00, length 332` and `ACK status: 0x07`. Then enroll as above.

On the test machine this changed the ACK status from `0x05` to `0x07`, restored the 332-byte
record, and the driver then enrolled and verified normally.

### `state-v2 directory open failed` / `state-v2 directory policy mismatch`

The state directory is missing or has the wrong owner/mode. Reinstalling the package fixes it, or:

```sh
sudo install -d -m 0700 -o root -g root /var/lib/fprint/goodix-5125-state-v2
```

### `Goodix production boundary permits enrollment, verify and identify only`

Expected: the driver deliberately refuses raw image capture (for example libfprint's
`img-capture` example). Use enroll / verify.

### `verify-no-match` with the right finger

Wait until `Verifying: …` is printed and about two more seconds before touching, then hold the
finger flat and still. Each session starts by measuring the sensor with **no** finger on it; a
finger already on the reader spoils that baseline. On the test machine, touching immediately
gave three `NO_MATCH` results in a row (and once `unexpected post-TLS A0 frame … phase=FDT_82`);
waiting two seconds matched straight away. Upstream gives the same advice.

### Enrollment "hangs" with no output

It is waiting for a finger. Commands piped through `tail`/`grep` show nothing until they exit.

### Things not to do

- Do **not** run goodix-fp-dump's `run_5110.py` / `run_5117.py` on this reader: they erase and
  reflash firmware; one user ended with a non-working reader
  ([goodix-fp-dump#61](https://github.com/goodix-fp-linux-dev/goodix-fp-dump/issues/61)).
- Firmware read-back is refused by this reader, so there is no way to back up its firmware.
- Never post PSKs, key hashes, pairing records, fingerprint images or templates, or raw USB
  captures in public issues.

## Uninstall

```sh
sudo pacman -S libfprint        # back to Arch's stock library
```

`/var/lib/fprint/goodix-5125-state-v2` is kept on purpose: it holds the Linux pairing state.
Delete it only if you will not use the driver again.

## Credits and license

- Driver, protocol work and libfprint integration: [sorguido/goodix-27c6-5125](https://github.com/sorguido/goodix-27c6-5125)
  (per-file LGPL-2.1-or-later / GPL-2.0-or-later; see its `LICENSE` and provenance notes,
  installed as `/usr/share/licenses/libfprint-goodix-5125/LICENSE.upstream`).
- Protocol background: [goodix-fp-linux-dev](https://github.com/goodix-fp-linux-dev).
- This repository's packaging, tool and documentation: GPL-2.0-or-later ([LICENSE](LICENSE)).
