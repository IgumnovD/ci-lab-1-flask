import logging

import psycopg2
import pytest
import redis
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app import create_app
from app.visits import init_db


@pytest.fixture()
def services(monkeypatch):
    # Function scope gives each test independent data and random host ports.
    with PostgresContainer("postgres:16") as pg, RedisContainer("redis:7") as redis_c:
        database_url = pg.get_connection_url().replace("postgresql+psycopg2", "postgresql")
        redis_url = (
            f"redis://{redis_c.get_container_host_ip()}:"
            f"{redis_c.get_exposed_port(6379)}/0"
        )
        monkeypatch.setenv("DATABASE_URL", database_url)
        monkeypatch.setenv("REDIS_URL", redis_url)
        init_db(database_url)
        app = create_app()
        app.config["TESTING"] = True
        try:
            with app.test_client() as client:
                with redis.Redis.from_url(redis_url) as cache:
                    conn = psycopg2.connect(database_url)
                    try:
                        yield client, conn, cache
                    finally:
                        conn.close()
        finally:
            logging.warning("Closing clients before Testcontainers cleanup")
    logging.warning("PostgreSQL and Redis containers stopped")
