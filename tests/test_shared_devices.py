"""Shared devices in the log: accounts that signed in from the same browser (a cookie holds a random device id)."""

from conftest import PASSWORD, error, login


def sign_in(client, username):
    response = client.post("/api/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.get_json()
    client.post("/api/logout")


def students(admin, count=3):
    """Usernames of some active sample students."""
    found = admin.get("/api/users?role=student&per_page=100").get_json()["users"]
    return [user["username"] for user in found if user["active"]][:count]


def devices(client):
    return client.get("/api/log/devices").get_json()["devices"]


def test_the_cookie_is_random_http_only_and_kept(app):
    client = app.test_client()
    first = client.post("/api/login", json={"username": "jdelacruz01", "password": PASSWORD})
    cookie = first.headers.get("Set-Cookie", "")
    assert "myguro-device=" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie
    device_id = client.get_cookie("myguro-device").value
    assert len(device_id) == 32
    client.post("/api/logout")
    client.post("/api/login", json={"username": "ecruz", "password": PASSWORD})
    assert client.get_cookie("myguro-device").value == device_id  # the same browser keeps its id
    # a made-up cookie is replaced, not trusted
    other = app.test_client()
    other.set_cookie("myguro-device", "not-a-real-id")
    other.post("/api/login", json={"username": "jdelacruz01", "password": PASSWORD})
    assert len(other.get_cookie("myguro-device").value) == 32 and other.get_cookie("myguro-device").value != "not-a-real-id"


def test_two_accounts_on_one_browser_are_listed(app, admin, supervisor):
    one, two, three = students(admin)
    phone = app.test_client()
    sign_in(phone, one)
    assert devices(admin) == []  # one account only: nothing shared
    sign_in(phone, two)
    sign_in(phone, two)
    listed = devices(admin)
    assert len(listed) == 1 and len(listed[0]["device"]) == 8
    accounts = {account["username"]: account for account in listed[0]["accounts"]}
    assert set(accounts) == {one, two} and accounts[two]["logins"] == 2
    assert devices(supervisor) == listed  # a supervisor reads it too
    # separate browsers are not the same device
    sign_in(app.test_client(), three)
    assert len(devices(admin)) == 1


def test_the_admin_account_does_not_count_and_only_staff_can_read(app, admin, teacher):
    one = students(admin, 1)[0]
    browser = app.test_client()
    sign_in(browser, one)
    assert browser.post("/api/login", json={"username": "admin", "password": "adminpass1"}).status_code == 200
    assert devices(admin) == []  # the admin signing in as helper on a student's browser is not sharing
    student = login(one)
    assert student.get("/api/log/devices").status_code == 403
    assert teacher.get("/api/log/devices").status_code == 403


def test_a_wrong_password_records_nothing(app, admin):
    one, two, _ = students(admin)
    browser = app.test_client()
    sign_in(browser, one)
    assert browser.post("/api/login", json={"username": two, "password": "wrong-one"}).status_code == 401
    assert devices(admin) == []
