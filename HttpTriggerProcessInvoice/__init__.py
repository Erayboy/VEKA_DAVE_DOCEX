import logging
import os
import tempfile

from shared.client import create_client
from shared.splitter import split_pdf_to_invoices
from shared.extractor import extract_invoice_records
from shared.exporter import export_to_excel
from shared.metadata import metadata_table


def main(blob: bytes, name: str):
    logging.info(f"Nieuwe blob ontvangen: {name}, grootte: {len(blob)} bytes")

    try:
        # Configuratie ophalen uit omgeving
        endpoint = os.getenv("FORM_RECOGNIZER_ENDPOINT")
        key = os.getenv("FORM_RECOGNIZER_KEY")

        # Bestandsnamen voorbereiden
        base_name = os.path.splitext(name)[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            input_pdf_path = os.path.join(temp_dir, name)
            output_dir = os.path.join(temp_dir, "split")
            output_excel = os.path.join(temp_dir, f"{base_name}_DOCEX.xlsx")

            # Blob-inhoud opslaan als tijdelijk PDF-bestand
            with open(input_pdf_path, "wb") as f:
                f.write(blob)

            # Client aanmaken
            client = create_client(endpoint, key)

            # Verwerk PDF
            split_pdf_to_invoices(input_pdf_path, output_dir, client)
            records = extract_invoice_records(output_dir, client, metadata_table)
            export_to_excel(records, output_excel)
             # Upload naar Blob Storage
            connection_string = os.getenv("AzureWebJobsStorage")
            if not connection_string:
                logging.error("AzureWebJobsStorage ontbreekt.")
                return

            from azure.storage.blob import BlobServiceClient
            blob_service = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service.get_container_client("output")

            with open(output_excel, "rb") as data:
                container_client.upload_blob(
                    name=f"{base_name}_DOCEX.xlsx",
                    data=data,
                    overwrite=True
                )
                logging.info(f"Excel-bestand succesvol geüpload als '{base_name}_DOCEX.xlsx' in container 'output'")


            logging.info(f"Facturen geëxporteerd naar: {output_excel}")

    except Exception as e:
        logging.error(f"Fout tijdens verwerking van blob '{name}': {e}")
        raise e
