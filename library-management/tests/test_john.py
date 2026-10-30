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


def test_list_books_shows_copy_availability(client):
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


