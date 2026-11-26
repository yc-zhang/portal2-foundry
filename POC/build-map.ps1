[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $Vmf,
    [string] $GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Portal 2',
    [switch] $Install
)
$ErrorActionPreference = 'Stop'
$source = Get-Item -LiteralPath $Vmf
if ($source.Extension -ine '.vmf') { throw 'Expected a VMF source file.' }
$game = Join-Path $GameRoot 'portal2'
$maps = Join-Path $GameRoot 'sdk_content\maps'
foreach ($required in @($maps, (Join-Path $game 'gameinfo.txt'))) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing: $required" }
}
# Separate intermediate files from other builds while preserving the BSP basename.
$stageDir = Join-Path $maps ('foundry_build_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stageDir | Out-Null
$base = Join-Path $stageDir $source.BaseName
Copy-Item -LiteralPath $source.FullName -Destination "$base.vmf"
Write-Host "Build directory: $stageDir"

function Invoke-Compiler([string] $Name, [string[]] $Arguments) {
    & (Join-Path $GameRoot "bin\$Name.exe") @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Name failed (exit $LASTEXITCODE). See $base.log" }
}
# Mount explicit assets for Hammer/VBSP. pack_map.py resolves runtime dependencies later.
$assetRoot = Join-Path $source.DirectoryName "assets\$($source.BaseName)"
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create POC/.venv and install requirements.txt before building.' }
if (Test-Path -LiteralPath $assetRoot -PathType Container) {
    foreach ($asset in Get-ChildItem -LiteralPath $assetRoot -File -Recurse) {
        $relative = $asset.FullName.Substring($assetRoot.Length + 1)
        $mounted = Join-Path $game $relative
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($mounted)) | Out-Null
        Copy-Item -LiteralPath $asset.FullName -Destination $mounted
    }
}
Invoke-Compiler 'vbsp' @('-game', $game, $base)
if (-not (Test-Path -LiteralPath "$base.prt") -or (Test-Path -LiteralPath "$base.lin")) {
    throw "Missing visibility portals or a leak. Inspect $base.log and the Hammer pointfile."
}
Invoke-Compiler 'vvis' @('-game', $game, $base)
Invoke-Compiler 'vrad' @('-both', '-game', $game, $base)
& $python (Join-Path $PSScriptRoot 'pack_map.py') "$base.bsp" $game $assetRoot
if ($LASTEXITCODE -ne 0) { throw "Dependency packing failed. See $stageDir" }
foreach ($extension in @('bsp', 'log')) {
    Copy-Item -LiteralPath "$base.$extension" -Destination (Join-Path $source.DirectoryName "$($source.BaseName).$extension")
}
if ($Install) {
    $destination = Join-Path $game "maps\$($source.BaseName).bsp"
    Copy-Item -LiteralPath "$base.bsp" -Destination $destination
    Write-Host "Installed $destination"
    Write-Host "Portal 2 console: map $($source.BaseName)"
}
