import tempfile
from datetime import datetime
from typing import List, Tuple

import cv2
from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter, Depends, Form
from sqlalchemy import desc
from sqlalchemy.orm import Session
import fitz
import numpy as np
from app.agent.evaluator import DocumentValidatorAgent
from app.agent.loader import extract_text_with_pypdfloader
from app.agent.state.state import DocumentValidationResponse, OverallState
from app.agent.tools.tools import find_signature_bounding_boxes
from app.config.database import get_db
import os
import logging
from langchain_community.document_loaders import PyPDFLoader

from app.workflow.diagnosis_graph import diagnosis_graph
from app.workflow.document_graph import document_graph

logger = logging.getLogger(__name__)

# Verificar que la variable esté configurada
router = APIRouter(prefix="/document", tags=["document"])


@router.post("/validate")
async def validate_document(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
):
    # if not file.filename.endswith(".pdf") or not file.filename.endswith(".PDF"):
    #     raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF.")

    # Guarda el archivo localmente
    directory = "uploaded_files/"
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_path = os.path.join(directory, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    logger.debug(f"Archivo guardado en {file_path}")
    print(f"Archivo guardado en {file_path}")
    # Validar el documento

    try:
        pages = extract_text_with_pypdfloader(file_path)
        doc_text = " ".join([page.page_content for page in pages])  # Unimos el contenido de todas las páginas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer el PDF: {str(e)}")

    try:
        document_validator = DocumentValidatorAgent()
        print(f"Validando documento {file.filename}")
        logger.debug(f"Validando documento {file.filename}")
        validation_result = document_validator.validate(doc_text)
    except Exception as e:
        logger.error(f"Error al procesar el documento: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el documento: {str(e)}")

    # Guardar los datos validados en la base de datos
    #validated_document = save_validated_document(validation_result, file.filename, file_path, db, user_id)
    #return {"document_id": validated_document.id, "validation_result": validation_result}

    return {"document_id": file.filename, "validation_result": validation_result}


def convert_pdf_to_images(pdf_path: str) -> List[np.ndarray]:
    """
    Convert PDF to a list of OpenCV images using PyMuPDF (fitz)
    """
    try:
        pdf_document = fitz.open(pdf_path)
        images = []

        for page_number in range(pdf_document.page_count):
            page = pdf_document[page_number]
            pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
            img_array = np.frombuffer(pix.samples, dtype=np.uint8)

            width, height = pix.width, pix.height
            if pix.alpha:
                img_array = img_array.reshape(height, width, 4)
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            else:
                img_array = img_array.reshape(height, width, 3)

            images.append(img_array)

        pdf_document.close()
        return images

    except Exception as e:
        logger.error(f"Error converting PDF to images: {str(e)}")
        raise


def convert_signature_to_dict(signature: Tuple[int, int, int, int]) -> dict:
    """
    Convierte una tupla de firma en un diccionario con valores nativos de Python
    """
    left, top, width, height = signature
    return {
        "left": int(left),
        "top": int(top),
        "width": int(width),
        "height": int(height)
    }


@router.post("/process_pdf/")
async def process_pdf(file: UploadFile = File(...)):
    try:
        # Crear directorio si no existe
        directory = "uploaded_files"
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(directory, filename)

        # Guardar el archivo
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"File saved at: {file_path}")

        # Convertir PDF a imágenes
        try:
            images = convert_pdf_to_images(file_path)
            logger.info(f"Successfully converted PDF with {len(images)} pages")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error converting PDF to images: {str(e)}"
            )

        # Procesar cada imagen
        page_results = []
        total_signatures = 0
        pages_with_signatures = 0

        for i, img in enumerate(images):
            try:
                page_number = i + 1
                signatures = find_signature_bounding_boxes(img)
                signatures_dict = [convert_signature_to_dict(sig) for sig in signatures]

                # Contar firmas en esta página
                signatures_count = len(signatures_dict)
                total_signatures += signatures_count
                if signatures_count > 0:
                    pages_with_signatures += 1

                page_results.append({
                    "page_number": page_number,
                    "signatures_found": signatures_count,
                    "signatures_details": signatures_dict
                })

                logger.info(f"Processed page {page_number}, found {signatures_count} signatures")
            except Exception as e:
                logger.error(f"Error processing page {i + 1}: {str(e)}")
                continue

        return {
            "summary": {
                "document_name": file.filename,
                "total_pages": len(images),
                "total_signatures": total_signatures,
                "pages_with_signatures": pages_with_signatures,
                "pages_without_signatures": len(images) - pages_with_signatures,
                "average_signatures_per_page": round(total_signatures / len(images), 2)
            },
            "file_info": {
                "saved_path": file_path,
                "processed_timestamp": timestamp
            },
            "page_analysis": page_results,
            "status": "success",
            "message": "Document processing completed successfully"
        }

    except Exception as e:
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up file: {cleanup_error}")

        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )


async def extract_pdf_text(file: UploadFile) -> str:
    """
    Extract text from PDF using PyPDFLoader without saving the file permanently.

    Args:
        file: UploadFile object containing the PDF

    Returns:
        str: Extracted text content from the PDF
    """
    temp_file_path = None
    try:
        # Read file content
        content = await file.read()

        # Create a temporary file with a unique name
        temp_fd, temp_file_path = tempfile.mkstemp(suffix='.pdf')
        try:
            # Write content to temporary file
            with os.fdopen(temp_fd, 'wb') as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()

            # Use PyPDFLoader to extract text
            loader = PyPDFLoader(temp_file_path)
            pages = loader.load()

            # Combine text from all pages
            full_text = "\n".join(page.page_content for page in pages)

            return full_text

        finally:
            # Ensure we close any open file descriptors
            try:
                os.close(temp_fd)
            except:
                pass

    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        raise ValueError(f"Error extracting PDF text: {str(e)}")
    finally:
        # Clean up: remove temporary file if it exists
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Could not delete temporary file {temp_file_path}: {str(e)}")
        # Reset file pointer for potential further use
        await file.seek(0)


@router.post("/v2/validate", response_model=dict)
async def validate_document(
        file: UploadFile = File(...),
        person_name: str = Form(...),
        user_date: str = Form(None),
        db: Session = Depends(get_db),
):
    """
    Validates a PDF document using the complete validation workflow.

    Args:
        file: PDF file to validate
        db: Database session

    Returns:
        Dict containing complete validation results
        :param file:
        :param person_name:
    """
    try:
        # Verify file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are accepted"
            )
        # Validate and normalize person_name
        normalized_name = person_name.strip()
        if not normalized_name:
            raise HTTPException(
                status_code=400,
                detail="Person name is required"
            )

        # Convert to uppercase and normalize spaces
        normalized_name = " ".join(normalized_name.upper().split())

        # Execute workflow
        logger.info(f"Starting document validation: {file.filename}")

        state = OverallState(file_signature=file,
                             file_logo=file,
                             file=file,
                             worker=normalized_name,
                             user_date=user_date)
        component = diagnosis_graph.compile()
        result = await component.ainvoke(state)
        print(f"result: {result}")

        # Format response
        response = {
            "total_pages": len(result["page_diagnosis"]),
            "pages": [
                {
                    "page_number": page_content["page_num"],
                    "diagnostics": {
                        "valid_info": page_content["valid_info"],
                    }
                }
                for i, page_content in enumerate(result["page_diagnosis"])
            ],
            "observations": [
                {
                    "page_number": page_verdict["page_num"],
                    "verdict": page_verdict["verdict"],
                    "reason": page_verdict["reason"],
                    "details": page_verdict["details"]
                }
                for page_verdict in result["pages_verdicts"]
            ],
            #"signatures": result["signature_diagnosis"],
            "validation_images": result["logo_diagnosis"],
            "final_verdict": result["final_verdict"]
        }

        return response

    except Exception as e:
        logger.error(f"Error in document validation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )
