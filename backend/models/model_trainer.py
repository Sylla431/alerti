"""Shim rétrocompatible — préférer models.trainers.model_trainer."""
from models.trainers.model_trainer import *  # noqa: F401,F403
from models.trainers.model_trainer import main

if __name__ == "__main__":
    main()
