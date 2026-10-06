param(
    [string]$GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord',
    [string]$CISource = 'C:\Program Files (x86)\Steam\steamapps\workshop\content\261550\3245522442'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$packageRoot = Join-Path $projectRoot 'module\CIItemLab'
$moduleRoot = Join-Path $GameRoot 'Modules\CIItemLab'
if (-not (Test-Path -LiteralPath (Join-Path $packageRoot 'bin\Win64_Shipping_Client\CIItemLab.dll'))) {
    throw 'Build CIItemLab first (tools\Build-Lab.ps1).'
}
if (Test-Path -LiteralPath $moduleRoot) {
    $manifest = Join-Path $moduleRoot 'SubModule.xml'
    if (-not (Test-Path -LiteralPath $manifest)) { throw 'Existing CIItemLab folder has no manifest; refusing to overwrite it.' }
    [xml]$existing = Get-Content -LiteralPath $manifest -Raw
    if ($existing.Module.Id.value -ne 'CIItemLab') { throw 'Existing folder belongs to another mod.' }
}
New-Item -ItemType Directory -Force -Path $moduleRoot | Out-Null
# Copy only our data and DLLs. Never traverse or copy the linked Workshop asset folders.
Get-ChildItem -LiteralPath $packageRoot -Recurse -File | ForEach-Object {
    $relative = $_.FullName.Substring($packageRoot.Length + 1)
    $target = Join-Path $moduleRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $target -Force
}
foreach ($name in @('AssetPackages', 'Assets', 'ModuleSounds', 'Prefabs')) {
    $sourcePath = Join-Path $CISource $name
    $targetPath = Join-Path $moduleRoot $name
    if (-not (Test-Path -LiteralPath $sourcePath)) { throw "Missing CI assets: $sourcePath" }
    if (Test-Path -LiteralPath $targetPath) {
        $existingLink = Get-Item -LiteralPath $targetPath -Force
        if ($existingLink.LinkType -ne 'Junction' -or $existingLink.Target -notcontains $sourcePath) {
            throw "Existing asset path does not point to the expected CI folder: $targetPath"
        }
    } else {
        New-Item -ItemType Junction -Path $targetPath -Value $sourcePath | Out-Null
    }
}
Write-Output "Installed singleplayer lab: $moduleRoot"
Write-Output 'CI Workshop must stay installed: this module links to its asset files.'
