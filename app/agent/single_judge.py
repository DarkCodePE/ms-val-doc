from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.instructions.single import VERDICT_PROMPT
from app.agent.state.single import DocumentValidationResponse, VerdictResponse
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

    async def validate(self, state: DocumentValidationResponse) -> dict:
        structured_llm = self.primary_llm.with_structured_output(VerdictResponse)
        total_found = sum(sig["metadata"]["signatures_found"] for sig in state["signature_diagnosis"])

        system_instructions = VERDICT_PROMPT.format(
            logo_diagnosis=state["logo_diagnosis"],
            date_of_issuance=state["valid_data"]["date_of_issuance"],
            validity=state["valid_data"]["validity"],
            total_found=total_found,
        )
        logger.debug(f"Judge Prompt: {system_instructions}")
        result = structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(content="Generar un veredicto para la validación de documentos.")
        ])
        return {"final_verdict": result}

    def cleanup(self):
        """Cleanup method to clear LLM caches when done."""
        self.llm_manager.clear_caches()
