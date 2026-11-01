# Library Management System (LMS)

A small Flask REST API for tracking books, members, and loans. Data is stored
**in memory** (plain Python objects, no database) and is reset every time the
app restarts — this project is meant to run before you've covered databases.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The API runs at `http://127.0.0.1:5000`.

## Web UI

Open `http://127.0.0.1:5000/` in a browser for a basic HTML front end (plain
forms and tables, no JavaScript) to add/delete books and members, and check
books in/out:

| Page | Path |
|---|---|
| Home | `/` |
| Books | `/ui/books` |
| Members | `/ui/members` |
| Loans | `/ui/loans` |

This UI is separate from the JSON API below — it's there so you can see the
app working without a REST client, and calls the same in-memory store.

## Entities

- **Book**: `id, title, author, isbn, total_copies, available_copies`
- **Member**: `id, name, email, membership_date`
- **Loan**: `id, book_id, member_id, loan_date, due_date, return_date`

## JSON API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/books` | List all books |
| POST | `/books` | Create a book |
| GET | `/books/<id>` | Get one book |
| PUT | `/books/<id>` | Update a book |
| DELETE | `/books/<id>` | Delete a book |
| GET | `/members` | List all members |
| POST | `/members` | Create a member |
| GET | `/members/<id>` | Get one member |
| PUT | `/members/<id>` | Update a member |
| DELETE | `/members/<id>` | Delete a member |
| POST | `/loans` | Check out a book (`book_id`, `member_id`) |
| PUT | `/loans/<id>/return` | Return a loaned book |
| GET | `/loans?member_id=&book_id=` | Look up loans |
| GET | `/loans/<id>/fine` | Get the outstanding loan fine |
| PUT | `/loans/<id>/fine/settle` | Record full fine settlement after return (no body) |

### Checkout restrictions

API and web-form checkouts reject members with outstanding fines (HTTP 409).
Fines accrue at $0.25 per overdue day, stop growing on return, and remain
outstanding until settled. The API rejection includes `outstanding_fine`, the
member's total unpaid amount. Other members' fines do not affect checkout.
Returning an item alone does not clear its fine. Staff can record full settlement
using `PUT /loans/<id>/fine/settle`; the item must first be returned (otherwise
HTTP 409). Repeating settlement is harmless. Once every outstanding fine is
settled, checkout is allowed again. Partial payments and other penalties are
outside this feature. Settlement records share the application's in-memory
storage and reset on restart; this endpoint records settlement, not a payment
processor transaction.

## Tests

```bash
pytest
```
