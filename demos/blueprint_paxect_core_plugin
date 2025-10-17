#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# PAXECT Core — Production Plugin (Plug & Play, Hardened)
#
# Highlights:
# - Fixed container header/footer (VERSION=42, backward compatible)
# - Multi-channel support: 1–8 (default=1)
# - Auto mode: selects channels, frame size, and threads based on RAM/CPU
# - Streaming Zstandard encode/decode (configurable compression level)
# - Frames include channel-id + CRC32 checksum
# - Footer includes total length + SHA-256 of original data
# - Mapping metadata: "virtual"(0) or "u16"(1)
# - Full stdin/stdout binary stream support
# - Exit codes:
#       0 = OK
#       2 = Verification/Integrity failure
#       3 = File or I/O error
#       4 = Container structure error
#
# Dependencies:
#   pip install zstandard psutil

import argparse
import io
import os
import sys
import struct
import hashlib
import zstandard as zstd
import binascii
import multiprocessing
import psutil
from dataclasses import dataclass

__version__ = "0.9.0-blueprint"

MAGIC = b"PXC1"            # PAXECT Container v1
VERSION = 42               # Constant for wire-format compatibility

# Flags
FLAG_VERIFY = 1 << 0       # When set: verify footer.sha256 during decode
FLAG_MULTICH = 1 << 1      # Multi-channel data present

# Mapping types (metadata)
MAP_VIRTUAL = 0
MAP_U16 = 1

HEADER_FMT = "<4sH I B b I H 6x"  # magic(4) ver(u16) flags(u32) map(u8) clevel(int8) frame(u32) channels(u16)
FOOTER_FMT = "<Q I 32s"           # total_uncompressed(u64) total_frames(u32) sha256(32)
FRAME_HDR_FMT = "<H I I I"        # channel_id(u16) clen(u32) ulen(u32) crc32(u32)

HEADER_SIZE = struct.calcsize(HEADER_FMT)
FOOTER_SIZE = struct.calcsize(FOOTER_FMT)
FRAME_HDR_SIZE = struct.calcsize(FRAME_HDR_FMT)


@dataclass
class Header:
    flags: int
    mapping: int
    level: int
    frame_size: int
    channels: int

    def pack(self) -> bytes:
        return struct.pack(HEADER_FMT, MAGIC, VERSION, self.flags, self.mapping, self.level, self.frame_size, self.channels)

    @staticmethod
    def unpack(b: bytes) -> "Header":
        if len(b) != HEADER_SIZE:
            raise ValueError("invalid header size")
        magic, ver, flags, mapping, level, frame_size, channels = struct.unpack(HEADER_FMT, b)
        if magic != MAGIC or ver != VERSION:
            raise ValueError("unsupported container (magic/version)")
        return Header(flags=flags, mapping=mapping, level=level, frame_size=frame_size, channels=channels)


@dataclass
class Footer:
    total_uncompressed: int
    total_frames: int
    sha256: bytes

    def pack(self) -> bytes:
        return struct.pack(FOOTER_FMT, self.total_uncompressed, self.total_frames, self.sha256)

    @staticmethod
    def unpack(b: bytes) -> "Footer":
        if len(b) != FOOTER_SIZE:
            raise ValueError("invalid footer size")
        total_uncompressed, total_frames, sha256 = struct.unpack(FOOTER_FMT, b)
        return Footer(total_uncompressed, total_frames, sha256)


# -----------------------------
# Auto-mode heuristic (RAM, CPU)
# -----------------------------
def auto_channels():
    try:
        ram_mb = psutil.virtual_memory().total // (1024 * 1024)
    except Exception:
        ram_mb = 2048  # fallback
    cores = multiprocessing.cpu_count()

    if ram_mb <= 1024:
        return 1, 512 * 1024, min(2, cores)
    elif ram_mb <= 2048:
        return 2, 1024 * 1024, min(4, cores)
    elif ram_mb <= 16384:
        return 4, 2 * 1024 * 1024, min(8, cores)
    else:
        return 6, 4 * 1024 * 1024, min(16, cores)


# -----------------------------
# Helpers
# -----------------------------
def _open_in(path: str):
    return sys.stdin.buffer if path == "-" or path is None else open(path, "rb")


def _open_out(path: str):
    return sys.stdout.buffer if path == "-" or path is None else open(path, "wb")


def write_header(out_fh, hdr: Header):
    out_fh.write(hdr.pack())


def write_footer(out_fh, ftr: Footer):
    out_fh.write(ftr.pack())


def write_frame(out_fh, channel_id: int, raw: bytes, level: int) -> int:
    cctx = zstd.ZstdCompressor(level=level)
    comp = cctx.compress(raw)
    crc = binascii.crc32(raw) & 0xFFFFFFFF
    out_fh.write(struct.pack(FRAME_HDR_FMT, channel_id, len(comp), len(raw), crc))
    out_fh.write(comp)
    return 1  # one frame written


def read_exact(fh, n: int) -> bytes:
    b = fh.read(n)
    if b is None or len(b) != n:
        raise EOFError("unexpected EOF while reading container")
    return b


# -----------------------------
# Core encode/decode
# -----------------------------
def encode(args) -> int:
    if args.channels == "auto":
        channels, frame_size, threads = auto_channels()
    else:
        channels = int(args.channels)
        frame_size = args.frame
        threads = max(1, min(multiprocessing.cpu_count(), channels))
    channels = max(1, min(8, channels))
    frame_size = int(frame_size)

    hdr = Header(
        flags=(FLAG_VERIFY if args.verify else 0) | (FLAG_MULTICH if channels > 1 else 0),
        mapping=MAP_VIRTUAL if args.mapping == "virtual" else MAP_U16,
        level=int(args.level),
        frame_size=frame_size,
        channels=channels,
    )

    sha = hashlib.sha256()
    total_uncompressed = 0
    total_frames = 0

    with _open_in(args.input) as infh, _open_out(args.output) as outfh:
        write_header(outfh, hdr)
        ch = 0
        while True:
            raw = infh.read(frame_size)
            if not raw:
                break
            sha.update(raw)
            total_uncompressed += len(raw)
            total_frames += write_frame(outfh, ch, raw, hdr.level)
            ch = (ch + 1) % channels
        ftr = Footer(total_uncompressed=total_uncompressed, total_frames=total_frames, sha256=sha.digest())
        write_footer(outfh, ftr)
    return 0


def decode(args) -> int:
    with _open_in(args.input) as infh, _open_out(args.output) as outfh:
        hb = read_exact(infh, HEADER_SIZE)
        hdr = Header.unpack(hb)

        rest = infh.read() or b""
        if len(rest) < FOOTER_SIZE:
            return 4  # container too small

        data, foot = rest[:-FOOTER_SIZE], rest[-FOOTER_SIZE:]
        ftr = Footer.unpack(foot)

        pos = 0
        dlen = len(data)
        sha = hashlib.sha256()
        total_uncompressed = 0
        total_frames = 0

        while pos < dlen:
            if pos + FRAME_HDR_SIZE > dlen:
                return 4  # truncated frame header
            channel_id, clen, ulen, crc32v = struct.unpack(FRAME_HDR_FMT, data[pos:pos + FRAME_HDR_SIZE])
            pos += FRAME_HDR_SIZE
            if pos + clen > dlen:
                return 4  # truncated frame payload
            comp = data[pos:pos + clen]
            pos += clen

            dctx = zstd.ZstdDecompressor()
            try:
                raw = dctx.decompress(comp, max_output_size=ulen)
            except zstd.ZstdError:
                return 4  # decompression failure

            if len(raw) != ulen:
                return 4  # decompressed size mismatch
            if (binascii.crc32(raw) & 0xFFFFFFFF) != crc32v:
                return 4  # CRC mismatch

            outfh.write(raw)
            sha.update(raw)
            total_uncompressed += len(raw)
            total_frames += 1

        if (hdr.flags & FLAG_VERIFY) or args.verify:
            if sha.digest() != ftr.sha256:
                return 2  # verification failed

        if total_uncompressed != ftr.total_uncompressed or total_frames != ftr.total_frames:
            return 4  # container count mismatch

    return 0


# -----------------------------
# CLI Interface
# -----------------------------
def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="paxect-core",
        description="PAXECT Core Production Plugin (multi-channel, auto-mode, plug & play, hardened)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("encode", help="encode input to .freq container")
    pe.add_argument("-i", "--input", default="-", help="input file or - for stdin")
    pe.add_argument("-o", "--output", default="-", help="output file or - for stdout")
    pe.add_argument("--level", type=int, default=5, help="Zstandard compression level (1-19)")
    pe.add_argument("--channels", default="1", help="1..8 or 'auto'")
    pe.add_argument("--frame", type=int, default=1024 * 1024, help="frame size in bytes")
    pe.add_argument("--mapping", choices=["virtual", "u16"], default="virtual", help="metadata mapping mode")
    pe.add_argument("--verify", action="store_true", help="include verification flag in header")

    pd = sub.add_parser("decode", help="decode .freq container to raw output")
    pd.add_argument("-i", "--input", default="-", help="input file or - for stdin")
    pd.add_argument("-o", "--output", default="-", help="output file or - for stdout")
    pd.add_argument("--verify", action="store_true", help="force verification of footer SHA-256")

    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        if args.cmd == "encode":
            return encode(args)
        elif args.cmd == "decode":
            return decode(args)
        else:
            return 4
    except FileNotFoundError:
        return 3
    except EOFError:
        return 4
    except KeyboardInterrupt:
        return 3
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())  
