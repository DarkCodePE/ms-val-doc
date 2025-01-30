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
        """Identifica la empresa aseguradora basado en el nombre del archivo."""
        filename_upper = filename.upper()
        clean_filename = re.sub(r'\.[^.]+$', '', filename_upper)
        clean_filename = re.sub(r'[^A-Z0-9\s]', ' ', clean_filename)

        for company, variations in self.INSURANCE_COMPANIES.items():
            if any(variation.upper() in clean_filename for variation in variations):
                logger.info(f"Empresa identificada por nombre de archivo: {company}")
                return company

        return None

    def _identify_company_from_text(self, text: str) -> Optional[str]:
        """Identifica la empresa aseguradora del texto del documento."""
        # Buscar menciones directas de empresas conocidas
        for company, variations in self.INSURANCE_COMPANIES.items():
            if any(variation.upper() in text.upper() for variation in variations):
                logger.info(f"Empresa identificada en el texto: {company}")
                return company
        return None

    async def extract_text_node(self, state: dict) -> dict:
        """
        Extrae texto y metadata del PDF, con validación por nombre de archivo primero.
        """
        try:
            data = state["valid_data"]
            file = state["file"]
            # 1. Intentar identificar por nombre de archivo
            company = self._identify_company_from_filename(file.filename)

            if not company:
                # 2. Si no se encontró, buscar en el contenido
                content = await file.read()
                memory_stream = io.BytesIO(content)
                pdf_document = fitz.open(stream=memory_stream, filetype="pdf")

                text_content = []
                for page in pdf_document:
                    text_content.append(page.get_text())

                full_text = "\n".join(text_content)
                company = self._identify_company_from_text(full_text)

                pdf_document.close()
                await file.seek(0)

            data["enterprise"] = company
            logger.debug(f"Actualizado el estado")
            logger.debug(f"Estado actualizado: {data}")

            return state

        except Exception as e:
            raise ValueError(f"Error extracting text and metadata: {str(e)}")

    def validate(self, document_data: str):
        try:
            result = self.format_chain.invoke({"document_data": document_data})
            return result["formatted_output"]
        except Exception as e:
            raise ValueError(f"Error during document validation: {e}")

    async def document_processor(self, state: DocumentValidationResponse) -> dict:
        structured_llm = self.primary_llm.with_structured_output(DocumentValidationDetails)
        logger.info(f"Document Processor Prompt: {state['valid_data']['enterprise']}")
        system_instructions = DOCUMENT_PROCESSOR.format(
            enterprise=state["valid_data"]["enterprise"]
        )
        HUMAN_PROMPT = """
               Extrae los datos clave de un documento : {document_data}, particularmente la vigencia (fechas o periodos), empresa, póliza
               """
        human_message = HUMAN_PROMPT.format(document_data=state["document_data"])
        logger.info(f"Document Processor Prompt: {system_instructions}")
        result = structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(content="Extrae los datos clave de un documento, particularmente la vigencia (fechas o periodos), empresa, póliza")
        ])
        logger.info(f"Document Processor Response: {result}")
        return {"valid_data": result}
