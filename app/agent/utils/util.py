import re
from typing import Optional, List
from fastapi import UploadFile

from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.utils.pdf_utils import extract_pdf_text, pdf_page_to_base64_image, pdf_to_base64_images
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

    segmented_sections = [
        section.strip()
        for section in response.content.strip().split("\n\n")  # Adjust parsing if needed based on model output
        if section.strip()
    ]

    return segmented_sections
