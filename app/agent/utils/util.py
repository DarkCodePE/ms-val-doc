import re
from datetime import datetime
from typing import Optional, List
from fastapi import UploadFile

from langchain_core.messages import SystemMessage, HumanMessage
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
    # (Opcional) Preparar un string que incluya todas las imágenes si se desea enviarlas
    images_str = "[Start Images]\n" + "\n".join(
        f"Page {i + 1} Image: data:image/jpeg;base64,{img}" for i, img in enumerate(base64_image)
    ) + "\n[End Images]"

    segmentation_prompt = """
    Analyze the image and segment it into logical, semantically distinct sections.

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

    **Page Image (Base64 Encoded):**
    [Start Image] data:image/jpeg;base64,{images_str} [End Image]
    
    **Output Format:**
    Return a Python list of strings, where each string is the text content of a semantically distinct section identified in the image.
    """
    print(f"prompt: {segmentation_prompt}")
    response = await primary_llm.ainvoke([
        SystemMessage(
            content="You are a helpful assistant for segmenting PDF pages into semantic sections based on visual analysis of the page image."),
        HumanMessage(content=[
            {"type": "text", "text": segmentation_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
            },
            #{"type": "text", "text": extracted_text}
        ]),
    ])
    # print(f"Segmentation response: {response}")
    segmented_sections = [
        section.strip()
        for section in response.content.strip().split("\n\n")  # Adjust parsing if needed based on model output
        if section.strip()
    ]
    print(f"Segmented sections: {segmented_sections}")
    return segmented_sections


async def semantic_segment_pdf_with_llm_v1(file: UploadFile, llm_manager: LLMManager) -> List[str]:
    """Semantically segments a specific page of a PDF document using a multimodal LLM."""
    base64_image = await pdf_to_base64_images(file)  # Convert PDF page to base64
    extracted_text = await extract_pdf_text_per_page(file)
    primary_llm = llm_manager.get_llm(LLMType.GPT_4O_MINI)
    print("Extracted text: ", extracted_text)
    segmentation_prompt = """
    Analyze the **entire PDF document**, which consists of multiple pages, and perform semantic segmentation to divide it into logical, semantically distinct sections that may span **across multiple pages**.

    **Crucially, process the entire document as a single unit, iterating through all pages to identify sections that are coherent across page breaks.**
    
    Identify sections based on:
    
    **Iterate through all pages of the document and identify document-level sections based on the following criteria:**
    
    Document titles and headings **across the entire document** that indicate the start of a new section. Detect variations such as "CONSTANCIA", "CONSTANCIA Nº", or phrases including "Seguro Complementario de Trabajo de Riesgo" as document-level titles.
    
    Header/Company Information: Look for company details that are **consistent across the headers of all pages** (e.g., "Oficina Principal", "Central Administrativa", "RUC:", "VIGENCIA:", "ACTIVIDAD:", "Issue Date:", "Signature Date:", "Policy Number:", "Company Name:"") and dates that are typically at the top of **each page or the first page**. Assume header information might repeat or slightly vary across pages but represents a single document-level header section.
    
    Recipient Information: Identify salutations or address blocks that are addressed to the recipient of the **entire document**, such as "Señores", "Presente.-", or similar variants, usually appearing at the beginning of the first page and applying to the whole document.
    
    Reference Line: Detect sections that begin with "Ref:" or similar markers, typically at the start of the document and applying document-wide.
    
    Disclaimer/Notes: Identify any text that is **consistently formatted as a disclaimer or note across multiple pages**. Look for text that begins with an asterisk (*) or contains key phrases like "No se brindara cobertura" as a distinct disclaimer or note section that applies to the entire document, even if mentioned on specific pages.
    
    Salutation/Greeting: Look for common greetings like "Estimados Señores:" at the start of the first page, intended for the entire document.
    
    Main Body Content: Group explanatory paragraphs, contractual details, or policy information into coherent sections that may logically flow and **span across multiple pages**. Treat the main body as a continuous flow of information segmented by semantic breaks, not page breaks.
    
    Tables of Data: **Critically identify tables that span multiple pages.**  When iterating through pages, look for repeating table headers and consistent column structure that indicates a single table continuing across pages. Even if the table header differs (for instance, "Nro. Nombres Apellido Paterno Apellido Materno Nro. Documento"), detect rows with numerical ordering, consistent alignment, and personal data to segment the ENTIRE multi-page table as a SINGLE independent section spanning all relevant pages.
    
    Footer/Signatures: Capture concluding information that appears at the end of the **last page of the document**, but also consider footers that may be **consistent or repeating on every page** (like page numbers or company website). Treat consistent footers across pages as a single document-level footer section.  Signatures and authorization blocks will typically be at the end of the *last* page.
    
    Ensure that, when iterating through all pages and segmenting:
    
    **Multi-Page Sections Allowed:** Sections in the output list *must* be able to contain text extracted from multiple pages if they represent a single semantic unit spanning pages (like a multi-page table, a body text section across pages, or a consistent header/footer across pages).
    
    **Single Table Section for Multi-Page Tables:** When iterating through pages, ensure that a table that spans multiple pages is represented as **one single string** in the output list, containing all the text content of the entire table, concatenated from all the pages it occupies. Do not break multi-page tables into page-based segments.
    
    **Grouping Short/Related Sections (Across Pages):** When iterating through pages, continue to group very short, dependent phrases within larger, semantically related sections, considering the context across the entire document.
    
    **Minimal Segmentation for Simple Documents (Entire Document Scope):** If, after iterating through all pages, the document is very simple and no clear semantic sections are identifiable beyond the entire document, return a **list containing the entire extracted text content of the *entire document* as a single string element.** Do not over-segment, especially for simple, short documents.
    
    If you only identify a single segment for the whole document after analyzing all pages, return a list with that single segment containing the entire document's text.
    
    The segmentation must be flexible enough to account for slight variations in wording and layout across different documents, but consistently aim to identify the major semantic components of the **entire PDF document** by iterating through all its pages.
    
    If parts are very short and logically belong to a larger section (e.g., "Presente.-" next to "Señores") across the document, combine them into the larger section.
    
    If no clear distinct sections are identifiable beyond considering the entire text as one block after analyzing all pages, return a list with the entire text content as a single section.
    
    If issue dates, policy numbers, company names, etc., are detected in headers or footers across multiple pages, ensure these are captured within the relevant document-level header/footer sections and are not missed due to page breaks.  Consider headers and footers as potentially document-spanning sections.
    
    **Extracted Text from the Entire Document (for context across all pages):**
    [Start Text] {extracted_text} [End Text]
    
    **Page Images (Base64 Encoded for ALL pages - use for visual context across the entire document, but prioritize TEXT):**
    [Start Images]
    Page 1 Image: data:image/jpeg;base64,{base64_images[0]}
    Page 2 Image: data:image/jpeg;base64,{base64_images[1]}
    ... (and so on for all pages - iterate through all available page images)
    [End Images]
    
    **Output Format:**
    Return a Python list of strings, where each string is the text content of a semantically distinct section identified in the **entire PDF document**, even if that section spans multiple pages.  Ensure that when processing multi-page documents, the segmentation reflects the document's overall semantic structure, not just page-by-page content.
    """
    response = await primary_llm.ainvoke([
        SystemMessage(
            content="You are an expert assistant for segmenting PDF documents into semantic sections. Your primary task is to understand the entire document and divide it into logically and semantically distinct parts that represent the document's overall structure, even if these parts span multiple pages.  You will iterate through all pages of the PDF to achieve this document-level segmentation. Prioritize text and semantic meaning over strict page boundaries."),
        HumanMessage(content=[
            {"type": "text", "text": segmentation_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
            },
            {"type": "text", "text": extracted_text}
        ]),
    ])
    print(f"Segmentation response: {response}")

    segmented_sections = [
        section.strip()
        for section in response.content.strip().split("\n\n")  # Adjust parsing if needed based on model output
        if section.strip()
    ]
    print(f"Segmented sections: {segmented_sections}")
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