#!/usr/bin/env python3
"""Write a trained network for medley/nnplayer.lisp: big-endian 32-bit floats, row by row.

    python3 selfplay/export_lisp.py out/selfplay/a/best.json dist/HEARTSNET

Order: layer 1 rows then biases (256 x 512, 256), layer 2 (256 x 256, 256), policy (52 x 256, 52).
"""
import json
import struct
import sys


def main(source, target):
    with open(source, encoding="utf-8") as f:
        model = json.load(f)
    shapes = [(256, 512), (256, 256), (52, 256)]
    with open(target, "wb") as out:
        for (weights, bias), (rows, columns) in zip(model["hidden"] + [model["policy"]], shapes):
            assert len(weights) == rows and all(len(r) == columns for r in weights) and len(bias) == rows
            for row in weights:
                out.write(struct.pack(f">{columns}f", *row))
            out.write(struct.pack(f">{rows}f", *bias))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
