from typing import List

from fastapi import UploadFile
from langchain_core.messages import HumanMessage, SystemMessage
import fitz
import base64
import io
from PIL import Image
import logging

from app.agent.instructions.prompt import LOGO_DETECTION_PROMPT
from app.agent.state.state import DocumentValidationResponse, LogoValidationDetails, PageContent
from app.config.config import get_settings
from app.providers.llm_manager import LLMConfig, LLMManager, LLMType

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class LogoAgent:
    def __init__(self, settings=None):
        """Initialize LogoAgent with configuration settings.

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

    async def verify_logo(self, state: PageContent) -> dict:
        """Verify signatures using multimodal LLM and OpenCV"""
        #print(f"state: {state}")
        try:

            # Convert base64 image to PIL Image
            structured_llm = self.primary_llm.with_structured_output(LogoValidationDetails)
            system_instructions = LOGO_DETECTION_PROMPT.format(
                enterprise=state["enterprise"],
                company=state["valid_data"]["company"],
                document_data=state["page_content"]
            )
            logger.debug(f"System instructions: {system_instructions}")
            human_message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Identifica si hay logotipo y firma en esta página. "
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{state['page_base64_image']}"}
                    }
                ]
            )
            response = structured_llm.invoke([
                SystemMessage(content=system_instructions),
                human_message
            ])

            state["logo_diagnosis"] = response
            # Return verification results
            return state

        except Exception as e:
            logger.error(f"Error verifying logo: {str(e)}")
            raise

    def cleanup(self):
        """Cleanup resources if needed"""
        pass
