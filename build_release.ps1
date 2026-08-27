param(
    [string]$Version = "1.1.0"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$releaseRoot = Join-Path $projectRoot "release"
$packageName = "KariHelper-v$Version-windows-x64"
$packageDir = Join-Path $releaseRoot $packageName
$zipPath = Join-Path $releaseRoot "$packageName.zip"

Push-Location $projectRoot
try {
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed. Release build stopped."
    }

    $distPath = Join-Path $projectRoot "dist"
    $workPath = Join-Path $projectRoot "build\work"
    $specPath = Join-Path $projectRoot "build"
    $pyinstallerArgs = @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "KariHelper",
        "--distpath", $distPath,
        "--workpath", $workPath,
        "--specpath", $specPath,
        "app.py"
    )
    python @pyinstallerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }

    $expectedReleasePrefix = [IO.Path]::GetFullPath($releaseRoot).TrimEnd('\') + '\'
    $resolvedPackageDir = [IO.Path]::GetFullPath($packageDir)
    if (-not $resolvedPackageDir.StartsWith($expectedReleasePrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Package path is outside the project release directory."
    }

    if (Test-Path -LiteralPath $packageDir) {
        Remove-Item -LiteralPath $packageDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path (Join-Path $packageDir "data") -Force | Out-Null

    Copy-Item -LiteralPath (Join-Path $projectRoot "dist\KariHelper.exe") -Destination $packageDir
    Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $packageDir
    Copy-Item -LiteralPath (Join-Path $projectRoot "packaging\models_index.json") -Destination (Join-Path $packageDir "data\models_index.json")

    Compress-Archive -LiteralPath $packageDir -DestinationPath $zipPath -CompressionLevel Optimal -Force
    Write-Host "Release created: $zipPath"
}
finally {
    Pop-Location
}
