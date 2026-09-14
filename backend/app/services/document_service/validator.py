import os

def validate_pdf(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 100

def validate_docx(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 100

def validate_pptx(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 100

def validate_xlsx(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 100
