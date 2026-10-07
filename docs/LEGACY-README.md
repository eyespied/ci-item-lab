# CI Item Lab

A Bannerlord singleplayer equipment catalog and testing environment built around the locally installed CI multiplayer modpack.

- **F8:** searchable item catalog with pack names and original IDs.
- **Ctrl+F8:** item-ID search and inventory utilities.
- **F7:** clan color profiles.
- **F9:** arenas, taverns and keep interiors.
- **F10:** leave a test scene and return to the campaign map.

## Build and run

Requires Windows, Bannerlord, the CI Workshop pack, .NET SDK 10, and Python 3. The scripts currently default to the original machine's installation paths; pass `GameRoot`, `CISource`, and `Python` as needed.

Run `tools/Build-Lab.ps1`, then `tools/Install-Lab.ps1` with Bannerlord closed. `Launch CI Item Lab.cmd` installs the current packaged build and starts the game with the lab module enabled.

CI asset packages are linked from the local Workshop installation and are not stored in this repository. The bundled TpacTool library and its license are in `tools/AssetInventory/lib`.

## Saved selections

`selections/civilian-items.json` and `.txt` contain the current 58-item Civilian shortlist. The previous selection is retained separately. These are saved selections, not changes to game equipment flags.

## Current limitations

This is a work in progress. Generated unused-asset items use inferred equipment types and copied test stats. Three reported crash entries are quarantined, four generated weapon tests fail initialization, and singleplayer colors are not yet verified to match CI multiplayer rendering. Runtime diagnostics are written to `Documents/Mount and Blade II Bannerlord/CIItemLab/diagnostics`.

See `CI-ITEM-LAB.txt` for usage details. This repository covers CIItemLab only; it sits within a workspace that can host other mods.
