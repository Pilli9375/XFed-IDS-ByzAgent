# Re-save the deck through PowerPoint with every font embedded (all characters, not a subset),
# then export the PDF. Windows COM; run from the repo root after build_ppt.py:
#   powershell -ExecutionPolicy Bypass -File docs\ppt\export_pdf.ps1
# The template's title-slide font, Bebas Neue (SIL Open Font License 1.1, from Google Fonts),
# must be installed first, or PowerPoint embeds its substitute instead.
Add-Type -AssemblyName System.Drawing
$have = (New-Object System.Drawing.Text.InstalledFontCollection).Families | Where-Object { $_.Name -eq "Bebas Neue" }
if (-not $have) { throw "Bebas Neue is not installed; install it before exporting." }
$root = (Resolve-Path ".").Path
$pptx = Join-Path $root "docs\ppt\XFed_Capstone_Final_Review.pptx"
$pdf  = Join-Path $root "docs\ppt\XFed_Capstone_Final_Review.pdf"
$tmp  = Join-Path $root "docs\ppt\_embed_tmp.pptx"
$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Open($pptx, $false, $false, $false)
$pres.SaveAs($tmp, 24, -1)   # 24 = ppSaveAsOpenXMLPresentation, -1 = msoTrue: embed TrueType fonts
$pres.SaveAs($pdf, 32)       # 32 = ppSaveAsPDF
$pres.Close()
$pp.Quit()
Move-Item -Force $tmp $pptx
Write-Output "wrote $pptx (fonts embedded) and $pdf"
