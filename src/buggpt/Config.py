from buggpt.util.Logs import Event, append_event

initial_globals = set(globals().keys())

# analyze only PRs that have code changes in files in specific programming languages
code_change_pl = "all"  # "all" or "python"

# analyze only PRs with a single parent
single_parent_PRs_only = False


# log configuration
current_globals = set(globals().keys())
config_parameters = current_globals - initial_globals
append_event(
    Event(pr_nb=0, message=f"Configuration: {config_parameters}"))
