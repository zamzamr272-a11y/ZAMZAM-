import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DATABASE_URL"] = "sqlite:////tmp/nexora_qa_test.db"
os.environ["AUTO_CREATE_SCHEMA"] = "false"
os.environ["JWT_SECRET"] = "qa-secret-not-for-production"

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app, Base, engine, _auth_attempts
import pytest

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _auth_attempts.clear()
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

def register(client, username):
    r = client.post("/api/v1/auth/register", json={"username": username, "password": "CorrectHorse2026!"})
    assert r.status_code == 201, r.text
    return r.json()

def auth(token):
    return {"Authorization": f"Bearer {token}"}

def test_auth_register_login_and_recovery(client):
    created = register(client, "tester_one")
    assert created["user"]["profile_code"].startswith("NX-")
    assert created["recovery_code"].startswith("NX-")
    logged = client.post("/api/v1/auth/login", json={"username": "tester_one", "password": "CorrectHorse2026!"})
    assert logged.status_code == 200
    me = client.get("/api/v1/me", headers=auth(logged.json()["access_token"]))
    assert me.status_code == 200 and me.json()["username"] == "tester_one"
    recovered = client.post("/api/v1/auth/recovery/redeem", json={
        "username": "tester_one", "recovery_code": created["recovery_code"], "new_password": "AnotherGoodPass2026!"
    })
    assert recovered.status_code == 200
    assert client.post("/api/v1/auth/login", json={"username": "tester_one", "password": "AnotherGoodPass2026!"}).status_code == 200
    used_again = client.post("/api/v1/auth/recovery/redeem", json={
        "username": "tester_one", "recovery_code": created["recovery_code"], "new_password": "YetAnotherPass2026!"
    })
    assert used_again.status_code == 400

def test_finance_crud_and_transfer_exclusion(client):
    account = register(client, "finance_user")
    headers = auth(account["access_token"])
    accounts = client.get("/api/v1/accounts", headers=headers).json()
    categories = client.get("/api/v1/categories", headers=headers).json()
    bank = next(a for a in accounts if a["kind"] == "bank")
    cash = next(a for a in accounts if a["kind"] == "cash")
    income_cat = next(c for c in categories if c["kind"] == "income")
    expense_cat = next(c for c in categories if c["kind"] == "expense")
    dt = "2026-11-07T09:00:00+08:00"
    add_income = client.post("/api/v1/transactions", headers=headers, json={
        "kind":"income","amount":"1000000","source_account_id":bank["id"],"category_id":income_cat["id"],
        "description":"Gaji tes","occurred_at":dt,"currency":"IDR"})
    assert add_income.status_code == 201, add_income.text
    add_expense = client.post("/api/v1/transactions", headers=headers, json={
        "kind":"expense","amount":"150000","source_account_id":bank["id"],"category_id":expense_cat["id"],
        "description":"Makan tes","occurred_at":dt,"currency":"IDR"})
    assert add_expense.status_code == 201, add_expense.text
    transfer = client.post("/api/v1/transactions", headers=headers, json={
        "kind":"transfer","amount":"200000","source_account_id":bank["id"],"target_account_id":cash["id"],
        "description":"Pindah tunai","occurred_at":dt,"currency":"IDR"})
    assert transfer.status_code == 201, transfer.text
    summary = client.get("/api/v1/reports/summary?start=2026-11-01&end=2026-11-30", headers=headers).json()
    assert summary["income"] == "1000000.00"
    assert summary["expense"] == "150000.00"
    assert summary["net_cashflow"] == "850000.00"
    listed = client.get("/api/v1/transactions", headers=headers).json()
    assert len(listed) == 3

    # Editing a transaction must update its amount and the same report dataset.
    edited_payload = {
        "kind":"expense", "amount":"175000", "source_account_id":bank["id"],
        "category_id":expense_cat["id"], "description":"Makan malam dikoreksi",
        "occurred_at":dt, "currency":"IDR", "notes":"koreksi QA"
    }
    edited = client.patch(f"/api/v1/transactions/{add_expense.json()['id']}", headers=headers, json=edited_payload)
    assert edited.status_code == 200, edited.text
    assert edited.json()["amount"] == "175000.00"
    refreshed = client.get("/api/v1/reports/summary?start=2026-11-01&end=2026-11-30", headers=headers).json()
    assert refreshed["expense"] == "175000.00"

    deleted = client.delete(f"/api/v1/transactions/{add_expense.json()['id']}", headers=headers)
    assert deleted.status_code == 200
    after_delete = client.get("/api/v1/reports/summary?start=2026-11-01&end=2026-11-30", headers=headers).json()
    assert float(after_delete["expense"]) == 0

def test_private_transaction_isolation(client):
    one = register(client, "owner_a")
    two = register(client, "owner_b")
    h1, h2 = auth(one["access_token"]), auth(two["access_token"])
    a1 = client.get("/api/v1/accounts", headers=h1).json()[0]
    c1 = next(c for c in client.get("/api/v1/categories", headers=h1).json() if c["kind"] == "expense")
    tx = client.post("/api/v1/transactions", headers=h1, json={
        "kind":"expense","amount":"10000","source_account_id":a1["id"],"category_id":c1["id"],
        "description":"Private transaction","occurred_at":"2026-11-07T10:00:00+08:00"})
    assert tx.status_code == 201
    foreign = client.get(f"/api/v1/transactions/{tx.json()['id']}", headers=h2)
    assert foreign.status_code == 404

def test_group_preview_request_approval_and_membership(client):
    owner = register(client, "group_owner")
    guest = register(client, "group_guest")
    ho, hg = auth(owner["access_token"]), auth(guest["access_token"])
    created = client.post("/api/v1/groups", headers=ho, json={"name":"Financial Circle","description":"Belajar bersama"})
    assert created.status_code == 201
    code = created.json()["invite_code"]
    preview = client.get(f"/api/v1/groups/preview/{code}", headers=hg)
    assert preview.status_code == 200
    req = client.post("/api/v1/groups/join-requests", headers=hg, json={"invite_code":code})
    assert req.status_code == 201
    group_id = created.json()["id"]
    requests = client.get(f"/api/v1/groups/{group_id}/requests", headers=ho).json()
    assert len(requests) == 1
    approved = client.post(f"/api/v1/groups/{group_id}/requests/{requests[0]['id']}/approve", headers=ho)
    assert approved.status_code == 200
    ticket_response = client.post(f"/api/v1/groups/{group_id}/ws-ticket", headers=hg)
    assert ticket_response.status_code == 200, ticket_response.text
    ticket = ticket_response.json()["ticket"]
    assert ticket_response.json()["expires_in"] == 60
    with client.websocket_connect(f"/api/v1/groups/{group_id}/ws?ticket={ticket}") as websocket:
        assert websocket.receive_json()["event"] == "connected"
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/groups/{group_id}/ws?ticket={ticket}") as websocket:
            websocket.receive_json()
    sent = client.post(f"/api/v1/groups/{group_id}/messages", headers=hg, json={"body":"Halo semua"})
    assert sent.status_code == 201
    msgs = client.get(f"/api/v1/groups/{group_id}/messages", headers=hg).json()
    assert len(msgs) == 1 and msgs[0]["body"] == "Halo semua"



def test_local_date_filters_use_configured_timezone(client):
    created = register(client, "local_date_user")
    headers = auth(created["access_token"])
    account = client.get("/api/v1/accounts", headers=headers).json()[0]
    category = next(c for c in client.get("/api/v1/categories", headers=headers).json() if c["kind"] == "expense")
    # 06:30 on 7 November in Asia/Makassar is still 6 November in UTC.
    tx = client.post("/api/v1/transactions", headers=headers, json={
        "kind":"expense", "amount":"25000", "source_account_id":account["id"],
        "category_id":category["id"], "description":"Sarapan pagi", "currency":"IDR",
        "occurred_at":"2026-11-06T22:30:00Z"
    })
    assert tx.status_code == 201, tx.text
    same_day = client.get("/api/v1/reports/summary?start=2026-11-07&end=2026-11-07", headers=headers).json()
    assert same_day["expense"] == "25000.00"
    listed = client.get("/api/v1/transactions?start=2026-11-07&end=2026-11-07", headers=headers).json()
    assert len(listed) == 1


def test_app_shell_and_health_routes(client):
    home = client.get("/")
    assert home.status_code == 200 and "NEXORA" in home.text
    logo = client.get("/assets/nexora-mark.svg")
    assert logo.status_code == 200 and "svg" in logo.text
    health = client.get("/health")
    assert health.status_code == 200 and health.json()["status"] == "ok"


def test_goals_are_user_scoped_and_fully_editable(client):
    from app.main import Goal
    owner = register(client, "goal_owner")
    other = register(client, "goal_other")
    ho, hx = auth(owner["access_token"]), auth(other["access_token"])
    created = client.post("/api/v1/goals", headers=ho, json={
        "name": "Dana darurat", "target_amount": "10000000", "current_amount": "2500000",
        "target_date": "2027-06-01", "note": "Setor rutin"
    })
    assert created.status_code == 201, created.text
    row = created.json()
    assert row["progress_percent"] == 25.0
    assert row["remaining"] == "7500000.00"
    assert client.get("/api/v1/goals", headers=hx).json() == []
    edited = client.patch(f"/api/v1/goals/{row['id']}", headers=ho, json={
        "name": "Dana darurat 6 bulan", "target_amount": "12000000", "current_amount": "3000000",
        "target_date": "2027-12-31", "note": "Diperbarui"
    })
    assert edited.status_code == 200 and edited.json()["progress_percent"] == 25.0
    assert client.delete(f"/api/v1/goals/{row['id']}", headers=ho).status_code == 200
    assert client.get("/api/v1/goals", headers=ho).json() == []


def test_recurring_rule_executes_idempotently_and_advances(client):
    from datetime import date as date_type
    from app.main import SessionLocal, process_due_recurring
    account_user = register(client, "recurring_user")
    headers = auth(account_user["access_token"])
    accounts = client.get("/api/v1/accounts", headers=headers).json()
    categories = client.get("/api/v1/categories", headers=headers).json()
    source = next(a for a in accounts if a["kind"] == "bank")
    expense_category = next(c for c in categories if c["kind"] == "expense")
    created = client.post("/api/v1/recurring", headers=headers, json={
        "kind": "expense", "amount": "125000", "currency": "IDR",
        "source_account_id": source["id"], "category_id": expense_category["id"],
        "description": "Internet bulanan", "notes": "otomatis", "frequency": "monthly",
        "next_run_on": "2026-11-06", "ends_on": "2027-11-06"
    })
    assert created.status_code == 201, created.text
    rule = created.json()
    with SessionLocal() as db:
        count = process_due_recurring(db, date_type(2026, 11, 7))
        assert count == 1
        count_again = process_due_recurring(db, date_type(2026, 11, 7))
        assert count_again == 0
    listed = client.get("/api/v1/transactions?start=2026-11-06&end=2026-11-07", headers=headers).json()
    assert len(listed) == 1 and listed[0]["description"] == "Internet bulanan"
    rules = client.get("/api/v1/recurring", headers=headers).json()
    assert rules[0]["id"] == rule["id"] and rules[0]["next_run_on"] == "2026-12-06"
    paused = client.patch(f"/api/v1/recurring/{rule['id']}", headers=headers, json={"active": False})
    assert paused.status_code == 200 and paused.json()["active"] is False


def test_ocr_parser_returns_suggestions_without_creating_transactions(client):
    from app.main import extract_ocr_fields
    parsed = extract_ocr_fields("""07/11/2026
DEBIT
WARUNG MAKAN
TOTAL Rp 35.000
SALDO Rp 1.200.000""")
    assert parsed["date"] == "2026-11-07"
    assert parsed["amount"] == "35000"
    assert parsed["kind"] == "expense"
    user = register(client, "ocr_user")
    headers = auth(user["access_token"])
    # The parser only creates candidate fields; it does not write a transaction.
    assert client.get("/api/v1/transactions", headers=headers).json() == []


def test_group_message_edit_reaction_report_block_and_moderation(client):
    owner = register(client, "moderator_owner")
    member = register(client, "moderator_member")
    ho, hm = auth(owner["access_token"]), auth(member["access_token"])
    group = client.post("/api/v1/groups", headers=ho, json={"name": "Moderation Circle"}).json()
    group_id = group["id"]
    request = client.post("/api/v1/groups/join-requests", headers=hm, json={"invite_code": group["invite_code"]})
    assert request.status_code == 201
    pending = client.get(f"/api/v1/groups/{group_id}/requests", headers=ho).json()[0]
    assert client.post(f"/api/v1/groups/{group_id}/requests/{pending['id']}/approve", headers=ho).status_code == 200

    message = client.post(f"/api/v1/groups/{group_id}/messages", headers=hm, json={"body": "Periksa sumber laporan ini"})
    assert message.status_code == 201
    message_id = message.json()["id"]
    edited = client.patch(f"/api/v1/groups/{group_id}/messages/{message_id}", headers=hm, json={"body": "Pesan sudah diperiksa"})
    assert edited.status_code == 200 and edited.json()["edited"] is True
    reaction = client.post(f"/api/v1/groups/{group_id}/messages/{message_id}/reactions", headers=ho, json={"emoji": "👍"})
    assert reaction.status_code == 201 and reaction.json()["reactions"][0]["count"] == 1
    report = client.post(f"/api/v1/groups/{group_id}/messages/{message_id}/report", headers=ho, json={"reason": "misinformation", "details": "Perlu sumber"})
    assert report.status_code == 201
    reports = client.get(f"/api/v1/groups/{group_id}/reports", headers=ho)
    assert reports.status_code == 200 and len(reports.json()) == 1
    resolved = client.patch(f"/api/v1/groups/{group_id}/reports/{report.json()['id']}", headers=ho, json={"status": "resolved", "moderator_note": "Sudah diperiksa"})
    assert resolved.status_code == 200 and resolved.json()["status"] == "resolved"

    blocked = client.post(f"/api/v1/users/{member['user']['id']}/block", headers=ho)
    assert blocked.status_code == 201
    visible = client.get(f"/api/v1/groups/{group_id}/messages", headers=ho).json()
    assert all(row["user_id"] != member["user"]["id"] for row in visible)
    assert client.delete(f"/api/v1/groups/{group_id}/messages/{message_id}", headers=hm).status_code == 200


def test_account_archive_pauses_recurrence_and_blocks_new_transactions(client):
    created = register(client, "archive_test")
    headers = auth(created["access_token"])
    accounts = client.get("/api/v1/accounts", headers=headers).json()
    bank = next(a for a in accounts if a["kind"] == "bank")
    categories = client.get("/api/v1/categories", headers=headers).json()
    category = next(c for c in categories if c["kind"] == "expense")
    recurring = client.post("/api/v1/recurring", headers=headers, json={
        "kind": "expense", "amount": "10000", "source_account_id": bank["id"],
        "category_id": category["id"], "description": "Tagihan arsip", "frequency": "monthly",
        "next_run_on": "2026-11-10"
    })
    assert recurring.status_code == 201, recurring.text
    archived = client.patch(f"/api/v1/accounts/{bank['id']}", headers=headers, json={"archived": True})
    assert archived.status_code == 200 and archived.json()["archived"] is True
    rules = client.get("/api/v1/recurring", headers=headers).json()
    assert rules[0]["active"] is False
    tx = client.post("/api/v1/transactions", headers=headers, json={
        "kind": "expense", "amount": "5000", "source_account_id": bank["id"],
        "category_id": category["id"], "description": "Tidak boleh", "occurred_at": "2026-11-07T10:00:00+08:00"
    })
    assert tx.status_code == 422
    restored = client.patch(f"/api/v1/accounts/{bank['id']}", headers=headers, json={"archived": False})
    assert restored.status_code == 200 and restored.json()["archived"] is False


def test_category_and_budget_crud(client):
    created = register(client, "category_budget")
    headers = auth(created["access_token"])
    category = client.post("/api/v1/categories", headers=headers, json={
        "name": "Kebutuhan kucing", "kind": "expense", "color": "#42D6C5", "icon": "🐾"
    })
    assert category.status_code == 201, category.text
    cid = category.json()["id"]
    edited = client.patch(f"/api/v1/categories/{cid}", headers=headers, json={
        "name": "Perawatan hewan", "kind": "expense", "color": "#F2B35E", "icon": "🐾"
    })
    assert edited.status_code == 200 and edited.json()["name"] == "Perawatan hewan"
    budget = client.post("/api/v1/budgets", headers=headers, json={
        "category_id": cid, "amount": "500000", "starts_on": "2026-11-01",
        "ends_on": "2026-11-30", "threshold_percent": 75
    })
    assert budget.status_code == 201, budget.text
    bid = budget.json()["id"]
    listing = client.get("/api/v1/budgets", headers=headers).json()
    assert len(listing) == 1 and listing[0]["threshold_percent"] == 75
    updated_budget = client.patch(f"/api/v1/budgets/{bid}", headers=headers, json={
        "category_id": cid, "amount": "600000", "starts_on": "2026-11-01",
        "ends_on": "2026-11-30", "threshold_percent": 85
    })
    assert updated_budget.status_code == 200
    # Changing semantic type after a budget references it must not silently
    # turn historical expense data into an income category.
    invalid_kind_change = client.patch(f"/api/v1/categories/{cid}", headers=headers, json={
        "name": "Kategori salah jenis", "kind": "income", "color": "#42D6C5", "icon": "◈"
    })
    assert invalid_kind_change.status_code == 409
    # A category that is referenced by a budget cannot be deleted.
    assert client.delete(f"/api/v1/categories/{cid}", headers=headers).status_code == 409
    assert client.delete(f"/api/v1/budgets/{bid}", headers=headers).status_code == 200
    assert client.delete(f"/api/v1/categories/{cid}", headers=headers).status_code == 200


def test_json_export_and_account_deletion(client):
    owner = register(client, "delete_owner")
    guest = register(client, "delete_guest")
    ho, hg = auth(owner["access_token"]), auth(guest["access_token"])
    account = client.get("/api/v1/accounts", headers=ho).json()[0]
    category = next(c for c in client.get("/api/v1/categories", headers=ho).json() if c["kind"] == "expense")
    tx = client.post("/api/v1/transactions", headers=ho, json={
        "kind": "expense", "amount": "19000", "source_account_id": account["id"],
        "category_id": category["id"], "description": "Kopi", "occurred_at": "2026-11-07T10:00:00+08:00"
    })
    assert tx.status_code == 201
    group = client.post("/api/v1/groups", headers=ho, json={"name": "Delete group"}).json()
    request = client.post("/api/v1/groups/join-requests", headers=hg, json={"invite_code": group["invite_code"]})
    assert request.status_code == 201
    pending = client.get(f"/api/v1/groups/{group['id']}/requests", headers=ho).json()[0]
    assert client.post(f"/api/v1/groups/{group['id']}/requests/{pending['id']}/approve", headers=ho).status_code == 200
    client.post(f"/api/v1/groups/{group['id']}/messages", headers=ho, json={"body": "Pesan akan dihapus bersama grup"})

    exported = client.get("/api/v1/export/data.json", headers=ho)
    assert exported.status_code == 200
    data = exported.json()
    assert data["user"]["username"] == "delete_owner"
    assert len(data["transactions"]) == 1
    assert len(data["groups"]) == 1

    deleted = client.post("/api/v1/auth/delete-account", headers=ho, json={
        "current_password": "CorrectHorse2026!", "confirmation": "HAPUS AKUN"
    })
    assert deleted.status_code == 200, deleted.text
    assert client.get("/api/v1/me", headers=ho).status_code == 401
    assert client.get("/api/v1/groups", headers=hg).json() == []


def test_receipt_ocr_remains_draft_until_explicit_confirmation(client):
    import base64
    import io
    import shutil
    from PIL import Image, ImageDraw, ImageFont

    if not shutil.which("tesseract"):
        pytest.skip("Tesseract binary is not installed in this test environment")

    created = register(client, "receipt_ocr_user")
    headers = auth(created["access_token"])

    # Create a deterministic synthetic statement image so OCR is exercised in CI
    # without uploading any real person's bank or financial information.
    image = Image.new("RGB", (1500, 800), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
    y = 70
    for line in ["BUKTI TRANSAKSI", "07/11/2026", "DEBIT", "WARUNG MAKAN", "TOTAL Rp 35.000", "SALDO Rp 1.200.000"]:
        draw.text((60, y), line, font=font, fill="black")
        y += 115
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    uploaded = client.post("/api/v1/receipts", headers=headers, json={
        "filename": "synthetic-statement.png", "mime_type": "image/png", "content_base64": encoded
    })
    assert uploaded.status_code == 201, uploaded.text
    receipt_id = uploaded.json()["id"]

    duplicate = client.post("/api/v1/receipts", headers=headers, json={
        "filename": "duplicate.png", "mime_type": "image/png", "content_base64": encoded
    })
    assert duplicate.status_code == 409

    extracted = client.post(f"/api/v1/receipts/{receipt_id}/extract", headers=headers)
    assert extracted.status_code == 200, extracted.text
    body = extracted.json()
    assert body["status"] == "ocr_review"
    assert body["fields"]["amount"] == "35000"
    assert body["fields"]["kind"] == "expense"
    assert body["fields"]["date"] == "2026-11-07"
    # OCR extraction cannot create a financial transaction by itself.
    assert client.get("/api/v1/transactions", headers=headers).json() == []

    account = client.get("/api/v1/accounts", headers=headers).json()[0]
    category = next(c for c in client.get("/api/v1/categories", headers=headers).json() if c["kind"] == "expense")
    confirmed = client.post(f"/api/v1/receipts/{receipt_id}/confirm", headers=headers, json={
        "kind": "expense", "amount": "35000", "occurred_at": "2026-11-07T12:00:00+08:00",
        "account_id": account["id"], "category_id": category["id"], "description": "Warung makan"
    })
    assert confirmed.status_code == 200, confirmed.text
    assert len(client.get("/api/v1/transactions", headers=headers).json()) == 1
    assert client.get(f"/api/v1/receipts/{receipt_id}", headers=headers).json()["status"] == "confirmed"
