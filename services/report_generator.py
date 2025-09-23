import pandas as pd

def generate_report(validation_result, output_path):
    writer = pd.ExcelWriter(output_path, engine="openpyxl")

    # Summary
    summary_df = pd.DataFrame([{
        "Total Rows": validation_result["total"],
        "Valid Rows": len(validation_result["clean_data"]),
        "Invalid Rows": len(validation_result["errors"])
    }])
    summary_df.to_excel(writer, sheet_name="Summary", index=False)

    # Invalid rows
    if validation_result["errors"]:
        error_df = pd.DataFrame(validation_result["errors"])
        error_df.to_excel(writer, sheet_name="Invalid Rows", index=False)

    # Clean data
    if validation_result["clean_data"]:
        clean_df = pd.DataFrame(validation_result["clean_data"])
        clean_df.to_excel(writer, sheet_name="Clean Data", index=False)

    writer.close()
