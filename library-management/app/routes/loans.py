from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from app import store
from app.models.loan import Loan, LOAN_PERIOD_DAYS

FINE_PER_DAY = 0.25  # dollars charged per day overdue

loans_bp = Blueprint("loans", __name__, url_prefix="/loans")


def outstanding_fine(loan):
    if loan.fine_settled:
        return 0.0
    end_date = loan.return_date or date.today()
    days_overdue = max(0, (end_date - loan.due_date).days)
    return round(days_overdue * FINE_PER_DAY, 2)


def member_outstanding_fines(member_id):
    return round(sum(outstanding_fine(loan) for loan in store.loans.values()
                     if loan.member_id == member_id), 2)


@loans_bp.route("", methods=["GET"])
def list_loans():
    results = list(store.loans.values())
    member_id = request.args.get("member_id", type=int)
    book_id = request.args.get("book_id", type=int)
    if member_id is not None:
        results = [l for l in results if l.book_id == member_id]
    if book_id is not None:
        results = [l for l in results if l.book_id == book_id]
    return jsonify([l.to_dict() for l in results])


@loans_bp.route("", methods=["POST"])
def checkout_book():
    data = request.get_json()
    book = store.books.get(data["book_id"])
    if book is None:
        return jsonify({"error": "Book not found"}), 404

    outstanding = member_outstanding_fines(data["member_id"])
    if outstanding > 0:
        return jsonify({"error": "Outstanding fines must be settled before checkout",
                        "outstanding_fine": outstanding}), 409

    book.available_copies -= 1

    loan_id = store.next_id("loan")
    loan = Loan(
        id=loan_id,
        book_id=data["book_id"],
        member_id=data["member_id"],
        due_date=Loan.default_due_date(),
    )
    store.loans[loan_id] = loan
    return jsonify(loan.to_dict()), 201


@loans_bp.route("/<int:loan_id>/return", methods=["PUT"])
def return_book(loan_id):
    loan = store.loans.get(loan_id)
    if loan is None:
        return jsonify({"error": "Loan not found"}), 404
    if loan.return_date is not None:
        return jsonify({"error": "Loan already returned"}), 400

    loan.return_date = date.today()
    book = store.books.get(loan.book_id)
    book.available_copies += 1

    return jsonify(loan.to_dict())


@loans_bp.route("/<int:loan_id>/renew", methods=["PUT"])
def renew_loan(loan_id):
    loan = store.loans.get(loan_id)
    if loan is None:
        return jsonify({"error": "Loan not found"}), 404
    if loan.return_date is not None:
        return jsonify({"error": "Loan already returned"}), 400

    loan.due_date = loan.due_date + timedelta(days=LOAN_PERIOD_DAYS)
    return jsonify(loan.to_dict())


@loans_bp.route("/<int:loan_id>/fine", methods=["GET"])
def get_fine(loan_id):
    loan = store.loans.get(loan_id)
    if loan is None:
        return jsonify({"error": "Loan not found"}), 404

    return jsonify({"loan_id": loan_id, "fine_amount": outstanding_fine(loan)})


@loans_bp.route("/<int:loan_id>/fine/settle", methods=["PUT"])
def settle_fine(loan_id):
    """Record full settlement at the front desk after the item is returned."""
    loan = store.loans.get(loan_id)
    if loan is None:
        return jsonify({"error": "Loan not found"}), 404
    if loan.return_date is None:
        return jsonify({"error": "Return the loan before settling its fine"}), 409
    loan.fine_settled = True
    return jsonify({"loan_id": loan_id, "fine_amount": outstanding_fine(loan)})
