# amigaos-kickstart-builder

YAML-driven builder for custom **1 MB AmigaOS Kickstart ROMs** with optional embedded modules. Drives Capitoline `capcli.Linux` from a single per-model config, supports AmigaOS **3.2.3, 3.1, 2.05, and 2.04** source ROMs, and lets you slot extra modules (filesystem handlers, drivers, libraries) into the E0 bank, or substitute / skip / relocate stock modules in F8.

Originally written to bake `compactflash.device` + `ptable.library` ([cfd project](https://github.com/pulchart/cfd)) into the Kickstart so RDB-partitioned CF cards autoboot before any disk-loaded driver. Generalises beyond `cfd` any module that has a `file:` (hunk binary) or `adf:` + `adf_path:` (entry inside an ADF) can be added.

## Prerequisites

The builder runs on Linux and shells out to [Capitoline](http://capitoline.twocatsblack.com/index.php/capcli/).

| # | Prerequisite | Install at | Needed for |
|---|---|---|---|
| 1 | Python 3.10+ with `jinja2` + `pyyaml` | system packages | all builds |
| 2 | Capitoline (`capcli.Linux`, `Components/`, `Capitoline Hashes/`) | `/opt/Capitoline/` | all builds |
| 3 | Hyperion AmigaOS 3.2.3 Update (`ROMs/`, `ADFs/`) | `/opt/AmigaOS/Update3.2.3/` | 3.2.3 builds |
| 4 | Workbench 3.2 ADF (`workbench3.2.adf`) | `/opt/AmigaOS/AmigaOS3.2/adf/` | 3.2.3 builds |
| 5 | AmigaOS 3.1 (`ROMs/`, `ADFs/`) | `/opt/AmigaOS/AmigaOS3.1/` | 3.1 builds |
| 6 | AmigaOS 2.05 ROM (v37.350, CRC `0x43b0df7b`) | `/opt/AmigaOS/AmigaOS2.05/ROMs/` | 2.05 build (A600) |
| 7 | AmigaOS 2.04 ROM (v37.175 A500+, CRC `0xc3bdb240`) | `/opt/AmigaOS/AmigaOS2.04/ROMs/` | 2.04 build (A500+) |
| 8 | pfs3aio | `/opt/AmigaOS/pfs/v20,0/` | all builds |
| 9 | fat95 (68000 + 68020) | `/opt/AmigaOS/fat95/3.22/{68000,68020}/` | all builds |
| 10 | cfd `compactflash.device` + `ptable.library` | `/opt/AmigaOS/cfd/1.42/full/{68000,68020}/{devs,libs}/` | all builds that embed cfd (currently 3.2.3 / 3.1 / 2.05; A500plus-2.04 has neither PCMCIA nor IDE and omits both) |

If a required prerequisite for a target you're building is missing, the script reports an error and stops. Targets you don't build don't need their source trees. Capitoline / ROMs / ADFs are user-supplied (none are bundled here).

For the technical details behind the scantable patches, see [docs/kickstart-scantable.md](docs/kickstart-scantable.md).

## Build

```sh
python3 kickstart.py             # default: every variant (3.2.3 + 3.1 + 2.05 + 2.04)
python3 kickstart.py 3.2.3       # both 3.2.3 ROMs
python3 kickstart.py 3.1         # both 3.1 ROMs
python3 kickstart.py 2.0x        # both 2.0x ROMs (A600-2.05 + A500plus-2.04)
python3 kickstart.py 2.05        # A600-2.05 ROM only
python3 kickstart.py 2.04        # A500plus-2.04 ROM only
python3 kickstart.py a1200-3.1   # one specific model
```

Output lands in `out/<MODEL>/` where `<MODEL>` is one of `A600-3.2.3`, `A1200-3.2.3`, `A600-3.1`, `A1200-3.1`, `A600-2.05`, `A500plus-2.04`:

| File | Description |
|---|---|
| `cfd.rom` | 1 MB merged image (F8 ROM concatenated with E0 ROM) |
| `cfd.F8` | F8 half (512 KB at `0xF80000`): base AmigaOS modules |
| `cfd.E0` | E0 half (512 KB at `0xE00000`): extra modules (rexxsyslib, pfs3aio, fat95, compactflash.device, ...) |
| `cfd.hi.bin`, `cfd.lo.bin` | (A1200 only) byteswapped halves for the A1200's two physical Kickstart chips |
| `capitoline.log` | full Capitoline build log |
| `capitoline.script` | rendered script that was fed to `capcli.Linux` |

## Customising the build

The set of extra modules and the per-machine config live in `config/kickstart.yaml`. Run `python3 kickstart.py --help` for the full schema. Each entry in the `modules:` list uses one of these verbs:

| Verb (full signature) | Effect | Notes |
|---|---|---|
| `file: <path>` + `rom: "E0"\|"F8"` | add a file from disk | `path` absolute or repo-relative; copied into workdir and added by basename. |
| `adf: <path>` + `adf_path: <inner>` + `rom: "E0"\|"F8"` | add a lib from a specific ADF | Capitoline `loadadf "<adf>"; add ADF:/<inner>`. **`adf_path:` is case-sensitive** (capcli does exact-case lookup against ADF entries); typos fail the build via the `error:` log guard rather than silently dropping the component. |
| `adf_modules: <inner>` + `rom: "E0"\|"F8"` | add a lib from the model's modules ADF | Shorthand for `adf:` + `adf_path:` using `$ADF`; 3.2.3 only (3.1 has no modules ADF). Same case-sensitivity caveat as `adf:`. |
| `replace: <stock>` + (`with: <path>` or `adf:` + `adf_path:`) + `rom: "F8"\|"E0"` | swap a stock F8 module for a replacement binary | `rom: "F8"` substitutes at the stock slot; `rom: "E0"` suppresses the F8 line and lands the substitute in E0 (useful when it exceeds the F8 budget). |
| `skip: <stock>` | drop a stock F8 module from the build | The module isn't added anywhere. No `rom:` (rejected). |
| `relocate: <stock>` + `rom: "E0"` | move a stock F8 module to E0 | Keeps the original content; only the ROM bank changes. `rom: "E0"` is the only valid value. |

All verbs accept the optional filters:

- `cpu: "68000" | "68020"`: include only for the matching CPU build.
- `os:  "2.04" | "2.05" | "3.1" | "3.2.3"`: include only for the matching OS build.

Order in the `modules:` list = order of `add` directives in the rendered Capitoline script.

## Flashing

- **A1200**: two physical Kickstart chips. Flash `cfd.hi.bin` to the upper chip and `cfd.lo.bin` to the lower chip; the dual-EPROM word layout is already byteswapped for you.
- **A600 / A500+**: single 16-bit Kickstart ROM. Flash the merged 1 MB image `cfd.rom` to a 1 MB Kickstart adapter chip.

Use whatever EPROM / flash programmer you normally use; the builder produces standard binary images with no further wrapping.

## Deeper docs

- [docs/kickstart-scantable.md](docs/kickstart-scantable.md): how the 1 MB scantable redirect works across 3.2.3 / 3.1 / 2.0x and why each family uses a different mechanism.
- [docs/ROMS.md](docs/ROMS.md): resident-module inventory across source Kickstart ROM (2.0x / 3.0 / 3.1 / 3.2.y).

## Licensing and IP boundary

The MIT licence (`LICENSE`) covers the **builder itself**: the Python driver, the YAML config under `config/`, the Jinja templates under `templates/`, and the docs in this repo. Everything else lives outside the repo and carries its own licence:

- **Capitoline `capcli.Linux`** (from the [capitoline.twocatsblack.com](http://capitoline.twocatsblack.com/)). This builder doesn't ship `capcli.Linux` or the `Capitoline Hashes/` database, `kickstart.py` shells out to whatever you have downloaded at `/opt/Capitoline/`.
- **AmigaOS Kickstart ROMs and Workbench ADFs** (Hyperion 3.2.3, Commodore 3.1 / 2.05 / 2.04, etc.) are copyrighted by their respective owners. You must supply your own legally-obtained copies; the builder doesn't redistribute any ROM or ADF.
- **Output 1 MB ROM images** produced by this tool embed code from the source Kickstart ROM and ADFs and are therefore subject to *those* licences, typically not redistributable. Build your own; don't share the binaries.
- **cfd modules** (`compactflash.device`, `ptable.library`) are LGPL v2.1 from the [cfd project](https://github.com/pulchart/cfd). The builder reads them as plain files from `/opt/AmigaOS/cfd/<version>/full/...`.
- **fat95** (AmigaOS FAT filesystem handler) is LGPL v2.1 from the [fat95 project](https://github.com/pulchart/fat95). The builder reads it as a plain file from `/opt/AmigaOS/fat95/<version>/<cpu>/fat95`.
- **pfs3aio** is a third-party AmigaOS PFS3 filesystem handler (Professional-File-System-III, originally by Michiel Pelt / Peltin BV; AIO variant maintained at [tonioni/pfs3aio](https://github.com/tonioni/pfs3aio)). The builder reads it as a plain file from `/opt/AmigaOS/pfs/<version>/pfs3aio`. License: see the pfs3aio distribution; the builder doesn't bundle it.

If you fork or extend the builder, the MIT licence applies to your fork's source. The output ROMs your fork produces remain subject to the upstream Kickstart / ADF / filesystem-handler / cfd licences regardless.
