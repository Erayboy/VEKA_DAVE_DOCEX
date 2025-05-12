import logging
import os
from azure.storage.blob import BlobServiceClient
import tempfile
from shared.process_invoices import split_pdf_to_invoices, extract_invoice_records, export_to_excel
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

def main(blob: bytes, name: str):
    logging.info(f"Bestand ontvangen: {name}")

    # Instellen van Document Intelligence client
    endpoint = os.environ["FORM_RECOGNIZER_ENDPOINT"]
    key = os.environ["FORM_RECOGNIZER_KEY"]
    client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))

    with tempfile.TemporaryDirectory() as tmpdir:
        local_pdf_path = os.path.join(tmpdir, name)
        with open(local_pdf_path, "wb") as f:
            f.write(blob)

        # 1. Splitsen
        split_dir = os.path.join(tmpdir, "gesplitste")
        split_pdf_to_invoices(local_pdf_path, split_dir, client)

        # 2. Extractie
        records = extract_invoice_records(split_dir, client)

        # 3. Excel export
        output_excel = os.path.join(tmpdir, f"{name}_output.xlsx")
        export_to_excel(records, output_excel)

        # 4. Upload output Excel naar blob
        storage_conn = os.environ["AzureWebJobsStorage"]
        blob_service_client = BlobServiceClient.from_connection_string(storage_conn)
        container_client = blob_service_client.get_container_client("output")
        container_client.upload_blob(f"{name}_output.xlsx", open(output_excel, "rb"), overwrite=True)
        logging.info(f"Excel bestand geüpload: {name}_output.xlsx")
