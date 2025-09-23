import pandas as pd
import re

def validate_file(filepath):
    # Load file depending on extension
    df = pd.read_excel(filepath) if filepath.endswith(".xlsx") else pd.read_csv(filepath)
    
    errors = []
    clean_rows = []
    seen_rows = set()  # for duplicate detection

    for idx, row in df.iterrows():
        row_errors = []

        # 1. Name validation (not empty)
        if "Name" in df.columns and pd.isna(row.get("Name", "")):
            row_errors.append("Missing Name")

        # 2. Email validation (simple check: must contain @ and end with .com)
        if "Email" in df.columns:
            email = str(row.get("Email", ""))
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                row_errors.append("Invalid Email")

        # 3. Phone validation (must be 10 digits)
        if "Phone" in df.columns:
            phone = str(row.get("Phone", ""))
            if not phone.isdigit() or len(phone) != 10:
                row_errors.append("Invalid Phone Number")

        # 4. Marks validation (0–100 range)
        if "Marks" in df.columns:
            marks = row.get("Marks")
            if pd.isna(marks) or not (0 <= marks <= 100):
                row_errors.append("Marks out of range")

        # 5. Duplicate row check (using tuple of row values)
        row_tuple = tuple(row.values)
        if row_tuple in seen_rows:
            row_errors.append("Duplicate Row")
        else:
            seen_rows.add(row_tuple)

        # Collect results
        if row_errors:
            errors.append({
                "Row": idx + 2,   # +2 because Excel has header row
                "Errors": ", ".join(row_errors),
                "Data": row.to_dict()
            })
        else:
            clean_rows.append(row.to_dict())

    return {
        "errors": errors,
        "clean_data": clean_rows,
        "total": len(df)
    }
