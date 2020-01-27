#!/usr/bin/python3

import numpy as np
from struct import unpack, calcsize
import collections
import time
from log_parsing import ParseDataFile
from os import path
import train_test_conf as conf
import argparse
from global_sp_func import check_no_outlier 

def get_input_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mode', help="if 1, run under training mode, if 0 run under test mode", type=int, default=1)
    args = parser.parse_args()
    return args

def append_array(array_a, array_b, axis=0):
    if array_a.size == 0:
        array_a = array_a.astype(array_b.dtype)
        array_a = array_a.reshape((0,) + array_b.shape[1:])
    array_a = np.concatenate([array_a, array_b], axis)
    return array_a


class ConstructImage:
    def __init__(self, n_timestamps, D, step_size, ntx, nrx, n_tones,skip_frames, offset_ratio):
        self.n_timestamps = n_timestamps
        self.D = D
        self.frame_dur = conf.frame_dur*1e3  # in microseconds
        self.ntx_max = ntx
        self.nrx_max = nrx
        self.n_tones = n_tones
        self.step_size = step_size
        self.skip_frames = skip_frames
        self.time_offset_tolerance = self.n_timestamps*offset_ratio*self.D*self.frame_dur
        print('allowed time offset {}'.format(self.time_offset_tolerance))

    def process_data(self, frame_data):
        frame_data = frame_data[self.skip_frames:-self.skip_frames] 
        num_instances = max(0, int((len(frame_data)-self.n_timestamps*self.D)/self.step_size)+5)
        
        final_data = np.zeros((num_instances, self.n_timestamps, self.nrx_max, self.ntx_max, self.n_tones), dtype=np.complex64)
        if num_instances == 0:
            return final_data
        d = 0
        valid_instance_c = 0
        while d<len(frame_data)-self.n_timestamps*self.D:
            temp_image = np.zeros((self.n_timestamps, self.nrx_max, self.ntx_max, self.n_tones), dtype=np.complex64)
            valid = True
            offset = self.step_size
            start_time = 0 
            end_time = 0
            start_index = 0
            end_index = 0
            time_index = []
            for k in range(self.n_timestamps):
                m = d + k*self.D
                nc = frame_data[m]['format'].nc
                csi = frame_data[m]['csi']
                if nc<self.ntx_max:
                    #print("not enough transmit antenna") 
                    valid = False
                    offset = k*self.D+1
                    break
                if k==0:
                    start_time = frame_data[m]['format'].timestamp
                    start_index = m
                elif k==self.n_timestamps-1:
                    end_time = frame_data[m]['format'].timestamp
                    end_index = m
                    time_off = abs(end_time-start_time-(self.n_timestamps-1)*self.D*self.frame_dur)
                    if end_time < start_time: # reseting error, skip
                        #print("end time is smaller than start time")
                        valid = False
                        offset = k*self.D+1
                        break
                    if time_off>self.time_offset_tolerance:
                        #print("timing off is {:.3f}".format(time_off/(self.D*self.frame_dur)))
                        valid = False
                        offset = 1
                        break
                temp_image[k, :, :nc, :] = csi
                time_index.append(frame_data[m]['format'].timestamp)
            if valid:
                final_data[valid_instance_c, ...] = temp_image
                valid_instance_c = valid_instance_c+1
                #v = check_no_outlier(temp_image)
            d = d+offset
        final_data = final_data[:valid_instance_c,...]
        print("total number of images: "+str(final_data.shape[0]))
        return final_data


class DataLogParser:
    def __init__(self, n_timestamps, D, step_size, ntx_max,
                 nrx_max, nsubcarrier_max, file_prefix, log_file_prefix, skip_frames, time_offset_ratio,conf, labels):
        self.parser = ParseDataFile()
        self.image_constructor = ConstructImage(n_timestamps, D, step_size,
                                                ntx_max, nrx_max, nsubcarrier_max, skip_frames, time_offset_ratio)
        self.file_prefix = file_prefix
        self.log_file_prefix = log_file_prefix
        self.data_shape = (n_timestamps, nrx_max, ntx_max, nsubcarrier_max)
        self.step_size = step_size
        self.n_timestamps = n_timestamps
        self.x_train, self.y_train, self.x_test, self.y_test = None, None, None, None
        self.conf = conf
        self.out_data_train, self.out_data_test, self.out_data_no_label= {}, {}, {}
        self.label = labels
        for k, o in self.label.items():
            self.out_data_train[o] = np.array([])
            self.out_data_test[o] = np.array([])

    def generate_image(self, train_date, test_date):
        date = training_date + test_date
        for d in date:
            #print("\nprocessing data from date {}\n".format(m))
            filename = self.file_prefix + d + '/'
            logfilename = self.log_file_prefix + d + '/'
            for label_name, o in self.label.items():
                out_data_train = np.array([])
                out_data_test = np.array([])
                if label_name in self.conf[d]:
                    total_tests = self.conf[m][label_name]
                else:
                    continue
                for i in range(1, total_tests+1):
                    frame_data = self.parser.parse(logfilename + label_name + str(i) + ".data")
                    dd = self.image_constructor.process_data(frame_data)
                    if d in test_date:
                        self.out_data_test[o] = append_array(self.out_data_test[o], dd)
                    else:
                        self.out_data_train[o] = append_array(self.out_data_train[o], dd)

    def generate_image_no_label(self, date, label_name):
        for d in date:
            #print("\nprocessing data from date {}\n".format(m))
            #print(self.conf[m])
            filename = self.file_prefix + d + '/'
            logfilename = self.log_file_prefix + d + '/'
            if label_name not in self.conf[m]:
                continue
            total_tests = self.conf[m][label_name]
            if total_tests == 0:
                continue
            self.out_data_no_label[d] = {}
            print('on date '+m)
            for i in range(1, total_tests+1):
                frame_data = self.parser.parse(logfilename + label_name + str(i) + ".data")
                dd = self.image_constructor.process_data(frame_data)
                self.out_data_no_label[m][label_name+'_'+str(i)] = dd 
                print('add mixed data: '+label_name+'_'+str(i))

    def save_data(self, train_model):
        for k, o in self.label:
            if train_model:
                self.out_data_train[o].tofile(self.file_prefix+"training_"+str(o)+'.dat')
                self.out_data_test[o].tofile(self.file_prefix+"training_test_"+str(o)+'.dat')
            else:
                self.out_data_test[o].tofile(self.file_prefix+"test_"+str(o)+'.dat')

    def get_data(self):
        return self.out_data_train, self.out_data_test

    def get_data_no_label(self):
        return self.out_data_no_label

def main():
    args = get_input_arguments()
    training_mode = args.mode
    date = conf.training_date if training_mode else conf.test_date
    data_generator = DataLogParser(conf.n_timestamps, conf.D, conf.step_size,
                                    conf.ntx_max, conf.nrx_max, 
                                    conf.nsubcarrier_max, conf.data_folder,
                                    conf.log_folder,
                                    conf.skip_frames,
                                    conf.time_offset_ratio,
                                    conf.day_conf,
                                    conf.label)
    if training_mode:
        data_generator.generate_image(conf.training_date, conf.training_validate_date)
    else:
        data_generator.generate_image([], conf.test_date)
    data_generator.save_data(training_mode)

if __name__ == "__main__":
    main()
