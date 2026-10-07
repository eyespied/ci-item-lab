# CI Item Lab

Singleplayer equipment catalog and test environment using the installed CI multiplayer modpack. F8 opens the catalog, Ctrl+F8 searches IDs, F7 shows clan colors, F9 chooses arenas/interiors and F10 leaves a test scene. Internal module ID remains `CIItemLab`.

## Build and run

Requires Windows, Bannerlord, CI Workshop subscription, .NET 10 SDK and Python. From this folder:

```powershell
.\tools\Build-Lab.ps1 -Python python
.\tools\Install-Lab.ps1
.\"Launch CI Item Lab.cmd"
```

Override `-GameRoot`, `-CISource` and `-Python` on the build as needed. Close game/launcher before installing. Launch installs the packaged module and opens the game with explicit modules; create a Sandbox test save. CI asset packages are linked from Workshop and are not backed up here.

`src/` holds the module, `tools/` prepares data and installs it, `module/CIItemLab` is staged content, `build/` is generated. `selections/civilian-items.json` and `.txt` hold the current shortlist; the obsolete previous shortlist has been removed. Nothing here changes the live pack's equipment flags.

Read [CI-ITEM-LAB.txt](CI-ITEM-LAB.txt) for controls and troubleshooting. Generated unused-asset items have inferred types/test stats; quarantined crashes and recipe limitations remain documented there. Diagnostics: `Documents/Mount and Blade II Bannerlord/CIItemLab/diagnostics`. Singleplayer colors and every generated item are not proven equivalent to multiplayer.

## Launchers and PowerShell scripts

All relative commands assume this repository root.

| File | Purpose / effect |
|---|---|
| [Launch CI Item Lab.cmd](Launch%20CI%20Item%20Lab.cmd) | Installs staged Item Lab and starts a singleplayer test game with the required modules. |
| [tools/Build-Lab.ps1](tools/Build-Lab.ps1) | Indexes installed CI assets, prepares test items/colors/recipes and builds the lab. |
| [tools/Install-Lab.ps1](tools/Install-Lab.ps1) | Stages/links CI assets and installs the lab with the game closed. |
| [tools/Launch-Lab.ps1](tools/Launch-Lab.ps1) | Installs and launches the explicit singleplayer test module list. |

## Environment and local configuration

No project-specific environment variables are required by current source. Build parameters and local game/server JSON/XML configuration are described above; standard OS environment variables are not application settings.

## Repository and workspace

Source: https://github.com/eyespied/ci-item-lab. Local home: `mods/ci-item-lab`. This is an independent repository in the consolidated Bannerlord workspace. Folder/repository names do not change internal module IDs. Existing detailed notes are retained in `docs/LEGACY-README*` where present. GitHub stores source and intentional release content; credentials, caches and installed game libraries require separate local/service backups.
