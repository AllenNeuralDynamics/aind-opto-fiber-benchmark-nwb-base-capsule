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
    number_of_trials = session_metadata["stimulus_epochs"][0][
        "trials_total"
    ]
    pulse_frequencies = stim_metadata["pulse_frequency"]
    baseline_duration = float(stim_metadata["baseline_duration"])
    number_pulse_trains = float(stim_metadata["number_pulse_trains"][0])
    pulse_durations = stim_metadata["pulse_train_duration"]
    pulse_interval = float(stim_metadata["pulse_train_interval"])

    event_table_dict = {"timestamp": [], "event": []}
    meanings_table_dict = {"value": [], "meaning": [], "HED_tag": []}

    # get starting slice into dataframe
    start_frame_onset = _get_frame_index(
        0, float(pulse_frequencies[0]), float(baseline_duration)
    )
    event_table_dict["timestamp"].append(
        stim_df["SoftwareTS"].iloc[start_frame_onset]
    )
    event_table_dict["event"].append("OptoStimLaser_onset")

    for num_train in range(int(number_of_trials - 1)):
        for pulse_frequency in pulse_frequencies:
            for pulse_duration in pulse_durations:
                logger.info(
                    f"Processing frequency {pulse_frequency} "
                    f"and duration {pulse_duration} "
                    f"for trial number {num_train + 1}"
                )
                frame_offset = _get_frame_index(
                    start_frame_onset,
                    float(pulse_frequency),
                    float(pulse_duration),
                )
                event_table_dict["timestamp"].append(
                    stim_df["SoftwareTS"].iloc[frame_offset]
                )
                event_table_dict["event"].append("OptoStimLaser_offset")

                start_frame_onset = _get_frame_index(
                    frame_offset, float(pulse_frequency), float(pulse_interval)
                )
                event_table_dict["timestamp"].append(
                    stim_df["SoftwareTS"].iloc[start_frame_onset]
                )
                event_table_dict["event"].append("OptoStimLaser_onset")

    final_frame_offset = _get_frame_index(
        start_frame_onset,
        float(pulse_frequencies[-1]),
        float(pulse_duration[-1]),
    )
    event_table_dict["timestamp"].append(
        stim_df["SoftwareTS"].iloc[final_frame_offset]
    )
    event_table_dict["event"].append("OptoStimLaser_offset")

    event_table_df = pd.DataFrame(event_table_dict)
    for event in event_table_df["event"].unique():
        meanings_table_dict["value"].append(event)
        meanings_table_dict["meaning"].append(MEANINGS[event])
        meanings_table_dict["HED_tag"].append(HED_TAGS[event])
    meanings_table_df = pd.DataFrame(meanings_table_dict)

    return event_table_df, meanings_table_df
