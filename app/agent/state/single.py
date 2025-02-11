from fastapi import UploadFile
from pydantic import BaseModel, Field
from typing import List, Optional, Annotated, Dict
from typing_extensions import TypedDict
import operator


class LogoValidationDetails(TypedDict):
    logo: str
    logo_status: bool
    diagnostics: str


class SignatureMetadata(TypedDict):
    page_number: int
    signatures_found: int
    signatures_details: List[Dict[str, int]]


class SignatureValidationDetails(TypedDict):
    signature: str  # Descripción de la página
    signature_status: bool  # True si se encontraron firmas
    metadata: SignatureMetadata


class DocumentValidationDetails(TypedDict):
    validity: str
    enterprise: str
    policy_number: str
    company: str
    date_of_issuance: str


class VerdictDetails(TypedDict):
    logo_validation_passed: bool
    document_validity_approved: bool
    signature_validation_passed: bool


class VerdictResponse(TypedDict):
    verdict: bool
    reason: str
    details: VerdictDetails


class DocumentValidationResponse(TypedDict):
    file: UploadFile
    extracted_text: Optional[str]
    document_path: str
    document_data: str
    valid_data: DocumentValidationDetails
    logo_diagnosis: List[LogoValidationDetails]
    signature_diagnosis: List[SignatureValidationDetails]
    final_verdict: VerdictResponse
