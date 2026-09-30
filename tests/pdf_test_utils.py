import io

def generate_minimal_pdf(pages_text: list[str]) -> bytes:
    """
    Generates a syntactically valid multi-page PDF in raw bytes with the specified text for each page.
    Zero external dependencies needed.
    """
    objects = []
    
    # 1 0 obj: Catalog
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    
    total_pages = len(pages_text)
    # Page object numbers will be 3, 5, 7... and contents will be 4, 6, 8...
    # Font will be object at the end
    font_obj_num = 3 + total_pages * 2
    
    kids_refs = " ".join(f"{3 + i*2} 0 R" for i in range(total_pages))
    # 2 0 obj: Pages
    objects.append(f"<< /Type /Pages /Kids [{kids_refs}] /Count {total_pages} >>")
    
    for i, text in enumerate(pages_text):
        page_num = 3 + i * 2
        content_num = page_num + 1
        
        # Page obj
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> "
            f"/Contents {content_num} 0 R >>"
        )
        
        # Escape parenthesis in text
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_content = f"BT /F1 12 Tf 50 720 Td ({escaped}) Tj ET"
        stream_bytes = stream_content.encode("latin1")
        
        # Content obj
        objects.append(f"<< /Length {len(stream_bytes)} >>\nstream\n{stream_content}\nendstream")

    # Font obj
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # Assemble PDF with cross-reference table
    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]  # object 0

    for i, obj_str in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{i} 0 obj\n{obj_str}\nendobj\n".encode("latin1"))

    xref_pos = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin1"))
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("latin1"))

    output.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode("latin1")
    )
    return output.getvalue()
