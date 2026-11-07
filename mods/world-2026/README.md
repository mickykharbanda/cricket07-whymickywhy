# Cricket 07: 2026 Teams (NEW)

Pick **2026 Teams** in the launcher (or the **Cricket 07 · 2026** tile in the app), then **Play Solo**.
On Team Select the nations are in **International**. Click the arrows beside the category name to
reach **Other**, where the IPL sides and the five dream XIs live.

## What's in it

| Slot (original) | 2026 Teams |
| --- | --- |
| India, Australia, England, New Zealand, South Africa, Pakistan, Sri Lanka, West Indies, Bangladesh, Zimbabwe | Each nation's latest 2026 ODI + T20I squad (up to 20, the engine's limit) |
| Kenya | Afghanistan |
| Ireland, Scotland, Netherlands, United States, Namibia, Canada | 2026 squads |
| Bermuda | Nepal |
| Australia A | **World XI 2026**: Rohit, Kohli, Gill, Head, Babar, Root, Brook, Smith, Buttler, de Kock, Rachin, Hardik, Jansen, Rashid, Bumrah, Cummins, Starc, Rabada, Shaheen, Kuldeep |
| Masters XI | **OG World XI**: Sachin, Ponting, AB de Villiers, MS Dhoni (c), Lara, Gilchrist, Kallis, Hayden, Gayle, Sehwag, Jayasuriya, Sangakkara, Watson, Flintoff, Warne, Muralitharan, McGrath, Brett Lee, Steyn, Malinga |
| World Test XI | **All-Time Test XI**: Hayden, Sehwag, Dravid, Sachin, **Brian Lara**, Ponting (c), Kallis, Sangakkara, Gilchrist, Warne, Muralitharan, McGrath, Steyn, Anderson, Kumble, Kohli, Root, Smith, Williamson, Bumrah |
| World One Day XI | **All-Time ODI XI**: Sachin, Rohit, Kohli, Gilchrist, Ponting (c), AB de Villiers, Dhoni, Kallis, Jayasuriya, Gayle, Sangakkara, Bevan, Shahid Afridi, Muralitharan, McGrath, Brett Lee, Malinga, Warne, Starc, Bumrah |
| Scottish Saltires | **All-Time T20 XI**: Rohit (c), Kohli, Gayle, Buttler, Suryakumar, Warner, AB de Villiers, Maxwell, Hardik, Russell, Pollard, Bravo, Yuvraj, Dhoni, Shahid Afridi, Rashid, Narine, Bumrah, Malinga, Shaheen |
| India A … V. Chancellor's XI | The ten IPL 2026 sides, as in the OG + IPL pack |

Every other original squad (counties, states, provinces, associates not listed) is verified
byte-for-byte unchanged by the builder.

**Legends use their original Cricket 07 records**, so Sachin, Lara, Dhoni, Malinga and the rest
play with the abilities EA gave them, under their real names (the 2006 game shipped unlicensed
spellings such as "S.Tendehar").

**2026 players** copy an original record of the same role, batting hand and bowling type, picked
from a pool for their region. Stars get an elite donor (Kohli and Gill bat on Tendulkar's record,
Bumrah bowls on Akhtar's, Cummins on McGrath's, Rashid on Kumble's). Zimbabwe and the associates
draw from 2006 county/state players, so their team ratings sit below the Test nations'. Career
statistics are reset. These are playable stand-ins, not official 2026 ratings or face scans.

**Kits and badges** are fan-made in each side's 2026 colours, with original roundel badges in
those colours. They are not the boards' trademarked crests or official game skins. The IPL
crests carry over from the OG + IPL pack. Commentary, stadiums and animations are the originals.

## Sources (squads current to 7 Nov 2026)

`team-plan.json` records the source of each squad. In short:

- India: BCCI ODI squad for New Zealand (16 Oct 2026) and T20I squad (6 Oct 2026).
- Australia: Cricket Australia ODI and T20I squads for England (2 Nov 2026).
- England: ECB ODI and T20I squads for Australia (13 Oct 2026).
- New Zealand: ODI squads v India (ICC, 5 Nov 2026).
- Bangladesh: ODI tri-series squad (10 Oct 2026); Asian Games T20 squad (2 Sep 2026).
- Afghanistan: multi-format squads (ICC, 1 Oct 2026). Zimbabwe: UAE tour squads (ICC, 9 Oct 2026).
- Ireland: Namibia ODI tour (Oct 2026). Sri Lanka: T20I squad v Pakistan (2 Oct 2026).
- All sides: 2026 Men's T20 World Cup squads.
- **South Africa, Pakistan, West Indies, and the Sri Lanka ODI picks** use the T20 World Cup 2026
  squad plus established 2026 ODI regulars, because no newer white-ball announcement could be
  reached. Check these first if a board names a new squad.

## Rebuild

```sh
python3 mod-tools/build_world_2026.py    # needs game/Data/data.gob, Pillow and CairoSVG
node --test mod-tools/workers.test.cjs
```

Edit `team-plan.json` to change a squad: `"Name|role,bat,bowl[,*][,region]"`, or
`"og:<original name>=<display name>"` to use a 2006 record. The pack installs into the browser's
cached copy only, and switching to another roster restores the original archive first.
