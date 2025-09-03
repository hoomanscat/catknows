$ErrorActionPreference = 'Stop'

# Paths and environment detection
$venvDir = '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$isActivatedVenv = $false
if ($env:VIRTUAL_ENV) { $isActivatedVenv = $true }

if (-not $isActivatedVenv) {
	if (-not (Test-Path $venvDir)) {
		Write-Host "Creating virtual environment in $venvDir..."
		try {
			python -m venv $venvDir
		} catch {
			Write-Error "Failed to create virtualenv: $($_.Exception.Message)"
			Write-Host "If you're running this script from inside a virtual environment, deactivate it first and re-run."
			exit 1
		}
	} else {
		Write-Host "Virtual environment already exists at $venvDir. Skipping creation."
	}
} else {
	Write-Host "Detected active virtual environment; skipping venv creation."
}

# Helper to invoke pip: prefer the venv python -m pip, fall back to pip in PATH
function Invoke-PipInstall {
	param(
		[Parameter(Mandatory=$true)][string[]]$Args
	)

	if (Test-Path $venvPython) {
		try {
			$argList = @('-m','pip') + $Args
			$proc = Start-Process -FilePath $venvPython -ArgumentList $argList -NoNewWindow -Wait -PassThru
			if ($proc.ExitCode -eq 0) { return $true } else { Write-Host "pip exited with code $($proc.ExitCode)" }
		} catch {
			Write-Host "Warning: couldn't run $venvPython -m pip: $($_.Exception.Message)"
		}
	}

	if (Get-Command pip -ErrorAction SilentlyContinue) {
		try {
			$proc = Start-Process -FilePath (Get-Command pip).Source -ArgumentList $Args -NoNewWindow -Wait -PassThru
			if ($proc.ExitCode -eq 0) { return $true } else { Write-Host "pip (PATH) exited with code $($proc.ExitCode)" }
		} catch {
			Write-Host "Warning: pip from PATH failed: $($_.Exception.Message)"
		}
	}

	return $false
}

# Upgrade pip (best-effort)
if (-not (Invoke-PipInstall -Args @('install','--upgrade','pip'))) {
	$suggest = Join-Path $venvDir 'Scripts\python.exe'
	Write-Host ("Could not upgrade pip automatically. You can try: & '" + $suggest + "' -m pip install --upgrade pip")
}

if (Test-Path .\requirements.txt) {
	if (-not (Invoke-PipInstall -Args @('install','-r', '.\requirements.txt'))) {
		Write-Host "Failed to install requirements automatically. Try running the command shown in the message or run this script from an elevated PowerShell and ensure no other process is locking files under $venvDir"
	}
}

if (-not (Test-Path .\.env)) { Copy-Item .\.env.example .\.env -ErrorAction SilentlyContinue }

Write-Host "Setup done. Next: run 'alembic upgrade head' and then 'python daily_runner.py'"
