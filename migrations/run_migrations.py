"""Simple migration runner for development."""
import asyncio
import os
from pathlib import Path

import asyncpg


async def run_migrations():
    dsn = os.environ.get(
        "POSTGRES_DSN",
        "postgresql://fraud_user:fraud_pass@localhost:5432/fraud_detection",
    )
    conn = await asyncpg.connect(dsn)
    try:
        migrations_dir = Path(__file__).parent
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            print(f"Running {sql_file.name}...")
            sql = sql_file.read_text()
            await conn.execute(sql)
            print("  Done.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migrations())
