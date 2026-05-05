import time
import json
from pathlib import Path
from extract_nova_chat import process_dataset

def run_benchmark():
    test_input = Path("bench_input")
    test_output = Path("bench_output")

    test_input.mkdir(exist_ok=True)
    test_output.mkdir(exist_ok=True)

    content = """User: I want to learn about trading stocks and options
Assistant: I can help you with that!
User: My depression is getting worse and I need goals
Assistant: Let's talk about achievable goals
User: This is irrelevant noise that should be filtered
User: Tell me about OSRS bots and automation strategies
"""

    try:
        for i in range(5000):
            (test_input / f"test_{i}.txt").write_text(content)

        start_time = time.time()
        process_dataset(test_input, test_output, max_chars=5000000)
        end_time = time.time()

        print(f"Time taken: {end_time - start_time:.4f} seconds")

    finally:
        import shutil
        if test_input.exists():
            shutil.rmtree(test_input)
        if test_output.exists():
            shutil.rmtree(test_output)

if __name__ == "__main__":
    run_benchmark()
