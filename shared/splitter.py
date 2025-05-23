import fitz  # PyMuPDF
import os
import io
import logging

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
