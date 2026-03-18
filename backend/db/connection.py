"""This file contains database helpers for connection records.
It wraps SQL reads and writes used by the API and service layers."""


import random
import string

import psycopg

from ..core.config import PG_DB, PG_HOST, PG_PASS, PG_PORT, PG_USER

FILE_TYPES = ("pdf", "audio", "slides")
DEFAULT_COURSE_NAME = "General Course"
DEFAULT_COURSE_DESCRIPTION = "Default course for uncategorized lectures"


def generate_join_code(length: int = 6) -> str:
    """Generate a random uppercase alphanumeric join code."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def get_conn():
    return psycopg.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
    )
