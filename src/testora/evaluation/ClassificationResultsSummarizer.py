from collections import Counter
import json

# Select the combination of prompt and model to evaluate:

# single-question, GPT-4o
# result_files = ["data/classification_results_03_2025/keras/single-question_GPT-4o.json",
#                 "data/classification_results_03_2025/marshmallow/single-question_GPT-4o.json",
#                 "data/classification_results_03_2025/pandas/single-question_GPT-4o.json",
#                 "data/classification_results_03_2025/scipy/single-question_GPT-4o.json"]

# single-question, GPT-4o-mini
# result_files = ["data/classification_results_03_2025/keras/single-question_GPT-4o-mini.json",
#                 "data/classification_results_03_2025/marshmallow/single-question_GPT-4o-mini.json",
#                 "data/classification_results_03_2025/pandas/single-question_GPT-4o-mini.json",
#                 "data/classification_results_03_2025/scipy/single-question_GPT-4o-mini.json"]

# single-question, DeepSeek-R1
# result_files = ["data/classification_results_03_2025/keras/single-question_DeepSeek-R1.json",
#                 "data/classification_results_03_2025/marshmallow/single-question_DeepSeek-R1.json",
#                 "data/classification_results_03_2025/pandas/single-question_DeepSeek-R1.json",
#                 "data/classification_results_03_2025/scipy/single-question_DeepSeek-R1.json"]

# multi-question, GPT-4o
# result_files = ["data/classification_results_03_2025/keras/multi-question_GPT-4o.json",
#                 "data/classification_results_03_2025/marshmallow/multi-question_GPT-4o.json",
#                 "data/classification_results_03_2025/pandas/multi-question_GPT-4o.json",
#                 "data/classification_results_03_2025/scipy/multi-question_GPT-4o.json"]

# multi-question, GPT-4o-mini
result_files = ["data/classification_results_03_2025/keras/multi-question_GPT-4o-mini.json",
                "data/classification_results_03_2025/marshmallow/multi-question_GPT-4o-mini.json",
                "data/classification_results_03_2025/pandas/multi-question_GPT-4o-mini.json",
                "data/classification_results_03_2025/scipy/multi-question_GPT-4o-mini.json"]

# multi-question, DeepSeek-R1
# result_files = ["data/classification_results_03_2025/keras/multi-question_DeepSeek-R1.json",
#                 "data/classification_results_03_2025/marshmallow/multi-question_DeepSeek-R1.json",
#                 "data/classification_results_03_2025/pandas/multi-question_DeepSeek-R1.json",
#                 "data/classification_results_03_2025/scipy/multi-question_DeepSeek-R1.json"]

# extract results
print("Project, PR, Prediction, Label, Result")
nb_fps = 0
nb_tps = 0
nb_fns = 0
nb_tns = 0
variance_ctr = Counter()
config_used = None
for result_file in result_files:
    if "keras" in result_file:
        project = "keras"
    elif "marshmallow" in result_file:
        project = "marshmallow"
    elif "pandas" in result_file:
        project = "pandas"
    elif "scipy" in result_file:
        project = "scipy"
    else:
        raise ValueError(f"Couldn't determine project from file name {result_file}")

    with open(result_file, "r") as f:
        result_json = json.load(f)
        config_used_here = result_json[0]["message"]
        if config_used is None:
            config_used = config_used_here
        else:
            assert config_used == config_used_here, f"Config mismatch:\nUsed before:\n{config_used}\nvs used now in {project}:\n {config_used_here}"
        for entry in result_json:
            if entry["message"] == "Classification result":
                # compare label and predictions
                results = []
                if entry["label"] in ["unintended", "coincidental fix"]:
                    for prediction in entry["predictions"].split("#"):
                        if prediction == "unintended":
                            results.append("TP")
                            nb_tps += 1
                        elif prediction == "intended":
                            results.append("FN")
                            nb_fns += 1
                        else:
                            raise ValueError(
                                f"Invalid prediction: {entry['prediction']}")
                elif entry["label"] in ["intended"]:
                    for prediction in entry["predictions"].split("#"):
                        if prediction == "intended":
                            results.append("TN")
                            nb_tns += 1
                        elif prediction == "unintended":
                            results.append("FP")
                            nb_fps += 1
                        else:
                            raise ValueError(
                                f"Invalid prediction: {entry['prediction']}")
                else:
                    raise ValueError(
                        f"Invalid label: {entry['label']}, {entry['pr_nb']}")

                # check variance of predictions
                results_counter = Counter(results)
                variance_str = str(
                    sorted(list(results_counter.values()), reverse=True))
                variance_ctr[variance_str] += 1

                # print into CSV
                print(f"{project}, "
                      f"{entry['pr_nb']}, "
                      f"{entry['predictions']}, "
                      f"{entry['label']}, "
                      f"{', '.join(results)}"
                      )

print(config_used)
print()
print(f"TP: {nb_tps}, FP: {nb_fps}, FN: {nb_fns}, TN: {nb_tns}")
precision = 0 if (nb_tps + nb_fps) == 0 else nb_tps / (nb_tps + nb_fps)
print(f"Precision: {precision}")
recall = 0 if (nb_tps + nb_fns) == 0 else nb_tps / (nb_tps + nb_fns)
print(f"Recall: {recall}")
f1 = 0 if (precision + recall) == 0 else 2 * \
    precision * recall / (precision + recall)
print(f"F1: {f1}")
print()
print(f"Variance of predictions: {variance_ctr}")
print(f"Total data points: {nb_tps+nb_fps+nb_fns+nb_tns}")
