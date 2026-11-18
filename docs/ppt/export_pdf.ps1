# Export the deck to PDF through PowerPoint (Windows COM). Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File docs\ppt\export_pdf.ps1
$root = (Resolve-Path ".").Path
$in   = Join-Path $root "docs\ppt\XFed_Capstone_Final_Review.pptx"
$out  = Join-Path $root "docs\ppt\XFed_Capstone_Final_Review.pdf"
$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Open($in, $true, $false, $false)
$pres.SaveAs($out, 32)   # 32 = ppSaveAsPDF
$pres.Close()
$pp.Quit()
Write-Output "wrote $out"
