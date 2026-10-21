$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location (Join-Path $PSScriptRoot 'xboxrecomp')
$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $py -m tools.xbe_parser game_files/default.xbe --json game_files/default_analysis.json
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& $py -m tools.disasm game_files/default.xbe --seed-functions ../rsc2/config/seed_functions.json
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& $py -m tools.func_id game_files/default.xbe
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& $py -m tools.abi_analysis game_files/default.xbe
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& $py -m tools.recomp game_files/default.xbe --all --split 250 --exclude-manual ../rsc2/src/rsc2_overrides.c --trace-functions ../rsc2/config/trace_functions.json --gen-dir ../rsc2/src/recomp/gen
exit $LASTEXITCODE
