# *****************************************************************************
#  * @file    HSD_DataToolkit.py
#  * @author  SRA
# ******************************************************************************
# * @attention
# *
# * Copyright (c) 2022 STMicroelectronics.
# * All rights reserved.
# *
# * This software is licensed under terms that can be found in the LICENSE file
# * in the root directory of this software component.
# * If no LICENSE file comes with this software, it is provided AS-IS.
# *
# *
# ******************************************************************************
"""HSD Data Toolkit worker thread.

This module defines the `HSD_DataToolkit` thread that receives component data
via a Qt `Signal`, performs packetization and timestamp extraction based on
component configuration, converts byte buffers to NumPy arrays, and forwards
them to the data toolkit pipeline for processing and visualization.

Modes:
- Timestamped packets: data samples followed by an 8-byte little-endian double
    timestamp per packet when `samples_per_ts` is not zero.
- Raw streams: data forwarded directly to the pipeline when `samples_per_ts`
    is zero (packetization and timestamping handled upstream, e.g., by a plugin).
"""

import queue
import struct
from threading import Thread

import numpy as np
from PySide6.QtCore import Signal
from stdatalog_dtk.HSD_DataToolkit_Pipeline import HSD_DataToolkit_data
from stdatalog_core.HSD.utils.type_conversion import TypeConversion
from stdatalog_core.HSD_utils.DataClass import DataClass


class HSD_DataToolkit(Thread):
    """Consumer thread for component data.

    Aggregates incoming bytes per component, extracts complete packets, decodes
    timestamps when present, converts data to NumPy arrays, and forwards them to
    the configured pipeline.

    Parameters:
    - components_status: dict mapping component names to status dicts (keys like
        `dim`, `data_type`, `samples_per_ts`).
    - data_pipeline: object exposing `process_data(HSD_DataToolkit_data)`.
    - data_ready_evt: PySide6 `Signal` that emits `DataClass` and is connected
        to enqueue incoming data.
    """

    def __init__(self, components_status, data_pipeline, data_ready_evt: Signal):
        Thread.__init__(self)
        self.components_status = components_status
        self.data_pipeline = data_pipeline
        self.data_queue = queue.Queue()

        self.data_ready_evt = data_ready_evt
        self.data_ready_evt.connect(self.add_data_to_queue)

        self.missing_bytes = {}
        self.incoming_data = {}
        self.stop_thread = False

    def extract_data(self, data):
        """Extract packets and forward to the pipeline.

        Parameters:
        - data: DataClass carrying `comp_name` and raw `data` bytes.

        Behavior:
        - Accumulates incoming bytes per component until complete packets are
            available.
        - When `samples_per_ts` is not zero, reads an 8-byte timestamp
            (`<d` little-endian) following each packet.
        - Converts packet bytes to a NumPy array using the component `data_type`
            and forwards `HSD_DataToolkit_data` to the pipeline.
        """
        comp_name = data.comp_name
        comp_data = data.data
        comp_status = self.components_status[comp_name]
        dim = comp_status.get("dim", 1)
        data_type = comp_status.get("data_type")
        spts = comp_status.get("samples_per_ts", 1)
        timestamp_bytes_len = 8 if spts != 0 else 0

        if comp_name in self.incoming_data:
            self.incoming_data[comp_name] += comp_data
        else:
            self.incoming_data[comp_name] = comp_data

        # When samples_per_ts != 0, each completed packet is followed by a
        # timestamp. Compute packet boundaries and extract timestamp per packet.
        if spts != 0:
            data_sample_bytes_len = dim * TypeConversion.check_type_length(data_type)
            data_packet_len = (
                spts * data_sample_bytes_len
            ) if spts != 0 else data_sample_bytes_len
            nof_cmplt_packets = (
                len(self.incoming_data[comp_name]) // (data_packet_len + timestamp_bytes_len)
            )

            for _ in range(nof_cmplt_packets):
                packet = self.incoming_data[comp_name][:data_packet_len]
                self.incoming_data[comp_name] = self.incoming_data[comp_name][data_packet_len:]

                if spts != 0:
                    timestamp = struct.unpack(
                        '<d',
                        self.incoming_data[comp_name][:timestamp_bytes_len],
                    )[0]
                    self.incoming_data[comp_name] = self.incoming_data[comp_name][
                        timestamp_bytes_len:
                    ]
                else:
                    timestamp = None
            data_buffer = np.frombuffer(
                packet, dtype=TypeConversion.get_np_dtype(data_type)
            )
            self.data_pipeline.process_data(
                HSD_DataToolkit_data(comp_name, data_buffer, timestamp)
            )
        else:
            # Raw data is passed without any processing (timestamps or packetization).
            # Packetization and timestamping should be handled at a higher level
            # (e.g., a buffering plugin as first stage in the pipeline).
            self.data_pipeline.process_data(
                HSD_DataToolkit_data(comp_name, comp_data, None)
            )

    def run(self):
        """Main consumer loop.

        Blocks on `data_queue` with a short timeout and calls
        `extract_data` for each received item until `stop_thread` is set.
        """
        while not self.stop_thread:
            try:
                # Wait for data to be available in the queue
                data = self.data_queue.get(timeout=1)  # Adjust timeout as needed
                self.extract_data(data)
            except queue.Empty:
                continue

    def add_data_to_queue(self, data: DataClass):
        """Enqueue incoming data emitted by the Qt signal.

        Parameters:
        - data: `DataClass` carrying component name and raw bytes.
        """
        self.data_queue.put(data)

    def start(self):
        """Start the consumer thread."""
        super().start()

    def stop(self):
        """Request the consumer thread to stop.

        Sets `stop_thread` to `True`. The loop will exit after the current
        blocking `get` returns or times out.
        """
        self.stop_thread = True
