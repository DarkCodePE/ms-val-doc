from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.agent.document import DocumentAgent
from app.agent.judge import JudgeAgent
from app.agent.logo import LogoAgent
from app.agent.signature import SignatureAgent
from app.agent.state.state import DocumentValidationResponse

from app.agent.evaluator import DocumentValidatorAgent
from app.agent.loader import extract_text_with_pypdfloader
from app.workflow.builder.base import GraphBuilder


class DocumentValidationGraphBuilder(GraphBuilder):

    def __init__(self):
        super().__init__()
        self.document = DocumentAgent()
        self.logo = LogoAgent()
        self.signature = SignatureAgent()
        self.judge = JudgeAgent()

    def init_graph(self) -> None:
        self.graph = StateGraph(DocumentValidationResponse)

    def add_nodes(self) -> None:
        self.graph.add_node("extract_text", self.document.extract_text_node)
        self.graph.add_node("document_processor", self.document.document_processor)
        self.graph.add_node("logo_detection", self.logo.verify_signatures)
        self.graph.add_node("detect_signatures", self.signature.verify_signatures)
        self.graph.add_node("validate_document", self.judge.validate)
        #self.graph.add_node("save_to_db", self.save_to_database)

    def add_edges(self) -> None:
        self.graph.add_edge(START, "extract_text")
        self.graph.add_edge("extract_text", "document_processor")
        self.graph.add_edge("document_processor", "logo_detection")
        self.graph.add_edge("logo_detection", "detect_signatures")
        self.graph.add_edge("detect_signatures", "validate_document")
        self.graph.add_edge("validate_document", END)
