# Tests for existing Loans and Reservations features (Gavin)
# Features covered (Table B): check out a book, return a book, look up loans,
# renew a loan, create a reservation, list reservations.
from datetime import date, timedelta


# ---------- helpers ----------

def make_book(client, title="Dune", copies=1):
    response = client.post("/books", json={
        "title": title, "author": "Frank Herbert",
        "isbn": "978-0441013593", "total_copies": copies,
    })
    return response.get_json()


def make_member(client, name="Alice", email="alice@example.com"):
    response = client.post("/members", json={"name": name, "email": email})
    return response.get_json()


def checkout(client, book_id, member_id):
    return client.post("/loans", json={"book_id": book_id, "member_id": member_id})


# ---------- check out a book ----------

def test_checkout_creates_loan_with_14_day_due_date(client):
    book = make_book(client)
    member = make_member(client)

    response = checkout(client, book["id"], member["id"])

    assert response.status_code == 201
    loan = response.get_json()
    assert loan["book_id"] == book["id"]
    assert loan["member_id"] == member["id"]
    assert loan["loan_date"] == date.today().isoformat()
    assert loan["due_date"] == (date.today() + timedelta(days=14)).isoformat()
    assert loan["return_date"] is None


def test_checkout_decreases_available_copies(client):
    book = make_book(client, copies=3)
    member = make_member(client)

    checkout(client, book["id"], member["id"])

    updated = client.get(f"/books/{book['id']}").get_json()
    assert updated["available_copies"] == 2
    assert updated["total_copies"] == 3


def test_checkout_nonexistent_book_returns_404_and_creates_no_loan(client):
    member = make_member(client)

    response = checkout(client, 999, member["id"])

    assert response.status_code == 404
    assert client.get("/loans").get_json() == []


def test_checkout_fails_when_no_copies_available(client):
    # R11/R2: a book with no available copies is "checked out" and can only
    # be placed on hold, so a second checkout must be refused.
    book = make_book(client, copies=1)
    alice = make_member(client)
    bob = make_member(client, "Bob", "bob@example.com")
    checkout(client, book["id"], alice["id"])

    response = checkout(client, book["id"], bob["id"])

    assert response.status_code in (400, 409)
    assert client.get(f"/books/{book['id']}").get_json()["available_copies"] == 0


def test_checkout_fails_for_nonexistent_member(client):
    # R31: the system must record which member borrowed each book,
    # so a loan for a member that does not exist must be rejected.
    book = make_book(client)

    response = checkout(client, book["id"], 999)

    assert response.status_code == 404
    assert client.get(f"/books/{book['id']}").get_json()["available_copies"] == 1
