#!/usr/bin/env python3
"""Append FFS files into the free space of an FFSv2 volume, in place."""
import argparse, struct, sys, uuid

FVH_SIG = b"_FVH"
ERASE_POLARITY = 0x800


def align8(x):
    return (x + 7) & ~7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("vol_offset", type=lambda x: int(x, 0))
    ap.add_argument("ffs", nargs="+")
    ap.add_argument("-o", "--output", required=True)
    a = ap.parse_args()

    img = bytearray(open(a.image, "rb").read())
    v = a.vol_offset
    if img[v + 40:v + 44] != FVH_SIG:
        sys.exit("no _FVH signature at 0x%x" % v)
    vlen, = struct.unpack_from("<Q", img, v + 32)
    attr, hlen, _, ext = struct.unpack_from("<IHHH", img, v + 44)
    polarity = bool(attr & ERASE_POLARITY)
    if not polarity:
        sys.exit("volume erase polarity is 0; script expects 1")
    vend = v + vlen
    start = v + hlen
    if ext:
        ext_size, = struct.unpack_from("<I", img, v + ext + 16)
        start = v + ext + ext_size
    off = align8(start - v) + v
    print("volume 0x%x len 0x%x attr 0x%08x hdrlen 0x%x" % (v, vlen, attr, hlen))

    # Walk the FFS file chain.
    last = None
    while off + 24 <= vend:
        if img[off:off + 24] == b"\xff" * 24:
            break
        size = int.from_bytes(img[off + 20:off + 23], "little")
        if size < 24 or size == 0xFFFFFF or off + size > vend:
            sys.exit("bad file header at 0x%x" % off)
        last = (off, size, uuid.UUID(bytes_le=bytes(img[off:off + 16])))
        off = v + align8(off + size - v)
    free = off
    if img[free:vend] != b"\xff" * (vend - free):
        sys.exit("data after 0x%x is not all 0xFF" % free)
    print("last file %s at 0x%x size 0x%x" % (str(last[2]).upper(), last[0], last[1]))
    print("free space 0x%x..0x%x (0x%x bytes)" % (free, vend, vend - free))

    pos = free
    for f in a.ffs:
        data = bytearray(open(f, "rb").read())
        size = int.from_bytes(data[20:23], "little")
        if size != len(data):
            sys.exit("%s: size field 0x%x != file length 0x%x" % (f, size, len(data)))
        # State byte is excluded from both checksums; match volume polarity.
        if polarity and not data[23] & 0x80:
            print("%s: state 0x%02x -> 0x%02x for erase polarity 1"
                  % (f, data[23], data[23] ^ 0xFF))
            data[23] ^= 0xFF
        pos = v + align8(pos - v)
        end = pos + len(data)
        if end > vend:
            sys.exit("%s does not fit" % f)
        if img[pos:end] != b"\xff" * len(data):
            sys.exit("target region 0x%x..0x%x not erased" % (pos, end))
        img[pos:end] = data
        print("wrote %s (%s) at 0x%x..0x%x" % (
            f, str(uuid.UUID(bytes_le=bytes(data[:16]))).upper(), pos, end))
        pos = end
    print("inserted range 0x%x..0x%x (0x%x bytes); free left 0x%x"
          % (free, pos, pos - free, vend - v - align8(pos - v)))
    open(a.output, "wb").write(img)


if __name__ == "__main__":
    main()
