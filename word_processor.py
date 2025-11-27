from docx import Document
import io


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract text from DOCX file bytes.
    Processes all paragraphs and tables.
    """
    try:
        doc = Document(io.BytesIO(file_bytes))
        
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text = cell.text.strip()
                    if text and text not in paragraphs:
                        paragraphs.append(text)
        
        return "\n".join(paragraphs)
        
    except Exception as e:
        raise Exception(f"Failed to extract text from DOCX: {e}")


def get_top_section_text(file_bytes: bytes, max_paragraphs: int = 15) -> str:
    """Get only the top section text for faster processing."""
    try:
        doc = Document(io.BytesIO(file_bytes))
        
        paragraphs = []
        count = 0
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
                count += 1
                if count >= max_paragraphs:
                    break
        
        if doc.tables:
            for row in doc.tables[0].rows[:5]:
                for cell in row.cells:
                    text = cell.text.strip()
                    if text and text not in paragraphs:
                        paragraphs.append(text)
        
        return "\n".join(paragraphs)
        
    except Exception as e:
        return ""
