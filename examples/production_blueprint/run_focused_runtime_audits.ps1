param(
    [string[]]$Configs = @(
        "config_chlorine_family_runtime.yaml",
        "config_bromine_family_runtime.yaml",
        "config_silicon_family_runtime.yaml",
        "config_o2_electron_argon_ion_runtime.yaml",
        "config_process_gas_secondary_runtime.yaml",
        "config_advanced_precursor_runtime.yaml"
    ),
    [string]$OutputDir = ".generated_runtime_audits"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$resolvedOutputDir = Join-Path $scriptDir $OutputDir
New-Item -ItemType Directory -Force -Path $resolvedOutputDir | Out-Null
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\\..")
$venvPython = Join-Path $repoRoot ".venv\\Scripts\\python.exe"
$venvCli = Join-Path $repoRoot ".venv\\Scripts\\plasma-rxn-builder.exe"

function Invoke-BuilderCommand {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    if (Test-Path $venvCli) {
        & $venvCli @Arguments
        return
    }
    if (Test-Path $venvPython) {
        & $venvPython -m plasma_reaction_builder.cli @Arguments
        return
    }
    py -3.13 -m uv run plasma-rxn-builder @Arguments
}

foreach ($configName in $Configs) {
    $configPath = Join-Path $scriptDir $configName
    if (-not (Test-Path $configPath)) {
        Write-Warning "Skip missing config: $configPath"
        continue
    }

    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($configName)
    $configAuditPath = Join-Path $resolvedOutputDir "$baseName.config_audit.json"
    $networkPath = Join-Path $resolvedOutputDir "$baseName.network.json"
    $networkAuditPath = Join-Path $resolvedOutputDir "$baseName.network_audit.json"

    Write-Host "Audit config: $configName"
    Invoke-BuilderCommand audit-config $configPath --output $configAuditPath
    if ($LASTEXITCODE -ne 0) {
        throw "audit-config failed for $configName"
    }

    Write-Host "Build network: $configName"
    Invoke-BuilderCommand build $configPath --output $networkPath
    if ($LASTEXITCODE -ne 0) {
        throw "build failed for $configName"
    }

    Write-Host "Audit network: $configName"
    Invoke-BuilderCommand audit-network $networkPath --output $networkAuditPath
    if ($LASTEXITCODE -ne 0) {
        throw "audit-network failed for $configName"
    }
}

Write-Host "Finished. Outputs written to $resolvedOutputDir"
