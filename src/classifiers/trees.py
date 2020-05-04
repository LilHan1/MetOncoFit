#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classifier.py contains the functions necessary to train, save, and load the machine learning model.
@authors: Krishna Dev Oruganty & Scott Campit
"""
import os
import numpy as np
import joblib

def decisionTreeClassification(Xtrain, Ytrain, Xtest, Ytest):
    """

    :return:
    """
    from sklearn.ensemble


def randomForestClassification(Xtrain, Ytrain, Xtest, Ytest):
    """
    random_forest will train a random forest classifier and outputs the trained classifier, predictions, and accuracy.

    :params:
        Xtrain:          A numpy array containing the training data
        Ytrain:          A numpy array containing the training labels
        Xtest:           A numpy array containing the test data
        Ytest:           A numpy array containing the test labels

    :return:
        RFC:             A model object of the trained random forest classifier
        RFC_prediction:  A numpy array of the predicted class values from a random forest classifier
        HoldOutAccuracy: A numpy array of the mean hold-out accuracy from the random forest classifier
        CVAccuracy:      A numpy array from 10-fold cross validation.

    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score as CV

    from tqdm import tqdm

    # For reproducibility
    np.random.seed(0)

    initialTrees = 64
    totalTrees = 128
    print("Starting to train random forest model")

    pbar = tqdm(total=initialTrees)
    while(initialTrees <= totalTrees):
        RFC = RandomForestClassifier(n_estimators=initialTrees,
                                     criterion="gini",
                                     max_features="auto",
                                     bootstrap=True,
                                     oob_score=True,
                                     random_state=True)
        RFC = RFC.fit(Xtrain, Ytrain)
        initialTrees += 1
        pbar.update(1)
    pbar.close()

    RFC_prediction = RFC.predict(Xtest)
    HoldOutAccuracy = RFC.score(Xtest, Ytest)
    CVAccuracy = CV(RFC, Xtest, Ytest, cv=10).mean()
    print("Finished training random forest")
    return RFC, RFC_prediction, HoldOutAccuracy, CVAccuracy

def pickleModel(cancer, target, excluded="DE_and_CNV", mdl, savepath='./../models/'):
    """
    pickleModel saves the tumor-specific random forest model as a pickled object.

    :params:
        cancer: A string denoting the tumor name.
        target: A string denoting the target variable.
        excluded: A string denoting which target variable excluded. The default value is "DE_and_CNV".
        mdl: A model object.
        savepath: A string denoting where the models will be saved to. If there is no directory path specified and the
            directory doesn't exist, a `models` directory will be made in the parent MetOncoFit directory.

    :return:
        The pickled file containing the trained MetOncoFit model.
    """
    if not os.path.exists(savepath):
        os.makedirs(savepath)

    filename = os.path.join(savepath, (cancer + '_' + target + "_" + excluded + '.pkl'))
    return joblib.dump(mdl, filename)

def loadModel(fileName):
    """
    loadModel loads the pickled MetOncoFit model to use.

    :params:
        fileName: A string denoting the path leading to the pickled MetOncoFit model.

    :return:
        mdl:      The pickled MetOncoFit model object.
    """
    return joblib.load(fileName)
