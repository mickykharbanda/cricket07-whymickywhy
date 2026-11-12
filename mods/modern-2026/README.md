# Cricket 07: modern teams

Choose **OG + India 2026 + IPL teams** in the launcher, then **Play Solo**. On Team Select, assign the keyboard to a side with left/right, switch that side's category to **Other**, then use up/down to choose its team. The normal **International** category still contains OG India.

This pack repurposes eleven secondary slots:

| Original slot | Expanded mode |
| --- | --- |
| Australia A | India ODI 2026 |
| India A | Chennai Super Kings |
| Pakistan A | Delhi Capitals |
| South Africa A | Gujarat Titans |
| West Indies A | Kolkata Knight Riders |
| Chairman's XI | Lucknow Super Giants |
| B. President's XI | Mumbai Indians |
| Duke's XI | Punjab Kings |
| Governor's XI | Rajasthan Royals |
| Minister's XI | Royal Challengers Bengaluru |
| V. Chancellor's XI | Sunrisers Hyderabad |

The build verifies that 52 other original squads, and 943 protected original player records, remain byte-for-byte unchanged. Modern players have distinct IDs and may be shared between their national and franchise squads. Every side names 20 players, the engine's squad capacity, and the build refuses to write a squad that names fewer: a squad record holds twenty slots and the engine reads all of them, so a part-filled squad leaves slots that resolve to unrelated players. The India squad is also checked to be all-Indian, against the country recorded for each name in `sources/`. The full fetched IPL squads remain in `sources/`.

## Scope and sources

- India ODI selection: the sixteen named in [BCCI's 16 October 2026 New Zealand tour announcement](https://www.bcci.tv/news/article/indias-odi-and-test-squads-for-new-zealand-tour-announced), plus four standbys to fill the engine's twenty-player squad — Yashasvi Jaiswal, Washington Sundar, Ravi Bishnoi and Dhruv Jurel. All four are current India players, taken with their real roles and shirt numbers from the official IPL squad data in `sources/`; they are this pack's own choice of reserves, not part of the BCCI announcement.
- IPL selections, captains, jersey numbers, crests and shirt references: official [IPL team pages](https://www.iplt20.com/teams), fetched from each team's `api/bff/cms/teams/<slug>?tab=squad&season=2026` endpoint. Each saved response records its source URL and season.
- Uniforms are editable fan recreations based on those references: shirts/trousers, pads, keeper equipment, hats and helmets. These are not official downloadable game skins. Faces and abilities use generic/proxy game templates; these are not authentic face scans or official 2026 ratings. Historic career counters are cleared without clearing the packed ability fields.
- Original stadiums, animations and commentary remain. Commentary does not gain newly recorded player or team names. Existing tours referencing repurposed secondary slots will face the modern teams in expanded mode.

## Why there is no IPL competition

The modern teams can play each other from **Play Now**, and tours schedule them as warm-up
opponents, but no competition in the game can be made to field them. The team list each
competition offers is fixed inside the recompiled executable, not in this archive.

Tested rather than assumed: `StandardOfCricket` in `teaminfo.xml` is the category Play Now files
a team under (0 International, 1 Australian State, 2 English County, 3 Other). Setting all eleven
modern teams to 0 moved them into Play Now's **International** category exactly as expected — and
changed nothing in any tournament. Knockout Cup still offered the same sixteen national sides and
still took eight of them; the modern teams appeared in none of the tournament team selects. The
build keeps a per-team `standard` field in `team-plan.json` for this, defaulting to 3, which is
the shipped behaviour; setting it does not and cannot create an IPL competition.

An IPL season with a table and playoffs therefore needs a change to the engine itself
(`cricket07-public`), not to this pack.

## Reversibility and saves

Only the browser's cached archive is patched. Files under `game/` remain untouched. The worker verifies the downloaded payload and its stored bytes before changing archive pointers. Choosing **Original teams** restores all original pointers and archive length; it also brings back the secondary teams listed above. Online multiplayer uses Original teams.

Original and expanded modes have separate save folders. Use the game's native save menu; the launcher can back up and restore those save files. Instant emulator-style save states are not implemented.

## Rebuild and checks

Run `tools/build_modern_2026.py` from an environment with Pillow (DDS encoding) and CairoSVG. The script asserts the protected records and squads before writing the pack and manifest. Run `node --test tools/workers.test.cjs` for archive restoration, expansion upgrades, integrity rejection, resumable installation and quota-recovery checks.

Validated locally in Chrome: India ODI 2026 and Chennai Super Kings selectable together; a live match renders their separate blue/yellow kits, badges and modern player names. All ten worker checks passed. Switching back restored the original archive length (341,202,052 bytes) and the exact original directory/header SHA-256 (`4f38a391dccef3f479d45cf58fc95e1ef1b948eb687eaa7a0a82c613f7400bfd`). This is a match smoke test, not a full season/tournament compatibility test.
