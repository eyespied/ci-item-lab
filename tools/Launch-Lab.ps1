param([string]$GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord')
$ErrorActionPreference = 'Stop'
$moduleRoot = Join-Path $GameRoot 'Modules\CIItemLab'
if (-not (Test-Path -LiteralPath (Join-Path $moduleRoot 'SubModule.xml'))) { throw 'Run Install-Lab.ps1 first.' }
if (Get-Process -Name 'Bannerlord','Bannerlord.Native' -ErrorAction SilentlyContinue) {
    throw 'Bannerlord is already running. Close it before launching the item lab.'
}
$gameBin = Join-Path $GameRoot 'bin\Win64_Shipping_Client'
& (Join-Path $PSScriptRoot 'Install-Lab.ps1') -GameRoot $GameRoot
# An explicit module list starts the isolated lab without altering launcher selections.
Start-Process -FilePath (Join-Path $gameBin 'Bannerlord.exe') -WorkingDirectory $gameBin -WindowStyle Normal -ArgumentList @(
    '/singleplayer', '_MODULES_*Native*SandBoxCore*CustomBattle*Sandbox*StoryMode*CIItemLab*_MODULES_'
)
