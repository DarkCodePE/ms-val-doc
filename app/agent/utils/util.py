import re
from datetime import datetime
from typing import Optional, List
from fastapi import UploadFile

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.config.config import get_settings
import fitz
import io
from app.agent.utils.pdf_utils import extract_pdf_text, pdf_page_to_base64_image, pdf_to_base64_images, \
    extract_pdf_text_per_page
from app.providers.llm import LLMType
from app.providers.llm_manager import LLMManager
import logging

logger = logging.getLogger(__name__)

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
    clean_filename = re.sub(r'\.[^.]+$', '', filename.upper())
    clean_filename = re.sub(r'[^A-Z0-9\s]', ' ', clean_filename)

    for company, variations in INSURANCE_COMPANIES.items():
        if any(variation.upper() in clean_filename for variation in variations):
            logger.info(f"Empresa identificada por nombre de archivo: {company}")
            return company
    return None


def _identify_company_from_text(text: str) -> Optional[str]:
    """Identifica la empresa aseguradora presente en el contenido del texto."""
    text_upper = text.upper()
    for company, variations in INSURANCE_COMPANIES.items():
        if any(variation.upper() in text_upper for variation in variations):
            logger.info(f"Empresa identificada en el texto: {company}")
            return company
    return None


async def extract_name_enterprise(file: UploadFile) -> str:
    """Extrae nombre de la empresa del PDF."""
    try:
        if not file:
            raise ValueError("No se encontró el archivo en el estado.")

        company = _identify_company_from_filename(file.filename)

        if not company:
            full_text = await extract_pdf_text(file)
            company = _identify_company_from_text(full_text)

        return company

    except Exception as e:
        raise ValueError(f"Error extracting text and metadata: {e}")


async def semantic_segment_pdf_with_llm(file: UploadFile, llm_manager: LLMManager) -> List[str]:
    """Semantically segments a specific page of a PDF document using a multimodal LLM."""
    base64_image = await pdf_to_base64_images(file)  # Convert PDF page to base64
    primary_llm = llm_manager.get_llm(LLMType.GPT_4O_MINI)

    segmentation_prompt = """
    Analyze the image of the PDF page and segment it into logical, semantically distinct sections.

    Identify sections based on:
    - Document titles and headings that indicate the start of a new section (e.g., "CONSTANCIA Nº", "Estimados Señores:", "Nº", "APELLIDOS Y NOMBRES", "Ref.:").
    - Distinct blocks of text that serve different purposes within the document (e.g., company information, recipient details, body text, tables of data, footer).
    - Visual separators or changes in layout if they clearly delineate different content areas (though rely more on text content for semantic segmentation).
    - Logical flow and coherence of information. Group related text blocks together into meaningful sections.
    
    Specifically aim to identify and separate sections like:
    - **Header/Company Information:**  Company logos, names, addresses, dates at the top.
    - **Document Title/Identification:** The main title of the document (e.g., "CONSTANCIA Nº 4440435").
    - **Recipient Information:** "Señores", company name, "Presente.-".
    - **Reference Line:** "Ref.:" and the subject of the document.
    - **Salutation/Greeting:** "Estimados Señores:".
    - **Body Text/Main Content:** Paragraphs of explanatory text.
    - **Tables of Data:**  Structured data like employee lists with columns "Nº", "APELLIDOS Y NOMBRES", "NRO. DOCUMENTO", "INICIO DE COBERTURA". Segment each table as a separate section if applicable.
    - **Footer/Contact Information:**  Office addresses, contact numbers, website addresses at the bottom.
    - **Signatures/Authorization Blocks:** (If present and distinct).

    **Page Image (Base64 Encoded):**
    [Start Image] data:image/jpeg;base64,{base64_image} [End Image]

    **Output Format:**
    Return a Python list of strings. Each string should be the text content of a semantically distinct section identified in the image.  Ensure that the sections are logically separated and represent different parts of the document's information. If some parts are very short and logically belong to a larger section (e.g., "Presente.-" with "Señores"), you can include them in the larger section. If no clear semantic sections are identifiable beyond the entire document, return a list containing the entire text content of the page as a single section.
    """

    response = await primary_llm.ainvoke([
        SystemMessage(
            content="You are a helpful assistant for segmenting PDF pages into semantic sections based on visual analysis of the page image."),
        HumanMessage(content=[
            {"type": "text", "text": segmentation_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]),
    ])
    logger.debug(f"Segmentation response: {response}")
    segmented_sections = [
        section.strip()
        for section in response.content.strip().split("\n\n")  # Adjust parsing if needed based on model output
        if section.strip()
    ]

    return segmented_sections


async def _extract_pdf_text(self, file) -> str:
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


async def semantic_segment_pdf_with_llm_v2(file: UploadFile, llm_manager: LLMManager) -> List[str]:
    """Semantically segments a specific page of a PDF document using a multimodal LLM."""
    base64_image = await pdf_to_base64_images(file)  # Convert PDF page to base64
    #print(f"base64_image: {base64_image}")
    extracted_text = await extract_pdf_text(file)
    primary_llm = llm_manager.get_llm(LLMType.GPT_4O_MINI)

    segmentation_prompt = """
    Analyze the following compiled text {compiled_text_document} representing an entire PDF document, which was extracted page by page using an LLM. Now, perform semantic segmentation on this **compiled text** to divide it into logical, semantically distinct sections that may span **across multiple original pages**.
    
    **Compiled Text from the Entire PDF Document (Extracted page by page):**
    [Start Compiled Text]
    {compiled_text_document}
    [End Compiled Text]
    
    Identify sections based on:

    Document titles and headings that indicate the start of a new section. Detect variations such as "CONSTANCIA", "CONSTANCIA Nº", or phrases including "Seguro Complementario de Trabajo de Riesgo". Even if a number is not present, treat the title as a section header.
    Header/Company Information: Look for company details (e.g., "Oficina Principal", "Central Administrativa", "RUC:", "VIGENCIA:", "ACTIVIDAD:", "Issue Date:", "Signature Date:", "Policy Number:", "Company Name:"") and dates that are typically at the top of the page.
    Recipient Information: Identify salutations or address blocks, such as "Señores", "Presente.-", or similar variants.
    Reference Line: Detect sections that begin with "Ref:" or similar markers.
    Disclaimer/Notes: Identify any text that begins with an asterisk (*) or contains key phrases like "No se brindara cobertura" as a distinct disclaimer or note section.
    Salutation/Greeting: Look for common greetings like "Estimados Señores:".
    Main Body Content: Group explanatory paragraphs, contractual details, or policy information.
    Tables of Data: Identify structured data sections. Even if the table header differs (for instance, "Nro. Nombres Apellido Paterno Apellido Materno Nro. Documento"), detect rows with numerical ordering and personal data to segment the table as an independent section.
    Footer/Signatures: Capture concluding information such as sign-off phrases, names, roles (e.g., "GERENTE"), dates, and web addresses.


    Ensure that:
    **Multi-Page Sections Allowed:** Sections in the output list *can* contain text extracted from multiple pages if they represent a single semantic unit (like a multi-page table or a body text section spanning pages).
    **Single Table Section:**  A table that spans multiple pages should be represented as **one single string** in the output list, containing all the text content of the entire table.
    **Grouping Short/Related Sections:** As before, group very short, dependent phrases within larger sections.
    **Minimal Segmentation:** If the document is very simple and no clear semantic sections are identifiable beyond the entire document, return a **list containing the entire extracted text content of the *entire document* as a single string element.*
    The segmentation is flexible enough to account for slight variations in wording and layout across different documents.
    If some parts are very short and logically belong to a larger section (e.g., "Presente.-" next to "Señores"), they should be combined.
    If no clear distinct sections are identifiable beyond the entire text, return a list with the entire text content as a single section.
    If the issue date is detected in other pages, include it in the text output as part of the header or a separate section.
    
 
    **Output Format:**
     Processing multi-page documents, the segmentation reflects the document's overall semantic structure, not just page-by-page content and then combine them into a single string .Make sure the answer is only a single string
    """
    system_instructions = segmentation_prompt.format(compiled_text_document=extracted_text)
    response = await primary_llm.ainvoke([
        system_instructions,
        HumanMessage(content="You are a helpful assistant for segmenting PDF pages into semantic sections"),
    ])
    # print(f"Segmentation response: {response}")
    segmented_sections = [
        section.strip()
        for section in response.content.strip().split("\n\n")  # Adjust parsing if needed based on model output
        if section.strip()
    ]
    #print(f"Segmented sections: {response.content.strip()}")
    return [response.content.strip()]


async def semantic_segment_pdf_with_llm_v3(file: UploadFile, llm_manager: LLMManager) -> List[str]:
    """Semantically segments a specific page of a PDF document using a multimodal LLM."""
    base64_image = await pdf_to_base64_images(file)  # Convert PDF page to base64
    extracted_text = await extract_pdf_text(file)
    primary_llm = llm_manager.get_llm(LLMType.GPT_4O_MINI)

    segmentation_prompt = """
    Analyze the image of the PDF page and segment it into logical, semantically distinct sections.

    Identify sections based on:

    Document titles and headings that indicate the start of a new section. Detect variations such as "CONSTANCIA", "CONSTANCIA Nº", or phrases including "Seguro Complementario de Trabajo de Riesgo". Even if a number is not present, treat the title as a section header.
    Header/Company Information: Look for company details (e.g., "Oficina Principal", "Central Administrativa", "RUC:", "VIGENCIA:", "ACTIVIDAD:", "Issue Date:", "Signature Date:", "Policy Number:", "Company Name:"") and dates that are typically at the top of the page.
    Recipient Information: Identify salutations or address blocks, such as "Señores", "Presente.-", or similar variants.
    Reference Line: Detect sections that begin with "Ref:" or similar markers.
    Disclaimer/Notes: Identify any text that begins with an asterisk (*) or contains key phrases like "No se brindara cobertura" as a distinct disclaimer or note section.
    Salutation/Greeting: Look for common greetings like "Estimados Señores:".
    Main Body Content: Group explanatory paragraphs, contractual details, or policy information.
    Tables of Data: Identify structured data sections. Even if the table header differs (for instance, "Nro. Nombres Apellido Paterno Apellido Materno Nro. Documento"), detect rows with numerical ordering and personal data to segment the table as an independent section.
    Footer/Signatures: Capture concluding information such as sign-off phrases, names, roles (e.g., "GERENTE"), dates, and web addresses.


    Ensure that:
    The segmentation is flexible enough to account for slight variations in wording and layout across different documents.
    If some parts are very short and logically belong to a larger section (e.g., "Presente.-" next to "Señores"), they should be combined.
    If no clear distinct sections are identifiable beyond the entire text, return a list with the entire text content as a single section.
    If the issue date is detected in other pages, include it in the text output as part of the header or a separate section.

     **Page Image (Base64 Encoded):**
    [Start Image] data:image/jpeg;base64,{base64_image} [End 

    **Texto extraído:**
    {extracted_text}

    **Output Format:**
    Return a Python list of strings, where each string is the text content of a semantically distinct section identified in the image.
    """

    response = await primary_llm.ainvoke([
        SystemMessage(
            content="You are a helpful assistant for segmenting PDF pages into semantic sections based on visual analysis of the page image."),
        HumanMessage(content=[
            {"type": "text", "text": segmentation_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
            {"type": "text", "text": extracted_text}
        ]),
    ])
    # print(f"Segmentation response: {response}")
    segmented_sections = [
        section.strip()
        for section in response.content.strip().split("\n\n")  # Adjust parsing if needed based on model output
        if section.strip()
    ]
    # print(f"Segmented sections: {segmented_sections}")
    return segmented_sections


def convertir_fecha_spanish(fecha_str: str) -> str:
    # Mapeo de meses en español a números
    meses = {
        "enero": "01",
        "febrero": "02",
        "marzo": "03",
        "abril": "04",
        "mayo": "05",
        "junio": "06",
        "julio": "07",
        "agosto": "08",
        "septiembre": "09",
        "octubre": "10",
        "noviembre": "11",
        "diciembre": "12"
    }

    # Suponiendo que el formato es "31 de enero de 2024"
    partes = fecha_str.lower().split(" de ")
    if len(partes) == 3:
        dia = partes[0].strip()
        mes_palabra = partes[1].strip()
        anio = partes[2].strip()
        mes = meses.get(mes_palabra, "00")
        # Aseguramos que el día tenga dos dígitos
        if len(dia) == 1:
            dia = f"0{dia}"
        return f"{dia}/{mes}/{anio}"
    else:
        return fecha_str  # En caso de un formato inesperado


def convertir_fecha_spanish_v2(fecha_str: str) -> str:
    """
    Convierte fechas en español a formato dd/mm/yyyy.
    Maneja múltiples formatos, por ejemplo:
      - "31 de enero de 2024"
      - "31 de enero del 2024"
      - "23 de Enero del 2025"
    Si el formato no es reconocido, devuelve la fecha original.
    """
    meses = {
        "enero": "01",
        "febrero": "02",
        "marzo": "03",
        "abril": "04",
        "mayo": "05",
        "junio": "06",
        "julio": "07",
        "agosto": "08",
        "septiembre": "09",
        "octubre": "10",
        "noviembre": "11",
        "diciembre": "12"
    }

    try:
        # Normalizar la cadena: convertir a minúsculas y manejar 'del' o 'de'
        fecha_str_norm = fecha_str.lower().replace(" del ", " de ")
        partes = fecha_str_norm.split(" de ")

        # Se espera al menos: día, mes y año
        if len(partes) >= 3:
            dia = partes[0].strip()
            mes_palabra = partes[1].strip()
            anio = partes[-1].strip()
            mes = meses.get(mes_palabra)
            if mes is None:
                # Si el nombre del mes no es reconocido, devolver la fecha original
                return fecha_str
            # Asegurar que el día tenga dos dígitos
            if len(dia) == 1:
                dia = f"0{dia}"
            # Validar que día y año sean números
            int(dia)
            int(anio)
            return f"{dia}/{mes}/{anio}"
        else:
            return fecha_str
    except Exception:
        # En caso de error, se devuelve la cadena original sin modificar
        return fecha_str


def es_fecha_emision_valida(date_of_issuance: str, end_date_validity: str) -> bool:
    """
    Compara si la fecha de emisión (date_of_issuance) no es mayor que la fecha fin de vigencia (end_date_validity).
    Ambas fechas deben estar en formato "dd/mm/yyyy".
    """
    fecha_emision = datetime.strptime(date_of_issuance, "%d/%m/%Y")
    fecha_fin_vigencia = datetime.strptime(end_date_validity, "%d/%m/%Y")
    return fecha_emision <= fecha_fin_vigencia


def es_fecha_vigencia_valida(end_date_validity: str, reference_date: str = None) -> bool:
    """
    Valida que la fecha fin de vigencia (end_date_validity) en formato "dd/mm/yyyy"
    no esté vencida respecto a una fecha de referencia.
    Si no se suministra reference_date, se utiliza la fecha actual.
    """
    fecha_fin_vigencia = datetime.strptime(end_date_validity, "%d/%m/%Y")
    if reference_date is None:
        ref_date = datetime.now()
    else:
        ref_date = datetime.strptime(reference_date, "%d/%m/%Y")

    print(f"ref_date: {ref_date}")
    return ref_date <= fecha_fin_vigencia


def es_fecha_emision_valida_compile(date_of_issuance: str, end_date_validity: str, reference_date: str = None) -> bool:
    """
    Valida que:
    1. La fecha de emisión (date_of_issuance) en formato "dd/mm/yyyy" no sea posterior a la fecha fin de vigencia (end_date_validity).
    2. La fecha fin de vigencia no esté vencida respecto a una fecha de referencia.
       Si no se suministra reference_date, se asume la fecha actual.
    """
    fecha_emision = datetime.strptime(date_of_issuance, "%d/%m/%Y")
    fecha_fin_vigencia = datetime.strptime(end_date_validity, "%d/%m/%Y")

    if reference_date is None:
        ref_date = datetime.now()
    else:
        ref_date = datetime.strptime(reference_date, "%d/%m/%Y")

    return fecha_emision <= fecha_fin_vigencia and ref_date <= fecha_fin_vigencia


async def count_pdf_pages(pdf_file: UploadFile) -> int:
    """Count total pages in PDF file using PyMuPDF."""
    try:
        content = await pdf_file.read()
        memory_stream = io.BytesIO(content)
        pdf_document = fitz.open(stream=memory_stream, filetype="pdf")
        page_count = pdf_document.page_count
        return page_count
    finally:
        await pdf_file.seek(0)
