class StateError(Exception):
    """A refusal. The message names the violated rule; the CLI maps this to exit 1."""
