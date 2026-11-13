#!/bin/bash
# Local OCR of the Machen scan with tesseract grc+eng (no remote service), one TSV + TXT per PDF page.
# Usage: bash build/_sources/machen/ocr_tesseract.sh   (needs machen-1924.pdf: python scripts/fetch-sources machen)
set -u
cd "$(dirname "$0")"
mkdir -p _tess/book

page_job() {
  local out="_tess/book/p$(printf %03d "$1")"
  if [ -f "$out.tsv" ] && [ -f "$out.txt" ]; then return; fi
  pdftoppm -f "$1" -l "$1" -r 310 -gray -singlefile machen-1924.pdf "$out.tmp" 2>/dev/null || { echo "render fail p$1"; return; }
  OMP_THREAD_LIMIT=1 tesseract "$out.tmp.pgm" "$out" -l grc+eng --psm 6 txt tsv 2>/dev/null
  rm -f "$out.tmp.pgm"
}
export -f page_job

seq 1 "$(pdfinfo machen-1924.pdf | awk '/^Pages:/{print $2}')" | xargs -P 8 -I{} bash -c 'page_job {}'
echo "OCR COMPLETE"
