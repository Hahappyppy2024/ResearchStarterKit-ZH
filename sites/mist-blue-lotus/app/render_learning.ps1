param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
$existingPowerPoint=Get-Process POWERPNT -ErrorAction SilentlyContinue
$app=$null; $presentation=$null; $oldSecurity=$null
try {
 New-Item -ItemType Directory -Force -Path $Output | Out-Null
 $app=New-Object -ComObject PowerPoint.Application
 $oldSecurity=$app.AutomationSecurity
 $app.AutomationSecurity=3
 $presentation=$app.Presentations.Open($Source,-1,0,0)
 for($i=1;$i -le $presentation.Slides.Count;$i++) {
  $image=Join-Path $Output ('slide-{0:D4}.png' -f $i)
  $height=[int](1600*$presentation.PageSetup.SlideHeight/$presentation.PageSetup.SlideWidth)
  $presentation.Slides.Item($i).Export($image,'PNG',1600,$height)
 }
} finally {
 if($presentation){$presentation.Close();[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation)}
 if($app){if($null -ne $oldSecurity){$app.AutomationSecurity=$oldSecurity};if(-not $existingPowerPoint){$app.Quit()};[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)}
}
