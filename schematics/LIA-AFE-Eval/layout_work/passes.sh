#!/bin/sh
# repeated passes: each starts from the hand-routed board, failed nets of the last pass go first
cd "$(dirname "$0")"
best=999
for k in 1 2 3; do
  cp hand.kicad_pcb pass.kicad_pcb
  MSYS_NO_PATHCONV=1 "/c/Program Files/KiCad/10.0/bin/python.exe" -u route.py pass.kicad_pcb > pass$k.log 2>&1
  nf=$(grep -c . failed.txt)
  echo "pass $k: failed $nf: $(tr '\n' ' ' < failed.txt)"
  if [ "$nf" -lt "$best" ]; then best=$nf; cp pass.kicad_pcb best.kicad_pcb; fi
  [ "$nf" -eq 0 ] && break
  # failed of this pass first, then the previous first list
  cat failed.txt first.txt | awk '!s[$0]++' > f2.txt; mv f2.txt first.txt
done
echo "best: $best"
