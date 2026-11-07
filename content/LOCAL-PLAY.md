# Play your browser build locally

1. Extract this ZIP into its own folder.
2. Install Python 3 if you do not already have it.
3. In that folder, run `python3 serve.py` (Windows: `py serve.py`).
4. Open http://localhost:8086/play/ in a desktop WebGPU-capable browser.
5. Game files download automatically from the hosted edition into your browser storage (about 1.17 GB). Keep an internet connection for this first launch. Interrupted downloads resume; later launches reuse the cache. No game folder selection is needed.
6. Choose **2026 Teams** (every 2026 nation, IPL, World XI and all-time XIs), **OG + IPL**, or **Original**. In Team Select, use left/right to assign your keyboard to a side and change its category to Other. Use up/down for India 2026 or an IPL team.

This ZIP has the browser runtime, modern mod resources, personal page and prompts. It includes the specifically supplied game EXE, and fetches the matching Data/Audio resources from the hosted edition on first launch. The Windows EXE by itself still requires matching Data and Audio folders; it is not a standalone installer. The EXE alone does not install the 2026 teams into Windows; those are applied by the browser mod pack. The runtime is specific to the executable/build used by this port; different game releases or existing mods can be incompatible. Use the source ZIP and engine/README.md to build a matching runtime from your own copy if necessary.

Save with the game's native menus. Native save files persist in this browser and can be backed up or restored in the launcher. There is no new instant save-state or save-anywhere feature. This public build supports solo/local play. Keep the included upstream MIT license and credits when sharing code.
