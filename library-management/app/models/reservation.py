from datetime import date


class Reservation:
    def __init__(self, id, book_id, member_id, reservation_date=None, fulfilled=False):
        self.id = id
        self.book_id = book_id
        self.member_id = member_id
        self.reservation_date = reservation_date or date.today()
        self.fulfilled = fulfilled

    def to_dict(self):
        return {
            "id": self.id,
            "book_id": self.book_id,
            "member_id": self.member_id,
            "reservation_date": self.reservation_date.isoformat(),
            "fulfilled": self.fulfilled,
        }


def active_holds(reservations, book_id):
    """Unfulfilled reservations for a book, oldest first (the hold queue)."""
    holds = [r for r in reservations if r.book_id == book_id and not r.fulfilled]
    return sorted(holds, key=lambda r: r.id)
