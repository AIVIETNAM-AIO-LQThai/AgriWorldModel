"""Record-level before/after diff of two compiled-study JSON files.

    python research/scripts/diff_compiled_study.py OLD.json NEW.json OUT.md

Records are matched by their identifier, so reordering is reported
separately from content changes. Output is Markdown with exact counts.
"""
import json
import sys
from collections import Counter
from pathlib import Path

KEYS = {
    "sites": "site_id", "interventions": "intervention_id", "arms": "arm_id",
    "outcomes": "outcome_id", "arm_results": "record_id",
    "comparison_families": "record_id", "contrasts": "record_id",
    "associations": "record_id", "interpretations": "record_id",
    "recommendations": "record_id", "flags": "record_id",
}


def short(value, limit=150):
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def diff_section(name, old, new):
    key = KEYS[name]
    old_by, new_by = {r[key]: r for r in old}, {r[key]: r for r in new}
    added = [i for i in new_by if i not in old_by]
    removed = [i for i in old_by if i not in new_by]
    common = [i for i in old_by if i in new_by]
    changed, fields, samples = [], Counter(), {}
    for rid in common:
        a, b = old_by[rid], new_by[rid]
        delta = [f for f in sorted(set(a) | set(b)) if a.get(f) != b.get(f)]
        if delta:
            changed.append(rid)
            for f in delta:
                fields[f] += 1
                samples.setdefault(f, (rid, a.get(f), b.get(f)))
    reordered = [i for i in common] != [i for i in new_by if i in old_by]
    return {"old": len(old), "new": len(new), "added": added,
            "removed": removed, "unchanged": len(common) - len(changed),
            "changed": changed, "fields": fields, "samples": samples,
            "reordered": reordered}


def main() -> int:
    old = json.loads(Path(sys.argv[1]).read_text("utf-8"))
    new = json.loads(Path(sys.argv[2]).read_text("utf-8"))
    out = ["# Dang 2025 compiled study: before/after record diff", "",
           (f"Old: `{Path(sys.argv[1]).name}` (schema "
            f"`{old['schema_version']}`). New: `{Path(sys.argv[2]).name}` "
            f"(schema `{new['schema_version']}`)."),
           ("Records are matched by identifier; `reordered` means the common "
            "records appear in a different order."), "",
           "| Section | Old | New | Added | Removed | Unchanged | Changed | Reordered |",
           "|---|---:|---:|---:|---:|---:|---:|---|"]
    details = []
    for name in KEYS:
        d = diff_section(name, old.get(name, []), new.get(name, []))
        reordered = "yes" if d["reordered"] else "no"
        out.append(f"| {name} | {d['old']} | {d['new']} | {len(d['added'])} | "
                   f"{len(d['removed'])} | {d['unchanged']} | "
                   f"{len(d['changed'])} | {reordered} |")
        if d["changed"] or d["added"] or d["removed"]:
            block = [f"### {name}", ""]
            if d["removed"]:
                block.append(f"- removed ids: {', '.join(d['removed'][:10])}")
            if d["added"]:
                block.append(f"- added: {len(d['added'])} records, e.g. "
                             f"`{d['added'][0]}` ... `{d['added'][-1]}`")
            for field, count in d["fields"].most_common():
                rid, before, after = d["samples"][field]
                block += [(f"- field `{field}` changed in {count} records "
                           f"(example `{rid}`):"),
                          f"  - before: `{short(before)}`",
                          f"  - after: `{short(after)}`"]
            details.append("\n".join(block))
    top = [k for k in sorted(set(old) | set(new))
           if k not in KEYS and old.get(k) != new.get(k)]
    out += ["", "## Changed or added records", ""] + [s + "\n" for s in details]
    out += ["## Other top-level fields that differ", ""]
    for k in top:
        out += [f"- `{k}`", f"  - before: `{short(old.get(k))}`",
                f"  - after: `{short(new.get(k))}`"]
    Path(sys.argv[3]).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {sys.argv[3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
