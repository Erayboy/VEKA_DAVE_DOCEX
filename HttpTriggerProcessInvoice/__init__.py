import logging
import os
import tempfile
from azure.storage.blob import BlobServiceClient
from shared.process_invoices import (
    create_client,
    split_pdf_to_invoices,
    extract_invoice_records,
    export_to_excel
)

def main(blob: bytes, name: str):
    logging.info("== Blob-trigger gestart ==")
    logging.info(f"Ontvangen bestand: {name}")

    endpoint = os.environ.get("FORM_RECOGNIZER_ENDPOINT")
    key = os.environ.get("FORM_RECOGNIZER_KEY")
    if not endpoint or not key:
        logging.error("Endpoint of key ontbreekt in Application Settings.")
        return

    client = create_client(endpoint, key)

    with tempfile.TemporaryDirectory() as tmpdir:
        local_pdf_path = os.path.join(tmpdir, name)
        with open(local_pdf_path, "wb") as f:
            f.write(blob)

        split_dir = os.path.join(tmpdir, "gesplitst")
        split_pdf_to_invoices(local_pdf_path, split_dir, client)
        records = extract_invoice_records(split_dir, client)

        output_excel = os.path.join(tmpdir, f"{name}_output.xlsx")
        export_to_excel(records, output_excel)

        connection_string = os.environ.get("AzureWebJobsStorage")
        if not connection_string:
            logging.error("AzureWebJobsStorage ontbreekt.")
            return

        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client("output")

        try:
            with open(output_excel, "rb") as data:
                container_client.upload_blob(
                    name=f"{name}_output.xlsx",
                    data=data,
                    overwrite=True
                )
                logging.info(f"Excel-bestand geüpload als: {name}_output.xlsx")
        except Exception as e:
            logging.error(f"Fout bij uploaden Excel-bestand: {e}")
