from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.instructions.prompt import VERDICT_PROMPT, VERDICT_PAGE_PROMPT
from app.agent.state.state import DocumentValidationResponse, VerdictResponse, PageVerdict, OverallState, \
    VerdictDetails, PageContent, PageDiagnosis, FinalVerdictResponse
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
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    async def validate(self, state: PageContent) -> dict:
        structured_llm = self.primary_llm.with_structured_output(VerdictResponse)
        valid_data = state["valid_data"]
        logo_diagnosis = state["logo_diagnosis"]
        page_num = state["page_num"]

        system_instructions = VERDICT_PAGE_PROMPT.format(
            logo_diagnosis=logo_diagnosis,
            date_of_issuance=valid_data["date_of_issuance"],
            validity=valid_data["validity"],
            page_num=page_num
        )

        result = structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(content="Generar un veredicto para la validación de documentos.")
        ])

        #state["pages_verdicts"] = [result]
        page_diagnosis_obj = PageDiagnosis(  # Create the PageDiagnosis object
            logo_diagnosis=logo_diagnosis,
            valid_info=valid_data,
            page_num=page_num
        )

        return {
            "pages_verdicts": [result],
            "page_diagnosis": [page_diagnosis_obj]
        }

    def summarize(self, state: OverallState) -> dict:
        """Summarizes pages_verdicts para un veredicto final."""
        approved_pages = 0
        rejected_pages = 0
        page_verdicts_details = []

        # Acceder correctamente a la lista de page_contents
        for page_content in state["pages_verdicts"]:
            # Verificar si existe pages_verdicts para esta página
            verdict = page_content["verdict"]
            page_num = page_content["page_num"]

            if verdict:
                approved_pages += 1
            else:
                rejected_pages += 1

            page_verdicts_details.append(
                f"Page {page_num}: {verdict}"
            )
        pages_verdicts = state["pages_verdicts"]
        signature_diagnosis = state["signature_diagnosis"]
        total_found_signatures = sum([1 for page in signature_diagnosis if page["signature_status"]])
        structured_llm = self.primary_llm.with_structured_output(FinalVerdictResponse)
        system_instructions = VERDICT_PROMPT.format(
            approved_pages=approved_pages,
            rejected_pages=rejected_pages,
            page_verdicts=pages_verdicts,
            total_found=total_found_signatures
        )
        final_verdict_response = structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(content="Analisa los veredictos de las páginas y genera un veredicto final.")
        ])
        return {"final_verdict": final_verdict_response}

    def cleanup(self):
        """Cleanup method to clear LLM caches when done."""
        self.llm_manager.clear_caches()
