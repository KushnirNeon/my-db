from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import re

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

@dataclass
class Column:
    name: str
    dtype: str
    enum_values: Optional[List[str]] = None

    def validate(self, value: Any) -> Any:
        if value is None:
            return None
        if self.dtype == "integer":
            if isinstance(value, bool):
                raise ValueError("Boolean is not allowed for integer")
            try:
                return int(value)
            except Exception:
                raise ValueError(f"'{value}' is not a valid integer")
        elif self.dtype == "real":
            try:
                return float(value)
            except Exception:
                raise ValueError(f"'{value}' is not a valid real")
        elif self.dtype == "char":
            s = str(value)
            if len(s) != 1:
                raise ValueError(f"'{value}' is not a single character")
            return s
        elif self.dtype == "string":
            return str(value)
        elif self.dtype == "email":
            s = str(value)
            if not EMAIL_RE.match(s):
                raise ValueError(f"'{value}' is not a valid email")
            return s
        elif self.dtype == "enum":
            if not self.enum_values:
                raise ValueError("Enum column must have predefined values")
            s = str(value)
            if s not in self.enum_values:
                raise ValueError(f"'{value}' is not in enum {self.enum_values}")
            return s
        else:
            raise ValueError(f"Unsupported dtype: {self.dtype}")

@dataclass
class Table:
    name: str
    columns: List[Column] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)

    def column_names(self) -> List[str]:
        return [c.name for c in self.columns]

    def add_column(self, column: Column) -> None:
        if column.name in self.column_names():
            raise ValueError(f"Column '{column.name}' already exists")
        self.columns.append(column)
        for r in self.rows:
            r[column.name] = None

    def delete_column(self, name: str) -> None:
        idx = None
        for i, c in enumerate(self.columns):
            if c.name == name:
                idx = i
                break
        if idx is None:
            raise ValueError(f"No such column '{name}'")
        self.columns.pop(idx)
        for r in self.rows:
            r.pop(name, None)

    def add_row(self, values: Dict[str, Any]) -> None:
        row = {}
        for col in self.columns:
            val = values.get(col.name)
            row[col.name] = col.validate(val) if val is not None else None
        self.rows.append(row)

    def edit_row(self, index: int, values: Dict[str, Any]) -> None:
        if not (0 <= index < len(self.rows)):
            raise IndexError("Row index out of range")
        current = self.rows[index].copy()
        for k, v in values.items():
            if k not in self.column_names():
                continue
            col = next(c for c in self.columns if c.name == k)
            current[k] = col.validate(v) if v is not None else None
        self.rows[index] = current

    def delete_row(self, index: int) -> None:
        if not (0 <= index < len(self.rows)):
            raise IndexError("Row index out of range")
        self.rows.pop(index)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "columns": [
                {"name": c.name, "dtype": c.dtype, "enum_values": c.enum_values}
                for c in self.columns
            ],
            "rows": self.rows,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Table":
        t = Table(name=d["name"])
        t.columns = [Column(**c) for c in d["columns"]]
        t.rows = [dict(r) for r in d.get("rows", [])]
        return t

@dataclass
class Database:
    name: str
    tables: Dict[str, Table] = field(default_factory=dict)

    def create_table(self, name: str) -> Table:
        if name in self.tables:
            raise ValueError(f"Table '{name}' already exists")
        t = Table(name=name)
        self.tables[name] = t
        return t

    def delete_table(self, name: str) -> None:
        if name not in self.tables:
            raise ValueError(f"No such table '{name}'")
        del self.tables[name]

    def get_table(self, name: str) -> Table:
        if name not in self.tables:
            raise ValueError(f"No such table '{name}'")
        return self.tables[name]

    def list_tables(self) -> List[str]:
        return list(self.tables.keys())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tables": {k: v.to_dict() for k, v in self.tables.items()},
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Database":
        db = Database(name=d["name"])
        for k, tv in d.get("tables", {}).items():
            db.tables[k] = Table.from_dict(tv)
        return db

def join_tables(left: Table, right: Table, key: str, suffixes: Tuple[str, str] = ("_x", "_y")) -> Table:
    if key not in left.column_names() or key not in right.column_names():
        raise ValueError(f"Join key '{key}' must exist in both tables")
    out_cols: List[Column] = []
    left_names = left.column_names()
    for c in left.columns:
        out_cols.append(Column(name=c.name, dtype=c.dtype, enum_values=c.enum_values))
    for c in right.columns:
        if c.name == key and key in left_names:
            continue
        name = c.name if c.name not in left_names else c.name + suffixes[1]
        out_cols.append(Column(name=name, dtype=c.dtype, enum_values=c.enum_values))
    out = Table(name=f"{left.name}_JOIN_{right.name}", columns=out_cols)
    idx: Dict[Any, List[Dict[str, Any]]] = {}
    for rr in right.rows:
        idx.setdefault(rr.get(key), []).append(rr)
    for lr in left.rows:
        matches = idx.get(lr.get(key), [])
        for rr in matches:
            merged: Dict[str, Any] = {}
            for c in left.columns:
                merged[c.name] = lr.get(c.name)
            for c in right.columns:
                if c.name == key and key in left_names:
                    continue
                name = c.name if c.name not in left_names else c.name + suffixes[1]
                merged[name] = rr.get(c.name)
            out.rows.append(merged)
    return out
