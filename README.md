# amigaos-kickstart-builder

YAML-driven builder for custom **1 MB AmigaOS Kickstart ROMs** with optional embedded modules. Drives Capitoline `capcli.Linux` from a single per-model config, supports AmigaOS 3.2.3, 3.1, 2.05, and 2.04 source ROMs, and lets you slot extra modules (filesystem handlers, drivers, libraries) into the E0 bank, or substitute / skip / relocate stock modules in F8.

Originally written to bake `compactflash.device` + `ptable.library` ([cfd project](https://github.com/pulchart/cfd)) into the Kickstart so RDB-partitioned CF cards autoboot before any disk-loaded driver. Generalises beyond `cfd`, with config profiles for different module sets.

## Contents

- [Quickstart](#quickstart)
- [Prerequisites](#prerequisites)
- [Usage](#usage)
- [Config profiles](#config-profiles)
- [Worked example: A1200 3.2.3 with cfd + pfs3aio + fat95](#worked-example-a1200-323-with-cfd--pfs3aio--fat95)
- [Customising the build](#customising-the-build)
- [Flashing](#flashing)
- [Deeper docs](#deeper-docs)
- [Licensing and IP boundary](#licensing-and-ip-boundary)

## Quickstart

```sh
sudo dnf install python3-jinja2 python3-pyyaml python3-tabulate    # or your distro's equivalent
# install Capitoline + at least one AmigaOS source (see Prerequisites)
./kickstart.py 3.2.3                                          # builds A600 + A1200 3.2.3 ROMs
ls out/*/A600-3.2.3/*.rom                                           # one ROM per config profile
```

## Prerequisites

The builder runs on Linux and shells out to [Capitoline](http://capitoline.twocatsblack.com/index.php/capcli/).

| # | Prerequisite | Install at | Needed by |
|---|---|---|---|
| 1 | Python 3.10+ with `jinja2`, `pyyaml`, `tabulate` | system packages | all configs |
| 2 | [Capitoline](http://capitoline.twocatsblack.com/) (`capcli.Linux`, `Components/`, `Capitoline Hashes/`) | `/opt/Capitoline/` | all configs |
| 3 | Hyperion AmigaOS 3.2.3 Update (`ROMs/`, `ADFs/`) | `/opt/AmigaOS/Update3.2.3/` | any 3.2.3 target |
| 4 | Workbench 3.2 ADF (`workbench3.2.adf`) | `/opt/AmigaOS/AmigaOS3.2/adf/` | `cfd.yaml`, `bare.yaml`, `iconlib.yaml` (rexxsyslib.library for 3.2.3) |
| 5 | AmigaOS 3.1 (`ROMs/`, `ADFs/`) | `/opt/AmigaOS/AmigaOS3.1/` | any 3.1 target |
| 6 | AmigaOS 2.05 ROM (v37.350, CRC `0x43b0df7b`) | `/opt/AmigaOS/AmigaOS2.05/ROMs/` | any 2.05 target |
| 7 | AmigaOS 2.04 ROM (v37.175 A500+, CRC `0xc3bdb240`) | `/opt/AmigaOS/AmigaOS2.04/ROMs/` | any 2.04 target |
| 8 | [pfs3aio](https://github.com/tonioni/pfs3aio) v20.0 test5 from [EAB  PFS3aio v3.2 test](https://eab.abime.net/showthread.php?t=115072) | `/opt/AmigaOS/pfs/v20,0/` | `cfd.yaml`, `iconlib.yaml` |
| 9 | [fat95](https://github.com/pulchart/fat95/releases) (68000 + 68020) | `/opt/AmigaOS/fat95/3.23/{68000,68020}/` | `cfd.yaml` only |
| 10 | [cfd](https://github.com/pulchart/cfd/releases) `compactflash.device` + `ptable.library` | `/opt/AmigaOS/cfd/1.43/full/{68000,68020}/{devs,libs}/` | `cfd.yaml` only (3.2.3 / 3.1 / 2.05; A500plus-2.04 omitted, no PCMCIA or IDE) |
| 11 | [IconLib 46.4](https://aminet.net/package/util/libs/IconLib_46.4) (`icon.library` 68000 + 68020) | `/opt/AmigaOS/IconLib/46.4.602/Libs/{,68000/}icon.library` | `iconlib.yaml` only |

If a required prerequisite for a target you're building is missing, the script reports an error and stops. Targets you don't build don't need their source trees. Capitoline / ROMs / ADFs are user-supplied (none are bundled here).

For the technical details behind the scantable patches, see [docs/kickstart-scantable.md](docs/kickstart-scantable.md).

## Usage

```sh
./kickstart.py                    # all non-underscore configs in config/, every variant
./kickstart.py -c cfd             # same, explicit config selection
./kickstart.py 3.2.3              # both 3.2.3 ROMs
./kickstart.py 3.1                # both 3.1 ROMs
./kickstart.py 2.0x               # both 2.0x ROMs (A600-2.05 + A500plus-2.04)
./kickstart.py 2.05               # A600-2.05 ROM only
./kickstart.py 2.04               # A500plus-2.04 ROM only
./kickstart.py a1200-3.1          # one specific model

# select a different config profile (see Config profiles below)
./kickstart.py -c bare 3.2.3
./kickstart.py -c iconlib a600

# override the output basename
./kickstart.py -c bare -n myrom a600
```

`-c` accepts a shortname (resolved against `config/<name>.yaml`) or a full path.

Output lands in `out/<name>/<MODEL>/` where `<name>` is the config stem (or `-n` override) and `<MODEL>` is one of `A600-3.2.3`, `A1200-3.2.3`, `A600-3.1`, `A1200-3.1`, `A600-2.05`, `A500plus-2.04`:

| File | Description |
|---|---|
| `<name>.rom` | 1 MB merged image (F8 ROM concatenated with E0 ROM) |
| `<name>.F8` | F8 half (512 KB at `0xF80000`): base AmigaOS modules |
| `<name>.E0` | E0 half (512 KB at `0xE00000`): extra modules (rexxsyslib, pfs3aio, fat95, compactflash.device, ...) |
| `<name>.hi.bin`, `<name>.lo.bin` | (A1200 only) byteswapped halves for the A1200's two physical Kickstart chips |
| `capitoline.log` | full Capitoline build log |
| `capitoline.script` | rendered script that was fed to `capcli.Linux` |

A successful run ends with a resident-module table like this (truncated):

```text
Residents in cfd.rom: A1200-3.2.3 (53 found, 2 shadowed by higher version):
  Bank    Addr    Type      Ver    Pri  Name                     IDString                                              Notes
  ------  ------  ------  -----  -----  -----------------------  ----------------------------------------------------  ------------------
  F8      F80000  lib        47      0  exec.library             exec 47.13 (1.1.2025)
  ...
  F8      FFCB78  lib        40   -120  workbench.library        workbench.library 47.42 (1.1.2025)                    shadowed -> E0 v47
  E0      E00014  lib        47   -120  workbench.library        workbench.library 47.42 (1.1.2025)
  E0      E352F8  lib        47      0  rexxsyslib.library       rexxsyslib 47.2 (19.8.2019)
  E0      E3DDBA  t0         20     78  pfs3aio                  Professional-File-System-III 20.0 PFS3AIO-VERSION...
  E0      E4CB1A  t0          3      0  fat95                    fat95 3.23 (19.05.2026) [68020]
  E0      E538A0  dev         1     21  compactflash.device      compactflash.device 1.43 (19.05.2026) [68020]
```

If the table is missing or any row looks wrong, check `capitoline.log` in the same output directory.

## Config profiles

Three profiles are bundled under `config/`. All share the same hardware model definitions (`config/_models.yaml`); only the `modules:` list differs.

| Profile | Command | What it adds to E0 (and F8) |
|---|---|---|
| `cfd.yaml` | `./kickstart.py -c cfd` | workbench.library, icon.library, rexxsyslib, pfs3aio, fat95, **compactflash.device + ptable.library** (cfd; 3.2.3 / 3.1 / 2.05 only) |
| `bare.yaml` | `./kickstart.py -c bare` | AmigaOS's native rom extension: workbench.library, icon.library (stock), rexxsyslib |
| `iconlib.yaml` | `./kickstart.py -c iconlib` | workbench.library, **icon.library 46.4.602** (replaces stock), rexxsyslib, pfs3aio |

To create your own profile, copy any existing config file, adjust the `modules:` list, and pass it with `-c`:

```sh
cp config/bare.yaml config/myprofile.yaml
# edit config/myprofile.yaml
./kickstart.py -c myprofile 3.2.3
# output: out/myprofile/A600-3.2.3/myprofile.rom, out/myprofile/A1200-3.2.3/myprofile.rom
```

The `models_from: _models.yaml` line at the top of every config pulls in the shared hardware model definitions automatically.

## Worked example: A1200 3.2.3 with cfd + pfs3aio + fat95

End-to-end from a clean machine to two flashable EPROM images.

1. Install the prerequisites listed in rows 1, 2, 3, 4, 8, 9, 10 of the [Prerequisites](#prerequisites) table: Python deps, Capitoline, the Hyperion 3.2.3 update, Workbench 3.2 ADF, pfs3aio, fat95, cfd.
2. Build:
   ```sh
   ./kickstart.py -c cfd a1200-3.2.3
   ```
3. Flash:
   - `out/cfd/A1200-3.2.3/cfd.hi.bin` to the upper Kickstart EPROM (27C400).
   - `out/cfd/A1200-3.2.3/cfd.lo.bin` to the lower Kickstart EPROM (27C400).

## Customising the build

Bundled profiles live under `config/`; when no `-c` is given, every non-underscore profile is built. Run `./kickstart.py --help` for usage and `./kickstart.py --help-config` for the full schema. Each entry in the `modules:` list uses one of these verbs:

| Verb (full signature) | Effect | Notes |
|---|---|---|
| `file: <path>` + `rom: "E0"\|"F8"` | add a file from disk | `path` absolute or repo-relative; copied into workdir and added by basename. |
| `adf: <path>` + `adf_path: <inner>` + `rom: "E0"\|"F8"` | add a lib from a specific ADF | Capitoline `loadadf "<adf>"; add ADF:/<inner>`. **`adf_path:` is case-sensitive** (capcli does exact-case lookup against ADF entries); typos fail the build via the `error:` log guard rather than silently dropping the component. |
| `replace: <stock>` + (`with: <path>` or `adf:` + `adf_path:`) + `rom: "F8"\|"E0"` | swap a stock F8 module for a replacement binary | `rom: "F8"` substitutes at the stock slot; `rom: "E0"` suppresses the F8 line and lands the substitute in E0 (useful when it exceeds the F8 budget). |
| `skip: <stock>` | drop a stock F8 module from the build | The module isn't added anywhere. No `rom:` (rejected). |
| `relocate: <stock>` + `rom: "E0"` | move a stock F8 module to E0 | Keeps the original content; only the ROM bank changes. `rom: "E0"` is the only valid value. |

All verbs accept the optional filters:

- `cpu: "68000" | "68020"`: include only for the matching CPU build.
- `os:  "2.04" | "2.05" | "3.1" | "3.2.3"`: include only for the matching OS build.

Order in the `modules:` list = order of `add` directives in the rendered Capitoline script.

## Flashing

Output filenames use `<name>` (the config stem, or `-n` override).

See the [Usage](#usage) section for the full list of files written under `out/<name>/<MODEL>/`. The flashing-relevant subset:

### A1200: dual-chip layout

The A1200 Kickstart socket takes two 512 KB (4 Mbit) EPROMs wired in parallel (odd/even byte lanes). The builder produces ready-to-flash split images with the byteswap already applied: flash `<name>.hi.bin` to the upper chip and `<name>.lo.bin` to the lower chip (both 27C400 / 4 Mbit / DIP42).

### A600 / A500+: single-chip layout

Flash the merged 1 MB `<name>.rom` to a single 27C800 (8 Mbit / DIP42).

### FS-UAE

For emulator use, point FS-UAE at the `<name>.F8` and `<name>.E0` halves instead of flashing anything.

### Programmer

The **T48 (MiniPro)** handles 27C400 and 27C800 directly; the **TL866II Plus** (MiniPro) works via a conversion adapter.

## Deeper docs

- [docs/kickstart-scantable.md](docs/kickstart-scantable.md): how the 1 MB scantable redirect works across 3.2.3 / 3.1 / 2.0x and why each family uses a different mechanism.
- [docs/ROMS.md](docs/ROMS.md): resident-module inventory across source Kickstart ROM (2.0x / 3.0 / 3.1 / 3.2.y).


## Licensing and IP boundary

The builder itself is MIT-licensed; ROMs, ADFs, and bundled third-party modules carry their own licences and are not redistributed.

<details>
<summary>Full IP scope (click to expand)</summary>

The MIT licence (`LICENSE`) covers the **builder itself**: the Python driver, the YAML config under `config/`, the Jinja templates under `templates/`, and the docs in this repo. Everything else lives outside the repo and carries its own licence:

- **Capitoline `capcli.Linux`** (from the [capitoline.twocatsblack.com](http://capitoline.twocatsblack.com/)). This builder doesn't ship `capcli.Linux` or the `Capitoline Hashes/` database, `kickstart.py` shells out to whatever you have downloaded at `/opt/Capitoline/`.
- **AmigaOS Kickstart ROMs and Workbench ADFs** (Hyperion 3.2.3, Commodore 3.1 / 2.05 / 2.04, etc.) are copyrighted by their respective owners. You must supply your own legally-obtained copies; the builder doesn't redistribute any ROM or ADF.
- **Output 1 MB ROM images** produced by this tool embed code from the source Kickstart ROM and ADFs and are therefore subject to *those* licences, typically not redistributable. Build your own; don't share the binaries.
- **cfd modules** (`compactflash.device`, `ptable.library`) are LGPL v2.1 from the [cfd project](https://github.com/pulchart/cfd). The builder reads them as plain files from `/opt/AmigaOS/cfd/<version>/full/...`.
- **fat95** (AmigaOS FAT filesystem handler) is LGPL v2.1 from the [fat95 project](https://github.com/pulchart/fat95). The builder reads it as a plain file from `/opt/AmigaOS/fat95/<version>/<cpu>/fat95`.
- **pfs3aio** is a third-party AmigaOS PFS3 filesystem handler (Professional-File-System-III, originally by Michiel Pelt / Peltin BV; AIO variant maintained at [tonioni/pfs3aio](https://github.com/tonioni/pfs3aio)). The builder reads it as a plain file from `/opt/AmigaOS/pfs/<version>/pfs3aio`. License: see the pfs3aio distribution; the builder doesn't bundle it.

If you fork or extend the builder, the MIT licence applies to your fork's source. The output ROMs your fork produces remain subject to the upstream Kickstart / ADF / filesystem-handler / cfd licences regardless.

</details>
