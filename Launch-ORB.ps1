$orbRoot = $PSScriptRoot
$orbQa = 'E:\ORB\Temp\orb-dashboard-qa'
$orbPython = 'C:\Users\sanku\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH = "$orbQa\sklearn-compat;$orbQa\piper;$orbQa\speech;$orbQa\audio;$orbQa\onnx;$orbQa\voice;$orbQa;$orbRoot\src"
& $orbPython -B -c 'import PySide6.QtWidgets, sounddevice, soundfile, scipy.signal, openwakeword, onnx_asr, piper'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $orbPython -B -m orb.gui
exit $LASTEXITCODE
