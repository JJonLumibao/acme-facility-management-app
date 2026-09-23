"""Make the api package root importable (modules use top-level imports like `from utils import ...`)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
