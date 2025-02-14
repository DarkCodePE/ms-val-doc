from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.instructions.prompt import VERDICT_PROMPT, VERDICT_PAGE_PROMPT, \
    FINAL_VERDICTO_PROMPT
from app.agent.state.state import DocumentValidationResponse, VerdictResponse, PageVerdict, OverallState, \
    VerdictDetails, PageContent, PageDiagnosis, FinalVerdictResponse, ObservationResponse
from app.agent.utils.util import es_fecha_emision_valida
from app.config.config import get_settings
from app.providers.llm_manager import LLMConfig, LLMType, LLMManager
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class JudgeAgent:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        llm_config = LLMConfig(
            temperature=0.0,
            streaming=False,
            max_tokens=4000
        )
        self.llm_manager = LLMManager(llm_config)
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O)

    async def validate(self, state: PageContent) -> dict:
        structured_llm = self.primary_llm.with_structured_output(VerdictResponse)
        valid_data = state["valid_data"]
        page_num = state["page_num"]
        enterprise = state["enterprise"]
        person = state["person"]
        end_date_validity = valid_data["end_date_validity"]
        start_date_validity = valid_data["start_date_validity"]
        date_of_issuance = valid_data["date_of_issuance"]
        validation_passed = es_fecha_emision_valida(valid_data["date_of_issuance"], valid_data["end_date_validity"])
        system_instructions = VERDICT_PAGE_PROMPT.format(
            enterprise=enterprise,
            date_of_issuance=date_of_issuance,
            validity=valid_data["validity"],
            start_date_validity=start_date_validity,
            end_date_validity=end_date_validity,
            policy_number=valid_data["policy_number"],
            page_num=page_num,
            person_by_policy=valid_data["person_by_policy"],
            person=person,
            validation_passed=validation_passed
        )

        result = structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(content="Generar un veredicto para la validación de documentos.")
        ])

        page_diagnosis_obj = PageDiagnosis(  # Create the PageDiagnosis object
            valid_info=valid_data,
            page_num=page_num
        )
        print(f"page_diagnosis_obj: {page_diagnosis_obj}")
        print(f"result: {result}")
        return {
            "pages_verdicts": [result],
            "page_diagnosis": [page_diagnosis_obj]
        }

    def summarize(self, state: OverallState) -> dict:
        """Summarizes pages_verdicts para un veredicto final."""

        pages_verdicts = state["pages_verdicts"]
        pages_diagnosis = state["page_diagnosis"]
        #signature_diagnosis = state["signature_diagnosis"]
        logo_diagnosis = state["logo_diagnosis"]
        #total_found_signatures = sum([1 for page in signature_diagnosis if page["signature_status"]])
        enterprise = state["page_contents"][0]["enterprise"]
        person = state["page_contents"][0]["person"]
        structured_llm = self.primary_llm.with_structured_output(FinalVerdictResponse)
        system_instructions = FINAL_VERDICTO_PROMPT.format(
            pages_verdicts=pages_verdicts,
            #total_found_signatures=total_found_signatures,
            page_diagnosis=pages_diagnosis,
            logo_diagnosis=logo_diagnosis,
            #signature_diagnosis=signature_diagnosis,
            enterprise=enterprise,
            person=person
        )
        final_verdict_response = structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(content="Analisa los veredictos de las páginas y genera un veredicto final.")
        ])
        return {"final_verdict": final_verdict_response}

    def cleanup(self):
        """Cleanup method to clear LLM caches when done."""
        self.llm_manager.clear_caches()
