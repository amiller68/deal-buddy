from io import BytesIO
import shutil
import asyncio
from typing import BinaryIO, AsyncGenerator, Tuple
import PyPDF2
from pdf2image import convert_from_bytes

async def extract_pdf(pdf_stream: BinaryIO) -> AsyncGenerator[Tuple[str, bytes, int], None]:
    """Extract text and images from PDF in parallel"""
    pdf_stream.seek(0)
    
    if not shutil.which('pdftoppm'):
        raise RuntimeError("Poppler is required but not installed.")

    pdf_data = pdf_stream.read()
    text_stream = BytesIO(pdf_data)
    image_stream = BytesIO(pdf_data)

    async def extract_text():
        reader = PyPDF2.PdfReader(text_stream)
        total_pages = len(reader.pages)
        return [[page.extract_text(), total_pages] for page in reader.pages]

    async def extract_images():
        try:
            images = convert_from_bytes(image_stream.read())
            image_data = []
            for img in images:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=95)
                image_data.append(buffer.getvalue())
            return image_data
        except Exception as e:
            raise RuntimeError(f"Failed to convert PDF images: {str(e)}") from e

    texts, images = await asyncio.gather(extract_text(), extract_images())
    
    for [text, total_pages], image in zip(texts, images):
        yield text, image, total_pages
