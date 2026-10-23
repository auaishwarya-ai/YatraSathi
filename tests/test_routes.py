"""End-to-end tests of pages and the JSON API."""
from conftest import login

PUBLIC = ["/", "/explore", "/explore?q=waterfall", "/explore?category=Beaches", "/explore?rating=4.5&sort=rating",
          "/place/hampi", "/place/coorg", "/assistant", "/planner", "/planner?preset=coorg-getaway", "/guide",
          "/guide/festivals", "/guide/faqs", "/guide/emergency", "/nearby", "/help", "/login", "/register", "/api/health"]


def test_public_pages(client):
    for url in PUBLIC:
        assert client.get(url).status_code == 200, url


def test_at_least_50_places(app, client):
    data = client.get("/api/destinations").get_json()
    assert data["count"] >= 50


def test_language_switch(client):
    client.get("/lang/kn")
    assert "ಅನ್ವೇಷಿಸಿ".encode() in client.get("/").data
    client.get("/lang/hi")
    assert "एआई प्लानर".encode() in client.get("/").data
    client.get("/lang/en")


def test_account_requires_login(client):
    assert client.get("/account/").status_code == 302
    assert client.get("/admin/").status_code == 302


def test_user_flow(client):
    assert login(client).status_code == 302
    for url in ["/account/", "/account/trips", "/account/saved", "/account/chats", "/account/profile"]:
        assert client.get(url).status_code == 200, url
    assert client.get("/admin/").status_code == 403
    fav = client.post("/api/favorites/badami").get_json()
    assert "saved" in fav
    r = client.post("/api/chat", json={"message": "Plan a 2 day trip to Hampi", "lang": "en"}).get_json()
    assert r["intent"] == "plan_trip" and r["trip_id"]
    saved = client.post(f"/api/trips/{r['trip_id']}/save", json={"start_date": "2030-01-10"}).get_json()
    assert saved["status"] == "upcoming"
    pdf = client.get(f"/account/trips/{r['trip_id']}/pdf")
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF"
    hist = client.get(f"/api/chat/{r['session_id']}").get_json()
    assert len(hist["messages"]) == 2
    client.get("/logout")


def test_itinerary_api(client):
    r = client.post("/api/itinerary", json={"start": "Bangalore", "destination": "auto", "days": 2, "travelers": 2,
                                             "budget": 6000, "interests": ["Nature"]})
    data = r.get_json()
    assert r.status_code == 200 and data["plan"]["costs"]["total"] <= 6000


def test_admin_pages(client):
    login(client, "admin@yatrasathi.in", "admin123")
    for url in ["/admin/", "/admin/destinations", "/admin/destinations/new", "/admin/users", "/admin/itineraries",
                "/admin/feedback", "/admin/knowledge", "/admin/knowledge?test=dasara", "/admin/chats", "/admin/reports",
                "/admin/reports/users.csv"]:
        assert client.get(url).status_code == 200, url
    # add a knowledge document -> the assistant can answer from it (RAG)
    client.post("/admin/knowledge", data={"title": "Hampi night market", "category": "Events",
                                          "content": "The Hampi bazaar night market opens every Saturday evening near Virupaksha temple."})
    r = client.post("/api/chat", json={"message": "When does the Hampi night market open?"}).get_json()
    assert any(s["title"] == "Hampi night market" for s in r["sources"])
    client.get("/logout")


def test_guest_chat_and_tts_validation(client):
    r = client.post("/api/chat", json={"message": "hello"}).get_json()
    assert r["intent"] == "greeting"
    assert client.post("/api/tts", json={"text": ""}).status_code == 400
