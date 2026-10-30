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


def test_view_specific_book(client):
    """Looking up a book by ID returns only that book and its details."""
    other_book = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "978-0132350884",
        "total_copies": 1,
    }
    target_book = {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "isbn": "978-0547928227",
        "total_copies": 3,
    }
    other_response = client.post("/books", json=other_book)
    target_response = client.post("/books", json=target_book)
    assert other_response.status_code == 201
    assert target_response.status_code == 201
    book_id = target_response.get_json()["id"]

    response = client.get(f"/books/{book_id}")

    assert response.status_code == 200
    assert response.get_json() == {
        "id": book_id, **target_book, "available_copies": 3
    }

def test_view_specific_book_book_id_does_not_exist(client):
    """Looking up a nonexistent book ID returns a not-found error."""
    response = client.get("/books/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Book not found"}


def test_search_books_by_title(client):
    """Search finds partial title matches regardless of case."""
    books = [
        {
            "title": "The Hobbit",
            "author": "J. R. R. Tolkien",
            "isbn": "978-0547928227",
            "total_copies": 2,
        },
        {
            "title": "The Fellowship of the Ring",
            "author": "J. R. R. Tolkien",
            "isbn": "978-0547928210",
            "total_copies": 1,
        },
        {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "isbn": "978-0132350884",
            "total_copies": 3,
        },
    ]
    expected_books = []
    for book in books:
        response = client.post("/books", json=book)
        assert response.status_code == 201
        expected_books.append(
            {"id": response.get_json()["id"], **book,
             "available_copies": book["total_copies"]}
        )

    # book exists, via title
    title_response = client.get("/books", query_string={"search": "HOBB"})
    assert title_response.status_code == 200
    assert title_response.get_json() == [expected_books[0]]

    author_response = client.get("/books", query_string={"search": "TOLK"})
    assert author_response.status_code == 200
    matches_by_id = {book["id"]: book for book in author_response.get_json()}
    assert len(author_response.get_json()) == 2
    assert matches_by_id == {book["id"]: book for book in expected_books[:2]}

def test_search_books_by_author(client):
    """Search finds partial author matches regardless of case."""
    books = [
        {
            "title": "The Hobbit",
            "author": "J. R. R. Tolkien",
            "isbn": "978-0547928227",
            "total_copies": 2,
        },
        {
            "title": "The Fellowship of the Ring",
            "author": "J. R. R. Tolkien",
            "isbn": "978-0547928210",
            "total_copies": 1,
        },
        {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "isbn": "978-0132350884",
            "total_copies": 3,
        },
    ]
    expected_books = []
    for book in books:
        response = client.post("/books", json=book)
        assert response.status_code == 201
        expected_books.append(
            {"id": response.get_json()["id"], **book,
             "available_copies": book["total_copies"]}
        )

    # book exists, via author
    author_response = client.get("/books", query_string={"search": "TOLK"})
    assert author_response.status_code == 200
    matches_by_id = {book["id"]: book for book in author_response.get_json()}
    assert len(author_response.get_json()) == 2
    assert matches_by_id == {book["id"]: book for book in expected_books[:2]}

def test_search_books_by_isbn(client):
    """Search finds book based on exact isbn."""
    books = [
        {
            "title": "The Hobbit",
            "author": "J. R. R. Tolkien",
            "isbn": "978-0547928227",
            "total_copies": 2,
        },
        {
            "title": "The Fellowship of the Ring",
            "author": "J. R. R. Tolkien",
            "isbn": "978-0547928210",
            "total_copies": 1,
        },
        {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "isbn": "978-0132350884",
            "total_copies": 3,
        },
    ]
    expected_books = []
    for book in books:
        response = client.post("/books", json=book)
        assert response.status_code == 201
        expected_books.append(
            {"id": response.get_json()["id"], **book,
             "available_copies": book["total_copies"]}
        )

    # book exists, via isbn
    isbn_response = client.get("/books", query_string={"search": "978-0132350884"})
    assert isbn_response.status_code == 200, f"ISBN search failed. Expected status 200, but got {isbn_response.status_code}"
    assert isbn_response.get_json() == [expected_books[3]]



def test_search_books_query_does_not_exit(client):
    """Search should not come up with a case."""
    books = [
        {
            "title": "The Hobbit",
            "author": "J. R. R. Tolkien",
            "isbn": "978-0547928227",
            "total_copies": 2,
        },
        {
            "title": "The Fellowship of the Ring",
            "author": "J. R. R. Tolkien",
            "isbn": "978-0547928210",
            "total_copies": 1,
        },
        {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "isbn": "978-0132350884",
            "total_copies": 3,
        },
    ]
    expected_books = []
    for book in books:
        response = client.post("/books", json=book)
        assert response.status_code == 201
        expected_books.append(
            {"id": response.get_json()["id"], **book,
             "available_copies": book["total_copies"]}
        )
    # doesn't exist
    no_match_response = client.get("/books", query_string={"search": "nonexistent"})
    assert no_match_response.status_code == 200
    assert no_match_response.get_json() == []


