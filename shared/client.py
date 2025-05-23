from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

def create_client(endpoint, key):
    """
    Maak een Form Recognizer client aan op basis van configuratie.
    """
    return DocumentAnalysisClient(endpoint, AzureKeyCredential(key))
