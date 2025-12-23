import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


CHANNEL_MAPPING = ["Signal", "Iso", "Stim"]
MEANINGS = {
    "OptoStimLaser_onset": "Onset of Optogenetic Stimulus Laser",
    "OptoStimLaser_offset": "Offset of Optogenetic Stimulus Laser",
}
HED_TAGS = {
    "OptoStimLaser_onset": "Onset/Experimental-stimulus",
    "OptoStimLaser_offset": "Offset/Experimental-stimulus",
}
# number of fiber index columns (0, 1, 2, 3, 4)
# index 4 corresponds to floor
# for when no headers in csv
NUM_FIBER_COLUMNS = 5
FIBER_SAMPLING_RATE = 20

VARYING_FREQUENCY_ITI_OFFSET = 3.1
VARYING_FREQUENCY_OFFSETS = [30.5, 30.1, 30, 30]

VARYING_DURATION_ITI_OFFSET = 3.9
VARYING_DURATION_OFFSETS = [28.05, 28.1, 28.25, 28.5, 29]

def get_channel_data(
    data_directory: Path,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
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
            raise FileNotFoundError(
                f"No {channel} csv file. Check data at path{data_directory}"
            )

        df_data = pd.read_csv(data_file[0])
        if "SoftwareTS" not in df_data.columns:
            logger.info(
                "No headers found. Defaulting to following "
                "0 index is time, 1-4 are Fiber ROIs"
            )
            df_data = pd.read_csv(data_file[0], header=None)
            # Assume first column is timestamps, the rest are ROIs
            columns = ["SoftwareTS"] + [
                f"ROI{i}" for i in range(0, NUM_FIBER_COLUMNS)
            ]
            df_data.columns = columns

        data_columns = df_data.filter(like="ROI").columns
        timestamps = df_data["SoftwareTS"].to_numpy()
        for column in data_columns:
            column_data = df_data[column].to_numpy()
            assert len(timestamps) == len(column_data)
            if "sensorfloor" in column:
                name = f"{channel}_{column.replace("_sensorfloor", "")[-1]}"
            else:
                name = f"{channel}_{column[-1]}"
            data[name] = (timestamps, column_data)

    return data


def _get_frame_index(
    frame_start: int, frequency: float, time_factor: float
) -> int:
    """
    Gets the corresponding frame index given a frame start,
    frequency, and time factor (duration or interval)

    Parameters
    ----------
    frame_start: int
        The starting frame
    frequency: float
        The frequency to be applied to the frame index
        calculation
    time_factor: float
        The duration or interval to be applied to the
        frame index calculation

    Returns
    -------
    int
        The corresponding frame index
    """

    return int(frame_start + (float(frequency) * time_factor))

def get_stim_indices_multi_frequency_mode(
    num_trials: int, 
    pulse_frequencies: list, 
    pulse_duration: float, 
    pulse_interval: float,
    baseline_duration: float
) -> np.ndarray:
    """
    Gets the stim indices for experiment mode with 
    varying pulse frequencies
    
    Parameters
    ----------
    num_trials: int
        Number of trials in experiment
    pulse_frequencies: list
       List of varying pulse frequencies
    pulse_duration: float
        Stim duration of laser
    pulse_interval: float
        The inter-trial-interval in seconds
    baseline_duration: float
        The period before stim laser 
        occurs in seconds

    Returns
    -------
    np.ndarray
        The stim indices for mode with 
        varying frequencies
    """
    stim_indices = []

    for num_index in range(len(pulse_frequencies)):
        # Compute the starting times of each trial for this frequency
        stim_train = np.arange(num_trials) * (pulse_interval * len(pulse_frequencies) + VARYING_FREQUENCY_ITI_OFFSET) + baseline_duration

        # Add frequency-specific offsets
        if num_index > 0:
            for offset_index in range(num_index):
                stim_train = stim_train + VARYING_FREQUENCY_OFFSETS[offset_index]

        # Convert time to sample indices
        stim_train_indices = (stim_train * FIBER_SAMPLING_RATE).astype(int)

        # Add pulse duration (in samples) for each trial
        pulse_samples = int(pulse_duration * FIBER_SAMPLING_RATE)
        for start_idx in stim_train_indices:
            stim_indices.extend(range(start_idx, start_idx + pulse_samples))

    return np.array(stim_indices)

def get_stim_indices_multi_duration_mode(
    num_trials: int, 
    pulse_durations: list, 
    pulse_interval: float,
    baseline_duration: float
) -> np.ndarray:
    """
    Gets the stim indices for experiment mode with 
    varying pulse durations
    
    Parameters
    ----------
    num_trials: int
        Number of trials in experiment
    pulse_durations: list
       List of varying pulse durations
    pulse_interval: float
        The inter-trial-interval in seconds
    baseline_duration: float
        The period before stim laser 
        occurs in seconds

    Returns
    -------
    np.ndarray
        The stim indices for mode with 
        varying durations
    """
    stim_indices = []

    for num_index in range(len(pulse_durations)):
        duration = float(pulse_durations[num_index])  # use the specific duration
        # Compute the starting times of each trial
        stim_train = np.arange(num_trials) * (pulse_interval * len(pulse_durations) + VARYING_DURATION_ITI_OFFSET) + baseline_duration

        # Add duration-specific offsets
        if num_index > 0:
            for offset_index in range(num_index):
                stim_train = stim_train + VARYING_DURATION_OFFSETS[offset_index]

        # Convert time to sample indices
        stim_train_indices = (stim_train * FIBER_SAMPLING_RATE).astype(int)

        # Add pulse duration (in samples) for each trial
        pulse_samples = int(duration * FIBER_SAMPLING_RATE)
        for start_idx in stim_train_indices:
            stim_indices.extend(range(start_idx, start_idx + pulse_samples))

    return np.array(stim_indices)

def get_pulse_onsets_offsets(stim_indices: np.ndarray):
    """
    Extract the onset and offset indices (or times) of
    pulses from a list of sample indices.

    Parameters
    ----------
    stim_indices : np.ndarray
        1D array of all sample indices during
        pulses (can be flattened across trials).

    Returns
    -------
    onsets : np.ndarray
        Array of pulse onset indices (or times if sampling_rate is given).
    offsets : np.ndarray
        Array of pulse offset indices (or times if sampling_rate is given).
    """
    stim_indices = np.sort(np.array(stim_indices))
    diffs = np.diff(stim_indices)
    
    # Find boundaries where gap > 1 sample
    pulse_boundaries = np.where(diffs > 1)[0]

    # Onsets: first index of each pulse
    onsets = stim_indices[np.insert(pulse_boundaries + 1, 0, 0)]
    # Offsets: last index of each pulse
    offsets = stim_indices[np.append(pulse_boundaries, len(stim_indices) - 1)]

    return onsets, offsets

def create_event_and_meanings_dataframes(
    data_directory: Path, session_metadata: dict
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Creates the event and meanings dataframes for the
    event table in the NWB

    Parameters
    ----------
    data_directory: Path
        Path to the event data files
    session_metadata: dict
        Metadata with parameters needed for event table

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        The event and meanings dataframes
    """
    stim_csv_path = tuple(data_directory.glob("Stim*.csv"))
    if not stim_csv_path:
        raise FileNotFoundError(
            f"No stim csv found in directory {data_directory}. Check data"
        )

    stim_df = pd.read_csv(stim_csv_path[0])
    stim_metadata = session_metadata["stimulus_epochs"][0][
        "stimulus_parameters"
    ][0]
    number_of_trials = session_metadata["stimulus_epochs"][0]["trials_total"]
    pulse_frequencies = stim_metadata["pulse_frequency"]
    baseline_duration = float(stim_metadata["baseline_duration"])
    pulse_durations = stim_metadata["pulse_train_duration"]
    pulse_interval = float(stim_metadata["pulse_train_interval"])

    event_table_dict = {"timestamp": [], "event": []}
    meanings_table_dict = {"value": [], "meaning": [], "HED_tag": []}

    if len(pulse_frequencies) > 1 and len(pulse_durations) > 1:
        raise ValueError(
            "Mode with varying pulse frequencies and durations "
            "not supported yet"
        )

    if len(pulse_frequencies) > 1:
        logger.info(
            f"Found mode with varying pulse frequences {pulse_frequencies}"
        )
        stim_time_indices = get_stim_indices_multi_frequency_mode(
            num_trials=number_of_trials,
            pulse_frequencies=pulse_frequencies,
            pulse_duration=float(pulse_durations[0]),
            pulse_interval=pulse_interval,
            baseline_duration=baseline_duration
        )
    elif len(pulse_durations) > 1:
        logger.info(
            f"Found mode with varying pulse durations {pulse_durations}"
        )
        stim_time_indices = get_stim_indices_multi_duration_mode(
            num_trials=number_of_trials,
            pulse_durations=pulse_durations,
            pulse_interval=pulse_interval,
            baseline_duration=baseline_duration
        )
    else:
        stim_times = np.arange(number_of_trials) * pulse_interval + baseline_duration
        pulse_samples = int(float(pulse_durations[0]) * FIBER_SAMPLING_RATE)
        stim_time_indices = []

        # Convert stim_times to sample indices
        stim_start_indices = (stim_times * FIBER_SAMPLING_RATE).astype(np.int64)

        for start in stim_start_indices:
            # Expand each trial to full pulse duration
            pulse_indices = np.arange(start, start + pulse_samples)
            stim_time_indices.extend(pulse_indices)

        # Convert to NumPy array
        stim_time_indices = np.array(stim_time_indices)

    logger.info(
        f"Found {len(stim_time_indices)} laser pulse indices for setup "
        f"with pulse frequences {pulse_frequencies} and "
        f"pulse durations {pulse_durations}"
    )

    stim_onsets, stim_offsets = get_pulse_onsets_offsets(stim_time_indices)
    # Pair each onset with its offset
    for onset_idx, offset_idx in zip(stim_onsets, stim_offsets):
        event_table_dict["timestamp"].append(stim_df["SoftwareTS"].iloc[onset_idx])
        event_table_dict["event"].append("OptoStimLaser_onset")
        
        event_table_dict["timestamp"].append(stim_df["SoftwareTS"].iloc[offset_idx])
        event_table_dict["event"].append("OptoStimLaser_offset")

    event_table_df = pd.DataFrame(event_table_dict)
    for event in event_table_df["event"].unique():
        meanings_table_dict["value"].append(event)
        meanings_table_dict["meaning"].append(MEANINGS[event])
        meanings_table_dict["HED_tag"].append(HED_TAGS[event])
    meanings_table_df = pd.DataFrame(meanings_table_dict)

    return event_table_df, meanings_table_df
