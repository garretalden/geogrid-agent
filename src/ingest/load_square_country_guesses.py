from pathlib import Path
import sqlite3

print("SCRIPT STARTED")

DB_PATH = Path("data/processed/geogrid.db")


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS square_country_guesses (
    grid_id INTEGER NOT NULL,
    square_id INTEGER NOT NULL,
    country TEXT NOT NULL,
    guess_count INTEGER NOT NULL,
    total_valid_guess_count INTEGER NOT NULL,
    guess_share REAL NOT NULL,
    PRIMARY KEY (grid_id, square_id, country)
);
"""


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    result = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?;
        """,
        (table_name,),
    ).fetchone()

    return result is not None


def load_square_country_guesses(conn: sqlite3.Connection) -> None:
    """
    Builds square_country_guesses from raw_guess_records.

    Assumes raw_guess_records has:
        grid_id
        square_id
        raw_answer_text
        guess_count
        is_valid_answer

    Only valid answers are inserted.
    """

    if not table_exists(conn, "raw_guess_records"):
        raise RuntimeError(
            "raw_guess_records table does not exist yet. "
            "Run load_guesses.py first."
        )

    conn.execute(CREATE_TABLE_SQL)

    # Rebuild this table from scratch each time.
    conn.execute("DELETE FROM square_country_guesses;")

    rows = conn.execute(
        """
        WITH valid_guesses AS (
            SELECT
                grid_id,
                square_id,
                raw_answer_text AS country,
                guess_count
            FROM raw_guess_records
            WHERE is_valid_answer = 1
              AND guess_count IS NOT NULL
              AND guess_count >= 0
        ),

        totals AS (
            SELECT
                grid_id,
                square_id,
                SUM(guess_count) AS total_valid_guess_count
            FROM valid_guesses
            GROUP BY grid_id, square_id
        )

        SELECT
            v.grid_id,
            v.square_id,
            v.country,
            v.guess_count,
            t.total_valid_guess_count,
            CASE
                WHEN t.total_valid_guess_count > 0
                THEN CAST(v.guess_count AS REAL) / t.total_valid_guess_count
                ELSE 0.0
            END AS guess_share
        FROM valid_guesses v
        JOIN totals t
          ON v.grid_id = t.grid_id
         AND v.square_id = t.square_id;
        """
    ).fetchall()

    conn.executemany(
        """
        INSERT OR REPLACE INTO square_country_guesses (
            grid_id,
            square_id,
            country,
            guess_count,
            total_valid_guess_count,
            guess_share
        )
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        rows,
    )

    conn.commit()

    print(f"Loaded {len(rows):,} rows into square_country_guesses.")


def print_sanity_checks(conn: sqlite3.Connection) -> None:
    total_rows = conn.execute(
        "SELECT COUNT(*) FROM square_country_guesses;"
    ).fetchone()[0]

    num_grids = conn.execute(
        "SELECT COUNT(DISTINCT grid_id) FROM square_country_guesses;"
    ).fetchone()[0]

    num_squares = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT grid_id, square_id
            FROM square_country_guesses
        );
        """
    ).fetchone()[0]

    print()
    print("Sanity checks")
    print("-------------")
    print(f"Rows: {total_rows:,}")
    print(f"Grids represented: {num_grids:,}")
    print(f"Grid-squares represented: {num_squares:,}")

    print()
    print("Sample rows:")
    sample_rows = conn.execute(
        """
        SELECT *
        FROM square_country_guesses
        ORDER BY grid_id, square_id, guess_count DESC
        LIMIT 10;
        """
    ).fetchall()

    for row in sample_rows:
        print(row)


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    try:
        load_square_country_guesses(conn)
        print_sanity_checks(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()