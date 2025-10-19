"""Png module to generate validation reports in Excel format."""
import pandas as pd

"""Generate an Excel report from validation results."""
def generate_report(validation_result, report_path, clean_only_path=None):
    # Full report (Summary, Invalid Rows, Clean Data)
    with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
        summary_df = pd.DataFrame([{
            'Total Rows': validation_result.get('total', 0),
            'Valid Rows': len(validation_result.get('clean_data', [])),
            'Invalid Rows': len(validation_result.get('errors', []))
        }])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        errors = validation_result.get('errors', [])
        if errors:
            expanded = []
            for e in errors:
                base = {'Row': e.get('Row'), 'Errors': e.get('Errors')}
                data = e.get('Data') or {}
                merged = {**base, **{str(k): v for k, v in data.items()}}
                expanded.append(merged)
            error_df = pd.DataFrame(expanded)
            error_df.to_excel(writer, sheet_name='Invalid Rows', index=False)

        clean = validation_result.get('clean_data', [])
        if clean:
            clean_df = pd.DataFrame(clean)
            clean_df.to_excel(writer, sheet_name='Clean Data', index=False)

    # Also create a clean-only workbook if requested
    if clean_only_path is not None:
        with pd.ExcelWriter(clean_only_path, engine='openpyxl') as w2:
            clean = validation_result.get('clean_data', [])
            if clean:
                pd.DataFrame(clean).to_excel(w2, sheet_name='Clean Data', index=False)
            else:
                pd.DataFrame([{'Message': 'No clean rows found'}]).to_excel(w2, sheet_name='Info', index=False)
