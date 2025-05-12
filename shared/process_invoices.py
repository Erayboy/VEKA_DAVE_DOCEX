from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import fitz  # PyMuPDF
import io
import os
import pandas as pd
import re
import logging

def create_client(endpoint, key):
    """
    Maak een Form Recognizer client aan op basis van configuratie.
    """
    return DocumentAnalysisClient(endpoint, AzureKeyCredential(key))


def split_pdf_to_invoices(input_pdf_path, output_dir, client):
    """
    Split een PDF in facturen op basis van unieke InvoiceId's en sla ze op als aparte bestanden.
    """
    os.makedirs(output_dir, exist_ok=True)
    pdf = fitz.open(input_pdf_path)

    factuurgroepen = []
    huidige_factuur = []
    vorige_invoice_id = None

    for i in range(len(pdf)):
        page_pdf = fitz.open()
        page_pdf.insert_pdf(pdf, from_page=i, to_page=i)
        page_bytes = page_pdf.write()

        poller = client.begin_analyze_document(
            model_id="prebuilt-invoice",
            document=io.BytesIO(page_bytes)
        )
        result = poller.result()

        invoice_id = None
        if result.documents:
            doc = result.documents[0]
            invoice_field = doc.fields.get("InvoiceId")
            invoice_id = invoice_field.value if invoice_field else None

        if invoice_id and invoice_id != vorige_invoice_id:
            if huidige_factuur:
                factuurgroepen.append(huidige_factuur)
            huidige_factuur = [i]
            vorige_invoice_id = invoice_id
        else:
            huidige_factuur.append(i)

    if huidige_factuur:
        factuurgroepen.append(huidige_factuur)

    for idx, pagina_groep in enumerate(factuurgroepen):
        nieuwe_pdf = fitz.open()
        for pagina_nummer in pagina_groep:
            nieuwe_pdf.insert_pdf(pdf, from_page=pagina_nummer, to_page=pagina_nummer)
        nieuwe_pdf.save(os.path.join(output_dir, f"factuur_{idx+1}.pdf"))
        logging.info(f"Gesplitste factuur opgeslagen: factuur_{idx+1}.pdf (pagina’s {pagina_groep})")

    logging.info(f"Totaal {len(factuurgroepen)} facturen gesplitst en opgeslagen in '{output_dir}'")
    return output_dir


def extract_invoice_records(output_dir, client):
    """
    Extracteer factuurgegevens uit afzonderlijke PDF-bestanden in een map.
    """
    invoice_records = []
    for file_name in os.listdir(output_dir):
        file_path = os.path.join(output_dir, file_name)
        try:
            pdf = fitz.open(file_path)
            page_pdf = fitz.open()
            page_pdf.insert_pdf(pdf)
            page_bytes = page_pdf.write()

            poller = client.begin_analyze_document(
                model_id="prebuilt-invoice",
                document=io.BytesIO(page_bytes)
            )
            invoice_data = poller.result()

            for invoice in invoice_data.documents:
                invoice_id_field = invoice.fields.get("InvoiceId", None)
                invoice_date_field = invoice.fields.get("InvoiceDate", None)
                invoice_total_field = invoice.fields.get("InvoiceTotal", None)

                extracted_invoice_id = invoice_id_field.value if invoice_id_field else None
                extracted_invoice_date = invoice_date_field.value if invoice_date_field else None
                extracted_invoice_total = invoice_total_field.value if invoice_total_field else None

                if extracted_invoice_total:
                    extracted_invoice_total = str(extracted_invoice_total)
                    extracted_invoice_total = extracted_invoice_total.encode("ascii", "ignore").decode("ascii")
                    extracted_invoice_total = re.sub(r"[^\d.]", "", extracted_invoice_total)
                    extracted_invoice_total = float(extracted_invoice_total) if extracted_invoice_total else None

                confidences = []
                for field in [invoice_id_field, invoice_date_field, invoice_total_field]:
                    if field and field.confidence is not None:
                        confidences.append(field.confidence)
                avg_confidence = sum(confidences) / len(confidences) if confidences else None

                invoice_records.append([
                    extracted_invoice_id,
                    extracted_invoice_date,
                    extracted_invoice_total,
                    avg_confidence,
                    file_name
                ])

        except Exception as e:
            logging.warning(f"Fout bij verwerken van bestand {file_name}: {e}")

    return invoice_records


def export_to_excel(invoice_records, filename):
    """
    Exporteer een lijst met factuurgegevens naar een Excel-bestand.
    """
    df = pd.DataFrame(invoice_records, columns=["InvoiceId", "InvoiceDate", "InvoiceTotal", "avg_confidence", "FactuurLocatie"])
    df.to_excel(filename, index=False)
    logging.info(f"Factuurgegevens geëxporteerd naar {filename}")
