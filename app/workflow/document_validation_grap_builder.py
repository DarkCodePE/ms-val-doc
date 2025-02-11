from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.agent.document import DocumentAgent
from app.agent.judge import JudgeAgent
from app.agent.logo import LogoAgent
from app.agent.signature import SignatureAgent
from app.agent.state.state import DocumentValidationResponse, PageContent

from app.agent.evaluator import DocumentValidatorAgent
from app.agent.loader import extract_text_with_pypdfloader
from app.workflow.builder.base import GraphBuilder


class DocumentValidationGraphBuilder(GraphBuilder):

    def __init__(self):
        super().__init__()
        self.document = DocumentAgent()
        self.logo = LogoAgent()
        self.judge = JudgeAgent()

    def init_graph(self) -> None:
        self.graph = StateGraph(PageContent)

    def add_nodes(self) -> None:
        self.graph.add_node("document_processor", self.document.document_processor)
        self.graph.add_node("page_validation", self.judge.validate)

    def add_edges(self) -> None:
        self.graph.add_edge(START, "document_processor")
        self.graph.add_edge("document_processor", "page_validation")
        self.graph.add_edge("page_validation", END)
