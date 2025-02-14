# *****************************************************************************
#  * @file    Controller.py
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
#

import queue
import struct
from threading import Thread

import numpy as np
from PySide6.QtCore import Signal
from stdatalog_dtk.HSD_DataToolkit_Pipeline import HSD_DataToolkit_data
from stdatalog_core.HSD.utils.type_conversion import TypeConversion
from stdatalog_core.HSD_utils.DataClass import DataClass

class HSD_DataToolkit(Thread):
    def __init__(self, components_status, data_pipeline, data_ready_evt:Signal):
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
        comp_name = data.comp_name
        comp_data = data.data
        comp_status = self.components_status[comp_name]
        dim = comp_status.get("dim",1)
        data_type = comp_status.get("data_type")
        data_sample_bytes_len = dim * TypeConversion.check_type_length(data_type)
        spts = comp_status.get("samples_per_ts", 1)
        timestamp_bytes_len = 8 if spts != 0 else 0
        data_packet_len = (spts * data_sample_bytes_len) if spts != 0 else data_sample_bytes_len

        if comp_name in self.incoming_data:
            self.incoming_data[comp_name] += comp_data
        else:
            self.incoming_data[comp_name] = comp_data

        nof_cmplt_packets = len(self.incoming_data[comp_name]) // (data_packet_len + timestamp_bytes_len)
        
        for _ in range(nof_cmplt_packets):
            packet = self.incoming_data[comp_name][:data_packet_len]
            self.incoming_data[comp_name] = self.incoming_data[comp_name][data_packet_len:]

            if spts != 0:
                timestamp = struct.unpack('<d', self.incoming_data[comp_name][:timestamp_bytes_len])[0]
                self.incoming_data[comp_name] = self.incoming_data[comp_name][timestamp_bytes_len:]
            else:
                #TODO!: Implement the case when spts = 0 (timestamp = None)
                timestamp = None

            data_buffer = np.frombuffer(packet, dtype=TypeConversion.get_np_dtype(data_type))
            self.data_pipeline.process_data(HSD_DataToolkit_data(comp_name, data_buffer, timestamp))


    def run(self):
        while not self.stop_thread:
            try:
                # Wait for data to be available in the queue
                data = self.data_queue.get(timeout=1)  # Adjust timeout as needed
                self.extract_data(data)
            except queue.Empty:
                continue

    def add_data_to_queue(self, data:DataClass):
            self.data_queue.put(data)

    def start(self):
        super().start()

    def stop(self):
        # stop the consumer thread
        self.stop_thread = True

