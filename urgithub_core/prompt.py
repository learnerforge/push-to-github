import logging

log = logging.getLogger("urgithub")

_confirm_cb = None


def register_confirm(callback):
    """Register a GUI confirmation provider (e.g. a messagebox).

    When set, every pipeline confirmation is answered through the callback
    instead of a terminal prompt. Pass None to unregister.
    """
    global _confirm_cb
    _confirm_cb = callback


def confirm(message, default=False, interactive=False):
    """Ask a yes/no question.

    Priority: registered GUI callback → terminal input (interactive runs) →
    defer (log only). Returns True only for an explicit yes.
    """
    if _confirm_cb is not None:
        return bool(_confirm_cb(message))
    if interactive:
        try:
            answer = input(f"{message} [y/N] ").strip().lower()
        except (EOFError, OSError):
            return default
        return answer in ("y", "yes")
    log.info("Question deferred (run manually or from the Control Center): %s", message)
    return default
