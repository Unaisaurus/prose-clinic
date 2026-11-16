"""All detection rules. Importing a module registers its rules (see base.py)."""

from . import (  # noqa: F401  (imported for their @register side effects)
    conflict,
    custom,
    dialogue,
    emotion,
    formulaic,
    punctuation,
    purple,
    repetition,
    stock_phrases,
)
from .base import Rule, RuleContext, all_rules, get_rule

__all__ = ["Rule", "RuleContext", "all_rules", "get_rule"]
