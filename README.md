# Huananzhi X99-CH8 BIOS mod: Resizable BAR + AST2400 GOP

This repository holds a modified BIOS for the Huananzhi X99-CH8 v3.0 board.
The mod adds two UEFI DXE drivers to the stock firmware:

- **ReBarDxe** from [ReBarUEFI](https://github.com/xCuri0/ReBarUEFI). It enables Resizable BAR.
- **ASPEED AST2400 GOP**. It gives the onboard VGA a UEFI Graphics Output Protocol driver, so you can disable CSM and still see video on the onboard VGA.

The repository also holds the original SPI dump, the vendor BIOS, the source packages and the Python tools used to build and check the images.

All facts below were verified on 2026-10-27.

> **Warning.** Flashing firmware can brick the board.
> Keep `dump1.bin` and a CH341A programmer ready before you flash.

## Board

| Item | Value |
|---|---|
| Board | Huananzhi X99-CH8 v3.0 |
| Chipset | Intel C612 (Wellsburg) |
| Firmware | AMI Aptio IV |
| BIOS version | G3X99018, DMI BIOS version 5.11, date 08/27/2022 |
| SPI flash | Winbond W25Q128 (16 MiB) |
| Boot Guard | Not present |
| Secure Flash (signed capsule) | Not present |
| Super IO | Nuvoton NCT5532D |
| Onboard VGA | ASPEED AST2400 (lspci: "ASPEED Graphics Family" rev 30, behind an AST1150 PCIe-to-PCI bridge) |

The stock BIOS contains only a legacy AST VBIOS 1.08.00.
It contains no GOP driver for the AST2400.
So with CSM disabled, the onboard VGA shows no picture.

## Goal

1. Enable Resizable BAR with ReBarUEFI `ReBarDxe`.
2. Add a UEFI GOP driver for the AST2400, so CSM can be disabled.

## Images

Both images are full 16 MiB SPI images (descriptor, ME and BIOS regions).
Both were built from `dump1.bin`, the dump of this board.

| File | Content | SHA-256 |
|---|---|---|
| `X99-CH8_G3X99018_rebar_only.bin` | ReBarDxe only | `4a9183710172dbad26670e45dc1b111cff04a07428537e05965ddda3ddc98c23` |
| `X99-CH8_G3X99018_rebar_astgop.bin` | ReBarDxe + AST2400 GOP | `203a68686d9da5b6f7e6b837436e45115628d203df1e96fcd09617e7eed7878c` |
| `dump1.bin` | Original dump (unmodified) | `7bd6e5fe1fee422d40e355c4c2cd4e73a061f10cf419d1ec05762461cbbd0fe2` |

A second dump (`dump2.bin`) was read for comparison.
It was identical to `dump1.bin` (same SHA-256 `7bd6e5fe1fee422d40e355c4c2cd4e73a061f10cf419d1ec05762461cbbd0fe2`), so it is not kept.

Check the hashes before you flash:

```bash
sha256sum -c dump1.bin.sha256
sha256sum -c X99-CH8_G3X99018_rebar_only.bin.sha256
sha256sum -c X99-CH8_G3X99018_rebar_astgop.bin.sha256
```

## What was inserted

| FFS file | GUID | Source | Image range |
|---|---|---|---|
| ReBarDxe | `A8EE1777-A4F5-4345-9DA4-13742084D31E` | ReBarUEFI 0.3 release `ReBarDxe.ffs` (xCuri0/ReBarUEFI) | `0xB2FE10`-`0xB30821` |
| AstGopDxe | `5AAFD210-7B28-4F20-A12E-C59C0A7C355B` | `uefi_2400_396.efi` from the ASPEED UEFI driver package v1.11.03 (`AST2400/v11103_vbios.zip`) | `0xB30828`-`0xB3B73B` (astgop image only) |

- Both FFS files are type `0x07` (DXE driver).
- The AST GOP FFS file contains a PE32 section and a UI section with the name `AstGopDxe`. It has no DEPEX section.
- Both files were appended to the free space at the end of the main DXE firmware volume. This volume starts at image offset `0x880000` and is `0x510000` bytes long.
- Before the mod, the free space started at `0xB2FE10`. After the last file there was `0x2601F0` bytes free.
- In `rebar_astgop`, only the bytes in `0xB2FE10`-`0xB3B73B` differ from `dump1.bin`.
- In `rebar_only`, only the bytes in `0xB2FE10`-`0xB30821` differ from `dump1.bin`.
- No other file, volume header or checksum in the image changed.

### ReBarUEFI patches were not applied

ReBarUEFI ships UEFIPatch patterns for `PciHostBridge` and NB PEI modules.
This Haswell-EP firmware uses `PciRootBridge` and `UncoreInitPeim` modules instead.
The patterns do not match, so no patches were applied.
The PciBus 64-bit and NvramSmiDxe patches were not needed either (see Results).

## Method

The images were built with pure Python.

- `tools/mkffs.py` builds an FFS file from a PE32 image.
- `tools/insert_ffs.py` appends one or more FFS files into the free space of a firmware volume, in place.

UEFITool 0.28 was **not** used to write the image.
It corrupts the PEI pad file in this image when it rebuilds the volumes.

### FFS state byte

The upstream `ReBarDxe.ffs` ships with FFS state byte `0x07`.
That value is correct only for a volume with erase polarity 0.
This volume has erase polarity 1, so a valid file needs state `0xF8`.
`insert_ffs.py` inverts the state byte when it writes the file into the volume.
The state byte is not part of the header or data checksum, so the checksums stay valid.
The AST GOP FFS was built with state `0xF8` directly.

### Reproduce the build

Run these commands from the repository root.
The output is byte-identical to the committed images (verified with `cmp`).

1. Build the AST GOP FFS file:

   ```bash
   python3 tools/mkffs.py \
     --template third_party/ReBarUEFI/ReBarDxe.ffs \
     --pe third_party/ASPEED/uefi_2400_396.efi \
     --name AstGopDxe \
     --guid 5AAFD210-7B28-4F20-A12E-C59C0A7C355B \
     --state 0xF8 \
     -o /tmp/AstGopDxe.ffs
   ```

   `--template` copies the FFS attributes from the ReBarDxe file.
   Without `--guid`, the script makes a random GUID.
   The result is identical to `build/AstGopDxe.ffs`.

2. Build the ReBarDxe + GOP image:

   ```bash
   python3 tools/insert_ffs.py dump1.bin 0x880000 \
     third_party/ReBarUEFI/ReBarDxe.ffs /tmp/AstGopDxe.ffs \
     -o X99-CH8_G3X99018_rebar_astgop.bin
   ```

3. Build the ReBarDxe-only image:

   ```bash
   python3 tools/insert_ffs.py dump1.bin 0x880000 \
     third_party/ReBarUEFI/ReBarDxe.ffs \
     -o X99-CH8_G3X99018_rebar_only.bin
   ```

4. Check the FFS files:

   ```bash
   python3 tools/mkffs.py --check build/*.ffs
   ```

`insert_ffs.py` checks the `_FVH` signature, walks the FFS file chain, and requires that all bytes after the last file are `0xFF`.
It aligns each new file to 8 bytes.
It stops with an error if a file does not fit or if the target area is not erased.

To use the tools on a different dump, find the offset of the main DXE volume first (for example with `tools/review/fv.py`).

## Verification

The scripts in `tools/review/` re-parse the images independently of the build scripts.
They were used for a structural review of the modified image against the original.

| Script | Purpose |
|---|---|
| `fd.py` | Parses the Intel flash descriptor (FLMAP, region table, master access, component section). |
| `fv.py` | Finds all firmware volumes in the BIOS region and checks header checksums, block maps, FFS file headers and checksums. |
| `sec.py` | Parses the two inserted FFS files, lists their sections, prints the UI name and PE32 SHA-256, and extracts the PE32 images. |
| `guids.py` | Checks which protocol GUIDs (GOP, PciIo, DriverBinding, EDID and others) an extracted PE32 image references. |
| `hashes.py` | Searches both images for stored hashes or CRCs of FV ranges, to confirm that no integrity value covers the changed area. |

## Flashing

`FLASH.md` describes the full procedure (in Chinese).
Short version:

### Internal, from Linux on the board

```bash
sudo flashrom -p internal --ifd -i bios -w X99-CH8_G3X99018_rebar_astgop.bin
```

- This writes only the BIOS region (`0x800000`-`0xFFFFFF`).
- `flashrom.log` shows that the descriptor, BIOS and ME regions are read-write.
- A verbose probe on the board showed no protected range (PR) registers set and BIOS_CNTL `0x09` with BIOS Lock Enable (BLE) off. These lines are not in the committed `flashrom.log`.
- Do not write the whole chip internally. Use `--ifd -i bios`.

### External, with a CH341A

The images are full-chip images.
A CH341A programmer can write the whole chip:

```bash
flashrom -p ch341a_spi -w X99-CH8_G3X99018_rebar_astgop.bin
```

Use the CH341A with `dump1.bin` to recover a board that does not boot.

## Enabling Resizable BAR

ReBarDxe reads the NVRAM variable `ReBarState`.

| Item | Value |
|---|---|
| Name | `ReBarState` |
| GUID | `a3c5b77a-c88f-4a93-bf1c-4a92a32c65ce` |
| Size | 1 byte |
| Value | Maximum BAR size as a power of two. `0x20` = unlimited. `0` = off. |

On Linux (booted in UEFI mode):

```bash
printf '\x07\x00\x00\x00\x20' | sudo tee /sys/firmware/efi/efivars/ReBarState-a3c5b77a-c88f-4a93-bf1c-4a92a32c65ce
```

The first 4 bytes are the variable attributes (NV + BS + RT).
The last byte is the value.

On Windows, use `ReBarState.exe` from the ReBarUEFI release.

The NVRAM write worked without the ReBarUEFI NvramSmiDxe patch.

Also enable "Above 4G Decoding" in Setup.
This option already exists in the stock Setup menu.

## Results on hardware (2026-10-27)

- `X99-CH8_G3X99018_rebar_astgop.bin` was flashed and verified.
- The kernel sees the RX 6700 XT BAR0 as 16 GiB at `0x383800000000`.
- The firmware assigned this BAR above 4 GiB. The PciBus 64-bit patch was not needed.
- The GPU link is PCIe Gen3 x16 to a CPU root port.
- With CSM disabled, the onboard AST2400 shows video through the new GOP driver.

## Warnings

- Flashing can brick the board. Keep a CH341A ready.
- Keep `dump1.bin`. It is the only full backup of this board, including its ME region and settings.
- The images contain the NVRAM region of the original dump. Flashing an image restores the BIOS settings to the state at the time of the dump.
- The images were built for one specific board. On another X99-CH8, build your own image from your own dump.

## Repository layout

| Path | Description |
|---|---|
| `README.md` | This file. |
| `FLASH.md` | Detailed flashing procedure (Chinese). |
| `.gitignore` | Ignores Python caches. |
| `dump1.bin` | Original 16 MiB SPI dump of the board, BIOS G3X99018. |
| `dump1.bin.sha256` | SHA-256 of `dump1.bin`. |
| `flashrom.log` | flashrom output from the internal read on the board. |
| `X99-CH8_G3X99018_rebar_only.bin` | Modified image: ReBarDxe only. |
| `X99-CH8_G3X99018_rebar_only.bin.sha256` | SHA-256 of the image above. |
| `X99-CH8_G3X99018_rebar_astgop.bin` | Modified image: ReBarDxe + AST2400 GOP. |
| `X99-CH8_G3X99018_rebar_astgop.bin.sha256` | SHA-256 of the image above. |
| `X99-CH8v3.022-08-27.zip` | Vendor BIOS package from Huananzhi (`99CH8.bin`, `fpt.exe`). |
| `AST2400/v11103_vbios.zip` | ASPEED VBIOS and UEFI driver package v1.11.03. Source of `uefi_2400_396.efi`. |
| `AST2400/VBIOS_UEFI_1.14.00.zip` | ASPEED VBIOS and UEFI driver package v1.14.00 (not used; it has no AST2400 x64 driver). |
| `build/ReBarDxe.ffs` | ReBarDxe FFS used for the build. Identical to the upstream file; the state byte is fixed by `insert_ffs.py`. |
| `build/AstGopDxe.ffs` | AST2400 GOP FFS built by `mkffs.py` (state `0xF8`). |
| `third_party/ReBarUEFI/ReBarDxe.ffs` | Upstream ReBarUEFI 0.3 release FFS, unmodified (state `0x07`). |
| `third_party/ReBarUEFI/README.md` | Upstream ReBarUEFI README. |
| `third_party/ReBarUEFI/patches.txt` | Upstream ReBarUEFI UEFIPatch patterns (not applied; see above). |
| `third_party/ASPEED/uefi_2400_396.efi` | ASPEED AST1400/2400 x64 UEFI GOP driver, MCLK 396 MHz, v1.11.03, extracted from `AST2400/v11103_vbios.zip`. |
| `tools/mkffs.py` | Builds an FFS file (PE32 + UI sections) or checks FFS files with `--check`. |
| `tools/insert_ffs.py` | Appends FFS files into the free space of a firmware volume. |
| `tools/romimg.py` | Lists the images in a PCI option ROM file (legacy and EFI). |
| `tools/oprom.py` | Scans a binary for PCI option ROM headers. |
| `tools/pchk.py` | Checks UEFIPatch patterns against PE32 bodies extracted by UEFIExtract. |
| `tools/ifr.py` | Dumps Setup form (IFR) strings and questions from a module, for example to find "Above 4G Decoding". |
| `tools/files.py` | Summarizes a UEFIExtract report into a volume and file list. |
| `tools/review/fd.py` | Flash descriptor parser. |
| `tools/review/fv.py` | Firmware volume and FFS checker. |
| `tools/review/sec.py` | Section parser for the inserted FFS files. |
| `tools/review/guids.py` | Protocol GUID reference check for PE32 images. |
| `tools/review/hashes.py` | Search for stored hashes or CRCs of firmware ranges. |

## Credits and licenses

- **ReBarUEFI** by xCuri0, MIT license. <https://github.com/xCuri0/ReBarUEFI>
- **ASPEED AST2400 UEFI GOP driver** (`uefi_2400_396.efi`) and the AST2400 packages are proprietary binaries from ASPEED Technology, published by ASPEED for redistribution with platform firmware.
- **Vendor BIOS** (`X99-CH8v3.022-08-27.zip` and the firmware inside `dump1.bin` and the modified images) is the property of Huananzhi and its suppliers (AMI, Intel).
- The Python tools in `tools/` were written for this project.
