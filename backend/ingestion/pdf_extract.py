import pypdf

def extract_text_from_pdf(file_path: str) -> str:
    '''
    Extract basic text elements from a PDF using pypdf.
    '''
    text = ""
    with open(file_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text
