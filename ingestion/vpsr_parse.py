"""
Shared XLS parser for VPSR median house/unit quarterly files (same layout).
"""
import xlrd


def parse_vpsr_xls(filepath: str) -> list[dict]:
    """
    Parse VPSR quarterly XLS. Returns list of {suburb, quarter_col: price, ...}.
    """
    wb = xlrd.open_workbook(filepath)
    ws = wb.sheet_by_index(0)

    row0 = ws.row_values(0)
    row1 = ws.row_values(1)
    quarter_cols = {}
    for i in range(1, ws.ncols - 4, 2):
        label = str(row0[i]).strip()
        year = str(row1[i]).strip()
        if label and year and year.replace(".0", "").isdigit():
            yr = year.replace(".0", "")
            quarter_cols[i] = f"{label.replace('-', '_')}_{yr}"

    sales_col = ws.ncols - 4

    results = []
    for row_idx in range(4, ws.nrows):
        suburb = str(ws.cell_value(row_idx, 0)).strip().upper()
        if not suburb:
            continue
        row_data = {"suburb": suburb}
        for col_idx, col_name in quarter_cols.items():
            raw = ws.cell_value(row_idx, col_idx)
            if isinstance(raw, str):
                clean = raw.strip().replace(",", "")
                row_data[col_name] = int(clean) if clean.isdigit() else None
            elif isinstance(raw, (int, float)) and raw > 0:
                row_data[col_name] = int(raw)
            else:
                row_data[col_name] = None
        sales_raw = ws.cell_value(row_idx, sales_col)
        if isinstance(sales_raw, (int, float)):
            row_data["sales_volume"] = int(sales_raw)
        results.append(row_data)
    return results
