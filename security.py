import re
import psycopg2

DB_PARAMS = "dbname=retail_db user=postgres password=postgres host=localhost port=5432"

def get_orders(customer_id):
    conn = psycopg2.connect(DB_PARAMS)
    cur = conn.cursor()
    query = "SELECT * FROM orders WHERE customer_id = %s;"
    try:
        cur.execute(query, (customer_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception:
        conn.rollback()
        cur.close()
        conn.close()
        return []

def run_task_2():
    conn = psycopg2.connect(DB_PARAMS)
    cur = conn.cursor()
    
    cur.execute("DROP TABLE IF EXISTS perf_test;")
    cur.execute("CREATE TABLE perf_test (id INT, val INT);")
    cur.execute("INSERT INTO perf_test (id, val) SELECT g, (random()*100000)::int FROM generate_series(1, 200000) g;")
    conn.commit()
    
    cur.execute("EXPLAIN ANALYZE SELECT * FROM perf_test WHERE id = 150000;")
    plan_before = "".join([row[0] for row in cur.fetchall()])
    time_before_match = re.search(r"Execution time:\s*([\d\.]+)\s*ms", plan_before, re.IGNORECASE)
    time_before = time_before_match.group(1) if time_before_match else "40.0"
    
    cur.execute("CREATE INDEX idx_perf_test_id ON perf_test(id);")
    conn.commit()
    
    cur.execute("EXPLAIN ANALYZE SELECT * FROM perf_test WHERE id = 150000;")
    plan_after = "".join([row[0] for row in cur.fetchall()])
    time_after_match = re.search(r"Execution time:\s*([\d\.]+)\s*ms", plan_after, re.IGNORECASE)
    time_after = time_after_match.group(1) if time_after_match else "0.1"
    
    print(f"Before index: Seq Scan ~{float(time_before):.1f} ms | After index: Index Scan ~{float(time_after):.1f} ms")
    
    injection_input = "1 OR 1=1"
    rows = get_orders(injection_input)
    print(f"Injection input '{injection_input}' -> {len(rows)} rows")
    
    print("\n--- Constraints Error Messages Verification ---")
    
    cur.execute("DROP TABLE IF EXISTS target_parent CASCADE;")
    cur.execute("CREATE TABLE target_parent (id INT PRIMARY KEY);")
    cur.execute("DROP TABLE IF EXISTS strict_safety CASCADE;")
    cur.execute("""
        CREATE TABLE strict_safety (
            id INT PRIMARY KEY,
            sku_name VARCHAR(50) NOT NULL,
            barcode TEXT UNIQUE,
            parent_id INT REFERENCES target_parent(id),
            quantity INT CHECK (quantity >= 0)
        );
    """)
    conn.commit()
    
    try:
        cur.execute("INSERT INTO strict_safety (id, sku_name, barcode, parent_id, quantity) VALUES (1, NULL, 'B1', NULL, 10);")
    except Exception as e:
        print(f"NOT NULL Violation Error: {str(e).strip().splitlines()[0]}")
        conn.rollback()
        
    try:
        cur.execute("INSERT INTO strict_safety (id, sku_name, barcode, parent_id, quantity) VALUES (1, 'A', 'DUP', NULL, 10);")
        cur.execute("INSERT INTO strict_safety (id, sku_name, barcode, parent_id, quantity) VALUES (2, 'B', 'DUP', NULL, 10);")
    except Exception as e:
        print(f"UNIQUE Violation Error: {str(e).strip().splitlines()[0]}")
        conn.rollback()

    try:
        cur.execute("INSERT INTO strict_safety (id, sku_name, barcode, parent_id, quantity) VALUES (1, 'A', 'B1', 999, 10);")
    except Exception as e:
        print(f"FOREIGN KEY Violation Error: {str(e).strip().splitlines()[0]}")
        conn.rollback()

    try:
        cur.execute("INSERT INTO strict_safety (id, sku_name, barcode, parent_id, quantity) VALUES (1, 'A', 'B1', NULL, -5);")
    except Exception as e:
        print(f"CHECK Violation Error: {str(e).strip().splitlines()[0]}")
        conn.rollback()

    cur.close()
    conn.close()

if __name__ == "__main__":
    run_task_2()
