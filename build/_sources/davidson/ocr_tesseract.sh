#!/bin/bash
# Re-OCR both Davidson PDFs with tesseract heb+eng, writing per-page TSV files.
# Usage: bash build/_sources/davidson/ocr_tesseract.sh
set -u
cd "$(dirname "$0")"
mkdir -p _tess/key _tess/grammar

ocr_book() {
  local pdf="$1" outdir="$2" pages="$3"
  for i in $(seq 1 "$pages"); do
    local page=$((i - 1))
    local out="$outdir/n$page"
    if [ -f "$out.tsv" ]; then continue; fi
    pdftoppm -f "$i" -l "$i" -r 400 -gray -singlefile "$pdf" "$out.tmp" 2>/dev/null || { echo "render fail $pdf p$page"; continue; }
    tesseract "$out.tmp.pgm" "$out" -l heb+eng --psm 6 tsv 2>/dev/null
    rm -f "$out.tmp.pgm"
    if [ $((page % 20)) -eq 0 ]; then echo "$pdf page $page done"; fi
  done
}

ocr_book key-1924.pdf _tess/key 168 &
KPID=$!
ocr_book grammar-1923-22nd.pdf _tess/grammar 264 &
GPID=$!
wait $KPID $GPID
echo "OCR COMPLETE"
