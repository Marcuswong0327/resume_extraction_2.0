import pdfplumber
from PyPDF2 import PdfReader
import io
from typing import Tuple, List, Optional
from pdf2image import convert_from_bytes
from PIL import Image
import base64


def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, bool]:
    """
    Extract text from PDF file bytes.
    Uses pdfplumber as primary method, falls back to PyPDF2 if needed.
    Also detects if PDF is image-based (scanned).
    
    Args:
        file_bytes: PDF file content as bytes
        
    Returns:
        Tuple of (extracted_text, is_image_based)
    """
    text = ""
    
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            max_pages = min(len(pdf.pages), 2)
            
            for i in range(max_pages):
                page = pdf.pages[i]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    
        if text.strip():
            is_image_based = is_minimal_text(text)
            return text, is_image_based
            
    except Exception as e:
        print(f"pdfplumber failed: {e}")
    
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
    
    is_image_based = is_minimal_text(text)
    return text, is_image_based


def is_minimal_text(text: str) -> bool:
    """
    Determine if extracted text is too minimal (likely image-based PDF).
    
    Args:
        text: Extracted text
        
    Returns:
        True if text appears to be from an image-based PDF
    """
    if not text:
        return True
    
    cleaned_text = text.strip()
    word_count = len(cleaned_text.split())
    char_count = len(cleaned_text)
    
    if word_count < 15 or char_count < 100:
        return True
    
    return False


def convert_pdf_to_images(file_bytes: bytes, max_pages: int = 1) -> List[Image.Image]:
    """
    Convert PDF pages to PIL Images for vision API processing.
    
    Args:
        file_bytes: PDF file content as bytes
        max_pages: Maximum number of pages to convert
        
    Returns:
        List of PIL Image objects
    """
    try:
        images = convert_from_bytes(
            file_bytes,
            first_page=1,
            last_page=max_pages,
            dpi=150
        )
        return images
    except Exception as e:
        print(f"PDF to image conversion failed: {e}")
        return []


def image_to_base64(image: Image.Image) -> str:
    """
    Convert PIL Image to base64 string for API.
    
    Args:
        image: PIL Image object
        
    Returns:
        Base64 encoded string
    """
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


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
