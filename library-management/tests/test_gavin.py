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


# ---------- return a book ----------

def test_return_sets_return_date_and_restores_copy(client):
    book = make_book(client, copies=2)
    member = make_member(client)
    loan = checkout(client, book["id"], member["id"]).get_json()

    response = client.put(f"/loans/{loan['id']}/return")

    assert response.status_code == 200
    assert response.get_json()["return_date"] == date.today().isoformat()
    assert client.get(f"/books/{book['id']}").get_json()["available_copies"] == 2


def test_return_same_loan_twice_is_rejected(client):
    book = make_book(client)
    member = make_member(client)
    loan = checkout(client, book["id"], member["id"]).get_json()
    client.put(f"/loans/{loan['id']}/return")

    response = client.put(f"/loans/{loan['id']}/return")

    assert response.status_code == 400
    # copies must not be added back a second time
    assert client.get(f"/books/{book['id']}").get_json()["available_copies"] == 1


def test_return_nonexistent_loan_returns_404(client):
    response = client.put("/loans/999/return")
    assert response.status_code == 404


def test_full_checkout_return_checkout_cycle(client):
    book = make_book(client, copies=1)
    alice = make_member(client)
    bob = make_member(client, "Bob", "bob@example.com")

    first = checkout(client, book["id"], alice["id"]).get_json()
    client.put(f"/loans/{first['id']}/return")
    second = checkout(client, book["id"], bob["id"])

    assert second.status_code == 201
    assert second.get_json()["member_id"] == bob["id"]
    assert client.get(f"/books/{book['id']}").get_json()["available_copies"] == 0


# ---------- look up loans ----------

def test_list_loans_filtered_by_book_id(client):
    book1 = make_book(client, "Dune")
    book2 = make_book(client, "Emma")
    member = make_member(client)
    checkout(client, book1["id"], member["id"])
    checkout(client, book2["id"], member["id"])

    loans = client.get(f"/loans?book_id={book2['id']}").get_json()

    assert len(loans) == 1
    assert loans[0]["book_id"] == book2["id"]


def test_list_loans_filtered_by_member_id(client):
    # R1/R31: a member's loans must be retrievable by member.
    # three books so that book ids and member ids do not line up
    make_book(client, "Dune")
    book2 = make_book(client, "Emma")
    book3 = make_book(client, "Ulysses")
    alice = make_member(client)
    bob = make_member(client, "Bob", "bob@example.com")
    checkout(client, book2["id"], alice["id"])   # book id 2, member id 1
    checkout(client, book3["id"], bob["id"])     # book id 3, member id 2

    loans = client.get(f"/loans?member_id={bob['id']}").get_json()

    assert len(loans) == 1
    assert loans[0]["member_id"] == bob["id"]


# ---------- renew a loan ----------

def test_renew_extends_due_date(client):
    book = make_book(client)
    member = make_member(client)
    loan = checkout(client, book["id"], member["id"]).get_json()

    response = client.put(f"/loans/{loan['id']}/renew")

    assert response.status_code == 200
    assert response.get_json()["due_date"] > loan["due_date"]
    stored = client.get(f"/loans?book_id={book['id']}").get_json()[0]
    assert stored["due_date"] == response.get_json()["due_date"]


def test_renew_returned_loan_is_rejected(client):
    book = make_book(client)
    member = make_member(client)
    loan = checkout(client, book["id"], member["id"]).get_json()
    client.put(f"/loans/{loan['id']}/return")

    response = client.put(f"/loans/{loan['id']}/renew")

    assert response.status_code == 400


def test_renew_nonexistent_loan_returns_404(client):
    assert client.put("/loans/999/renew").status_code == 404


# ---------- create a reservation ----------

def test_create_reservation_returns_unfulfilled_hold(client):
    book = make_book(client)
    member = make_member(client)

    response = client.post("/reservations", json={
        "book_id": book["id"], "member_id": member["id"],
    })

    assert response.status_code == 201
    reservation = response.get_json()
    assert reservation["book_id"] == book["id"]
    assert reservation["member_id"] == member["id"]
    assert reservation["fulfilled"] is False
    assert reservation["reservation_date"] == date.today().isoformat()


def test_create_reservation_for_nonexistent_book_returns_404(client):
    member = make_member(client)
    response = client.post("/reservations", json={"book_id": 999, "member_id": member["id"]})
    assert response.status_code == 404
    assert client.get("/reservations").get_json() == []


def test_create_reservation_for_nonexistent_member_returns_404(client):
    book = make_book(client)
    response = client.post("/reservations", json={"book_id": book["id"], "member_id": 999})
    assert response.status_code == 404
    assert client.get("/reservations").get_json() == []


def test_hold_on_lent_book_blocks_checkout_by_other_member(client):
    # R2: a member who places a hold on a lent book must receive it at its
    # earliest availability, so another member cannot take it first.
    book = make_book(client, copies=1)
    alice = make_member(client)
    bob = make_member(client, "Bob", "bob@example.com")
    carol = make_member(client, "Carol", "carol@example.com")
    loan = checkout(client, book["id"], alice["id"]).get_json()
    client.post("/reservations", json={"book_id": book["id"], "member_id": bob["id"]})
    client.put(f"/loans/{loan['id']}/return")

    response = checkout(client, book["id"], carol["id"])

    assert response.status_code in (400, 409)


# ---------- list reservations ----------

def test_list_reservations_empty_initially(client):
    response = client.get("/reservations")
    assert response.status_code == 200
    assert response.get_json() == []


def test_list_reservations_filtered_by_book_and_member(client):
    book1 = make_book(client, "Dune")
    book2 = make_book(client, "Emma")
    alice = make_member(client)
    bob = make_member(client, "Bob", "bob@example.com")
    client.post("/reservations", json={"book_id": book1["id"], "member_id": alice["id"]})
    client.post("/reservations", json={"book_id": book2["id"], "member_id": alice["id"]})
    client.post("/reservations", json={"book_id": book2["id"], "member_id": bob["id"]})

    assert len(client.get("/reservations").get_json()) == 3
    by_book = client.get(f"/reservations?book_id={book2['id']}").get_json()
    assert {r["member_id"] for r in by_book} == {alice["id"], bob["id"]}
    by_member = client.get(f"/reservations?member_id={bob['id']}").get_json()
    assert len(by_member) == 1 and by_member[0]["book_id"] == book2["id"]
