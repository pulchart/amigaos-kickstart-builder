"""Bank order of the merged ROM: address mapping and resident scan follow `e0_first`."""

from __future__ import annotations

import struct

from kickstart.residents import _rom_addr_to_offset, _rom_offset_to_addr, scan_residents

_HALF = 0x80000


def _rom_with_resident(offset: int, addr: int) -> bytes:
    """1 MB blank ROM with one resident at *offset* whose self-pointer is *addr*."""
    data = bytearray(b"\xff" * (2 * _HALF))
    struct.pack_into(">HI", data, offset, 0x4AFC, addr)
    return bytes(data)


def test_default_order_maps_f8_first():
    assert _rom_offset_to_addr(0) == 0xF80000
    assert _rom_offset_to_addr(_HALF) == 0xE00000
    assert _rom_addr_to_offset(0xE00010) == _HALF + 0x10


def test_e0_first_order_maps_e0_first():
    assert _rom_offset_to_addr(0, e0_first=True) == 0xE00000
    assert _rom_offset_to_addr(_HALF, e0_first=True) == 0xF80000
    assert _rom_addr_to_offset(0xF80010, e0_first=True) == _HALF + 0x10


def test_scan_follows_bank_order(tmp_path):
    rom = tmp_path / "x.rom"
    rom.write_bytes(_rom_with_resident(0x100, 0xE00100))
    assert [r["bank"] for r in scan_residents(rom, e0_first=True)] == ["E0"]
    assert scan_residents(rom) == []
