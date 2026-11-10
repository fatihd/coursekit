// Vision OCR of a PDF to JSON: one object per page with per-line text + boxes.
//
// Usage:
//   swiftc -O ocr_pdf.swift -o ocr_pdf
//   ./ocr_pdf <input.pdf> <output.json> [firstPage] [lastPageExclusive]
//
// Output: {"pages": [{"page": i, "width": w, "height": h,
//                      "lines": [{"t": "...", "x": ..., "y": ..., "w": ..., "h": ...}]}]}
// x,y are top-left origin pixel boxes; lines are emitted in Vision reading order.

import Foundation
import CoreGraphics
import ImageIO
import Vision

struct LineBox: Codable {
    let t: String
    let x: Double
    let y: Double
    let w: Double
    let h: Double
}

struct PageOut: Codable {
    let page: Int
    let width: Double
    let height: Double
    let lines: [LineBox]
}

struct DocOut: Codable {
    let pages: [PageOut]
}

func ocr(cgImage: CGImage, langs: [String]) throws -> [LineBox] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = langs
    request.usesLanguageCorrection = false
    request.customWords = []

    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try handler.perform([request])

    let W = Double(cgImage.width)
    let H = Double(cgImage.height)
    var out: [LineBox] = []
    for obs in request.results ?? [] {
        guard let cand = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox
        // Vision normalized origin is lower-left; convert to top-left pixels.
        let x = b.minX * W
        let y = (1.0 - b.maxY) * H
        let w = b.width * W
        let h = b.height * H
        out.append(LineBox(t: cand.string, x: x, y: y, w: w, h: h))
    }
    return out
}

func renderPage(_ doc: CGPDFDocument, _ index: Int, scale: CGFloat) -> CGImage? {
    guard let page = doc.page(at: index) else { return nil }
    let box = page.getBoxRect(.mediaBox)
    let w = Int(ceil(box.width * scale))
    let h = Int(ceil(box.height * scale))
    let cs = CGColorSpaceCreateDeviceRGB()
    guard let ctx = CGContext(
        data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
        space: cs, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue
    ) else { return nil }
    ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.scaleBy(x: scale, y: scale)
    ctx.drawPDFPage(page)
    return ctx.makeImage()
}

func main() {
    let args = CommandLine.arguments
    guard args.count >= 3 else {
        FileHandle.standardError.write(Data("usage: ocr_pdf in.pdf out.json [first] [lastEx]\n".utf8))
        exit(2)
    }
    let inPath = args[1]
    let outPath = args[2]
    let scale: CGFloat = 2.0
    var langs = ["he-IL", "en-US"]
    if args.count >= 6 { langs = args[5].split(separator: ",").map(String.init) }

    guard let doc = CGPDFDocument(NSURL(fileURLWithPath: inPath)) else {
        FileHandle.standardError.write(Data("cannot open pdf\n".utf8))
        exit(3)
    }
    let total = doc.numberOfPages
    var first = 0
    var last = total
    if args.count >= 4 { first = Int(args[3]) ?? 0 }
    if args.count >= 5 { last = Int(args[4]) ?? total }

    var pages: [PageOut] = []
    for i in first..<min(last, total) {
        autoreleasepool {
            guard let img = renderPage(doc, i, scale: scale) else { return }
            let lines: [LineBox]
            do { lines = try ocr(cgImage: img, langs: langs) } catch { return }
            let pw = Double(img.width) / Double(scale)
            let ph = Double(img.height) / Double(scale)
            pages.append(PageOut(page: i, width: pw, height: ph, lines: lines))
        }
        if (i - first) % 10 == 9 {
            FileHandle.standardError.write(Data("page \(i + 1)/\(total)\n".utf8))
        }
    }

    let out = DocOut(pages: pages)
    let enc = JSONEncoder()
    enc.outputFormatting = [.prettyPrinted]
    do {
        let data = try enc.encode(out)
        try data.write(to: URL(fileURLWithPath: outPath))
    } catch {
        FileHandle.standardError.write(Data("write error \(error)\n".utf8))
        exit(4)
    }
}

main()
