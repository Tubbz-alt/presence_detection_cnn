#!/usr/bin/env python3

import numpy as np
import argparse
from parse_data_from_log import DataLogParser
from data_preprocessing import DataPreprocess
from data_learning import NeuralNetworkModel
import train_test_conf as conf
import matplotlib.pyplot as plt

def main():
    ##################################################
    # parse data from original data & construct images
    ##################################################
    print("parsing data from log files which are generated by Atheros-CSI-TOOL\n")
    data_generator = DataLogParser(conf.n_timestamps, conf.D, conf.step_size,
                                    conf.ntx_max, conf.nrx_max, conf.nsubcarrier_max,
                                    conf.data_folder, conf.log_folder,
                                    conf.skip_frames,
                                    conf.time_offset_ratio,
                                    conf.day_conf,
                                    conf.train_label)
    data_generator.generate_image_no_label(conf.draw_date, conf.draw_label)
    # train_data, test_data: classes (key: label, value: images under this label)
    test_data = data_generator.get_data_no_label()
    if len(test_data) == 0:
        print('find no data to draw under date {} and label {}!!!'.format(conf.draw_date, conf.draw_label))
        return
    ##################################################
    # apply signal processing blocks to images
    ##################################################
    print("Pre-processing data\n")
    data_process = DataPreprocess(conf.n_timestamps, conf.D, conf.step_size,
                                    conf.ntx_max, conf.ntx, conf.nrx_max, 
                                    conf.nrx, conf.nsubcarrier_max, conf.nsubcarrier,
                                    conf.data_shape_to_nn,
                                    conf.data_folder,conf.train_label)
    data_process.add_image_no_label(test_data)
    data_process.signal_processing(conf.do_fft, conf.fft_shape)
    data_process.prepare_shape()
    final_test_data = data_process.get_data_no_label()

    ##################################################
    # train or test data with neural netowrk
    ##################################################

    nn_model = NeuralNetworkModel(conf.data_shape_to_nn, conf.abs_shape_to_nn, 
                                  conf.phase_shape_to_nn, conf.total_classes)
    print("Get test result using existing model (in test mode)\n")
    nn_model.load_model(conf.model_name)
    for key in final_test_data:
        plt.figure()
        total_test = len(final_test_data[key])
        cc = 1
        for idx in final_test_data[key]:
            # if want to output motion probability, please set output_label == False
            result = nn_model.get_no_label_result(final_test_data[key][idx], output_label=True)
            plt.subplot(total_test, 1, cc)
            plt.plot(result)
            plt.title(idx)
            plt.ylim(0,1.05)
            cc = cc+1
        plt.suptitle(key)
    nn_model.end()
    plt.show()
    print("Done!")


if __name__ == "__main__":
    main()

