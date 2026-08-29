from pypdf import PdfReader
import io

def extract_text_from_pdf(pdf_file) -> str:
    """
    Extracts text from an uploaded Streamlit file or a file path.
    """
    try:
        if isinstance(pdf_file, str):
            reader = PdfReader(pdf_file)
        else:
            reader = PdfReader(io.BytesIO(pdf_file.getvalue()))
        
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""
