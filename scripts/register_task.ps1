<#
  Dang ky tac vu Windows "Agnet-Daemon": tu chay Agnet nen khi may bat / khi dang nhap,
  va tu bat lai moi 30 phut neu tien trinh da chet (khoa file chong chay trung).
  Chay bang PowerShell: 
      powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1
#>
param(
  [string]$TaskName = "Agnet-Daemon",
  [switch]$AtStartup   # them trigger khi may khoi dong (can quyen Administrator)
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$bat  = Join-Path $root "scripts\start_agnet.bat"
if (-not (Test-Path $bat)) { throw "Khong thay $bat" }

Write-Host "Thu muc du an: $root"
Write-Host "Kiem tra dieu kien (agnet doctor)..." -ForegroundColor Cyan
Push-Location $root
$py = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
& $py -m agnet doctor
$doctor = $LASTEXITCODE
Pop-Location
if ($doctor -ne 0) {
  Write-Warning "doctor bao con thieu (xem tren). Van dang ky tac vu, nhung hay sua truoc khi tin vao lich chay."
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`"" -WorkingDirectory $root

$triggers = @()
$triggers += New-ScheduledTaskTrigger -AtLogOn
# Trigger lap: canh gac — neu daemon da chet thi 30 phut sau tu bat lai.
$watch = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(5) `
          -RepetitionInterval (New-TimeSpan -Minutes 30)
$triggers += $watch
if ($AtStartup) { $triggers += New-ScheduledTaskTrigger -AtStartup }

$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
            -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 0) `
            -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) -Hidden

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings `
  -Description "Agnet: chay nen theo lich trong config/flows.yaml, bu lich khi may tung tat, bao Telegram." -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Write-Host "Da dang ky va bat tac vu '$TaskName'." -ForegroundColor Green
Write-Host "Xem trang thai : Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo"
Write-Host "Xem log        : Get-Content '$root\logs\agnet.log' -Tail 40 -Wait"
Write-Host "Huy dang ky    : powershell -ExecutionPolicy Bypass -File scripts\unregister_task.ps1"
