import os
import fitz
import io
import logging
import re

def extract_invoice_records(output_dir, client, metadata_table):
    """
    Extracteer factuurgegevens op basis van opgegeven metadata kolommen.
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
