def row_count(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM visits")
        return cur.fetchone()[0]


def test_first_request_uses_database(services):
    client, conn, cache = services
    response = client.get("/visits")
    assert response.status_code == 200
    assert response.get_json() == {"count": 999, "source": "db", "lastId": 1}
    assert row_count(conn) == 1
    assert cache.get("visits_count") == b"1"
    assert 0 < cache.ttl("visits_count") <= 10


def test_second_request_uses_cache(services):
    client, conn, cache = services
    client.get("/visits")
    response = client.get("/visits")
    assert response.status_code == 200
    assert response.get_json() == {"count": 1, "source": "cache"}
    assert row_count(conn) == 1


def test_expired_cache_returns_to_database(services):
    client, conn, cache = services
    client.get("/visits")
    # Deterministic expiration instead of a flaky sleep near the TTL boundary.
    cache.expire("visits_count", 0)
    response = client.get("/visits")
    assert response.get_json() == {"count": 2, "source": "db", "lastId": 2}
    assert row_count(conn) == 2
