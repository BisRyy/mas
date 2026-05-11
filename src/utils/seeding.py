"""Global seeding for reproducibility (Section 3.1 of the proposal)."""
from __future__ import annotations

import os
import random


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
