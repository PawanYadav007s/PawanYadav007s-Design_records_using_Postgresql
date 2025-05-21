import pandas as pd
from models import db, DesignRecord, PORecord, Quotation
import json
import os
import sys

from datetime import datetime


def get_base_path():
    """Returns the base path depending on whether app is frozen (compiled) or not."""
    return os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))

def load_settings():
    """Loads or creates default settings.json for Excel export path."""
    base_path = get_base_path()
    settings_path = os.path.join(base_path, 'settings.json')
    default_settings = {
        "excel_save_path": os.path.join(base_path, "ExcelBackup")
    }

    # Create settings file if it doesn't exist
    if not os.path.exists(settings_path):
        os.makedirs(default_settings["excel_save_path"], exist_ok=True)
        with open(settings_path, "w") as f:
            json.dump(default_settings, f, indent=4)

    with open(settings_path, "r") as f:
        settings = json.load(f)

    # Ensure Excel path exists
    os.makedirs(settings["excel_save_path"], exist_ok=True)
    return settings


def export_all_data_to_excel():
    """Exports all design records to an Excel file for backup."""
    try:
        settings = load_settings()
        filepath = os.path.join(settings['excel_save_path'], 'design_records.xlsx')

        records = DesignRecord.query.all()
        data = []
        for record in records:
            po = PORecord.query.get(record.po_id)
            if not po:
                continue
            data.append({
                'PO Number': po.po_number,
                'Quotation Number': po.quotation_number,
                'PO Date': po.po_date,
                'Client Name': po.client_company_name,
                'Project Name': po.project_name,
                'Designer Name': record.designer_name,
                'Design Location': record.design_location,
                'Reference Design Location': record.reference_design_location,
                'Design Release Date': record.design_release_date,
            })

        pd.DataFrame(data).to_excel(filepath, index=False)
    except Exception as e:
        print(f"[ERROR] Failed to export Excel: {e}")



def log_to_history_excel(action, record, po):
    """
    Logs an action to the history Excel file.
    :param action: 'insert', 'update', or 'delete'
    :param record: DesignRecord instance
    :param po: PORecord instance
    """
    try:
        settings = load_settings()
        history_path = os.path.join(settings['excel_save_path'], 'design_records_history.xlsx')

        row = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Action': action,
            'PO Number': po.po_number if po else '',
            'Quotation Number': po.quotation_number if po else '',
            'PO Date': po.po_date if po else '',
            'Client Name': po.client_company_name if po else '',
            'Project Name': po.project_name if po else '',
            'Designer Name': record.designer_name,
            'Design Location': record.design_location,
            'Reference Design Location': record.reference_design_location,
            'Design Release Date': record.design_release_date
        }

        df_new = pd.DataFrame([row])

        if os.path.exists(history_path):
            df_existing = pd.read_excel(history_path)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new

        df_combined.to_excel(history_path, index=False)

        # ✅ Log success outside of try-except
        print(f"[LOG] {action.upper()} recorded for design by {record.designer_name} on PO {po.po_number}")

    except Exception as e:
        print(f"[ERROR] Logging to history Excel failed: {e}")
        
        
        
        
def update_quotation_master_excel():
    """
    Updates the master Excel file with all quotations (pending and non-pending).
    """
    try:
        settings = load_settings()
        filepath = os.path.join(settings['excel_save_path'], 'quotations_master.xlsx')

        all_quotations = Quotation.query.all()
        data = []
        for q in all_quotations:
            data.append({
                'Quotation No': q.quotation_number,
                'Date': q.quotation_date.strftime('%Y-%m-%d'),
                'Details': q.quotation_details,
                'Project': q.project_name,
                'Location': q.design_location,
                'Status': q.status
            })

        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False)
        print(f"[AUTO-SAVE] Updated quotations_master.xlsx with {len(df)} records.")

    except Exception as e:
        print(f"[ERROR] Failed to update quotation master Excel: {e}")