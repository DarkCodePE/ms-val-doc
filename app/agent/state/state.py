from fastapi import UploadFile
from pydantic import BaseModel, Field
from typing import List, Optional, Annotated, Dict
from typing_extensions import TypedDict
import operator


class LogoValidationDetails(TypedDict):
    logo: str
    logo_status: bool
    diagnostics: str
    page_num: int


class SignatureMetadata(TypedDict):
    page_number: int
    signatures_found: int
    signatures_details: List[Dict[str, int]]


class SignatureValidationDetails(TypedDict):
    signature: str  # Descripción de la página
    signature_status: bool  # True si se encontraron firmas
    metadata: SignatureMetadata


class PersonValidationDetails(TypedDict):
    name: str
    policy_number: str
    company: str


class DocumentValidationDetails(TypedDict):
    start_date_validity: str
    end_date_validity: str
    validity: str
    policy_number: str
    company: str
    date_of_issuance: str
    date_of_signature: str
    person_by_policy: PersonValidationDetails


class VerdictDetails(TypedDict):
    logo_validation_passed: bool
    validity_validation_passed: bool
    signature_validation_passed: bool
    person_validation_passed: bool


class SignatureInfo(TypedDict):
    has_signature_page: bool
    total_found_page: int
    metadata: List[Dict[str, int]]


class PageDiagnosis(TypedDict):
    page_num: int
    valid_info: DocumentValidationDetails


class VerdictResponse(TypedDict):
    verdict: bool
    reason: str
    details: VerdictDetails
    page_num: int


class ObservationResponse(TypedDict):
    observations: str
    page_num: int


class FinalVerdictResponse(TypedDict):
    verdict: bool
    reason: str
    details: VerdictDetails


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
    valid_data: Optional[DocumentValidationDetails]
    page_diagnosis: Optional[PageDiagnosis]
    enterprise: str
    pages_verdicts: Optional[VerdictResponse]
    person: str


class OverallState(TypedDict):
    file_signature: UploadFile
    file_logo: UploadFile
    file: UploadFile
    page_contents: list[PageContent]
    page_diagnosis: Annotated[List[PageDiagnosis], operator.add]
    signature_diagnosis: list[SignatureValidationDetails]
    pages_verdicts: Annotated[List[VerdictResponse], operator.add]
    final_verdict: Optional[FinalVerdictResponse]
    logo_diagnosis: list[LogoValidationDetails]
    worker: str
