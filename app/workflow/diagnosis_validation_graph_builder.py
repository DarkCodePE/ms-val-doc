from typing import List

from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import Send

from app.agent.document import DocumentAgent
from app.agent.judge import JudgeAgent
from app.agent.logo import LogoAgent
from app.agent.signature import SignatureAgent
from app.agent.state.state import OverallState, DocumentValidationResponse, PageVerdict, VerdictResponse, \
    VerdictDetails, PageContent, DocumentValidationDetails
from app.agent.utils.util import extract_pdf_text_per_page, pdf_page_to_base64_image, extract_name_enterprise
from app.workflow.builder.base import GraphBuilder
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DiagnosisValidationGraph(GraphBuilder):
    def __init__(self):
        super().__init__()
        self.document = DocumentAgent()
        self.logo = LogoAgent()
        self.signature = SignatureAgent()
        self.judge = JudgeAgent()
        self.document_graph = None
        self.PAGE_PER_TIME = 5

    def init_graph(self) -> None:
        self.graph = StateGraph(OverallState)
        from .document_validation_grap_builder import DocumentValidationGraphBuilder
        document_graph = DocumentValidationGraphBuilder()
        self.document_graph = document_graph.build().compile()

    def add_nodes(self) -> None:
        self.graph.add_node("extract_pages_content",
                            self.extract_pages_content)  # **Nuevo nodo de extracción por página**
        self.graph.add_node("detect_signatures", self.signature.verify_signatures)
        self.graph.add_node("validate_page", self.document_graph)
        self.graph.add_node("compile_verdict", self.judge.summarize)

    def add_edges(self) -> None:
        self.graph.add_edge(START, "detect_signatures")  # **Inicio: Extracción por página**
        self.graph.add_edge("detect_signatures",
                            "extract_pages_content")  # Extracción -> Detección de firmas (por página)
        self.graph.add_conditional_edges("extract_pages_content",
                                         self.generate_pages_to_validate,
                                         ["validate_page"]
                                         )
        self.graph.add_edge("validate_page", "compile_verdict")
        self.graph.add_edge("compile_verdict", END)

        #self.graph.add_edge("judge_page", "summarize")

        #self.graph.add_edge("summarize", END)

    async def extract_pages_content(self, state: OverallState) -> dict:
        """Extracts page content, base64 images, and performs initial signature detection.

        Populates OverallState['page_contents'] with a list of PageContent objects.
        """
        pdf_file = state["file"]
        text_per_page = await extract_pdf_text_per_page(pdf_file)
        pages_signatures = state["signature_diagnosis"]
        print(f"text_per_page: {text_per_page}")
        print(f"pages_signatures: {pages_signatures}")
        # Extraer el nombre de la empresa una única vez, ya que se asume que es el mismo para todas las páginas.
        try:
            enterprise = await extract_name_enterprise(state["file"])
        except Exception as e:
            enterprise = ""

        page_content_list: List[PageContent] = []
        for i, content in enumerate(text_per_page):
            page_num = i + 1
            base64_image = await pdf_page_to_base64_image(pdf_file, page_num)
            signature_data = pages_signatures[i] if i < len(pages_signatures) else None

            page_content = PageContent(
                page_num=page_num,
                page_content=content,
                page_base64_image=base64_image,
                signature_data=signature_data,
                valid_data=None,  # Dummy valid_data - you'll populate this in the subgraph
                pages_verdicts=None,  # Dummy pages_verdicts - you'll populate this in the subgraph
                enterprise=enterprise,  # Dummy enterprise - you'll populate this in the subgraph
                logo_diagnosis=None  # Dummy logo_diagnosis - you'll populate this in the subgraph
            )
            page_content_list.append(page_content)

        return {"page_contents": page_content_list}

    def generate_pages_to_validate(self, state: OverallState) -> list[Send]:
        """Creates Send objects for each PageContent in OverallState['page_contents'] for parallel validation."""
        return [
            Send("validate_page",
                 {"page_content": page["page_content"],
                  "enterprise": page["enterprise"],
                  "page_base64_image": page["page_base64_image"],
                  "valid_data": page["valid_data"],
                  "page_num": page["page_num"],
                  "signature_data": page["signature_data"]}
                 )
            for page in state["page_contents"]
            #if page["valid_data"]
        ]
