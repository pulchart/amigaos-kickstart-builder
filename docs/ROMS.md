# Kickstart source-ROM module inventory

Resident modules (entries marked by the `0x4AFC` `RTC_MATCHWORD`) and their `rt_IDString` values, extracted from each source Kickstart ROM image. One section per OS family, targets currently use 2.04 / 2.05 / 3.1 / 3.2.3; 3.0 / 3.2.0 / 3.2.1 / 3.2.2 are included for cross-version reference.

# AmigaOS 2.0x (Kickstart v37.x)

The "2.0x" line spans Kickstart v37.175 through v37.350.

## ROM revisions covered

| Marketing label | Revision | Board | CRC32 | Resident count | Notes |
|---|---|---|---|---|---|
| 2.04 | 37.175 | A500+ | `0xc3bdb240` | 40 | no HD, no PCMCIA |
| 2.04 | 37.175 | A3000 | `0x234a7233` | 42 | no PCMCIA; SCSI built into board |
| 2.05* | 37.299 | A600 | `0x83028fb5` | 42 | PCMCIA, no HD; filename labels it "v2.05" but feature set is 2.04 |
| 2.05 | 37.300 | A600HD | `0x64466c2a` | 43 | HD up to 40 MB, PCMCIA flaky |
| 2.05 | 37.350 | A600HD | `0x43b0df7b` | 43 | IDE up to 2 GB, PCMCIA OK |

## What changed

* A coloured dot marks a cell whose version differs from the cell to its left:
🔵 = differs from 37.175 (A500+) → 37.175 (A3000)
🟡 = differs from 37.175 (A3000) → 37.299 (A600)
🟢 = differs from 37.299 (A600) → 37.300 (A600HD)
🟠 = differs from 37.300 (A600HD) → 37.350 (A600HD)
* Column-2 marker = same revision, different board (A500+ vs A3000)
* Columns 3–5 markers = revision bumps along the 37.175 → 37.299 → 37.300 → 37.350 progression.

| Resident | 37.175 (A500+) | 37.175 (A3000) | 37.299 (A600) | 37.300 (A600HD) | 37.350 (A600HD) |
|---|---|---|---|---|---|
| `cia.resource` | cia 37.11 (18.4.91) | cia 37.11 (18.4.91) | 🟡 cia 37.13 (23.10.91) | cia 37.13 (23.10.91) | cia 37.13 (23.10.91) |
| `dos.library` | dos 37.44 (22.5.91) | dos 37.44 (22.5.91) | 🟡 dos 37.45 (21.10.91) | dos 37.45 (21.10.91) | dos 37.45 (21.10.91) |
| `exec.library` | exec 37.132 (23.5.91) | exec 37.132 (23.5.91) | 🟡 exec 37.151 (1.11.91) | exec 37.151 (1.11.91) | 🟠 exec 37.152 (27.3.92) |
| `expansion.library` | expansion 37.44 (23.5.91) | expansion 37.44 (23.5.91) | 🟡 expansion 37.50 (28.10.91) | expansion 37.50 (28.10.91) | expansion 37.50 (28.10.91) |
| `filesystem` | fs 37.26 (7.5.91) | fs 37.26 (7.5.91) | 🟡 fs 37.28 (31.10.91) | fs 37.28 (31.10.91) | fs 37.28 (31.10.91) |
| `graphics.library` | graphics 37.35 (23.5.91) | graphics 37.35 (23.5.91) | 🟡 graphics 37.41 (31.10.91) | graphics 37.41 (31.10.91) | graphics 37.41 (31.10.91) |
| `intuition.library` | intuition 37.318 (16.5.91) | intuition 37.318 (16.5.91) | 🟡 intuition 37.331 (29.10.91) | intuition 37.331 (29.10.91) | intuition 37.331 (29.10.91) |
| `layers.library` | layers 37.7 (13.3.91) | layers 37.7 (13.3.91) | 🟡 layers 37.9 (7.10.91) | layers 37.9 (7.10.91) | layers 37.9 (7.10.91) |
| `mathieeesingbas.library` | mathieeesingbas 37.3 (9.5.91) | 🔵 mathieeesingbas 37.2 (7.2.91) | 🟡 mathieeesingbas 37.3 (9.5.91) | mathieeesingbas 37.3 (9.5.91) | mathieeesingbas 37.3 (9.5.91) |
| `ramdrive.device` | ramdrive 37.23 (1.5.91) | ramdrive 37.23 (1.5.91) | 🟡 ramdrive 37.27 (11.10.91) | ramdrive 37.27 (11.10.91) | ramdrive 37.27 (11.10.91) |
| `romboot` | romboot 37.23 (15.3.91) | romboot 37.23 (15.3.91) | 🟡 romboot 37.25 (11.10.91) | romboot 37.25 (11.10.91) | romboot 37.25 (11.10.91) |
| `scsi.device` |  | 🔵 scsidisk 37.19 (10.5.91) |  | 🟢 scsidisk 37.34 (4.11.91) | 🟠 scsidisk 37.55 (22.4.92) |
| `strap` | strap 37.23 (15.3.91) | strap 37.23 (15.3.91) | 🟡 strap 37.25 (11.10.91) | strap 37.25 (11.10.91) | strap 37.25 (11.10.91) |

## Board-specific modules

Modules whose presence varies by board. The version cell shows the `rt_IDString` from the boards where the module exists.

| Resident | Boards present | Version |
|---|---|---|
| `A3000 bonus` | 37.175 (A3000) | bonus 37.3 (16.5.91) |
| `card.resource` | 37.299 (A600), 37.300 (A600HD), 37.350 (A600HD) | cardres 37.11 (28.10.91) |
| `carddisk.device` | 37.299 (A600), 37.300 (A600HD), 37.350 (A600HD) | carddisk 37.11 (24.10.91) |

<details>
<summary>Stable modules across the 2.0x line (28 rows, click to expand)</summary>

| Resident | Version |
|---|---|
| `alert.hook` | alert.hook |
| `audio.device` | audio 37.10 (26.4.91) |
| `battclock.resource` | battclock 37.3 (11.3.91) |
| `battmem.resource` | battmem 37.3 (4.3.91) |
| `bootmenu` | bootmenu 37.2 (15.1.91) |
| `con-handler` | con-handler 37.60 (21.5.91) |
| `console.device` | console 37.157 (22.5.91) |
| `diag init` | diag init |
| `disk.resource` | disk 37.2 (21.4.91) |
| `FileSystem.resource` | filesysres 37.2 (25.4.91) |
| `gadtools.library` | gadtools 37.110 (16.5.91) |
| `gameport.device` | gameport 37.12 (3.5.91) |
| `icon.library` | icon 37.11 (2.5.91) |
| `input.device` | input 37.12 (3.5.91) |
| `keyboard.device` | keyboard 37.12 (3.5.91) |
| `keymap.library` | keymap 37.2 (8.1.91) |
| `mathffp.library` | mathffp 37.1 (13.1.91) |
| `misc.resource` | misc 37.1 (8.1.91) |
| `potgo.resource` | potgo 37.4 (28.1.91) |
| `ram-handler` | ram 37.11 (4.5.91) |
| `ramlib` | ramlib 37.13 (14.3.91) |
| `shell` | shell 37.69 (22.5.91) |
| `syscheck` | syscheck 37.2 (15.1.91) |
| `timer.device` | timer 37.128 (22.4.91) |
| `trackdisk.device` | trackdisk 37.10 (2.5.91) |
| `utility.library` | utility 37.3 (13.2.91) |
| `workbench.library` | wb 37.132 (17.5.91) |
| `workbench.task` | Pre-2.0 LoadWB stub |

</details>

## Notable deltas across the 2.0x line

- **37.175 (A500+)** vs **37.175 (A3000)**: same OS source compiled with different inclusion list. A3000 adds `scsi.device` (`scsidisk 37.19`) and a small `A3000 bonus` resident; A500+ omits both. (`mathieeesingbas` shows a 37.2 / 37.3 build-flag divergence between the two same-rev ROMs.)
- **37.299 (A600)**: adds PCMCIA stack (`card.resource cardres 37.11`, `carddisk.device carddisk 37.11`) and bumps the core libs (`exec 37.132→37.151`, `dos 37.44→37.45`, `graphics 37.35→37.41`, `intuition 37.318→37.331`, `expansion 37.44→37.50`, `cia 37.11→37.13`, …). Still **no `scsi.device`** -- this build targeted the HD-less A600.
- **37.300 (A600HD)**: adds `scsi.device` (`scsidisk 37.34`) for HD-capable A600s. Everything else identical to 37.299.
- **37.350 (A600HD)**: only two residents change vs 37.300 -- `exec 37.151→37.152` and `scsi.device 37.34→scsidisk 37.55`. The scsi.device bump is what raises the IDE volume ceiling from 40 MB to 2 GB and stabilises PCMCIA behaviour. Everything else stays at the late-91 baseline.

# AmigaOS 3.0 (Kickstart v39.106)

Two 512 KB Kickstart 3.0 ROMs (A1200 and A4000 boards). 3.0 is the bridge between the v37 (2.0x) and v40 (3.1) families: new exec/dos/intuition versions. No project build target uses these, included for reference.

## ROM revisions covered

| Label | File | Size | CRC32 | Resident count |
|---|---|---|---|---|
| A1200 | `Kickstart v3.0 rev 39.106 (1992)(Commodore)(A1200)[!].rom` | 512 KB | `0x6c9b07d2` | 43 |
| A4000 | `Kickstart v3.0 rev 39.106 (1992)(Commodore)(A4000)[!].rom` | 512 KB | `0x9e6ac152` | 42 |

## Board-specific modules

Modules whose presence varies by board. The version cell shows the `rt_IDString` from the boards where the module exists.

| Resident | Boards present | Version |
|---|---|---|
| `A1000 Bonus` | A4000 | bonus 39.5 (28.5.92) |
| `card.resource` | A1200 | cardres 37.11 (28.10.91) |
| `carddisk.device` | A1200 | carddisk 37.11 (24.10.91) |

<details>
<summary>Stable modules at v39.106 (41 rows, click to expand)</summary>

| Resident | Version |
|---|---|
| `alert.hook` | alert.hook |
| `audio.device` | audio 37.10 (26.4.91) |
| `battclock.resource` | battclock 39.3 (20.4.92) |
| `battmem.resource` | battmem 39.2 (6.3.92) |
| `bootmenu` | bootmenu 39.19 (26.8.92) |
| `cia.resource` | cia 39.1 (10.3.92) |
| `con-handler` | con-handler 39.8 (18.8.92) |
| `console.device` | console 39.28 (17.7.92) |
| `diag init` | diag init |
| `disk.resource` | disk 37.2 (21.4.91) |
| `dos.library` | dos 39.23 (8.9.92) |
| `exec.library` | exec 39.47 (28.8.92) |
| `expansion.library` | expansion 39.7 (7.6.92) |
| `filesystem` | fs 39.27 (8.9.92) |
| `FileSystem.resource` | filesysres 39.2 (14.7.92) |
| `gadtools.library` | gadtools 39.356 (2.9.92) |
| `gameport.device` | gameport 37.12 (3.5.91) |
| `graphics.library` | graphics 39.89 (1.9.92) |
| `icon.library` | icon 39.3 (28.7.92) |
| `input.device` | input 37.12 (3.5.91) |
| `intuition.library` | intuition 39.2084 (2.9.92) |
| `keyboard.device` | keyboard 37.12 (3.5.91) |
| `keymap.library` | keymap 37.2 (8.1.91) |
| `layers.library` | layers 39.61 (16.6.92) |
| `mathffp.library` | mathffp 39.1 (20.4.92) |
| `mathieeesingbas.library` | mathieeesingbas 37.3 (9.5.91) |
| `misc.resource` | misc 37.1 (8.1.91) |
| `potgo.resource` | potgo 37.4 (28.1.91) |
| `ram-handler` | ram 39.4 (9.8.92) |
| `ramdrive.device` | ramdrive 39.35 (21.5.92) |
| `ramlib` | ramlib 39.5 (27.5.92) |
| `romboot` | romboot |
| `scsi.device` | scsidisk 37.64 (13.8.92) |
| `shell` | shell 39.13 (21.8.92) |
| `strap` | strap 39.27 (20.5.92) |
| `syscheck` | syscheck 39.19 (26.8.92) |
| `timer.device` | timer 39.4 (29.7.92) |
| `trackdisk.device` | trackdisk 39.4 (10.8.92) |
| `utility.library` | utility 39.10 (3.6.92) |
| `workbench.library` | wb 39.48 (20.8.92) |
| `workbench.task` | wbtag 39.1 (20.4.92) |

</details>

# AmigaOS 3.1 (Kickstart v40.x)

Two 512 KB Kickstart 3.1 ROMs, single F8 bank each. Used as the source for `A600-3.1` and `A1200-3.1` builds; the E0 half is built by the project (`ROMHeader_E0` chunk + scantable redirect + filesystems + cfd modules).

## ROM revisions covered

| Label | File | Size | CRC32 | Resident count |
|---|---|---|---|---|
| A600 (kick40063) | `kick40063.A600` | 512 KB | `0xfc24ae0d` | 43 |
| A1200 (kick40068) | `kick40068.A1200` | 512 KB | `0x1483a091` | 43 |

## What changed

A coloured dot marks a cell whose `rt_IDString` differs from the cell to its left: 🔵 = differs from A600 (kick40063) → A1200 (kick40068).

| Resident | A600 (kick40063) | A1200 (kick40068) |
|---|---|---|
| `scsi.device` | scsidisk 40.5 (13.9.93) | 🔵 scsidisk 40.12 (21.12.93) |

<details>
<summary>Stable modules at v40 (42 rows, click to expand)</summary>

| Resident | Version |
|---|---|
| `alert.hook` | alert.hook |
| `audio.device` | audio 37.10 (26.4.91) |
| `battclock.resource` | battclock 39.3 (20.4.92) |
| `battmem.resource` | battmem 39.2 (6.3.92) |
| `bootmenu` | bootmenu 40.5 (17.3.93) |
| `card.resource` | cardres 40.4 (4.5.93) |
| `carddisk.device` | carddisk 40.1 (12.2.93) |
| `cia.resource` | cia 39.1 (10.3.92) |
| `con-handler` | con-handler 40.2 (12.5.93) |
| `console.device` | console 40.2 (5.3.93) |
| `diag init` | diag init |
| `disk.resource` | disk 37.2 (21.4.91) |
| `dos.library` | dos 40.3 (1.4.93) |
| `exec.library` | exec 40.10 (15.7.93) |
| `expansion.library` | expansion 40.2 (9.3.93) |
| `filesystem` | fs 40.1 (15.2.93) |
| `FileSystem.resource` | filesysres 40.1 (15.2.93) |
| `gadtools.library` | gadtools 40.4 (24.5.93) |
| `gameport.device` | gameport 40.1 (8.3.93) |
| `graphics.library` | graphics 40.24 (18.5.93) |
| `icon.library` | icon 40.1 (15.2.93) |
| `input.device` | input 40.1 (8.3.93) |
| `intuition.library` | intuition 40.85 (5.5.93) |
| `keyboard.device` | keyboard 40.1 (8.3.93) |
| `keymap.library` | keymap 40.4 (12.3.93) |
| `layers.library` | layers 40.1 (15.2.93) |
| `mathffp.library` | mathffp 40.1 (16.3.93) |
| `mathieeesingbas.library` | mathieeesingbas 40.4 (16.3.93) |
| `misc.resource` | misc 37.1 (8.1.91) |
| `potgo.resource` | potgo 37.4 (28.1.91) |
| `ram-handler` | ram 39.4 (9.8.92) |
| `ramdrive.device` | ramdrive 39.35 (21.5.92) |
| `ramlib` | ramlib 40.2 (5.3.93) |
| `romboot` | romboot |
| `shell` | shell 40.2 (4.3.93) |
| `strap` | strap 40.1 (8.3.93) |
| `syscheck` | syscheck |
| `timer.device` | timer 39.4 (29.7.92) |
| `trackdisk.device` | trackdisk 40.1 (12.3.93) |
| `utility.library` | utility 40.1 (10.2.93) |
| `workbench.library` | wb 40.5 (24.5.93) |
| `workbench.task` | wbtag 39.1 (20.4.92) |

</details>

# AmigaOS 3.2.0 (Hyperion initial release)

Five 512 KB Kickstart 3.2.0 source ROMs from Hyperion's initial 3.2 release (filenames `kicka*.rom`, no update-build-number stamp; exec.library is 47.7). Same single-F8-bank shape as 3.1; no project build target uses these (3.2.3 is the supported 3.2.x family target), included as the cross-Hyperion-update comparison baseline.

## ROM revisions covered

| Label | File | Size | CRC32 | Resident count |
|---|---|---|---|---|
| CDTV/A500/A600/A2000 | `kickcdtva1000a500a2000a600.rom` | 512 KB | `0x8173d7b6` | 45 |
| A1200 | `kicka1200.rom` | 512 KB | `0xbd1ff75e` | 45 |
| A3000 | `kicka3000.rom` | 512 KB | `0xf3af46cc` | 44 |
| A4000 | `kicka4000.rom` | 512 KB | `0x9bb8fc93` | 44 |
| A4000T | `kicka4000t.rom` | 512 KB | `0x9188a509` | 45 |

## Per-module version comparison

Module versions live in the consolidated inventory below: see [3.2.x consolidated module inventory](#amigaos-32x-consolidated-module-inventory).

# AmigaOS 3.2.1 (Hyperion 47.102)

Five 512 KB Kickstart 3.2.1 source ROMs (Hyperion 47.102 update).  No project build target uses these, included for cross-Hyperion-update comparison.

## ROM revisions covered

| Label | File | Size | CRC32 | Resident count |
|---|---|---|---|---|
| CDTV/A500/A600/A2000 | `CDTVA500A600A2000.47.102.rom` | 512 KB | `0x4f078456` | 45 |
| A1200 | `A1200.47.102.rom` | 512 KB | `0x2b653371` | 45 |
| A3000 | `A3000.47.102.rom` | 512 KB | `0x78f607` | 44 |
| A4000 | `A4000.47.102.rom` | 512 KB | `0xf3ced3b8` | 44 |
| A4000T | `A4000T.47.102.rom` | 512 KB | `0xaf3452ec` | 45 |

## Per-module version comparison

Module versions live in the consolidated inventory below: see [3.2.x consolidated module inventory](#amigaos-32x-consolidated-module-inventory).

# AmigaOS 3.2.2 (Hyperion 47.111)

Five 512 KB Kickstart 3.2.2 source ROMs (Hyperion 47.111 update). No project build target uses these, included for cross-Hyperion-update comparison.

## ROM revisions covered

| Label | File | Size | CRC32 | Resident count |
|---|---|---|---|---|
| CDTV/A500/A600/A2000 | `CDTVA500A600A2000.47.111.rom` | 512 KB | `0xe4458462` | 45 |
| A1200 | `A1200.47.111.rom` | 512 KB | `0x5c40328a` | 45 |
| A3000 | `A3000.47.111.rom` | 512 KB | `0x46335b57` | 44 |
| A4000 | `A4000.47.111.rom` | 512 KB | `0x4bea9798` | 44 |
| A4000T | `A4000T.47.111.rom` | 512 KB | `0x36bbcd8a` | 45 |

## Per-module version comparison

Module versions live in the consolidated inventory below: see [3.2.x consolidated module inventory](#amigaos-32x-consolidated-module-inventory).

# AmigaOS 3.2.3 (Hyperion 47.115)

Five 512 KB Kickstart 3.2.3 source ROMs from the Hyperion 47.115 update (same single-F8-bank shape as 3.1). Used as the source for the project's 3.2.3 builds: `A600-3.2.3` pulls from the CDTV/A500/A600/A2000 ROM, `A1200-3.2.3` pulls from the A1200 ROM. E0 modules (workbench.library, icon.library, rexxsyslib, pfs3aio, fat95, cfd) are added separately from the Hyperion Modules ADFs / Workbench ADF / `dist/`.

## ROM revisions covered

| Label | File | Size | CRC32 | Resident count |
|---|---|---|---|---|
| CDTV/A500/A600/A2000 | `CDTVA500A600A2000.47.115.rom` | 512 KB | `0xe1f50b0b` | 45 |
| A1200 | `A1200.47.115.rom` | 512 KB | `0xb18d3b67` | 45 |
| A3000 | `A3000.47.115.rom` | 512 KB | `0x74c0b23f` | 44 |
| A4000 | `A4000.47.115.rom` | 512 KB | `0xb6a4698e` | 44 |
| A4000T | `A4000T.47.115.rom` | 512 KB | `0x588a5e6d` | 45 |

## Per-module version comparison

Module versions live in the consolidated inventory below: see [3.2.x consolidated module inventory](#amigaos-32x-consolidated-module-inventory).

# AmigaOS 3.2.x consolidated module inventory

Single-source module-version reference for the 3.2.x line:
* 3.2.0 initial release
* 3.2.1 (47.102)
* 3.2.2 (47.111)
* 3.2.3 (47.115).

Three sub-tables: modules whose version changes across the line, modules stable across all four releases, and modules whose presence or label varies by board. Per-release per-board tables in the four sections above carry only the ROM-level metadata (filename / CRC32 / resident count); for individual module versions, read here.

## Modules that change across 3.2.x

A coloured dot marks a cell where a version bump in that release. One dot colour per release column:
🔵 = bump landed in 3.2.1 
🟡 = bump landed in 3.2.2 
🟢 = bump landed in 3.2.3.

| Resident | 3.2.0 | 3.2.1 (47.102) | 3.2.2 (47.111) | 3.2.3 (47.115) |
|---|---|---|---|---|
| `bootmenu` | bootmenu 47.11 (1.1.2021) | bootmenu 47.11 (1.1.2021) | bootmenu 47.11 (1.1.2021) | 🟢 bootmenu 47.12 (19.4.2024) |
| `dos.library` | dos 47.23 (2.1.2021) | 🔵 dos 47.30 (2.12.2021) | dos 47.30 (2.12.2021) | dos 47.30 (2.12.2021) |
| `exec.library` | exec 47.7 (12.11.2020) | 🔵 exec 47.8 (27.10.2021) | 🟡 exec 47.10 (21.01.2023) | 🟢 exec 47.13 (1.1.2025) |
| `expansion.library` | expansion 47.1 (3.8.2019) | 🔵 expansion 47.3 (18.10.2021) | expansion 47.3 (18.10.2021) | 🟢 expansion 47.4 (1.1.2025) |
| `gadtools.library` | gadtools 47.16 (20.2.2021) | 🔵 gadtools 47.17 (16.7.2021) | gadtools 47.17 (16.7.2021) | gadtools 47.17 (16.7.2021) |
| `graphics.library` | graphics 47.4 (3.4.2021) | 🔵 graphics 47.10 (31.10.2021) | graphics 47.10 (31.10.2021) | graphics 47.10 (31.10.2021) |
| `icon.library` | icon.library 47.4 (16.7.2020) | 🔵 icon.library 47.5 (28.5.2021) | icon.library 47.5 (28.5.2021) | icon.library 47.5 (28.5.2021) |
| `intuition.library` | intuition 47.51 (3.4.2021) | intuition 47.51 (3.4.2021) | 🟡 intuition 47.52 (19.4.2022) | 🟢 intuition 47.53 (27.11.2024) |
| `ram-handler` | ram 47.7 (8.1.2020) | 🔵 ram 47.8 (4.10.2021) | 🟡 ram 47.45 (27.2.2023) | 🟢 ram 47.57 (24.3.2024) |
| `shell` | shell 47.47 (23.2.2021) | 🔵 shell 47.48 (29.9.2021) | shell 47.48 (29.9.2021) | shell 47.48 (29.9.2021) |
| `strap` | strap 45.1 (11.5.2018) | 🔵 strap 47.2 (30.5.2021) | strap 47.2 (30.5.2021) | strap 47.2 (30.5.2021) |
| `system-startup` | system-startup 47.21 (7.9.2020) | 🔵 system-startup 47.22 (26.10.2021) | 🟡 system-startup 47.23 (6.2.2022) | 🟢 system-startup 47.26 (25.11.2023) |
| `workbench.library` | workbench.library 47.33 (31.3.2021) | 🔵 workbench.library 47.36 (27.10.2021) | 🟡 workbench.library 47.37 (17.12.2022) | 🟢 workbench.library 47.42 (1.1.2025) |

(13 rows — modules whose `rt_IDString` differs in at least one release column.)

<details>
<summary>Stable modules across 3.2.x (29 rowsm, click to expand)</summary>

| Resident | Version (all four releases) |
|---|---|
| `FileSystem.resource` | filesysres 47.4 (16.1.2021) |
| `alert.hook` | alert.hook |
| `audio.device` | audio 47.1 (4.8.2019) |
| `battclock.resource` | battclock 47.2 (16.9.2020) |
| `battmem.resource` | battmem 39.2 (6.3.1992) |
| `cia.resource` | cia 45.1 (19.7.2018) |
| `con-handler` | con-handler 47.19 (5.12.2020) |
| `console.device` | console 46.1 (4.8.2019) |
| `diag init` | diag init |
| `disk.resource` | disk 47.1 (8.8.2020) |
| `filesystem` | fs 47.4 (16.6.2020) |
| `gameport.device` | gameport 47.1 (4.8.2019) |
| `input.device` | input 47.1 (21.7.2019) |
| `keyboard.device` | keyboard 47.1 (28.7.2019) |
| `keymap.library` | keymap 47.1 (28.7.2019) |
| `layers.library` | layers 46.2 (18.12.2019) |
| `mathffp.library` | mathffp 46.1 (4.8.2019) |
| `mathieeesingbas.library` | mathieeesingbas 47.1 (5.5.2019) |
| `misc.resource` | misc 37.1 (8.1.1991) |
| `potgo.resource` | potgo 37.5 (8.5.1991) |
| `ramdrive.device` | ramdrive 46.2 (26.12.2019) |
| `ramlib` | ramlib 45.1 (6.5.2017) |
| `romboot` | romboot |
| `syscheck` | syscheck 47.1 (8.8.2019) |
| `syslog` | syslog 47.1 (20.10.2019) |
| `timer.device` | timer 46.1 (4.8.2019) |
| `trackdisk.device` | trackdisk 47.14 (9.9.2020) |
| `utility.library` | utility 47.3 (3.2.2020) |
| `workbench.task` | wbtag 39.1 (20.4.1992) |

</details>

## Board-specific modules

Modules whose presence or label varies by board. `rt_IDString` does not change across 3.2.x for any of these, so a single version column suffices.

| Resident | Boards present | Version / variant |
|---|---|---|
| `A3000 bonus` | A3000 | bonus 40.1 (15.2.1993) |
| `A4000 bonus` | A4000, A4000T | bonus 40.1 (15.2.1993) |
| `NCR scsi.device` | A4000T | A4000T_scsidisk 47.4 (30.12.2019) |
| `card.resource` | CDTV/A500/A600/A2000, A1200 | cardres 47.4 (8.8.2020) |
| `carddisk.device` | CDTV/A500/A600/A2000, A1200 | carddisk 47.2 (10.3.2020) |
| `scsi.device` | A3000 | scsidisk 47.4 (30.12.2019) |
| `scsi.device` | CDTV/A500/A600/A2000, A1200, A4000, A4000T | IDE_scsidisk 47.4 (30.12.2019) |
