from typing import List

import numpy as np
from fastapi import UploadFile
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import fitz
import base64
import io
from PIL import Image
import logging
import cv2

from app.agent.state.state import SignatureValidationDetails, DocumentValidationResponse
from app.agent.tools.tools import find_signature_bounding_boxes
from app.config.config import get_settings
from app.providers.llm_manager import LLMConfig, LLMManager, LLMType

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class SignatureAgent:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        llm_config = LLMConfig(
            temperature=0.0,
            streaming=False,
            max_tokens=4000
        )
        self.llm_manager = LLMManager(llm_config)
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    async def pdf_to_images(self, file: UploadFile) -> List[np.ndarray]:
        """Convierte PDF a lista de imágenes para OpenCV"""
        content = await file.read()
        memory_stream = io.BytesIO(content)

        pdf_document = fitz.open(stream=memory_stream, filetype="pdf")
        images = []

        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))

            # Convertir a formato numpy para OpenCV
            img_array = np.frombuffer(pix.samples, dtype=np.uint8)

            width, height = pix.width, pix.height
            if pix.alpha:
                img_array = img_array.reshape(height, width, 4)
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            else:
                img_array = img_array.reshape(height, width, 3)

            images.append(img_array)

        await file.seek(0)
        return images

    def convert_signature_to_dict(self, signature: tuple) -> dict:
        """Convierte una tupla de firma en un diccionario"""
        left, top, width, height = signature
        return {
            "left": int(left),
            "top": int(top),
            "width": int(width),
            "height": int(height)
        }

    async def verify_signatures(self, state: DocumentValidationResponse) -> dict:
        """Detecta firmas usando OpenCV"""
        try:
            # Convertir PDF a imágenes
            cv_images = await self.pdf_to_images(state["file"])
            signature_diagnosis = []

            # Procesar cada página
            for page_num, img in enumerate(cv_images, 1):
                # Detectar firmas
                signatures = find_signature_bounding_boxes(img)
                signatures_dict = [self.convert_signature_to_dict(sig) for sig in signatures]

                # Crear resultado de la página
                page_result = {
                    "signature": f"Página {page_num}",
                    "signature_status": len(signatures) > 0,
                    "metadata": {
                        "page_number": page_num,
                        "signatures_found": len(signatures),
                        "signatures_details": signatures_dict
                    }
                }

                signature_diagnosis.append(page_result)
                logger.debug(f"Processed page {page_num}, found {len(signatures)} signatures")

            state["signature_diagnosis"] = signature_diagnosis
            return state

        except Exception as e:
            logger.error(f"Error en detección de firmas: {str(e)}")
            raise

    def cleanup(self):
        """Limpia recursos si es necesario"""
        pass
