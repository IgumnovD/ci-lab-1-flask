import os
from pathlib import Path

import psycopg2
import redis
from flask import Blueprint, jsonify


def create_visits_blueprint():
    bp = Blueprint("visits", __name__)

    @bp.get("/visits")
    def visits():
        # Connections are created per request and closed even when a request fails.
        with redis.Redis.from_url(os.environ["REDIS_URL"], socket_timeout=5) as cache:
            cached = cache.get("visits_count")
            if cached is not None:
                return jsonify(count=int(cached), source="cache")

            conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5)
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO visits DEFAULT VALUES RETURNING id")
                        new_id = cur.fetchone()[0]
                        cur.execute("SELECT COUNT(*) FROM visits")
                        count = cur.fetchone()[0]
            finally:
                conn.close()
            cache.setex("visits_count", 10, count)
            return jsonify(count=count, source="db", lastId=new_id)

    return bp


def init_db(database_url):
    conn = psycopg2.connect(database_url, connect_timeout=5)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(Path(__file__).with_name("schema.sql").read_text())
    finally:
        conn.close()
