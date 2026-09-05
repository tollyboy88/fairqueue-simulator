"""Rasterise Word-exported PDF proofs when the packaged DOCX renderer lacks soffice."""
from pathlib import Path

import pypdfium2 as pdfium

root = Path("submission/Health_Systems/_rendered")
for pdf_path in root.glob("*/*.pdf"):
    document = pdfium.PdfDocument(pdf_path)
    for index in range(len(document)):
        image = document[index].render(scale=1.5).to_pil()
        image.save(pdf_path.parent / f"page-{index + 1}.png")
    print(f"{pdf_path.parent.name}: {len(document)} pages")
