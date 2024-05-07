import json
import matplotlib.pyplot as plt

def analyze_llm_cache(file_path):
    with open(file_path, "r") as f:
        cache = json.load(f)
    print(f"Total cache entries: {len(cache)}")
    query_sizes = []
    answer_sizes = []
    for query, answer in cache.items():
        query_sizes.append(len(query))
        answer_sizes.append(len(answer))

    # plot histogram of query sizes
    plt.hist(query_sizes, bins=50)
    plt.title("Query sizes")
    plt.xlabel("Size")
    plt.ylabel("Frequency")
    plt.show()

    # plot histogram of answer sizes
    plt.hist(answer_sizes, bins=50)
    plt.title("Answer sizes")
    plt.xlabel("Size")
    plt.ylabel("Frequency")
    plt.show()

    

if __name__ == "__main__":
    analyze_llm_cache("data/llm_cache/gpt-4-0125-preview/cache.json")
