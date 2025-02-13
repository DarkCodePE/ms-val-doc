from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.instructions.prompt import DOCUMENT_PROCESSOR
from app.agent.loader import extract_text_with_pypdfloader
from app.agent.state.state import DocumentValidationDetails, DocumentValidationResponse, PageContent
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


class InfoAgent:
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
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O)

    async def info_processor(self, state: PageContent) -> dict:

        structured_llm = self.primary_llm.with_structured_output(DocumentValidationDetails)

        system_instructions = DOCUMENT_PROCESSOR.format(
            enterprise=state["enterprise"],
            document_data=state["page_content"],
            person=state["person"]
        )

        result = structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(
                content="Extrae los datos clave de un documento, particularmente la vigencia (fechas o periodos), empresa, póliza")
        ])

        state["valid_data"] = result
        return state
