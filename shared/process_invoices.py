def create_client(endpoint, key):
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential
    return DocumentAnalysisClient(endpoint, AzureKeyCredential(key))

def split_pdf_to_invoices(input_pdf_path, output_dir, client):
    pass

def extract_invoice_records(output_dir, client):
    return []

def export_to_excel(records, filename):
    import pandas as pd
    df = pd.DataFrame(records, columns=["InvoiceId", "InvoiceDate", "InvoiceTotal", "avg_confidence", "FactuurLocatie"])
    df.to_excel(filename, index=False)
