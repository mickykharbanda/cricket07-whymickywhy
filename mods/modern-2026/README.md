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

The build verifies that 52 other original squads, and 943 protected original player records, remain byte-for-byte unchanged. Modern players have distinct IDs and may be shared between their national and franchise squads. India has 16 players; each IPL side has 20 selected players, the engine's squad capacity. The full fetched IPL squads remain in `sources/`.

## Scope and sources

- India ODI selection: [BCCI's 16 October 2026 New Zealand tour announcement](https://www.bcci.tv/news/article/indias-odi-and-test-squads-for-new-zealand-tour-announced).
- IPL selections, captains, jersey numbers, crests and shirt references: official [IPL team pages](https://www.iplt20.com/teams), fetched from each team's `api/bff/cms/teams/<slug>?tab=squad&season=2026` endpoint. Each saved response records its source URL and season.
- Uniforms are editable fan recreations based on those references: shirts/trousers, pads, keeper equipment, hats and helmets. These are not official downloadable game skins. Faces and abilities use generic/proxy game templates; these are not authentic face scans or official 2026 ratings. Historic career counters are cleared without clearing the packed ability fields.
- Original stadiums, animations and commentary remain. Commentary does not gain newly recorded player or team names. Existing tours referencing repurposed secondary slots will face the modern teams in expanded mode.

## Reversibility and saves

Only the browser's cached archive is patched. Files under `game/` remain untouched. The worker verifies the downloaded payload and its stored bytes before changing archive pointers. Choosing **Original teams** restores all original pointers and archive length; it also brings back the secondary teams listed above. Online multiplayer uses Original teams.

Original and expanded modes have separate save folders. Use the game's native save menu; the launcher can back up and restore those save files. Instant emulator-style save states are not implemented.

## Rebuild and checks

Run `tools/build_modern_2026.py` from an environment with Pillow (DDS encoding) and CairoSVG. The script asserts the protected records and squads before writing the pack and manifest. Run `node --test tools/workers.test.cjs` for archive restoration, expansion upgrades, integrity rejection, resumable installation and quota-recovery checks.

Validated locally in Chrome: India ODI 2026 and Chennai Super Kings selectable together; a live match renders their separate blue/yellow kits, badges and modern player names. All ten worker checks passed. Switching back restored the original archive length (341,202,052 bytes) and the exact original directory/header SHA-256 (`4f38a391dccef3f479d45cf58fc95e1ef1b948eb687eaa7a0a82c613f7400bfd`). This is a match smoke test, not a full season/tournament compatibility test.
