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
# Make map-specific resources visible to Hammer and the compilers. BSPZIP
# uses the same files below so subscribers receive the matching versions.
$assetRoot = Join-Path $source.DirectoryName "assets\$($source.BaseName)"
$packList = @()
if (Test-Path -LiteralPath $assetRoot -PathType Container) {
    foreach ($asset in Get-ChildItem -LiteralPath $assetRoot -File -Recurse) {
        $relative = $asset.FullName.Substring($assetRoot.Length + 1)
        $mounted = Join-Path $game $relative
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($mounted)) | Out-Null
        Copy-Item -LiteralPath $asset.FullName -Destination $mounted
        $packList += $relative.Replace('\', '/'), $asset.FullName
    }
}
Invoke-Compiler 'vbsp' @('-game', $game, $base)
if (-not (Test-Path -LiteralPath "$base.prt") -or (Test-Path -LiteralPath "$base.lin")) {
    throw "Missing visibility portals or a leak. Inspect $base.log and the Hammer pointfile."
}
Invoke-Compiler 'vvis' @('-game', $game, $base)
Invoke-Compiler 'vrad' @('-both', '-game', $game, $base)
if ($packList.Count -gt 0) {
    $listFile = Join-Path $stageDir 'packlist.txt'
    [IO.File]::WriteAllLines($listFile, [string[]]$packList, [Text.UTF8Encoding]::new($false))
    $env:VPROJECT = $game
    Invoke-Compiler 'bspzip' @('-addlist', "$base.bsp", $listFile, "$base.packed.bsp")
    Move-Item -LiteralPath "$base.packed.bsp" -Destination "$base.bsp" -Force
}
foreach ($extension in @('bsp', 'log')) {
    Copy-Item -LiteralPath "$base.$extension" -Destination (Join-Path $source.DirectoryName "$($source.BaseName).$extension")
}
if ($Install) {
    $destination = Join-Path $game "maps\$($source.BaseName).bsp"
    Copy-Item -LiteralPath "$base.bsp" -Destination $destination
    Write-Host "Installed $destination"
    Write-Host "Portal 2 console: map $($source.BaseName)"
}
