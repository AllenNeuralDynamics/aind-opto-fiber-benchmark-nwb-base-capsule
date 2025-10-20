# aind-opto-fiber-benchmark-nwb-base-capsule

This capsule takes in the raw data for the optogenetics fiber benchmark indicator experiment, structured here [acquisition-repo](https://github.com/AllenNeuralDynamics/FIP_DAQ_Control_IndicatorBenchmarking/blob/main/README.md) in the file formats section, and packages to a NWB file. 

In addition, at the top level, there will be a `session.json` file containing information about the optogenetic parameters used. An example is shown below

```json
"stimulus_parameters": [
  {
     "stimulus_type": "Opto Stimulation",
     "stimulus_name": "OptoStim",
     "pulse_shape": "Square",
     "pulse_frequency": [
        "1.0",
        "5.0",
        "10.0",
        "20.0",
        "40.0"
     ],
     "pulse_frequency_unit": "hertz",
     "number_pulse_trains": [
        40
     ],
     "pulse_width": [
        5
     ],
     "pulse_width_unit": "millisecond",
     "pulse_train_duration": [
        "0.5"
     ],
     "pulse_train_duration_unit": "second",
     "fixed_pulse_train_interval": true,
     "pulse_train_interval": "29.5",
     "pulse_train_interval_unit": "second",
     "baseline_duration": "120.0",
     "baseline_duration_unit": "second",
     "other_parameters": {},
     "notes": null
  }
]
```

### NWB Structure
The NWB output of this capsule contains 2 relevant containers, the `acquisition` and `events`. The acquisition contains the raw timeseries data for each of the `Signal`, `Iso`, and `Stim` data for each of the fiber connection indices. Index 4 corresponds to the sensor floor. The strucutre is shown below

```
acquisition
├── Iso_0
├── Iso_1
├── Iso_2
├── Iso_3
├── Iso_4
├── Signal_0
├── Signal_1
├── Signal_2
├── Signal_3
├── Signal_4
├── Stim_0
├── Stim_1
├── Stim_2
├── Stim_3
└── Stim_4
```

The events table contains the timestamps for each of the onset and offset laser stimulus delivered over the course of the experiment. Sample output is shown below

<img width="221" height="443" alt="image" src="https://github.com/user-attachments/assets/c267e2d0-3b35-4519-ba69-433f03a7b443" />



The sample code below shows how to access the NWB 

```
import json
from hdmf_zarr import NWBZarrIO

# REPLACE WITH PATH TO NWB
with NWBZarrIO('path/to/nwb', 'r') as io:
  nwb = io.read()

events = nwb.get_events__events_tables()
event_table_df = events.to_dataframe()
event_meanings_table = events.meanings_tables["meanings"][:]
timeseries_streams = nwb.acquisition
data = timeseries_streams["Iso_0"].data[:]
timestamps = timeseries_streams["Iso_0"].timestamps[:]

