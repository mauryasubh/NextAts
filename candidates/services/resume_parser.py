import os
import hashlib
from typing import Optional, Tuple
from django.conf import settings

def _hash_file(file_path: str) -> str:
    """Calculate SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def _parse_pdf(file_path: str) -> str:
    import PyPDF2
    text = ""
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def _parse_docx(file_path: str) -> str:
    import docx
    doc = docx.Document(file_path)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs).strip()

def extract_resume_text(candidate) -> Tuple[bool, Optional[str]]:
    """
    Extracts text from a candidate's resume. 
    Returns (updated, text).
    If the file hash matches the stored hash, returns (False, cached_text).
    """
    if not candidate.resume:
        return False, None
    
    file_path = candidate.resume.path
    if not os.path.exists(file_path):
        return False, None
        
    # Check if the file has changed via SHA-256
    current_hash = _hash_file(file_path)
    if candidate.resume_hash == current_hash and candidate.resume_text:
        return False, candidate.resume_text
        
    # Parsing new or changed file
    ext = file_path.lower().rsplit('.', 1)[-1]
    text = ""
    try:
        if ext == 'pdf':
            text = _parse_pdf(file_path)
        elif ext in ('doc', 'docx'):
            text = _parse_docx(file_path)
        elif ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
        else:
            raise ValueError(f"Unsupported file format: {ext}")
            
        # Clean up text a bit (remove excessive null characters or weird spaces if needed)
        text = text.replace('\x00', '')
        
        # Cache the extracted text and hash
        candidate.resume_text = text[:50000] # Cap size for safety
        candidate.resume_hash = current_hash
        candidate.save(update_fields=['resume_text', 'resume_hash'])
        
        return True, candidate.resume_text
    except Exception as e:
        # We could log the error here
        raise e
