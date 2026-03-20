"""Tests for VPSR XLS parsing (minimal synthetic workbook)."""
import os
import tempfile

import pytest
import xlwt

from ingestion.vpsr_parse import parse_vpsr_xls


def _write_minimal_vpsr_xls(path: str) -> None:
    """
    Layout matches VPSR: row0/1 headers, data from row 4, col0 suburb,
    odd price columns 1,3,... until ncols-4, sales at ncols-4.
    """
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Sheet1")
    # ncols = 8 -> sales_col = 4; quarter cols at 1 and 3
    ws.write(0, 1, "Apr-Jun")
    ws.write(1, 1, 2025)
    ws.write(0, 3, "Jul-Sep")
    ws.write(1, 3, 2025)
    ws.write(4, 0, "Melbourne")
    ws.write(4, 1, 800000)
    ws.write(4, 3, 850000)
    ws.write(4, 4, 12)  # sales_volume (ncols must be 8 so sales_col = ncols - 4 == 4)
    ws.write(4, 7, 0)  # pad last column so xlrd ncols >= 8 (empty cell at col 7 is ignored by xlwt)
    wb.save(path)


def test_parse_vpsr_returns_suburb_and_quarters():
    with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp:
        path = tmp.name
    try:
        _write_minimal_vpsr_xls(path)
        rows = parse_vpsr_xls(path)
    finally:
        os.unlink(path)

    assert len(rows) == 1
    r = rows[0]
    assert r["suburb"] == "MELBOURNE"
    assert r["Apr_Jun_2025"] == 800000
    assert r["Jul_Sep_2025"] == 850000
    assert r["sales_volume"] == 12


def test_parse_vpsr_string_price():
    with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp:
        path = tmp.name
    try:
        wb = xlwt.Workbook()
        ws = wb.add_sheet("Sheet1")
        ws.write(0, 1, "Apr-Jun")
        ws.write(1, 1, 2025)
        ws.write(4, 0, "Ballarat")
        ws.write(4, 1, "650,000")
        ws.write(4, 4, 5)
        ws.write(4, 7, 0)
        wb.save(path)
        rows = parse_vpsr_xls(path)
    finally:
        os.unlink(path)

    assert rows[0]["suburb"] == "BALLARAT"
    assert rows[0]["Apr_Jun_2025"] == 650000


def test_parse_vpsr_skips_empty_suburb_row():
    with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp:
        path = tmp.name
    try:
        wb = xlwt.Workbook()
        ws = wb.add_sheet("Sheet1")
        ws.write(0, 1, "Apr-Jun")
        ws.write(1, 1, 2025)
        ws.write(4, 0, "")
        ws.write(5, 0, "Geelong")
        ws.write(5, 1, 500000)
        ws.write(5, 4, 1)
        ws.write(5, 7, 0)
        wb.save(path)
        rows = parse_vpsr_xls(path)
    finally:
        os.unlink(path)

    assert len(rows) == 1
    assert rows[0]["suburb"] == "GEELONG"
