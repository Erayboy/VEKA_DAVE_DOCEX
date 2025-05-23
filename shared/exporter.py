import pandas as pd
import logging

def export_to_excel(invoice_records, filename):
    """
    Exporteer een lijst met factuurgegevens naar een Excel-bestand.
    """
    df = pd.DataFrame(invoice_records)
    df.to_excel(filename, index=False)
    logging.info(f"Factuurgegevens geëxporteerd naar {filename}")
