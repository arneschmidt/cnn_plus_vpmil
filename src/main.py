from __future__ import print_function
import yaml
import os
import argparse
import numpy as np
import pandas as pd
import timeit
from vgpmil.helperfunctions import RBF
from vgpmil.vgpmil import vgpmil
from typing import Dict
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

from loading import load_dataframe, load_cnn_predictions, get_bag_level_information
from metrics import Metrics
from tsne_visualization import visualize_and_save

def initialize_models(config):
    vgpmil_model = None
    random_forest_model = None
    svm_model = None

    if config['use_models']['vgpmil'] == True:
        vgpmil_config = config['vgpmil']
        kernel = RBF(lengthscale=vgpmil_config['kernel_length_scale'], variance=vgpmil_config['kernel_variance'])
        vgpmil_model = vgpmil(kernel=kernel,
                               num_inducing=int(vgpmil_config['inducing_points']),
                               max_iter=int(vgpmil_config['iterations']),
                               normalize=bool(vgpmil_config['normalize']),
                               verbose=bool(vgpmil_config['verbose']))
    if config['use_models']['random_forest'] == True:
        random_forest_model = RandomForestClassifier()
    if config['use_models']['svm'] == True:
        svm_model = SVC()

    return vgpmil_model, random_forest_model, svm_model

def train(config: Dict, vgpmil_model: vgpmil = None, rf_model: RandomForestClassifier = None, svm_model: SVC = None):
    print('Training..')
    train_df = pd.read_csv(config['path_train_df'])
    print('Loaded training dataframe. Number of instances: ' + str(len(train_df)))
    features, bag_labels_per_instance, bag_names_per_instance, instance_labels = load_dataframe(train_df, config)
    bag_features, bag_labels, bag_names = get_bag_level_information(features, bag_labels_per_instance, bag_names_per_instance)

    if config['tsne']['visualize']:
        visualize_and_save(features=features, instance_labels=instance_labels, config=config)

    if vgpmil_model is not None:
        print('Train VGPMIL')
        vgpmil_model.train(features, bag_labels_per_instance, bag_names_per_instance, Z=None, pi=None, mask=None)
    if rf_model is not None:
        print('Train Random Forest')
        rf_model.fit(X=bag_features, y=np.ravel(bag_labels))
    if svm_model is not None:
        print('Train SVM')
        svm_model.fit(X=bag_features, y=np.ravel(bag_labels))

def test(config: Dict, vgpmil_model: vgpmil = None, rf_model: RandomForestClassifier = None, svm_model: SVC = None):
    print('Testing..')
    test_df = pd.read_csv(config['path_test_df'])
    print('Loaded test dataframe. Number of instances: ' + str(len(test_df)))
    features, bag_labels_per_instance, bag_names_per_instance, instance_labels = load_dataframe(test_df, config)
    bag_features, bag_labels, bag_names = get_bag_level_information(features, bag_labels_per_instance, bag_names_per_instance)

    metrics_calculator = Metrics(instance_labels, bag_labels, bag_names, bag_names_per_instance)

    if vgpmil_model is not None:
        print('Test VGPMIL')
        start = timeit.timeit()
        instance_predictions, bag_predictions = vgpmil_model.predict(features, bag_names_per_instance, bag_names)
        end = timeit.timeit()
        print('Average runtime per bag: ', str((end - start) / bag_predictions.size))
        metrics_calculator.calc_metrics(instance_predictions, bag_predictions, 'vgpmil')
    if rf_model is not None:
        print('Test Random Forest')
        bag_predictions = rf_model.predict(bag_features)
        metrics_calculator.calc_metrics(np.array([]), bag_predictions, 'random_forest')
    if svm_model is not None:
        print('Test SVM')
        bag_predictions = svm_model.predict(bag_features)
        metrics_calculator.calc_metrics(np.array([]), bag_predictions, 'svm')
    if config['use_models']['cnn'] == True:
        cnn_predictions, bag_cnn_predictions, bag_cnn_probability = load_cnn_predictions(test_df, config)
        metrics_calculator.calc_metrics(cnn_predictions, bag_cnn_probability, 'cnn')

    metrics_calculator.write_to_file(config)

def main():
    parser = argparse.ArgumentParser(description="Cancer Classification")
    parser.add_argument("--config", "-c", type=str, default="./config.yaml",
                        help="Config path (yaml file expected) to default config.")
    args = parser.parse_args()
    with open(args.config) as file:
        config = yaml.full_load(file)
    vgpmil_model, random_forest_model, svm_model = initialize_models(config)
    train(config, vgpmil_model, random_forest_model, svm_model)
    test(config, vgpmil_model, random_forest_model, svm_model)




if __name__ == "__main__":
    main()
