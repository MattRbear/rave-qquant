import re
import time

MESSAGE_PATTERN_MODULE = re.compile(
    r'^(User|Assistant|Human|AI|System|You|Me):\s*',
    re.MULTILINE | re.IGNORECASE
)

def benchmark_local_compile(iterations=10000):
    text = "User: Hello\nAssistant: Hi there\nUser: How are you?\nAI: I am fine."
    start = time.perf_counter()
    for _ in range(iterations):
        message_pattern = re.compile(
            r'^(User|Assistant|Human|AI|System|You|Me):\s*',
            re.MULTILINE | re.IGNORECASE
        )
        splits = message_pattern.split(text)
    end = time.perf_counter()
    return end - start

def benchmark_module_compile(iterations=10000):
    text = "User: Hello\nAssistant: Hi there\nUser: How are you?\nAI: I am fine."
    start = time.perf_counter()
    for _ in range(iterations):
        splits = MESSAGE_PATTERN_MODULE.split(text)
    end = time.perf_counter()
    return end - start

if __name__ == "__main__":
    iterations = 500000
    local_time = benchmark_local_compile(iterations)
    module_time = benchmark_module_compile(iterations)

    print(f"Local compile time: {local_time:.4f}s")
    print(f"Module compile time: {module_time:.4f}s")
    print(f"Improvement: {(local_time - module_time) / local_time * 100:.2f}%")
