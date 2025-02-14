from typing import List

from fastapi import UploadFile
from langchain_core.messages import HumanMessage, SystemMessage
import fitz
import base64
import io
from PIL import Image
import logging

from app.agent.instructions.single import LOGO_DETECTION_PROMPT

from app.agent.state.state import OverallState, LogoValidationDetails
from app.agent.utils.pdf_utils import extract_pdf_text
from app.agent.utils.util import extract_name_enterprise
from app.config.config import get_settings
from app.providers.llm_manager import LLMConfig, LLMManager, LLMType

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class SingleLogoAgent:
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

    @staticmethod
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

    async def verify_logo(self, state: OverallState) -> dict:
        """Verify logos and store diagnosis per page."""
        try:
            base64_images = await self.pdf_to_base64_images(self, state["file_logo"])
            logger.debug(f"Base64 images: {base64_images}")
            logo_diagnosis_per_page: List[LogoValidationDetails] = []  # Change to PageLogoValidationDetails
            try:
                enterprise = await extract_name_enterprise(state["file_logo"])
            except Exception as e:
                enterprise = ""
            document_data = await extract_pdf_text(state["file_logo"])

            for page_num, base64_image in enumerate(base64_images, 1):
                logger.debug(f"Checking page {page_num} for logo")
                structured_llm = self.primary_llm.with_structured_output(LogoValidationDetails)
                system_instructions = LOGO_DETECTION_PROMPT.format(
                    enterprise=enterprise,
                    document_data=document_data
                )

                human_message = HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": f"Identifica si hay logotipo en esta página {page_num}. "  # Page number in prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                )
                response = structured_llm.invoke([
                    SystemMessage(content=system_instructions),
                    human_message
                ])

                # 2. Create PageLogoValidationDetails and append to list
                page_logo_detail = LogoValidationDetails(  # Create PageLogoValidationDetails object
                    logo=response["logo"],
                    logo_status=response["logo_status"],
                    diagnostics=response["diagnostics"],
                    signature_status=response["signature_status"],
                    page_num=page_num  # Add page_num here
                )
                logo_diagnosis_per_page.append(page_logo_detail)  # Append PageLogoValidationDetails
            #state["enterprise"] = enterprise
            state["logo_diagnosis"] = logo_diagnosis_per_page  # Store the list of PageLogoValidationDetails
            return state

        except Exception as e:
            logger.error(f"Error verifying logo: {str(e)}")
            raise

    def cleanup(self):
        """Cleanup resources if needed"""
        pass
