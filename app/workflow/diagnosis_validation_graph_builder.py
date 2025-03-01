from typing import List

from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import Send

from app.agent.document import DocumentAgent
from app.agent.judge import JudgeAgent

from app.agent.signature import SignatureAgent
from app.agent.single_logo import SingleLogoAgent
from app.agent.state.state import OverallState, PageContent
from app.agent.utils.util import semantic_segment_pdf_with_llm, extract_name_enterprise, \
    semantic_segment_pdf_with_llm_v2, count_pdf_pages, semantic_segment_pdf_with_llm_v3

from app.workflow.builder.base import GraphBuilder
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DiagnosisValidationGraph(GraphBuilder):
    def __init__(self):
        super().__init__()
        self.document = DocumentAgent()
        self.logo = SingleLogoAgent()
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
        self.graph.add_node("logo_detection", self.logo.verify_logo)

    def add_edges(self) -> None:
        # Parallel branches for signature and logo detection
        #self.graph.add_edge(START, "detect_signatures")
        #self.graph.add_edge(START, "logo_detection")
        #self.graph.add_edge(START, "detect_signatures")
        #self.graph.add_edge("detect_signatures", "logo_detection")
        #self.graph..add_conditional_edges("node_a", routing_function)
        # After both signature and logo detection are done, proceed to extract_pages_content
        #self.graph.add_edge(["detect_signatures", "logo_detection"], "extract_pages_content")
        self.graph.add_edge(START, "logo_detection")
        self.graph.add_edge("logo_detection", "extract_pages_content")
        #self.graph.add_edge(START, "extract_pages_content")
        self.graph.add_conditional_edges("extract_pages_content",
                                         self.generate_pages_to_validate,
                                         ["validate_page"]
                                         )
        self.graph.add_edge("validate_page", "compile_verdict")
        self.graph.add_edge("compile_verdict", END)

    async def extract_pages_content(self, state: OverallState) -> dict:
        """Extracts page content using semantic segmentation with LLM."""
        pdf_file = state["file"]
        total_pages = await count_pdf_pages(pdf_file)
        if total_pages > 1:
            # Use semantic segmentation instead of page-based extraction
            segmented_sections = await semantic_segment_pdf_with_llm_v2(pdf_file,
                                                                        self.document.llm_manager)  # Use LLM for segmentation
        else:
            # Use page-based extraction
            segmented_sections = await semantic_segment_pdf_with_llm_v3(pdf_file,
                                                                        self.document.llm_manager)

        try:
            enterprise = await extract_name_enterprise(state["file"])
        except Exception as e:
            enterprise = ""

        person = state["worker"]
        document_type = state["worker_type"]
        user_date = state["user_date"]
        page_content_list: List[PageContent] = []
        for i, content in enumerate(segmented_sections):  # Iterate over segmented sections now
            page_num = i + 1
            page_content = PageContent(
                page_num=page_num,  # Rethink page_num - maybe section_num?
                page_content=content,
                valid_data=None,
                pages_verdicts=None,
                enterprise=enterprise,
                person=person,
                reference_date=user_date,
                document_type=document_type
            )
            page_content_list.append(page_content)

        print("Page content list: ", page_content_list)
        return {"page_contents": page_content_list}

    def generate_pages_to_validate(self, state: OverallState) -> list[Send]:
        """Creates Send objects for each PageContent in OverallState['page_contents'] for parallel validation."""
        return [
            Send("validate_page",
                 {"page_content": page["page_content"],
                  "enterprise": page["enterprise"],
                  "valid_data": page["valid_data"],
                  "page_num": page["page_num"],
                  "person": page["person"],
                  "reference_date": page["reference_date"],
                  "document_type": page["document_type"]}
                 )
            for page in state["page_contents"]
        ]

    def issue_date_detection(self, state: OverallState) -> str:
        """Detects the issue date of the document."""
        pass
