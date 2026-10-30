def test_add_book(client):
    """Adding a book stores its details and makes all copies available."""
    payload = {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "isbn": "978-0547928227",
        "total_copies": 3,
    }

    response = client.post("/books", json=payload)

    assert response.status_code == 201
    expected_book = {"id": 1, **payload, "available_copies": 3}
    assert response.get_json() == expected_book

    catalog_response = client.get("/books")
    assert catalog_response.status_code == 200
    assert catalog_response.get_json() == [expected_book]


# contenious, should this be unique?
def test_add_book_same_book_twice(client):
    """Adding identical book details twice creates two independent records."""
    payload = {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "isbn": "978-0547928227",
        "total_copies": 3,
    }
    first_response = client.post("/books", json=payload)
    second_response = client.post("/books", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    first_id = first_response.get_json()["id"]
    second_id = second_response.get_json()["id"]
    assert first_id != second_id
    expected_first = {"id": first_id, **payload, "available_copies": 3}
    expected_second = {"id": second_id, **payload, "available_copies": 3}
    assert first_response.get_json() == expected_first
    assert second_response.get_json() == expected_second

    catalog_response = client.get("/books")
    assert catalog_response.status_code == 200
    books = catalog_response.get_json()
    assert len(books) == 2
    assert {book["id"]: book for book in books} == {
        first_id: expected_first, second_id: expected_second
    }

def test_add_book_missing_title(client):
    """Missing required book fields should be rejected without adding a book."""
    # Capture server errors as HTTP responses so the assertion reports the bug.
    client.application.config["PROPAGATE_EXCEPTIONS"] = False
    payload = {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "isbn": "978-0547928227",
        "total_copies": 3,
    }
    missing_field="title"
    del payload[missing_field]

    response = client.post("/books", json=payload)

    assert response.status_code == 400, (
        f"Missing Title should return 400, "
        f"got {response.status_code}"
    )
    catalog_response = client.get("/books")
    assert catalog_response.status_code == 200
    assert catalog_response.get_json() == []


def test_add_book_missing_author(client):
    """Missing required book fields should be rejected without adding a book."""
    # Capture server errors as HTTP responses so the assertion reports the bug.
    client.application.config["PROPAGATE_EXCEPTIONS"] = False
    payload = {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "isbn": "978-0547928227",
        "total_copies": 3,
    }
    missing_field="author"
    del payload[missing_field]

    response = client.post("/books", json=payload)

    assert response.status_code == 400, (
        f"Missing Author should return 400, "
        f"got {response.status_code}"
    )
    catalog_response = client.get("/books")
    assert catalog_response.status_code == 200
    assert catalog_response.get_json() == []

def test_add_book_missing_isbn(client):
    """Missing required book fields should be rejected without adding a book."""
    # Capture server errors as HTTP responses so the assertion reports the bug.
    client.application.config["PROPAGATE_EXCEPTIONS"] = False
    payload = {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "isbn": "978-0547928227",
        "total_copies": 3,
    }
    missing_field="isbn"
    del payload[missing_field]

    response = client.post("/books", json=payload)

    assert response.status_code == 400, (
        f"Missing ISBN should return 400, "
        f"got {response.status_code}"
    )
    catalog_response = client.get("/books")
    assert catalog_response.status_code == 200
    assert catalog_response.get_json() == []

def test_add_book_missing_total_copies(client):
    """total_copies is an optional parameter, and should be set to 1 by default"""
    # Capture server errors as HTTP responses so the assertion reports the bug.
    client.application.config["PROPAGATE_EXCEPTIONS"] = False
    payload = {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "isbn": "978-0547928227",
        "total_copies": 3,
    }
    missing_field="total_copies"
    del payload[missing_field]

    response = client.post("/books", json=payload)

    catalog_response = client.get("/books")
    assert catalog_response.status_code == 200

    books = catalog_response.get_json()
    assert len(books) > 0
    assert books[0]["total_copies"] == 1


def test_list_books_shows_copy_availability_non_empty_catalog(client):
    """The catalog lists every book with its current total and available copies."""
    # add books
    first_book = {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "isbn": "978-0547928227",
        "total_copies": 1,
    }
    second_book = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "978-0132350884",
        "total_copies": 3,
    }
    first_response = client.post("/books", json=first_book)
    second_response = client.post("/books", json=second_book)
    assert first_response.status_code == 201
    assert second_response.status_code == 201
    
    # get ids
    first_id = first_response.get_json()["id"]
    second_id = second_response.get_json()["id"]

    # make a member to take a loan of the first book
    member_response = client.post(
        "/members", json={"name": "John", "email": "john@example.com"}
    )
    assert member_response.status_code == 201
    checkout_response = client.post(
        "/loans",
        json={"book_id": first_id, "member_id": member_response.get_json()["id"]},
    )
    assert checkout_response.status_code == 201

    # check that the books have the right # of values to them
    response = client.get("/books")

    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 2
    books_by_id = {book["id"]: book for book in books}
    assert books_by_id[first_id] == {
        "id": first_id, **first_book, "available_copies": 0
    }
    assert books_by_id[second_id] == {
        "id": second_id, **second_book, "available_copies": 3
    }


def test_list_books_shows_copy_availability_empty_catalog(client):
    """An empty catalog returns no books or copy availability entries."""
    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == []

