import tempfile
import os
import io
from typing import List
import logging
from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
import fitz
from PIL import Image
import base64

logger = logging.getLogger(__name__)


async def extract_pdf_text(file: UploadFile) -> str:
    """
    Extract text from PDF using PyPDFLoader without saving the file permanently.
    """
    temp_file_path = None
    try:
        content = await file.read()
        temp_fd, temp_file_path = tempfile.mkstemp(suffix='.pdf')

        try:
            with os.fdopen(temp_fd, 'wb') as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()

            loader = PyPDFLoader(temp_file_path)
            pages = loader.load()
            full_text = "\n".join(page.page_content for page in pages)
            return full_text

        finally:
            try:
                os.close(temp_fd)
            except:
                pass

    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        raise ValueError(f"Error extracting PDF text: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Could not delete temporary file {temp_file_path}: {str(e)}")
        await file.seek(0)


async def extract_pdf_text_per_page(file: UploadFile) -> List[str]:
    """Extract text from each page of a PDF file."""
    temp_file_path = None
    page_contents = []
    try:
        content = await file.read()
        temp_fd, temp_file_path = tempfile.mkstemp(suffix='.pdf')

        with os.fdopen(temp_fd, 'wb') as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()

        reader = PyPDFLoader(temp_file_path)
        documents = reader.load()
        page_contents = [doc.page_content for doc in documents]

    except Exception as e:
        logger.error(f"Error extracting PDF text per page: {str(e)}")
        raise ValueError(f"Error extracting PDF text per page: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Could not delete temporary file {temp_file_path}: {str(e)}")
        await file.seek(0)

    return page_contents


async def pdf_to_base64_images(file: UploadFile) -> List[str]:
    """Convert all PDF pages to base64 encoded images."""
    base64_images = []

    content = await file.read()
    memory_stream = io.BytesIO(content)

    pdf_document = fitz.open(stream=memory_stream, filetype="pdf")

    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        base64_images.append(base64_image)

    await file.seek(0)
    return base64_images


async def pdf_page_to_base64_image(file: UploadFile, page_num: int) -> str:
    """Convert a specific page of a PDF to base64 encoded image."""
    content = await file.read()
    memory_stream = io.BytesIO(content)
    pdf_document = fitz.open(stream=memory_stream, filetype="pdf")

    if page_num < 1 or page_num > pdf_document.page_count:
        raise ValueError(f"Invalid page number: {page_num}. Document has {pdf_document.page_count} pages.")

    page_index = page_num - 1
    page = pdf_document[page_index]
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    await file.seek(0)
    return base64_image
