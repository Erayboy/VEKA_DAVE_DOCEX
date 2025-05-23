import os
import logging

from shared.client import create_client
from shared.splitter import split_pdf_to_invoices
from shared.extractor import extract_invoice_records
from shared.exporter import export_to_excel
from shared.metadata import metadata_table

# ===== Configuratie =====
INPUT_FILE = "input/test_invoice.pdf"  # Jouw testbestand hier
OUTPUT_DIR = "output/test_invoice"     # Hier worden de gesplitste PDF’s opgeslagen
EXCEL_OUTPUT = "output/test_invoice_DOCEX.xlsx"

# Voeg je Form Recognizer config toe via env vars of hardcoded hier (alleen voor lokaal)
FORM_RECOGNIZER_ENDPOINT = os.getenv("FORM_RECOGNIZER_ENDPOINT") or "<je-endpoint-hier>"
FORM_RECOGNIZER_KEY = os.getenv("FORM_RECOGNIZER_KEY") or "<je-key-hier>"

logging.basicConfig(level=logging.INFO)

def main():
    # 1. Controleer of inputbestand bestaat
    if not os.path.exists(INPUT_FILE):
        logging.error(f"Inputbestand niet gevonden: {INPUT_FILE}")
        return

    # 2. Maak client aan
    client = create_client(FORM_RECOGNIZER_ENDPOINT, FORM_RECOGNIZER_KEY)

    # 3. Verwerk
    logging.info("Stap 1: PDF splitsen...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    split_pdf_to_invoices(INPUT_FILE, OUTPUT_DIR, client)

    logging.info("Stap 2: Gegevens extraheren...")
    records = extract_invoice_records(OUTPUT_DIR, client, metadata_table)

    logging.info("Stap 3: Exporteren naar Excel...")
    export_to_excel(records, EXCEL_OUTPUT)

    logging.info(f"✅ Klaar! Geëxporteerd naar: {EXCEL_OUTPUT}")

if __name__ == "__main__":
    main()
