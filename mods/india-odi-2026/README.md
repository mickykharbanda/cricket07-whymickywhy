# India ODI 2026 replacement trial (retired)

This prototype is retired: it renamed original India player records. The
requested expansion must preserve the OG team, clone modern players into
separate slots, and provide distinct kits. The launcher defaults to Original
teams and restores the unmodified database before launch.

The notes below document the earlier prototype, not a completed expansion.

Select **India ODI 2026 — roster trial** in the launcher, then **Play Solo**.
Choose India in the game. The dated 16-player squad is from BCCI's 16 October
2026 announcement for the first three New Zealand ODIs. Prasidh Krishna's
selection is subject to fitness. The starting XI is a game selection, not an
announced real match XI.

Source: https://www.bcci.tv/news/article/indias-odi-and-test-squads-for-new-zealand-tour-announced

## What this trial changes

- Names on 16 existing India player records.
- India's selected squad and captain (Shubman Gill).
- Four unused squad slots are empty.

## What it does not yet update

Original player models, kits, commentary, career statistics, abilities and
handedness remain donor placeholders. Some displayed roles will differ from
the actual players. This is a working roster-format proof, not a complete
2026 simulation or a modern graphics patch. Other teams referencing those
same India players can also display their updated names.

## Reversibility and saved games

The source `game/Data/data.gob` and executable stay untouched. Before launching,
a worker appends a 620 KB roster to the browser's cached archive and updates its
resource directory entry. Selecting **Original teams** restores the original
entry and truncates the added bytes before launch. India trial saves use their
own directory, separate from existing saves. Multiplayer is available with
Original teams so both players use the same game data.

The roster can be rebuilt with `python3 tools/build_india_odi_2026.py`.
`tools/big_archive.py` reads BIG archives and decodes RefPack resources.

## Storage recovery

Installation streams directly into OPFS in a worker, preserving partial files
for Range resume. On a storage-quota failure it drops only cached `.vp6`
intro/tutorial movies and finishes a compact install. Original on-disk movies
and all saved games remain intact. A compact install was verified to reach the
title, stadium and updated India squad screens on this Mac.
