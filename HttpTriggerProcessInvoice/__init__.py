import logging
import os
import tempfile
import fitz  # PyMuPDF
from azure.storage.blob import BlobServiceClient
from shared.process_invoices import (
    create_client,
    split_pdf_to_invoices,
    extract_invoice_records,
    export_to_excel
)

def main(blob: bytes, name: str):
    logging.info("==== Blob trigger gestart ====")
    logging.info(f"Ontvangen bestand: {name}")

    # Ophalen endpoint en key uit Application Settings
    endpoint = os.environ.get("FORM_RECOGNIZER_ENDPOINT")
    key = os.environ.get("FORM_RECOGNIZER_KEY")
    if not endpoint or not key:
        logging.error("Endpoint of key is niet ingesteld in Application Settings.")
        return

    client = create_client(endpoint, key)

    with tempfile.TemporaryDirectory() as tmpdir:
        local_pdf_path = os.path.join(tmpdir, name)
        with open(local_pdf_path, "wb") as f:
            f.write(blob)

        # 1. PDF splitsen
        split_dir = os.path.join(tmpdir, "gesplitst")
        split_pdf_to_invoices(local_pdf_path, split_dir, client)

        # 2. Gegevens extraheren
        records = extract_invoice_records(split_dir, client)

        # 3. Opslaan als Excel
        output_excel_path = os.path.join(tmpdir, f"{name}_output.xlsx")
        export_to_excel(records, output_excel_path)

        # 4. Upload Excel naar output-container
        connection_string = os.environ.get("AzureWebJobsStorage")
        if not connection_string:
            logging.error("AzureWebJobsStorage ontbreekt in Application Settings.")
            return

        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client("output")

        try:
            with open(output_excel_path, "rb") as data:
                container_client.upload_blob(
                    name=f"{name}_output.xlsx",
                    data=data,
                    overwrite=True
                )
                logging.info(f" Excel-bestand geüpload: {name}_output.xlsx")
        except Exception as e:
            logging.error(f" Fout bij uploaden Excel-bestand: {e}")
