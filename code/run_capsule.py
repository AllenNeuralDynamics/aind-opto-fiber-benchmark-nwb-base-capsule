"""
Capsule to package benchmark
indicator data
"""

import json
import logging
from pathlib import Path

import pynwb
from aind_nwb_utils.utils import get_subject_nwb_object
from dateutil import parser
from hdmf_zarr import NWBZarrIO
from ndx_events import EventsTable, MeaningsTable, NdxEventsNWBFile
from pydantic import Field
from pydantic_settings import BaseSettings

import utils

logger = logging.getLogger(__name__)


class OptoInputSettings(BaseSettings, cli_parse_args=True):
    """
    Settings for Opto + Fiber NWB Packaging
    """

    input_directory: Path = Field(
        default=Path("/data/"), description="Directory where data is"
    )
    output_directory: Path = Field(
        default=Path("/results/"), description="Output directory"
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    settings = OptoInputSettings()
    primary_data_path = tuple(settings.input_directory.glob("raw_data"))

    if not primary_data_path:
        raise FileNotFoundError("No primary data asset attached")

    if len(primary_data_path) > 1:
        raise ValueError(
            "Multiple primary data assets attached. Only single asset needed"
        )

    primary_data_path = primary_data_path[0]
    logger.info(f"Found primary data at path {primary_data_path}")

    session_json_path = primary_data_path / "session.json"
    data_description_json_path = primary_data_path / "data_description.json"
    subject_json_path = primary_data_path / "subject.json"
    if not session_json_path.exists():
        raise FileNotFoundError("Primary data asset has no session json file")
    if not data_description_json_path.exists():
        raise FileNotFoundError(
            "Primary data asset has no data description json"
        )

    if not subject_json_path.exists():
        raise FileNotFoundError("Primary data asset has no subject json")

    with open(session_json_path, "r") as f:
        session_json = json.load(f)
    with open(data_description_json_path, "r") as f:
        data_description_json = json.load(f)
    with open(subject_json_path, "r") as f:
        subject_json = json.load(f)
    logger.info(
        f"Found primary data {data_description_json['name']}. \
        Starting acquisition nwb packaging now"
    )

    # using this ndx object for events table
    nwb_file = NdxEventsNWBFile(
        session_id=data_description_json["name"],
        session_description="Opto + Fiber Indicator Benchmarking",
        session_start_time=parser.parse(session_json["session_start_time"]),
        identifier=data_description_json["subject_id"],
        subject=get_subject_nwb_object(data_description_json, subject_json),
    )

    data = utils.get_channel_data(primary_data_path / "fib")
    logger.info(f"Found data to package {tuple(data.keys())}. Adding to NWB")
    for key, values in data.items():
        description = f"{key} timeseries data"
        ts = pynwb.TimeSeries(
            name=key,
            data=values[1],
            unit="s",
            timestamps=values[0],
            description=description,
        )
        nwb_file.add_acquisition(ts)

    logger.info("Finished packaging timeseries")
    logger.info("Gathering events and meanings table now")

    events_df, meanings_df = utils.create_event_and_meanings_dataframes(
        settings.input_directory / "fib", session_json
    )

    event_table = EventsTable.from_dataframe(
        events_df,
        name="events",
        table_description="Events for Benchmark Indicator experiment",
    )
    meanings_table = MeaningsTable.from_dataframe(
        meanings_df,
        name="meanings",
        table_description=(
            "Description of values in events table for "
            "Benchmark Indicator experiment",
        )[0],
    )
    event_table.add_meanings_tables(meanings_table)
    nwb_file.add_events_table(event_table)
    logger.info("Finished gathering events and meanings tables")

    logger.info(
        f"Finished packaging. Saving to path {settings.output_directory}"
    )
    nwb_output_path = (
        settings.output_directory / f"{data_description_json["name"]}.nwb"
    )
    with NWBZarrIO(nwb_output_path.as_posix(), "w") as io:
        io.write(nwb_file)
    logger.info("Finished saving nwb with timseries and event data")
