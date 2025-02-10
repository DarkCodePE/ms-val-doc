from langgraph.graph import StateGraph

from app.workflow.document_validation_grap_builder import DocumentValidationGraphBuilder
from app.workflow.diagnosis_validation_graph_builder import DiagnosisValidationGraph


class GraphDirector:
    """Director que maneja la construcción de grafos"""

    @staticmethod
    def diagnosis_validation_graph() -> StateGraph:
        builder = DiagnosisValidationGraph()
        return builder.build()

    @staticmethod
    def document_validation_graph() -> StateGraph:
        builder = DocumentValidationGraphBuilder()
        return builder.build()
