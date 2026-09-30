"""Tabular and Structured Data Reader Tool.
Parses CSV and Excel files, calculates column statistics, summaries, and value distributions.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from tools.registry import BaseTool
from backend.config import settings


class TabularReaderTool(BaseTool):
    name = "tabular_reader"
    description = "Inspects and analyzes CSV and Excel datasets, reporting columns, sample rows, and summary statistics."
    parameters_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path or filename of CSV/Excel file in data/uploads."
            },
            "preview_rows": {
                "type": "integer",
                "description": "Number of sample rows to preview (default 5)."
            }
        },
        "required": ["file_path"]
    }

    def execute(self, file_path: str, preview_rows: int = 5, **kwargs) -> Dict[str, Any]:
        target = Path(file_path)
        if not target.exists():
            # Check within uploads directory
            target = settings.UPLOAD_DIR / file_path
            if not target.exists():
                return {"ok": False, "error": f"File '{file_path}' not found."}

        try:
            if target.suffix.lower() == ".csv":
                df = pd.read_csv(target)
            elif target.suffix.lower() in (".xlsx", ".xls"):
                df = pd.read_excel(target)
            else:
                return {"ok": False, "error": f"Unsupported tabular format: '{target.suffix}'"}

            columns = list(df.columns.astype(str))
            shape = {"rows": len(df), "columns": len(columns)}
            head_data = df.head(preview_rows).to_dict(orient="records")

            # Numeric summary
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            stats = {}
            if numeric_cols:
                desc = df[numeric_cols].describe().to_dict()
                stats = {col: {k: round(v, 2) for k, v in desc[col].items()} for col in numeric_cols[:5]}

            return {
                "ok": True,
                "filename": target.name,
                "shape": shape,
                "columns": columns,
                "preview": head_data,
                "numeric_statistics": stats
            }
        except Exception as e:
            return {"ok": False, "error": f"Failed to parse tabular data: {str(e)}"}
