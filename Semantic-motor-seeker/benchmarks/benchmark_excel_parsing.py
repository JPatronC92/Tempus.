import sys
import os
import time
import io
import tracemalloc
import openpyxl

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.parsers import parse_excel

def generate_large_excel(rows=50000, cols=20):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    # Header
    ws.append([f"Header{c}" for c in range(cols)])

    # Data
    for r in range(rows):
        ws.append([f"Row{r}Col{c}" for c in range(cols)])

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out

def run_benchmark():
    print("Generating Excel file (~50000 rows, 20 cols)...")
    file_obj = generate_large_excel(rows=50000, cols=20)
    file_bytes = file_obj.read()

    print("Starting benchmark...")

    tracemalloc.start()
    start_time = time.time()

    # Use BytesIO(file_bytes) for parse_excel to consume
    parse_excel(io.BytesIO(file_bytes))

    end_time = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Execution Time: {end_time - start_time:.4f} seconds")
    print(f"Peak Memory Usage: {peak / 1024 / 1024:.2f} MB")
    print(f"Current Memory Usage: {current / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    run_benchmark()
