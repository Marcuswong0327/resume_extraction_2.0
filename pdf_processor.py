import pdfplumber
from PyPDF2 import PdfReader
import io


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from PDF file bytes.
    Uses pdfplumber as primary method, falls back to PyPDF2 if needed.
    Focuses on first 2-3 pages for efficiency.
    
    Args:
        file_bytes: PDF file content as bytes
        
    Returns:
        Extracted text string
    """
    text = ""
    
    try:
        # Primary method: pdfplumber (better layout handling)
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            # Only process first 2 pages max (contact info is usually on first page)
            max_pages = min(len(pdf.pages), 2)
            
            for i in range(max_pages):
                page = pdf.pages[i]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    
        if text.strip():
            return text
            
    except Exception as e:
        print(f"pdfplumber failed: {e}")
    
    # Fallback: PyPDF2
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        max_pages = min(len(reader.pages), 2)
        
        for i in range(max_pages):
            page = reader.pages[i]
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
                
    except Exception as e:
        print(f"PyPDF2 failed: {e}")
        raise Exception(f"Failed to extract text from PDF: {e}")
    
    return text


def get_first_page_text(file_bytes: bytes) -> str:
    """
    Get only the first page text for faster processing.
    Contact info is almost always on the first page.
    
    Args:
        file_bytes: PDF file content as bytes
        
    Returns:
        First page text string
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            if pdf.pages:
                return pdf.pages[0].extract_text() or ""
    except:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            if reader.pages:
                return reader.pages[0].extract_text() or ""
        except:
            pass
    
    return ""
