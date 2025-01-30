from typing import List

from fastapi import UploadFile
from langchain_core.messages import HumanMessage, SystemMessage
import fitz
import base64
import io
from PIL import Image
import logging

from app.agent.instructions.prompt import LOGO_DETECTION_PROMPT
from app.agent.state.state import DocumentValidationResponse, LogoValidationDetails
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

    async def pdf_to_base64_images(self, file: UploadFile) -> List[str]:
        """Convert all PDF pages to base64 encoded images from UploadFile"""
        base64_images = []

        # Read file into memory
        content = await file.read()
        memory_stream = io.BytesIO(content)

        # Open PDF from memory stream
        pdf_document = fitz.open(stream=memory_stream, filetype="pdf")

        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
            base64_images.append(base64_image)

        # Reset file pointer for future reads
        await file.seek(0)

        return base64_images

    async def verify_signatures(self, state: DocumentValidationResponse) -> dict:
        """Verify signatures using multimodal LLM and OpenCV"""
        try:
            # Get base64 images of all pages
            base64_images = await self.pdf_to_base64_images(state["file"])
            logger.debug(f"Base64 images: {base64_images}")
            # Initialize signature verification results
            signatures_found = []

            # Check each page for signatures
            for page_num, base64_image in enumerate(base64_images, 1):
                logger.debug(f"Checking page {page_num} for signatures")
                # Convert base64 image to PIL Image
                structured_llm = self.primary_llm.with_structured_output(LogoValidationDetails)
                system_instructions = LOGO_DETECTION_PROMPT.format(
                    enterprise=state["valid_data"]["enterprise"]
                )
                logger.debug(f"System instructions: {system_instructions}")
                human_message = HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": "Identifica si hay firmas en esta página. "
                                    "Si hay, describe su ubicación y características."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_images}"}
                        }
                    ]
                )
                response = structured_llm.invoke([
                    SystemMessage(content=system_instructions),
                    human_message
                ])
                signatures_found.append(response)
            state["logo_diagnosis"] = signatures_found
            # Return verification results
            return state

        except Exception as e:
            logger.error(f"Error verifying signatures: {str(e)}")
            raise

    def cleanup(self):
        """Cleanup resources if needed"""
        pass
