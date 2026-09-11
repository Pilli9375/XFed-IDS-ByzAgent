"""
XFed-IDS -- shared raw-label -> family mapping.

Lives in its own module because BOTH clean.py and families.py need it, and
because the order matters: family assignment must happen BEFORE duplicate and
label-conflict detection.

Why: the model's target is the family, not the raw label. Two raw labels that
map to the same family are not in conflict with each other. Detecting
conflicts on raw labels discards rows that are perfectly learnable at the
granularity we actually train on. (Found empirically in Chat 02: 58,307
"Infiltration - Portscan | Portscan" rows were being dropped despite both
labels mapping to PortScan.)
"""

from __future__ import annotations

import pandas as pd


def build_label_to_family(family_map: dict[str, list[str]]) -> dict[str, str]:
    """Invert the config's family -> [raw labels] into raw label -> family."""
    lookup: dict[str, str] = {}
    for family, raw_labels in family_map.items():
        for raw in raw_labels:
            if raw in lookup:
                raise ValueError(
                    f"Raw label {raw!r} is mapped to two families in config "
                    f"({lookup[raw]!r} and {family!r})"
                )
            lookup[raw] = family
    return lookup


def assign_families(
    df: pd.DataFrame, label_col: str, family_map: dict[str, list[str]]
) -> pd.Series:
    """
    Map raw labels to families, raising if any observed label is unmapped.

    Fails loudly rather than producing a silent NaN family -- an unmapped label
    on a future rerun would otherwise propagate into training as a missing
    class and be very hard to trace back.
    """
    lookup = build_label_to_family(family_map)
    unmapped = set(df[label_col].unique()) - set(lookup)
    if unmapped:
        raise ValueError(
            f"{len(unmapped)} raw label(s) in the data have no entry in "
            f"family_map: {sorted(unmapped)}. Update configs/data.yaml -- "
            f"do not guess a mapping here."
        )
    return df[label_col].map(lookup)
