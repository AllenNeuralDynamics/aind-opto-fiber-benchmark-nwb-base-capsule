import pandas as pd
import numpy as np
from pathlib import Path

CHANNEL_MAPPING = ["Signal", "Iso", "Stim"]
def get_channel_data(data_directory: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """
    Gets the timestamps and data for each channel

    Parameters
    ----------
    data_directory: Path
        The path to the data with the relevant files
    
    Returns
    -------
    dict[str, tuple[np.ndarray, np.ndarray]]
        Dictionary with key as name and value as tuple
        of timestamps and data
    """
    data = {}
    for channel in CHANNEL_MAPPING:
        data_file = tuple(data_directory.glob(f"{channel}*.csv"))
        if not data_file:
            raise FileNotFoundError(f"No {channel} csv file. Check data at path{data_directory}")
        
        df_data = pd.read_csv(data_file[0])
        data_columns = df_data.filter(like="ROI").columns
        timestamps = df_data["SoftwareTS"].to_numpy()
        for column in data_columns:
            column_data = df_data[column].to_numpy()
            assert len(timestamps) == len(column_data)
            data[f"{channel}_{column}"] = (
                timestamps,
                column_data
            )
    
    return data