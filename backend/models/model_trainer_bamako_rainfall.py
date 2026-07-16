"""Shim rétrocompatible — préférer models.trainers.model_trainer_bamako_rainfall."""
from models.trainers.model_trainer_bamako_rainfall import *  # noqa: F401,F403
from models.trainers.model_trainer_bamako_rainfall import main

if __name__ == "__main__":
    main()
