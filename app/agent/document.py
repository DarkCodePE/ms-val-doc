from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.instructions.prompt import DOCUMENT_PROCESSOR
from app.agent.loader import extract_text_with_pypdfloader
from app.agent.state.state import DocumentValidationDetails, DocumentValidationResponse
from app.config.config import get_settings
import fitz
import io
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from app.providers.llm_manager import LLMConfig, LLMManager, LLMType
import logging
import re

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DocumentAgent:
    """
   Agente para la extracción y procesamiento de documentos PDF.
   Se encarga de identificar la empresa aseguradora, extraer el contenido del documento y procesar los datos clave.
   """
    def __init__(self, settings=None):
        """Initialize ReportCompiler with configuration settings.

                Args:
                    settings: Optional application settings. If None, will load default settings.
                """
        self.settings = settings or get_settings()
        # Initialize LLM manager with compilation-specific configuration
        llm_config = LLMConfig(
            temperature=0.0,  # Use deterministic output for compilation
            streaming=False,
            max_tokens=4000  # Larger context for final compilation
        )
        self.llm_manager = LLMManager(llm_config)
        # Get the primary LLM for report generation
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    # Lista de empresas aseguradoras conocidas
    INSURANCE_COMPANIES = {
        "MAPFRE": ["MAPFRE", "MAPFRE PERU"],
        "PACIFICO": ["PACIFICO", "PACIFICO SEGUROS", "PACIFICO EPS"],
        "RIMAC": ["RIMAC", "RIMAC SEGUROS"],
        "SANITAS": ["SANITAS", "SANITAS PERU"],
        "LA POSITIVA": ["LA POSITIVA", "LA POSITIVA VIDA"]
    }

    def _identify_company_from_filename(self, filename: str) -> Optional[str]:
        """Identifica la empresa aseguradora a partir del nombre del archivo."""
        # Se limpia y estandariza el nombre del archivo.
        clean_filename = re.sub(r'\.[^.]+$', '', filename.upper())
        clean_filename = re.sub(r'[^A-Z0-9\s]', ' ', clean_filename)

        for company, variations in self.INSURANCE_COMPANIES.items():
            if any(variation.upper() in clean_filename for variation in variations):
                logger.info(f"Empresa identificada por nombre de archivo: {company}")
                return company
        return None

    def _identify_company_from_text(self, text: str) -> Optional[str]:
        """Identifica la empresa aseguradora presente en el contenido del texto."""
        text_upper = text.upper()
        for company, variations in self.INSURANCE_COMPANIES.items():
            if any(variation.upper() in text_upper for variation in variations):
                logger.info(f"Empresa identificada en el texto: {company}")
                return company
        return None

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

    async def extract_text_node(self, state: dict) -> dict:
        """
        Extrae texto y metadata del PDF.
        Primero intenta identificar la empresa a partir del nombre del archivo;
        si no se encuentra, extrae el texto completo para identificarla.
        """
        try:
            file = state.get("file")
            if not file:
                raise ValueError("No se encontró el archivo en el estado.")
            logger.debug(f"Estado ddddddddddddddddddddddd: {state}")
            # Intentar identificar la empresa por el nombre del archivo.
            company = self._identify_company_from_filename(file.filename)
            logger.debug(f"Empresa identificada: {company}")
            # Si no se identifica, extraer el texto completo del PDF y buscar en él.

            if not company:
                full_text = await self._extract_pdf_text(file)
                company = self._identify_company_from_text(full_text)
                # Almacenar el texto extraído para posteriores procesos.
                state["document_data"] = full_text
            logger.debug(f"Empresa identificada: {company}")
            state["valid_data"]["enterprise"] = company
            logger.debug(f"Estado actualizado: {state}")
            return state

        except Exception as e:
            raise ValueError(f"Error extracting text and metadata: {e}")

    async def document_processor(self, state: DocumentValidationResponse) -> dict:
        structured_llm = self.primary_llm.with_structured_output(DocumentValidationDetails)
        logger.info(f"Document Processor Prompt: {state['valid_data']['enterprise']}")
        system_instructions = DOCUMENT_PROCESSOR.format(
            enterprise=state["valid_data"]["enterprise"],
            document_data=state["document_data"]
        )
        result = structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(
                content="Extrae los datos clave de un documento, particularmente la vigencia (fechas o periodos), empresa, póliza")
        ])
        logger.info(f"Document Processor Response: {result}")
        return {"valid_data": result}
