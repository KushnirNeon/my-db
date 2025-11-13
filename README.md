# Mini DBMS (Desktop & Web)

A lightweight database management system with **desktop GUI** (Tkinter) and **web version** (FastAPI + JS/HTML/CSS). Supports tables, columns, rows, and basic SQL-like operations.

---

## Features

### Desktop (Tkinter)
- GUI with menus, table list, and editable grid.
- CRUD for **tables**, **columns**, and **rows**.
- Data validation (`integer`, `real`, `char`, `string`, `email`, `enum`).
- Join operation between tables.
- Serialization to/from JSON (`storage.py`).

### Web (FastAPI)
- REST API for database operations.
- Endpoints for CRUD: `/db`, `/tables`, `/tables/{name}/columns`, `/tables/{name}/rows`.
- Join support via `/join`.
- Frontend: dynamic tables, modals, toast notifications.
- Supports `integer`, `real`, `char`, `email`, `enum` validation.

---

## Models
- **Column**: name, dtype, enum_values; validates input.
- **Table**: columns, rows, add/edit/delete operations.
- **Database**: collection of tables, serialization.
- **join_tables**: SQL-like inner join between tables.

---

## Tests
- Email validation, enum validation.
- Char and real type validation.
- Join operations correctness.
- Error handling for missing join keys.
