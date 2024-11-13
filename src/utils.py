import PyPDF2


def extract_text_from_pdf_stream(pdf_stream):
    reader = PyPDF2.PdfReader(pdf_stream)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text
