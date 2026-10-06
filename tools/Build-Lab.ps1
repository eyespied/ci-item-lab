param(
    [string]$GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord',
    [string]$CISource = 'C:\Program Files (x86)\Steam\steamapps\workshop\content\261550\3245522442',
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
& dotnet run --project (Join-Path $PSScriptRoot 'AssetInventory\AssetInventory.csproj') -- $CISource (Join-Path $projectRoot 'docs\asset-mesh-index.json')
if ($LASTEXITCODE -ne 0) { throw 'Asset indexing failed.' }
& $Python (Join-Path $PSScriptRoot 'prepare_lab.py') --source $CISource --game $GameRoot
if ($LASTEXITCODE -ne 0) { throw 'Item conversion failed.' }
if (Test-Path -LiteralPath (Join-Path $projectRoot 'docs\asset-mesh-index.json')) {
    & $Python (Join-Path $PSScriptRoot 'expand_assets.py')
    if ($LASTEXITCODE -ne 0) { throw 'Asset expansion failed.' }
}
& $Python (Join-Path $PSScriptRoot 'repair_recipes.py')
if ($LASTEXITCODE -ne 0) { throw 'Recipe compatibility repair failed.' }
& $Python (Join-Path $PSScriptRoot 'prepare_colors.py')
if ($LASTEXITCODE -ne 0) { throw 'Color profile preparation failed.' }
& $Python (Join-Path $PSScriptRoot 'verify_lab.py') --game $GameRoot
if ($LASTEXITCODE -ne 0) { throw 'Item data validation failed.' }
& dotnet build (Join-Path $projectRoot 'src\CIItemLab\CIItemLab.csproj') -c Release --nologo "-p:GameRoot=$GameRoot"
if ($LASTEXITCODE -ne 0) { throw 'Mod build failed.' }
$bin = Join-Path $projectRoot 'module\CIItemLab\bin\Win64_Shipping_Client'
Copy-Item -LiteralPath (Join-Path $projectRoot 'build\CIItemLab\CIItemLab.dll') -Destination $bin -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'build\CIItemLab\CIItemLab.pdb') -Destination $bin -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'build\CIItemLab\0Harmony.dll') -Destination $bin -Force
