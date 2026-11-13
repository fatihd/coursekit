#!/bin/bash
# Local OCR of the Davis scan with tesseract grc+eng (no remote service), one TSV + TXT per PDF page.
# Usage: bash build/_sources/davis/ocr_tesseract.sh   (needs davis-1923.pdf: python scripts/fetch-sources davis)
set -u
cd "$(dirname "$0")"
mkdir -p _tess/book

page_job() {
  local out="_tess/book/p$(printf %03d "$1")"
  if [ -f "$out.tsv" ] && [ -f "$out.txt" ]; then return; fi
  pdftoppm -f "$1" -l "$1" -r 400 -gray -singlefile davis-1923.pdf "$out.tmp" 2>/dev/null || { echo "render fail p$1"; return; }
  OMP_THREAD_LIMIT=1 tesseract "$out.tmp.pgm" "$out" -l grc+eng --psm 6 txt tsv 2>/dev/null
  rm -f "$out.tmp.pgm"
}
export -f page_job

seq 1 "$(pdfinfo davis-1923.pdf | awk '/^Pages:/{print $2}')" | xargs -P 8 -I{} bash -c 'page_job {}'
echo "OCR COMPLETE"
