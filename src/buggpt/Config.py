from buggpt.util.Logs import Event, append_event

# KEEP THIS AT THE TOP: needed to log the current configuration
initial_globals = set(globals().keys())

# analyze only PRs that have code changes in files in specific programming languages
code_change_pl = "all"  # "all" or "python"

# analyze only PRs with a single parent
single_parent_PRs_only = False

# use program merger to merge programs
use_program_merger = False


# KEEP THIS AT THE END: log the current configuration
current_globals = set(globals().keys())
config_parameters = current_globals - initial_globals
append_event(
    Event(pr_nb=0, message=f"Configuration: {config_parameters}"))
