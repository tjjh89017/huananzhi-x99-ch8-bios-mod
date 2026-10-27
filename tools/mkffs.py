#!/usr/bin/env python3
"""Build or check an FFSv2 file (PE32 + UI sections)."""
import argparse, struct, sys, uuid

FFS_ATTRIB_CHECKSUM = 0x40
SEC_PE32, SEC_UI = 0x10, 0x15


def sum8(b):
    return sum(b) & 0xFF


def section(sec_type, payload):
    size = 4 + len(payload)
    if size > 0xFFFFFF:
        sys.exit("section too large")
    return size.to_bytes(3, "little") + bytes([sec_type]) + payload


def align4(b):
    return b + b"\x00" * (-len(b) % 4)


def build(guid, ftype, attrib, state, sections):
    data = b""
    for i, s in enumerate(sections):
        if i:
            data = align4(data)
        data += s
    size = 24 + len(data)
    if size > 0xFFFFFF:
        sys.exit("file too large")
    hdr = bytearray(guid.bytes_le + b"\x00\x00" + bytes([ftype, attrib])
                    + size.to_bytes(3, "little") + b"\x00")
    hdr[16] = (-sum8(hdr)) & 0xFF
    hdr[17] = (-sum8(data)) & 0xFF if attrib & FFS_ATTRIB_CHECKSUM else 0xAA
    hdr[23] = state
    return bytes(hdr) + data


def parse(ffs):
    """Return a dict with header fields, checksum results and sections."""
    guid = uuid.UUID(bytes_le=ffs[:16])
    hchk, fchk, ftype, attrib = ffs[16:20]
    size = int.from_bytes(ffs[20:23], "little")
    state = ffs[23]
    h = bytearray(ffs[:24]); h[17] = 0; h[23] = 0
    data = ffs[24:size]
    if attrib & FFS_ATTRIB_CHECKSUM:
        fok = sum8(data + bytes([fchk])) == 0
    else:
        fok = fchk == 0xAA
    secs, off = [], 0
    while off + 4 <= len(data):
        ssz = int.from_bytes(data[off:off + 3], "little")
        if ssz < 4 or off + ssz > len(data):
            raise ValueError("bad section at 0x%x" % off)
        secs.append((data[off + 3], off, ssz))
        off += ssz
        off += -off % 4
    return dict(guid=guid, type=ftype, attrib=attrib, size=size, state=state,
                header_ok=sum8(h) == 0, file_ok=fok, sections=secs,
                size_ok=size == len(ffs))


def show(name, ffs):
    p = parse(ffs)
    print("%s: guid=%s type=0x%02x attrib=0x%02x size=0x%x state=0x%02x "
          "header_ok=%s file_ok=%s size_ok=%s" % (
              name, str(p["guid"]).upper(), p["type"], p["attrib"], p["size"],
              p["state"], p["header_ok"], p["file_ok"], p["size_ok"]))
    for t, o, s in p["sections"]:
        print("  section type=0x%02x off=0x%x size=0x%x" % (t, o, s))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", nargs="+", help="parse FFS files and verify")
    ap.add_argument("--template", help="FFS file to copy Attributes/State from")
    ap.add_argument("--pe")
    ap.add_argument("--name")
    ap.add_argument("--guid", help="file GUID; random v4 if omitted")
    ap.add_argument("--state", type=lambda x: int(x, 0),
                    help="override State byte (0xF8 for erase polarity 1)")
    ap.add_argument("-o", "--output")
    a = ap.parse_args()

    if a.check:
        bad = 0
        for f in a.check:
            p = show(f, open(f, "rb").read())
            bad += not (p["header_ok"] and p["file_ok"] and p["size_ok"])
        sys.exit(1 if bad else 0)

    tpl = parse(open(a.template, "rb").read())
    state = tpl["state"] if a.state is None else a.state
    guid = uuid.UUID(a.guid) if a.guid else uuid.uuid4()
    pe = open(a.pe, "rb").read()
    if pe[:2] != b"MZ":
        sys.exit("not a PE file")
    ui = (a.name + "\x00").encode("utf-16-le")
    ffs = build(guid, 0x07, tpl["attrib"], state,
                [section(SEC_PE32, pe), section(SEC_UI, ui)])
    open(a.output, "wb").write(ffs)
    print("GUID:", str(guid).upper())
    show(a.output, ffs)


if __name__ == "__main__":
    main()
