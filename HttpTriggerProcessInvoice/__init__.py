import logging
import json
import os
import tempfile
from azure.storage.blob import BlobClient
from shared.process_invoices import (
    create_client,
    split_pdf_to_invoices,
    extract_invoice_records,
    export_to_excel
)

def main(event: dict):
    logging.info("== Event Grid Trigger ontvangen ==")
    event_data = event.get("data", {})
    blob_url = event_data.get("url")

    if not blob_url:
        logging.error("Geen blob URL gevonden in event.")
        return

    logging.info(f"Verwerken van blob: {blob_url}")

    # Blob downloaden
    connection_string = os.environ.get("AzureWebJobsStorage")
    blob_client = BlobClient.from_blob_url(blob_url, credential=connection_string)

    filename = os.path.basename(blob_url)

    endpoint = os.environ.get("FORM_RECOGNIZER_ENDPOINT")
    key = os.environ.get("FORM_RECOGNIZER_KEY")
    client = create_client(endpoint, key)

    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, filename)
        with open(local_path, "wb") as f:
            f.write(blob_client.download_blob().readall())

        split_dir = os.path.join(tmpdir, "gesplitst")
        split_pdf_to_invoices(local_path, split_dir, client)
        records = extract_invoice_records(split_dir, client)

        output_excel = os.path.join(tmpdir, f"{filename}_output.xlsx")
        export_to_excel(records, output_excel)

        container_client = blob_client._container_client  # zelfde container
        with open(output_excel, "rb") as data:
            container_client.upload_blob(
                name=f"{filename}_output.xlsx",
                data=data,
                overwrite=True
            )
            logging.info(f"Excel-bestand geüpload als: {filename}_output.xlsx")
