from langgraph.constants import START

from app.workflow.builder.base import GraphBuilder


class DiagnosisValidationGraph(GraphBuilder):
    def __init__(self):
        super().__init__()
        self.graph = None
        self.nodes = []
        self.edges = []

    def add_node(self, node):
        self.nodes.append(node)

    def add_edge(self, source, target):
        self.graph.add_edge(START, "plan")
        self.graph.add_conditional_edges(
            "plan",
            ReportPlanner.initiate_section_writing,
            ["research"]
        )
