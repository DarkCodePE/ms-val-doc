from langchain_community.document_loaders import PyPDFLoader


# Función para cargar el PDF
def extract_text_with_pypdfloader(file_path: str):
    loader = PyPDFLoader(file_path)
    pages = loader.load()  # Carga todas las páginas como objetos Document
    return pages
