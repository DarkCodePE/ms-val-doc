import tempfile
import os
from typing import List, Optional
import io
import base64
import fitz  # Importamos fitz aquí también
from PIL import Image
import re
from fastapi import UploadFile
from pypdf import PdfReader  # Usando pypdf en lugar de PyPDFLoader para control granular
import logging

logger = logging.getLogger(__name__)


async def extract_pdf_text_per_page(file: UploadFile) -> List[str]:
    temp_file_path = None
    page_contents = []
    try:
        # 1. Leemos el contenido del archivo subido
        content = await file.read()

        # 2. Creamos un archivo temporal
        temp_fd, temp_file_path = tempfile.mkstemp(suffix='.pdf')

        # 3. Escribimos el contenido en el archivo temporal
        with os.fdopen(temp_fd, 'wb') as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()

        # 4. Leemos el PDF y extraemos el texto
        reader = PdfReader(temp_file_path)
        for page in reader.pages:
            text = page.extract_text()
            page_contents.append(text)

    except Exception as e:
        logger.error(f"Error extracting PDF text per page: {str(e)}")
        raise ValueError(f"Error extracting PDF text per page: {str(e)}")
    finally:
        # 5. Limpieza: eliminamos el archivo temporal
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)  # Elimina el archivo temporal
            except Exception as e:
                logger.warning(f"Could not delete temporary file {temp_file_path}: {str(e)}")
                raise ValueError(f"Could not delete temporary file {temp_file_path}: {str(e)}")
        await file.seek(0)  # Reiniciamos el puntero del archivo

    return page_contents


async def pdf_page_to_base64_image(file: UploadFile, page_num: int) -> str:
    """Convierte una página específica de un PDF (UploadFile) a una imagen base64."""
    content = await file.read()
    memory_stream = io.BytesIO(content)
    pdf_document = fitz.open(stream=memory_stream, filetype="pdf")

    if page_num < 1 or page_num > pdf_document.page_count:
        raise ValueError(
            f"Número de página inválido: {page_num}. El documento tiene {pdf_document.page_count} páginas.")

    page_index = page_num - 1  # fitz indexa desde 0
    page = pdf_document[page_index]
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    await file.seek(0)  # Reset file pointer
    return base64_image


# Lista de empresas aseguradoras conocidas
INSURANCE_COMPANIES = {
    "MAPFRE": ["MAPFRE", "MAPFRE PERU"],
    "PACIFICO": ["PACIFICO", "PACIFICO SEGUROS", "PACIFICO EPS"],
    "RIMAC": ["RIMAC", "RIMAC SEGUROS"],
    "SANITAS": ["SANITAS", "SANITAS PERU"],
    "LA POSITIVA": ["LA POSITIVA", "LA POSITIVA VIDA"]
}


def _identify_company_from_filename(filename: str) -> Optional[str]:
    """Identifica la empresa aseguradora a partir del nombre del archivo."""
    # Se limpia y estandariza el nombre del archivo.
    clean_filename = re.sub(r'\.[^.]+$', '', filename.upper())
    clean_filename = re.sub(r'[^A-Z0-9\s]', ' ', clean_filename)

    for company, variations in INSURANCE_COMPANIES.items():
        if any(variation.upper() in clean_filename for variation in variations):
            logger.info(f"Empresa identificada por nombre de archivo: {company}")
            return company
    return None


async def _extract_pdf_text(file) -> str:
    """
    Extrae todo el texto de un PDF utilizando PyMuPDF (fitz).
    Se asegura de reiniciar el puntero del archivo después de la lectura.
    """
    content = await file.read()
    with io.BytesIO(content) as memory_stream:
        with fitz.open(stream=memory_stream, filetype="pdf") as pdf_document:
            text_content = [page.get_text() for page in pdf_document]
    await file.seek(0)
    return "\n".join(text_content)


def _identify_company_from_text(text: str) -> Optional[str]:
    """Identifica la empresa aseguradora presente en el contenido del texto."""
    text_upper = text.upper()
    for company, variations in INSURANCE_COMPANIES.items():
        if any(variation.upper() in text_upper for variation in variations):
            logger.info(f"Empresa identificada en el texto: {company}")
            return company
    return None


async def extract_name_enterprise(file: UploadFile) -> str:
    """
    Extrae texto y metadata del PDF.
    Primero intenta identificar la empresa a partir del nombre del archivo;
    si no se encuentra, extrae el texto completo para identificarla.
    """
    try:

        if not file:
            raise ValueError("No se encontró el archivo en el estado.")

        # Intentar identificar la empresa por el nombre del archivo.
        company = _identify_company_from_filename(file.filename)

        # Si no se identifica, extraer el texto completo del PDF y buscar en él.

        if not company:
            full_text = await _extract_pdf_text(file)
            company = _identify_company_from_text(full_text)
            # Almacenar el texto extraído para posteriores procesos.
            # state["document_data"] = full_text

        return company

    except Exception as e:
        raise ValueError(f"Error extracting text and metadata: {e}")
