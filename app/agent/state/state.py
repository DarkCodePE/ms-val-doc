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
    policy_number: str
    company: str
    date_of_issuance: str


class VerdictDetails(TypedDict):
    logo_validation_passed: bool
    document_validity_approved: bool
    signature_validation_passed: bool


class SignatureInfo(TypedDict):
    has_signature_page: bool
    total_found_page: int
    metadata: List[Dict[str, int]]


class PageDiagnosis(TypedDict):
    page_num: int
    valid_info: DocumentValidationDetails
    logo_diagnosis: LogoValidationDetails
    signature_info: SignatureInfo


class VerdictResponse(TypedDict):
    verdict: bool
    reason: str
    details: VerdictDetails
    page_num: int


class FinalVerdictResponse(TypedDict):
    verdict: bool
    reason: str


class DocumentValidationResponse(TypedDict):
    extracted_text: Optional[str]
    valid_data: DocumentValidationDetails
    logo_diagnosis: List[LogoValidationDetails]


class PageVerdict(TypedDict):
    page_num: int
    verdict: str
    reason: str


class PageContent(TypedDict):
    page_num: int
    page_content: str
    signature_data: Optional[SignatureValidationDetails]
    page_base64_image: str
    valid_data: Optional[DocumentValidationDetails]
    logo_diagnosis: Optional[LogoValidationDetails]
    page_diagnosis: Optional[PageDiagnosis]
    enterprise: str
    pages_verdicts: List[VerdictResponse]


class OverallState(TypedDict):
    file: UploadFile
    page_contents: list[PageContent]
    page_diagnosis: Annotated[List[PageDiagnosis], operator.add]
    signature_diagnosis: list[SignatureValidationDetails]
    pages_verdicts: Annotated[List[VerdictResponse], operator.add]
    final_verdict: Optional[FinalVerdictResponse]
