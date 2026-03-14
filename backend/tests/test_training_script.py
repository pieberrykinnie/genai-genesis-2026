from pathlib import Path

import pandas as pd
import pytest

from scripts.train_grid_model import _build_dataset


def test_build_dataset_requires_real_data_by_default(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="No real IESO/AESO CSVs"):
        _build_dataset(tmp_path, allow_synthetic=False)


def test_build_dataset_allows_synthetic_optin(tmp_path: Path) -> None:
    df, used_synthetic = _build_dataset(tmp_path, allow_synthetic=True)
    assert used_synthetic is True
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
