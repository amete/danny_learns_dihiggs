#!/usr/bin/env python

import argparse
import sys
import os
from time import time

# h5py
import h5py

# keras
from keras.models import Model
from keras.layers import Input, Dense, Dropout
from keras.optimizers import SGD
from keras import regularizers
from keras import initializers
#import keras

# numpy
import numpy as np
seed = 347
np.random.seed(seed)

class Sample :

    """
    Sample

    This class will hold the feature data for a given sample.
    """

    def __init__(self, name = "", class_label = -1, input_data = None) :
        """
        Sample constructor

        Args :
            name : descriptive name of the sample (obtained from the input
                pre-processed file)
            input_data : numpy array of the data from the pre-processed file
                (expects an array of dtype = np.float64, not a structured array!)
            class_label : input class label as found in the input pre-processed
                file
        """

        if input_data.dtype != np.float64 :
            raise Exception("ERROR Sample input data must be type 'np.float64', input is '{}'".format(input_data.dtype))

        if class_label < 0 :
            raise ValueError("ERROR Sample (={})class label is not set (<0)".format(name, class_label))

        self._name = name
        self._class_label = class_label
        self._input_data = input_data

    def name(self) :
        return self._name
    def class_label(self) :
        return self._class_label
    def data(self) :
        return self._input_data
        


class DataScaler :

    """
    DataScaler

    This class will hold the scaling information needed for the training
    features (variables) contained in the input, pre-processed file.
    Its constructor takes as input the scaling data dataset object
    contained in the pre-processed file and it builds the associated
    feature-list and an associated dictionary to store the scaling
    parameters for each of the input features.
    """

    def __init__(self, scaling_dataset = None, ignore_features = []) :

        """
        ScalingData constructor

        Args:
            scaling_dataset : input HDF5 dataset object which contains the
                scaling data and feature-list
        """

        self._raw_feature_list = []
        self._feature_list = []
        self._scaling_dict = {}
        self._mean = []
        self._scale = []
        self._var = []
        self.load(scaling_dataset, ignore_features)

    def load(self, scaling_dataset = None, ignore_features = []) :

        self._raw_feature_list = list( scaling_dataset['name'] )
        self._feature_list = list( filter( lambda x : x not in ignore_features, self._raw_feature_list ) )

        #self._mean = scaling_dataset['mean']
        #self._scale = scaling_dataset['scale']
        #self._var = scaling_dataset['var']


        for x in scaling_dataset :
            name, mean, scale, var = x['name'], x['mean'], x['scale'], x['var']
            if name in ignore_features : continue
            self._scaling_dict[name] = { 'mean' : mean, 'scale' : scale, 'var' : var }
            self._mean.append(mean)
            self._scale.append(scale)
            self._var.append(var)

        self._mean = np.array(self._mean, dtype = np.float64)
        self._scale = np.array(self._scale, dtype = np.float64)
        self._var = np.array(self._var, dtype = np.float64)

    def raw_feature_list(self) :
        return self._raw_feature_list

    def feature_list(self) :
        return self._feature_list

    def scaling_dict(self) :
        return self._scaling_dict

    def get_params(self, feature = "") :
        if feature in self._scaling_dict :
            return self._scaling_dict[feature]
        raise KeyError("requested feature (={}) not found in set of scaling features".format(feature))

    def mean(self) :
        return self._mean
    def scale(self) :
        return self._scale
    def var(self) :
        return self._var

def floatify(input_array, feature_list) :
    ftype = [(name, float) for name in feature_list]
    return input_array.astype(ftype).view(float).reshape(input_array.shape + (-1,))

def load_input_file(args) :

    """
    Check that the provided input HDF5 file is of the expected form
    as defined by the pre-processing. Exits if this is not the case.
    Returns a list of the sample names found in the file.

    Args :
        args : user input to the executable
    """

    # check that the file can be found
    if not os.path.isfile(args.input) :
        print("ERROR provided input file (={}) is not found or is not a regular file".format(args.input))
        sys.exit()

    samples_group_name = "samples"
    scaling_group_name = "scaling"
    scaling_data_name = "scaling_data"

    found_samples = False
    found_scalings = False
    samples = []
    data_scaler = None
    with h5py.File(args.input, 'r', libver = 'latest') as input_file :

        # look up the scalings first, in order to build the feature list used for the Sample creation
        if scaling_group_name in input_file :
            found_scalings = True
            scaling_group = input_file[scaling_group_name]
            scaling_dataset = scaling_group[scaling_data_name]
            data_scaler = DataScaler( scaling_dataset = scaling_dataset, ignore_features = ['eventweight'] )
            print("DataScaler found {} features to train on (there were {} total features in the input)".format( len(data_scaler.feature_list()), len(data_scaler.raw_feature_list() )))
        else :
            print("scaling group (={}) not found in file".format(scaling_group_name))
            sys.exit()

        # now build the samples
        if samples_group_name in input_file :
            found_samples = True
            sample_group = input_file[samples_group_name]
            for p in sample_group :
                process_group = sample_group[p]
                class_label = process_group.attrs['training_label']
                s = Sample(name = p, class_label = int(class_label),
                    input_data = floatify( process_group['train_features'][tuple(data_scaler.feature_list())], data_scaler.feature_list() ) )
                samples.append(s)

        else :
            print("samples group (={}) not found in file".format(samples_group_name))
            sys.exit()

    return samples, data_scaler
    
def main() :

    parser = argparse.ArgumentParser(description = "Train a Keras model over you pre-processed files")
    parser.add_argument("-i", "--input",
        help = "Provide input, pre-processed HDF5 file with training, validation, and scaling data",
        required = True)
    parser.add_argument("-o", "--output", help = "Provide output filename descriptor", default = "test")
    parser.add_argument("-v", "--verbose", action = "store_true", default = False,
        help = "Be loud about it")
    args = parser.parse_args()

    training_samples, data_scaler = load_input_file(args)
    print("Pre-processed file contained {} samples: {}, {}".format(len(training_samples), [s.name() for s in training_samples], [s.class_label() for s in training_samples]))

if __name__ == "__main__" :
    main()
