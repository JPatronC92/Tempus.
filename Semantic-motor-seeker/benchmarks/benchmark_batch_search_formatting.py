
import time
import copy

class MockPoint:
    def __init__(self, id, score, payload):
        self.id = id
        self.score = score
        self.payload = payload

EXCLUDED_METADATA_KEYS = {"text_snippet", "full_text", "original_id"}

def current_implementation(batch_results):
    formatted_results = []
    for result_group in batch_results:
        group = []
        for point in result_group:
            payload = point.payload
            doc_id = payload.get("original_id", str(point.id))
            text_snippet = payload.get("text_snippet", "")
            for k in EXCLUDED_METADATA_KEYS:
                payload.pop(k, None)
            group.append({
                "id": doc_id,
                "score": point.score,
                "text_snippet": text_snippet,
                "metadata": payload
            })
        formatted_results.append(group)
    return formatted_results

def _format_helper_static(point):
    payload = point.payload
    doc_id = payload.get("original_id", str(point.id))
    text_snippet = payload.get("text_snippet", "")
    for k in EXCLUDED_METADATA_KEYS:
        payload.pop(k, None)
    return {
        "id": doc_id,
        "score": point.score,
        "text_snippet": text_snippet,
        "metadata": payload
    }

def list_comp_helper_static(batch_results):
    # Simulating static method call
    return [
        [_format_helper_static(point) for point in result_group]
        for result_group in batch_results
    ]

def run_benchmark():
    print("Generating data...")
    data1 = generate_large_data()
    data2 = copy.deepcopy(data1)

    print("Running benchmark (1 run, large data)...")

    t0 = time.time()
    current_implementation(data1)
    t1 = time.time()
    print(f"Current loop:               {t1-t0:.6f} s")

    t0 = time.time()
    list_comp_helper_static(data2)
    t1 = time.time()
    print(f"List comp (static helper):  {t1-t0:.6f} s")

def generate_large_data(num_groups=1000, items_per_group=50):
    data = []
    for i in range(num_groups):
        group = []
        for j in range(items_per_group):
            payload = {
                "original_id": f"uuid-{i}-{j}",
                "text_snippet": "snippet " * 5,
                "full_text": "full text " * 50,
                "filename": f"file_{i}_{j}.txt",
                "indexed_at": 1234567890,
                "other_meta": "some data"
            }
            group.append(MockPoint(id=f"{i}-{j}", score=0.9, payload=payload))
        data.append(group)
    return data

if __name__ == "__main__":
    run_benchmark()
