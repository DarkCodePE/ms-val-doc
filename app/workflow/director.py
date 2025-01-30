from langgraph.graph import StateGraph

from app.workflow.document_validation_grap_builder import DocumentValidationGraphBuilder


class GraphDirector:
    """Director que maneja la construcción de grafos"""

    @staticmethod
    def document_validation_graph() -> StateGraph:
        builder = DocumentValidationGraphBuilder()
        return builder.build()
