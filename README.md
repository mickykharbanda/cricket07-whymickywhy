# Cricket 07 — The Micky Edit

A personal landing page, playable browser shell, source download and AI customization kit by Karan Singh, also known online as Micky. Instagram: [@whymickywhy](https://www.instagram.com/whymickywhy/). X: [@mickykharbanda](https://x.com/mickykharbanda). Work: [Clearlyy](https://clearlyy.io). LinkedIn: [Karan Singh](https://www.linkedin.com/in/karansinghworks).

This extends [Dhaiwat Pandya's Cricket 07 browser port](https://github.com/Dhaiwat10/cricket07-browser). The complete upstream source is retained in `engine/`, including its build instructions, licenses and contributor credits. The original browser port and recompilation are not Micky's original work. The additions here are the modern squad/kit pack, browser save-file tools, installation fixes, personal page and customization prompts.

## What's here

- `site/`: responsive landing page and browser launcher. The public launcher downloads hosted game resources automatically into OPFS browser storage, using resumable, SHA-256 verified chunks.
- `engine/`: the upstream translator, host, runtime and build tools, pinned by the included source snapshot.
- `mods/modern-2026/`: eleven teams, 200 distinct player records, native-resource manifest, fan kit sources and official squad-reference snapshots.
- `mods/world-2026/` (**NEW**): the 2026 Teams roster. Every nation's latest ODI/T20I squad, the ten IPL sides, World XI 2026 and the OG World, All-Time Test, ODI and T20 XIs. Built by `mod-tools/build_world_2026.py`; see its README.
- `mod-tools/`: archive/texture helpers and roster builder. The builder reads `game/Data/data.gob` from your own copy. Python dependencies: Pillow (DDS encoding), CairoSVG and a working Cairo library.
- `tools/`: publication packaging and local serving.
- `content/`: copyable prompts and local-play instructions.

Original EA executables, Data/Audio archives, generated game C code and compiled WebAssembly are not included in the source repository or source ZIP. The separately hosted browser-build ZIP includes the prebuilt runtime, mod resources and the explicitly requested game EXE in a separate `game-executable/` folder. The same EXE is available as its own download. The browser downloads matching resources automatically from the hosted edition. The standalone Windows EXE still needs its matching Data/Audio folders. The supplied file is the compatible unprotected build used by this project, not a claim of a signed retail installer. Do not mistake the upstream MIT license for a license to redistribute EA's commercial game assets or team/player trademarks.

## Play

Use a desktop/laptop with keyboard/controller and a WebGPU-capable browser. Game files download automatically on first launch (about 1.17 GB), resume after interruptions and remain cached in that browser. No folder picker is required. The launcher offers three rosters: **2026 Teams** (new, the default), **OG + IPL** and **Original**. In 2026 Teams the nations are in **International**, and the IPL sides and dream XIs are in **Other**. In OG + IPL, India ODI 2026 and the IPL teams are in **Other**. Eleven A-team/invitational slots are repurposed in expanded mode; Original teams restores every secondary side too.

Native save files are retained locally with backup/restore controls. There is no instant save-state system or new save-anywhere feature. The public edition is solo/local play; upstream multiplayer requires deploying its own room service. Do not expose the local tunnel server or proxy someone else's assets or signaling endpoint as a substitute.

## Build the site

First build a compatible browser runtime from your own game executable by following `engine/README.md`. Then:

```sh
python3 tools/build_site.py --runtime /path/to/compiled/build --game-exe /path/to/compatible/Cricket07.exe --game-dir /path/to/game
python3 tools/serve.py --directory dist --port 8086
```

Open http://localhost:8086. The build creates `dist/`, a source ZIP, all prompts as Markdown and a separate ready-to-run browser-build ZIP. It uses an allowlist, rejects secret-file names, verifies the explicitly supplied EXE, and stages only files listed in the supplied game manifest as content-addressed 8 MB chunks. The source ZIP retains the complete upstream MIT license and the original engine source. Original resources are hosted as browser-download chunks, separate from the source ZIP. The portable browser ZIP references these hosted chunks and needs internet on its first launch.

To edit the roster, put your own original archive at `game/Data/data.gob`, then run `python3 mod-tools/build_modern_2026.py` in a Pillow/CairoSVG environment. Never overwrite the original archive. The builder checks 943 protected OG player records and 52 protected squads. Fan-created kits and proxy/generic player abilities do not claim authentic 2026 faces or official ratings. Old commentary/stadiums remain.

```sh
node --test mod-tools/workers.test.cjs
```

These checks cover archive restoration, pack upgrades, rejected corrupt downloads, installer resuming and quota recovery. A live-match smoke test does not prove every tour or tournament is compatible.

## Publish to Netlify

Publish **only `dist/`**, never the surrounding OYT workspace or the original game folder. `netlify.toml` sets the cross-origin isolation headers required by WebAssembly threads and WebGPU. The landing page is mobile-friendly; the game has no touch controls. Build locally, then use `netlify deploy --dir=dist --no-build` for a preview and `--prod` after verification. Keep `.netlify/` and credential files untracked. The game runs entirely in the browser and needs no game server or email gate.

Netlify's standard hostname is `cricket07-whymickywhy.netlify.app`. A nested name such as `cricket07.whymickywhy.netlify.com` is not a normal Netlify site hostname. For a custom nested hostname, use a domain you own and configure DNS. For high traffic, review hosting bandwidth/credit usage before adding large automatic game downloads.

## AI prompts

See `content/CUSTOMIZE-WITH-AI.md`. These starter prompts were written for this customization kit. They are not transcripts of how the original game or browser port was created. Use a coding assistant with file access, supply accurate player/reference data, preserve OG teams, and test changes in an actual match.

## Credits

- Cricket 07 / EA Sports: Electronic Arts, not affiliated with or sponsoring this project.
- Browser port and upstream open-source software: Dhaiwat Pandya and contributors. Its README credits Stephan Cilliers for the Rugby 06 scheduler/netplay port and controller support.
- This edition's page and customizations: Micky Kharbanda.
- Squad sources: BCCI's October 2026 ODI announcement and official IPL 2026 team endpoints, recorded in the mod manifest/reference snapshots.
- Bricolage Grotesque and DM Sans: open fonts; licenses are in `LICENSES/`.

Keep the included upstream `LICENSE` with all redistributed code. The source bundle is MIT-licensed for code; game data, trademarks, public reference imagery and the compiled game-specific runtime have their own ownership. No promise is made of compatibility with every game release or existing mod.

## Profile and supplied EXE

The expanded profile identifies Karan Singh / Micky as a Clearlyy co-founder. The photo and work description are sourced from the public Clearlyy site; the requested LinkedIn profile is linked directly. LinkedIn page contents were unavailable to the research tools, so no LinkedIn-only employment history was invented. Photo source: https://clearlyy.io/__l5e/assets-v1/c1c1feff-9308-4f39-9bd6-06073d5403ab/karan-formal.jpg .

The separately supplied Windows game executable is 4,354,048 bytes, SHA-256 `d776dba0cc506b968f7d228e036cf42aeb4abe45a8d1ad0d7226cdebf91553a2`. It is excluded from the MIT source ZIP and source repository. Its original local filename was `Cricket07.cracked.exe`; the public filename is `Cricket07.exe`. Its ownership is separate from the open-source software license. Original Data and Audio resources are hosted separately as verified chunks for automatic browser downloads, and are excluded from the source repository and ZIP. The modern team/kit pack applies to the browser build, not to this EXE by itself.

## Visitor analytics

Cloudflare Web Analytics is installed on the landing page and game launcher, registered to `cricket07-whymickywhy.netlify.app` in Micky's Cloudflare account. The public beacon token identifies the site; it does not grant dashboard access. View visits and page views privately at https://dash.cloudflare.com/3fb775a6edefa8f3b530ca6327c14289/web-analytics/overview?siteTag~in=3ebfb4873c6948d4a17d69b7f9cf8e09&excludeBots=Yes . Counts start after installation and may take time to appear; blocked scripts and browsers that block telemetry can reduce counts. No advertising pixel is installed.

## Personal link page

The mobile bio page lives at https://whymickywhy.netlify.app/ and its editable source is `site/links/index.html`. It highlights Cricket 07 with separate copy/open actions and links to Instinct, Clearlyy, Instagram, X and LinkedIn. The Instinct invite uses the direct destination supplied by Micky, without the Instagram redirect wrapper. `python3 tools/build_bio.py` creates the lightweight `bio-dist/` bundle without game files. Deploy it with `netlify deploy --prod --site b466c16e-f6ac-4e9d-8dfc-da5589cba805 --dir=bio-dist`. This explicitly targets the bio site and keeps the original project's Netlify link unchanged.

The bio site has separate Cloudflare analytics in the same account, site tag `719defc76041499c913f399d16a2ebd2`. Analytics for both sites: https://dash.cloudflare.com/3fb775a6edefa8f3b530ca6327c14289/web-analytics/sites . Instagram acceptance of a URL is controlled by Instagram; this page cannot guarantee that a rejected URL will be accepted.

The bio page also links to Micky’s three-level Game Room at https://micky-game-room.netlify.app/ . Its separate source and portable setup live in the sibling `game-room-public` project.
