"""Independent check of the Dang 2025 build inputs against the source PDF.

The PDF is read with pypdf (project dependency) and its Tables 1-5 are
re-parsed from scratch; the result is compared string-for-string with the
printed cells, family markers and correlations in the build inputs. The two
paths share no parsing code with the builder, so a typo in an input file
cannot be masked by the same typo in the checker.
"""
from __future__ import annotations

import csv
import hashlib
import logging
import re
from pathlib import Path

from pypdf import PdfReader

_CELL = re.compile(r"(-?\d+\.?\d*)\s+(?:([a-c]{1,2})\s+)?±\s*(\d*\.?\d+)")
_MARK = re.compile(r"\*{1,3}|ns")
_CORR = re.compile(r"(−?\d+\.\d+)(?: (\*{1,2}))?")

SEASONS = ("2022-2023", "2023-2024")
SITES = ("D1", "D2", "D3")
ARMS = ("Control", "OM", "FF", "OM+FF")
VARIABLES = {
    "Table 1": ("ph", "soc", "ap", "k", "ca"),
    "Table 3": ("peel", "seed", "aril"),
    "Table 4": ("yield", "bstar", "tss", "pd"),
}
# Table 5 matrix: row variables, and the column variables in print order.
T5_ROWS = (("SOC", "soc"), ("AP", "available_p"), ("Ex. K+", "exchangeable_k"),
           ("Ex. Ca2+", "exchangeable_ca"), ("Leaf K", "leaf_k"),
           ("Leaf Ca", "leaf_ca"), ("Fruit yield", "fruit_yield"),
           ("PD rate", "pd_rate"))
T5_COLS = ("soil_ph",) + tuple(key for _, key in T5_ROWS)


def _printed(match: tuple[str, str, str]) -> str:
    value, letter, sd = match
    return f"{value}" + (f" {letter}" if letter else "") + f" ± {sd}"


def _section(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i:text.index(end, i + len(start))]


def _cells_and_markers(block: str) -> tuple[list[str], list[list[str]]]:
    cells, markers = [], []
    for line in block.splitlines():
        if line.startswith("p-value"):
            markers.append(_MARK.findall(line[len("p-value"):]))
        else:
            cells += [_printed(m) for m in _CELL.findall(line)]
    return cells, markers


def extract_printed(pdf_path: Path) -> dict[str, dict]:
    """Return {'cells', 'markers', 'corr'} keyed like the build inputs."""
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf_path).pages)
    text = text.replace("OM + FF", "OM+FF")
    cells: dict[tuple, str] = {}
    markers: dict[tuple, str] = {}

    # Tables 1, 3 and 4: strata of (site, season) rows; Table 2: per site.
    bounds = {"Table 1": ("Table 1. Mean values", "Table 2. Mean values"),
              "Table 2": ("Table 2. Mean values", "2.2. Fruit Yield"),
              "Table 3": ("Table 3. Mean values", "2.2.2. Fruit Yield"),
              "Table 4": ("Table 4. Mean values", "Table 5. Pearson")}
    for table, (start, end) in bounds.items():
        got, marks = _cells_and_markers(_section(text, start, end))
        if table == "Table 2":
            cols = [(y, v) for y in SEASONS for v in ("K", "Ca")]
            for si, site in enumerate(SITES):
                for ai, arm in enumerate(ARMS):
                    for ci, (season, var) in enumerate(cols):
                        index = si * 16 + ai * 4 + ci
                        cells[(table, site, season, arm, var)] = got[index]
                for ci, (season, var) in enumerate(cols):
                    markers[(table, site, season, var)] = marks[si][ci]
        elif table == "Table 3":
            cols = [(y, v) for y in SEASONS for v in VARIABLES[table]]
            for si, site in enumerate(SITES):
                for ai, arm in enumerate(ARMS):
                    for ci, (season, var) in enumerate(cols):
                        index = si * 24 + ai * 6 + ci
                        cells[(table, site, season, arm, var)] = got[index]
                for ci, (season, var) in enumerate(cols):
                    markers[(table, site, season, var)] = marks[si][ci]
        else:
            variables = VARIABLES[table]
            width = len(variables)
            strata = [(s, y) for s in SITES for y in SEASONS]
            for si, (site, season) in enumerate(strata):
                for ai, arm in enumerate(ARMS):
                    for vi, var in enumerate(variables):
                        cells[(table, site, season, arm, var)] = got[
                            si * 4 * width + ai * width + vi]
                for vi, var in enumerate(variables):
                    markers[(table, site, season, var)] = marks[si][vi]

    # Table 5: lower-triangular matrix, one printed row per variable.
    block = _section(text, "Table 5. Pearson", "SOC, soil organic carbon")
    block = block.replace("Fruit\nyield", "Fruit yield")
    corr: dict[tuple, str] = {}
    for ri, (label, row_key) in enumerate(T5_ROWS):
        line = next(l for l in block.splitlines()
                    if l.startswith(label + " ") and l.endswith(" " + label))
        body = line[len(label) + 1:-len(label) - 1]
        found = [m.group(0) for m in _CORR.finditer(body)]
        if len(found) != ri + 1:
            raise ValueError(f"Table 5 row {label!r}: expected {ri + 1} values")
        for ci, printed in enumerate(found):
            corr[(row_key, T5_COLS[ci])] = printed
    return {"cells": cells, "markers": markers, "corr": corr}


def read_inputs(input_dir: Path) -> dict[str, dict]:
    """The printed strings of the build inputs, keyed like extract_printed."""
    def rows(name):
        with (input_dir / name).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    return {
        "cells": {(r["table"], r["site"], r["season"], r["treatment"],
                   r["variable"]): r["printed"] for r in rows("cells.csv")},
        "markers": {(r["table"], r["site"], r["season"], r["variable"]):
                    r["marker"] for r in rows("markers.csv")},
        "corr": {(r["x"], r["y"]): r["printed"] for r in rows("table5.csv")},
    }


# A digest of the printed strings lets tests detect any drift between the
# inputs and the PDF extraction without the (untracked) PDF itself.
def printed_digest(printed: dict[str, dict]) -> dict[str, str]:
    out = {}
    for section in ("cells", "markers", "corr"):
        lines = sorted("|".join(k) + "\t" + v
                       for k, v in printed[section].items())
        data = "\n".join(lines).encode("utf-8")
        out[section] = f"{len(lines)} {hashlib.sha256(data).hexdigest()}"
    return out


def compare_inputs(input_dir: Path, extracted: dict[str, dict]) -> dict:
    """Compare build inputs with the PDF extraction; list every mismatch."""
    mine = read_inputs(input_dir)
    mismatches = []
    in_cells, in_marks, in_corr = mine["cells"], mine["markers"], mine["corr"]
    for label, mine, theirs in (("cell", in_cells, extracted["cells"]),
                                ("marker", in_marks, extracted["markers"]),
                                ("correlation", in_corr, extracted["corr"])):
        for key in sorted(set(mine) | set(theirs)):
            if mine.get(key) != theirs.get(key):
                mismatches.append(
                    f"{label} {key}: input={mine.get(key)!r} pdf={theirs.get(key)!r}")
    return {"cells": len(in_cells), "markers": len(in_marks),
            "correlations": len(in_corr), "mismatches": mismatches}
