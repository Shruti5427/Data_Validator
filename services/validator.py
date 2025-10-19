import pandas as pd
import re

EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")


def _is_valid_email(email):
    if not email or pd.isna(email):
        return False
    return bool(EMAIL_RE.match(str(email).strip()))


def _is_valid_phone(phone):
    if pd.isna(phone) or phone is None:
        return False
    s = str(phone).strip()
    s_digits = ''.join(ch for ch in s if ch.isdigit())
    return len(s_digits) == 10


def validate_file(filepath, rules=None):
    """
    rules: list of strings among: ["name", "email", "phone", "marks", "duplicates"]
    returns dict: { errors: [...], clean_data: [...], total: int }
    """
    if rules is None:
        rules = []

    ext = filepath.rsplit('.', 1)[-1].lower()
    # read file defensively
    if ext == 'xlsx':
        df = pd.read_excel(filepath, engine="openpyxl")
    else:
        df = pd.read_csv(filepath)

    # Ensure df is a DataFrame
    if df is None:
        df = pd.DataFrame()

    df = df.copy()
    total = len(df)

    dup_mask = None
    if 'duplicates' in rules and total > 0:
        dup_mask = df.duplicated(keep='first')

    errors = []
    clean_rows = []

    for idx, row in df.iterrows():
        row_errors = []

        # Name
        if 'name' in rules and 'Name' in df.columns:
            if pd.isna(row.get('Name', '')) or str(row.get('Name', '')).strip() == '':
                row_errors.append('Missing Name')

        # Email
        if 'email' in rules and 'Email' in df.columns:
            if not _is_valid_email(row.get('Email')):
                row_errors.append('Invalid Email')

        # Phone
        if 'phone' in rules and 'Phone' in df.columns:
            if not _is_valid_phone(row.get('Phone')):
                row_errors.append('Invalid Phone Number')

        # Marks
        if 'marks' in rules and 'Marks' in df.columns:
            try:
                m = pd.to_numeric(row.get('Marks'), errors='coerce')
                if pd.isna(m) or not (0 <= m <= 100):
                    row_errors.append('Marks out of range')
            except Exception:
                row_errors.append('Marks invalid')

        # Duplicate
        if 'duplicates' in rules and dup_mask is not None:
            if dup_mask.iloc[idx]:
                row_errors.append('Duplicate Row')

        if row_errors:
            errors.append({
                'Row': idx + 2,
                'Errors': ', '.join(row_errors),
                'Data': row.to_dict()
            })
        else:
            clean_rows.append(row.to_dict())

    return {
        'errors': errors,
        'clean_data': clean_rows,
        'total': total
    }
