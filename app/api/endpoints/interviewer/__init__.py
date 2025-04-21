"""
Interviewer domain package.
Contains all endpoints related to interview management, questions, tokens, results, and theming.
"""

# Make the routers available at the package level for cleaner imports
from .interviews import interviews_router
from .questions import questions_router
from .tokens import tokens_router
from .results import results_router
from .theme import theme_router

__all__ = [
    "interviews_router",
    "questions_router",
    "tokens_router",
    "results_router",
    "theme_router",
]