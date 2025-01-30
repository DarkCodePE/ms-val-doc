from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv

from app.model.model import DocumentValidationResponse

load_dotenv()


class DocumentValidatorAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

        # Parser para formatear la salida final
        self.parser = PydanticOutputParser(pydantic_object=DocumentValidationResponse)

        # Prompt principal para validar documentos
        self.validation_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                    Validate the authenticity of a document by checking expiration, signature presence, and endorsement details. Your task is to design a system or model to evaluate the validity and current status of a document. The model should be capable of:

                    - Determining the presence and validity of a signature.
                    - Identifying and validating the certificate number, validity period, issuance date, and insurees of the document.
                    - Comparing the start and end dates of validity with the current date to verify if the document is still valid.

                    # Steps

                    1. **Date Validation:**
                       - Extract "validity_start" and "validity_end" from the document.
                       - Compare these dates with the current date to determine the document’s validity status.

                    2. **Signature Detection:**
                       - Analyze the document VERIFY IF THERE EXISTS a handwritten signature section to check for visible signatures or digital stamps.
                       - Detect a signature in the document from a text pattern commonly consisting of:
                         - Full name of the signer (e.g., “DIANA CAROLINA NIETO LUQUE”).
                         - The position or title of the person (e.g., “UNIDAD DE VIDA, DECESOS Y ACCIDENTES”).
                         - (Optional) The name of the company or organization.

                    3. **Endorsement Check:**
                       - Verify the document for endorsement details and ensure these match expected patterns or criteria. 

                    4. **Extraction and Verification:**
                       - Identify and extract pertinent fields such as the certificate number, validity period, issuance date, and insured parties.
                       - Validate the extracted information against expected formats or predefined criteria.

                    # Output Format

                    Provide a clear and structured report containing:
                    - The document's validity status (e.g., valid/invalid).
                    - The presence or absence of a recognized signature.
                    - Details on the certificate number, validity period, issuance date, and insured parties.

                    # Examples

                    **Example 1:**
                    - **Document Entry Details**:
                      - Start of Validity: 01-01-2023
                      - End of Validity: 01-01-2024
                      - Signature: Present, recognizable
                      - Certificate number: ABC123
                      - Issuance Date: 01-01-2023
                      - Insured Parties: John Doe, Corp Inc.
                    - **Output Report**:
                      - Document validity status: Valid
                      - Signature: Present and recognized
                      - Certificate number: ABC123
                      - Validity Period: 01-01-2023 to 01-01-2024
                      - Issuance Date: 01-01-2023
                      - Insured Parties: John Doe, Corp Inc.

                    # Notes

                    - Consider that documents may have manual or electronic signatures. Verify the authenticity and recognition of each type.
                    - Ensure date comparisons use the current date accurately.
                    - Report in Spanish where indicated, such as in the signature detection section. Ensure the language matches the document’s relevant fields.
                    
                    # Output Format
                    - Provide a clear and structured report containing:
                      - Document validity status (e.g., valid/invalid).
                      - Presence or absence of signature.
                      - Details on the Certificate Number, Period of Validity, Issue Date, and Insured Parties.
                    """,
                ),
                (
                    "human",
                    """
                    Document Data:\n\n{document_data}\n\nCurrent Date: {current_date}\n
                    """,
                ),
            ]
        )

        # Prompt para formatear la salida final
        self.format_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Format the following validation result into the required JSON structure:\n{format_instructions}"
                ),
                (
                    "human",
                    "Validation Result:\n\nDocument ID: {document_id}\nValidity Status: {validity_status}\nSignature: {signature}\nCertificate Number: {certificate_number}\nValidity Period: {validity_period}\nInsured Parties: {insured_parties}"
                ),
            ]
        ).partial(format_instructions=self.parser.get_format_instructions())

        # Cadena para validar el documento
        self.validation_chain = (
                {
                    "document_data": RunnablePassthrough(),
                    "current_date": RunnablePassthrough(lambda _: datetime.utcnow().strftime("%Y-%m-%d")),
                }
                | self.validation_prompt
                | {"validation_result": self.llm | StrOutputParser()}
        )

        # Cadena para formatear la salida final
        self.format_chain = (
                {
                    "document_id": RunnablePassthrough(),
                    "validity_status": self.validation_chain,
                    "signature": self.validation_chain,
                    "certificate_number": self.validation_chain,
                    "validity_period": self.validation_chain,
                    "insured_parties": self.validation_chain,
                }
                | self.format_prompt
                | {"formatted_output": self.llm | self.parser}
        )

    def validate(self, document_data: str):
        try:
            result = self.format_chain.invoke({"document_data": document_data})
            return result["formatted_output"]
        except Exception as e:
            raise ValueError(f"Error during document validation: {e}")
