from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import fitz  # PyMuPDF
import io
import os
import pandas as pd
import re
import logging

metadata_table = [
    {"id": 1, "SourceColumnName": "InvoiceId", "TargetColumnName": "invoice_id"},
    {"id": 2, "SourceColumnName": "InvoiceDate", "TargetColumnName": "invoice_date"},
    {"id": 3, "SourceColumnName": "InvoiceTotal", "TargetColumnName": "invoice_total"},
    {"id": 4, "SourceColumnName": "SubTotal", "TargetColumnName": "invoice_total_without_vat"},
    {"id": 5, "SourceColumnName": "CustomerName", "TargetColumnName": "customer_name"},
    {"id": 6, "SourceColumnName": "Description", "TargetColumnName": "invoice_topic"}
]




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


def extract_invoice_records(output_dir, client, metadata_table):
    """
    Extracteer factuurgegevens op basis van opgegeven metadata kolommen.
    Alles wordt bepaald via metadata_table, incl. totaal zonder btw (SubTotal).
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
                record = {}
                confidences = []

                for column in metadata_table:
                    source_col = column["SourceColumnName"]
                    target_col = column["TargetColumnName"]

                    field = invoice.fields.get(source_col, None)
                    value = field.value if field else None

                    # Schoonmaak voor bedragvelden
                    if source_col in ["InvoiceTotal", "TotalTax", "SubTotal"] and value:
                        value = str(value)
                        value = value.encode("ascii", "ignore").decode("ascii")
                        value = re.sub(r"[^\d.]", "", value)
                        value = float(value) if value else None

                    record[target_col] = value

                    if field and field.confidence is not None:
                        confidences.append(field.confidence)

                record["confidence"] = sum(confidences) / len(confidences) if confidences else None
                record["file_name"] = file_name

                invoice_records.append(record)

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
