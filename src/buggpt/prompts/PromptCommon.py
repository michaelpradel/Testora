from buggpt.Config import model_version

# NOTE: when changing the system message, must remove the old cache

if model_version.startswith("gpt"):
    system_message = "You are an experienced Python developer."
elif model_version.startswith("deepseek"):
    system_message = ""

