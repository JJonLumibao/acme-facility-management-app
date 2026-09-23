"""Lambda entry point. Terraform requires this file/name (handler = 'function.handler')."""
from main import handler

__all__ = ["handler"]

if __name__ == "__main__":
    print(handler())
