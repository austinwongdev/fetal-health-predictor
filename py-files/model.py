"""
Austin Wong
001355444
2/22/2021
"""

# IMPORTS
# Data Analysis Imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Machine Learning Imports
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, plot_confusion_matrix

# General and File Management Imports
import os
from pathlib import Path
from joblib import dump, load
import datetime

# Database Imports
from sqlite3 import Error
from dbinter import get_conn


# CLASSES
class Model:
    """
    Model class for access to Machine Learning model, underlying data, and new data to be inserted
    """
    fetal_data = None
    current_patient = None
    model = None


# Getters and Setters
def set_current_patient(data):
    """
    Saves patient data to variable for later access, such as autopopulating fields and inserting data into database
    :param data: Dictionary with keys representing health attributes. Example:
        {'baseline_value':120,
        'accelerations':0,
        'fetal_movement':0,
        'uterine_contractions':0,
        'light_decelerations':0,
        'severe_decelerations':0,
        'prolongued_decelerations':0,
        'abnormal_short_term_variability':73,
        'mean_value_of_short_term_variability':0.5,
        'percentage_of_time_with_abnormal_long_term_variability':43,
        'mean_value_of_long_term_variability':2.4,
        'histogram_width':64,
        'histogram_min':62,
        'histogram_max':126,
        'histogram_number_of_peaks':2,
        'histogram_number_of_zeroes':0,
        'histogram_mode':120,
        'histogram_mean':137,
        'histogram_median':121,
        'histogram_variance':73,
        'histogram_tendency':1}
    :return: None
    """
    Model.current_patient = data


def get_current_patient():
    """
    :return: Dictionary with current patient data
    """
    return Model.current_patient


def load_fetal_data(conn):
    """
    Loads all fetal health data from fetal_health table in SQLite DB
    :param conn: connection to SQLite DB
    :return: None
    """
    fetal_data = pd.read_sql("SELECT * from fetal_health", conn)
    fetal_data.drop(columns=['id'], inplace=True)
    Model.fetal_data = fetal_data


def get_fetal_data():
    """
    :return: Pandas DataFrame with all loaded fetal health data
    """
    return Model.fetal_data


def load_model():
    """
    Loads current machine learning model for predicting fetal health status from .joblib file
    :return: None
    """
    filename = 'new_model'
    dirname = Path(__file__).parent.absolute()
    suffix = ".joblib"
    filepath = Path(dirname, filename).with_suffix(suffix)
    if os.path.exists(filepath):
        Model.model = load(filename=filepath)


def get_model():
    """
    :return: Current machine learning model used for predicting fetal health status
    """
    return Model.model


# Functions
def split_data():
    """
    Prepares pre-loaded data for training and evaluating models
    :return: X_train, X_test, y_train, y_test
    Lists of datasets split into features (X) and labels (y) with 80% train data and 20% test data.
    """
    df = get_fetal_data()
    X = df.drop("fetal_health", axis=1)
    y = df["fetal_health"]
    random_state = 42
    np.random.seed(42)

    return train_test_split(X,
                            y,
                            test_size=0.2,
                            random_state=random_state)


def tune_hyperparameters():
    """
    Sets up a hyperparameter grid search for RandomForestClassifier using optimal settings from previous experimentation
    :return: GridSearchCV estimators
    """

    rf_grid = {"n_estimators": np.arange(460, 910, 50),
               "max_depth": [None],
               "min_samples_split": [2, 8, 14],
               "min_samples_leaf": [1]}

    gs_rf = GridSearchCV(RandomForestClassifier(),
                         param_grid=rf_grid,
                         cv=5,
                         scoring='f1_macro',
                         verbose=True)

    return gs_rf


def train_model():
    """
    Trains two RandomForest models and compares their macro avg F1-scores to determine the model with best performance
    :return: estimator with highest macro avg F1-score
    """

    # Split Data
    X_train, X_test, y_train, y_test = split_data()

    # Train and Evaluate tuned model
    gs_rf = tune_hyperparameters()
    gs_rf.fit(X_train, y_train)
    hyper_scores = evaluate_model(gs_rf, X_test, y_test)

    # Evaluate base model
    rf = RandomForestClassifier()
    rf.fit(X_train, y_train)
    base_scores = evaluate_model(rf, X_test, y_test)

    # Prevent previous graphs and figures from displaying before displaying confusion matrix
    plt.close('all')

    # Compare base model to tuned model, then prepare confusion matrix for display and return best model with report
    if base_scores['macro avg']['f1-score'] >= hyper_scores['macro avg']['f1-score']:
        plot_confusion_matrix(rf, X_test, y_test, display_labels=['Normal', 'Suspect', 'Pathologic'])
        return rf, base_scores
    else:
        plot_confusion_matrix(gs_rf, X_test, y_test, display_labels=['Normal', 'Suspect', 'Pathologic'])
        return gs_rf, hyper_scores


def evaluate_model(model, X_test, y_test):
    """
    Makes predictions on test data then evaluates the model's predictions
    :param model: Estimator
    :param X_test: List of features to use for evaluation
    :param y_test: List of labels to use for evaluation
    :return: Dictionary with classification report full of various metrics
    """
    y_preds = model.predict(X_test)
    return classification_report(y_test, y_preds, target_names=['Normal', 'Suspect', 'Pathologic'], output_dict=True)


def save_model(model):
    """
    Saves machine learning model to file, overwriting previous file
    :param model: Estimator
    :return: None
    """

    # Create filepath
    dirname = Path(__file__).parent.absolute()
    filename = "new_model"
    suffix = ".joblib"
    filepath = Path(dirname, filename).with_suffix(suffix)

    # Save model to disk
    dump(model, filepath)

    # Update reference to model in Model object
    Model.model = model


def insert_fetal_data(placeholder):
    """
    Inserts current patient data into fetal health database
    :param placeholder: List with ordered values for fetal health attributes and fetal health status
    :return: 1 if successful, 0 if unsuccessful
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()
        insert_query = "INSERT INTO fetal_health (baseline_value, accelerations, fetal_movement, uterine_contractions,\
                        light_decelerations, severe_decelerations, prolongued_decelerations, " \
                       "abnormal_short_term_variability, mean_value_of_short_term_variability, " \
                       "percentage_of_time_with_abnormal_long_term_variability, mean_value_of_long_term_variability, " \
                       "histogram_width, histogram_min, histogram_max, histogram_number_of_peaks, " \
                       "histogram_number_of_zeroes, histogram_mode, histogram_mean, histogram_median, " \
                       "histogram_variance, histogram_tendency, fetal_health) " \
                       "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

        cursor.execute(insert_query, placeholder)
        conn.commit()
        return 1
    except Error as error:

        dirname = Path(__file__).parent.absolute()
        error_filepath = Path(dirname, 'error_log').with_suffix('.txt')
        f = open(error_filepath, 'a')
        f.write('{} - {}\n'.format(datetime.datetime.now(), error))
        f.close()
        return 0
