"""
validator.py contains several functions that assesses and reports model performance.

@authors: Krishna Oruganty & Scott Campit
"""

from sklearn import preprocessing
from sklearn.externals import joblib
from scipy import stats
import scipy

import pandas as pd
import numpy as np
np.seterr(divide='ignore', invalid='ignore')

import DataPreparation
import Classifier

def computeConfusionMatrix(filename, target, exclude, iterations=1000):
    """
    computeConfusionMatrix generates the raw confusion matrix and normalized confusion matrix using the test data and
    the predicted data.

    :params:
        filename:   The path to the .csv file containing the rows as observations and the columns as features.
        target:     A string denoting the target variable of interest.
        exclude:    A string denoting which features to keep in the dataset.
        iterations: An integer denoting the number of times to compute the confusion matrix.

    :return:
        matrix:           A numpy array containing the non-normalized confusion matrix after i iterations.
        normalizedMatrix: A numpy array containing the normalized confusion matrix after i iterations.

    """
    from sklearn.metrics import confusion_matrix
    np.set_printoptions(precision=2)

    count = 0
    while (count <= iterations):
        Xtrain, Xtest, Ytrain, Ytest = DataPreparation.processDataFromFile(filename, target, exclude)
        _, Ypred, _, _ = Classifier.random_forest(Xtrain, Ytrain, Xtest, Ytest)
        if count is 0:
            matrix = confusion_matrix(Ytest, Ypred)
        elif count > 1:
            matrix = np.add(matrix, confusion_matrix(Ytest, Ypred))
        count += 1
    normalizedMatrix = matrix.astype('float') / matrix.sum(axis=1)[:, np.newaxis]

    return matrix, normalizedMatrix

def Summarize(filename, target, exclude, iterations=1000):
    """
    Summarize outputs several statistical metrics used to evaluate the MetOncoFit model.

    :params:
        filename:   The path to the .csv file containing the rows as observations and the columns as features.
        target:     A string denoting the target variable of interest.
        exclude:    A string denoting which features to keep in the dataset.
        iterations: An integer denoting the number of times to compute the summary statistics.

    :return:
        Summary: A pandas dataframe that stores several statistical values, including:
            CV:        10-fold cross validation score
            Accuracy:  Out-of-bag accuracy
            Mean:      Mean of the out-of-bag accuracy values
            Sigma:     The standard deviation of the out-of-bag accuracy values
            Kappa:     Cohen's kappa coefficient
            F1:        F1 score or harmonic average of the precision and recall
            Precision: The average precision score across all classes
            Recall:    The average recall score across all classes
            UPREG/GAIN Precision, DOWNREG/LOSS Precision: The precision score for the
                upregulated/gain and downregulated/loss class.
            UPREG/GAIN Recall, DOWNREG/LOSS Recall: The recall score for the
                upregulated/gain and downregulated/loss class
            T-score: the T-score of accuracy
            P-value: the P-value of accuracy using a Two-Tailed T-test
    """
    from random import shuffle
    from sklearn.metrics import f1_score, classification_report, \
        matthews_corrcoef, cohen_kappa_score as coh_kap

    if target is "CNV":
        labels = ["GAIN", "NEUT", "LOSS"]
    else:
        labels = ["UPREG", "NEUTRAL", "DOWNREG"]
    cancer = filename.split('.')[0]

    Summary = pd.DataFrame(columns=['CV', 'Accuracy', 'Sigma', 'Mean', 'Kappa', 'F1', 'MCC'
                                            'Precision', 'Recall', 'UPREG/GAIN Precision',
                                            'DOWNREG/LOSS Precision', 'UPREG/GAIN Recall',
                                            'DOWNREG/LOSS Recall', 'T-score', 'P-value'])
    count = 0
    while(count <= iterations):
        Xtrain, Xtest, Ytrain, Ytest = DataPreparation.processDataFromFile(filename, target, exclude)
        _, Ypred, OOBAccuracy, CVAccuracy = Classifier.random_forest(Xtrain, Ytrain, Xtest, Ytest)

        report = classification_report(Ytest, Ypred, output_dict=True)
        report = pd.DataFrame.from_dict(report).round(2)

        Summary[count, 'Accuracy'] = OOBAccuracy
        Summary[count, 'CV'] = CVAccuracy
        Summary[count, 'Kappa'] = coh_kap(Ytest, Ypred)
        Summary[count, 'F1'] = f1_score(Ytest, Ypred, average='micro')
        Summary[count, 'MCC'] = matthews_corrcoef(Ytest, Ypred)

        Summary[count, 'Precision'] = report.loc[['precision'], ['micro avg']].values[0])
        Summary[count, 'UPREG/GAIN Precision'] = report.loc[['precision'], [labels[0]]].values[0]
        Summary[count, 'DOWNREG/LOSS Precision'] = report.loc[['precision'], [labels[2]]].values[0]

        Summary[count, 'Recall'] = report.loc[['recall'], ['micro avg']].values[0]
        Summary[count, 'UPREG/GAIN Recall'] = report.loc[['recall'], [labels[0]]].values[0]
        Summary[count, 'DOWNREG/LOSS Recall'] = report.loc[['recall'], [labels[2]]].values[0]

        count += 1

    sigma = Summary['Accuracy'].std(axis=1)
    mu = Summary['Accuracy'].mean(axis=1)
    tscore, pvalue = scipy.stats.ttest_1samp(Summary['Accuracy'], mu)
    if pvalue < 1E-50:
        pvalue = 1E-50

    Summary = Summary.mean(axis=1)
    Summary['T-score'] = tscore
    Summary['P-Value'] = pvalue
    Summary['Sigma'] = sigma
    Summary['Mean'] = mu
    Summary['Cancer'] = cancer

    return Summary


def PearsonCorrelation(diffExpDFs, target):
    """
    PearsonCorrelation returns a dictionary of pearson correlation coefficients that correspond to the features in
    the up / neutral / down dataframes stored in the diffExpDFs dictionary.

    :params:
        diffExpDFs: A dictionary containing pandas dataframes that correspond to unique target labels.
        target:     A pandas series containing the labels corresponding to a specific target variable.

    :return:
        pearsonCorrelationDict: A dictionary corresponding to particular features and pearson correlation coefficients.

    """
    from scipy.stats import pearsonr

    pearsonCorrelationDict = dict()
    for df in diffExpDFs:
        count = 0
        corr = dict()
        median = dict()

        df = df.pop(target)
        for col in df.columns:
            median = df[col].median()
            gradient = [1.0, 0.0, -1.0]
            correlation = pearsonr(median, gradient)

            if np.isnan(correlation) != True:
                corr[col] = correlation
            else:
                corr[col] = 0.0

        pearsonCorrelationDict[count] = corr
        count += 1

    return pearsonCorrelationDict


def computeAUROC(filename, target, exclude):
    """
    Calculates the score for the Area Under the Receiver Operating Characteristic Curve
    from the MetOncoFit models.

    :params:
        filename:   The path to the .csv file containing the rows as observations and the columns as features.
        target:     A string denoting the target variable of interest.
        exclude:    A string denoting which features to keep in the dataset.

    OUTPUTS:
        AUROC: A pandas dataframe containing the AUROC curve with respect to each class.
    """
    from sklearn.preprocessing import label_binarize
    from sklearn.metrics import roc_curve, auc

    if targ is "CNV":
        labels = {"GAIN", "NEUT", "LOSS"}
    else:
        labels = {"UPREG", "NEUTRAL", "DOWNREG"}

    # Pop out the classification labels & binarize the array. This is necessary for calculating the auroc using sklearn.
    model, cancer = DataPreparation.load_data(filename)
    label_encoded_model = DataPreparation.label_encode(model)
    prune_models, cls = DataPreparation.prune_targets(label_encoded_model, target, exclude)
    cls = label_binarize(
        cls, classes=[labels[0], labels[1], labels[2]]
    )
    robust_model = DataPreparation.robust_scaler(prune_models)
    Xtrain, Xtest, Ytrain, Ytest = DataPreparation.randomOversampling(robust_model, cls, testSize=0.2)
    _, Ypred, OOBAccuracy, CVAccuracy = Classifier.random_forest(Xtrain, Ytrain, Xtest, Ytest)

    FPR, TPR, _ = roc_curve(Ytest.ravel(), Ypred.ravel())
    auroc = auc(FPR, TPR)
    data = {"Cancer": [cancer],
            "Target": [target],
            "AUROC": [auroc]}
    AUROC = pd.DataFrame.from_dict(data)
    return AUROC


def leave_one_feat_out(filename, target, exclude):
    """
    Leave one feature out reports the accuracy obtained from removing the following features:

    1. Topological features only
    2. Dynamic features only
    3. Expression only
    4. Expression and kcat
    5. RECON1 subsystem
    """

    # create 4 dataframes that will be used for each of the features after robust scaler
    model, cancer = DataPreparation.load_data(filename)
    label_encoded_model = DataPreparation.label_encode(model)
    prune_models, classes = DataPreparation.prune_targets(label_encoded_model, target, exclude)
    prune_models = prune_models.drop(columns=['Genes', 'Cell Line'])
    robust_model = DataPreparation.robust_scaler(prune_models)
    df = pd.DataFrame(robust_model,
                      columns=model.columns,
                      index=model.index)

dynm = df.drop(df.columns[0:52], axis=1)
    topo = df.drop(df.columns[53:132], axis=1)
    kexp = df.drop(df.columns[132:], axis=1)
    genexp = df.drop(df.columns[133:], axis=1)
    subsys = df.drop(df.columns[134], axis=1)

    # concatenate the dataframes to a single structure and get accuracies
    dfs = [topo, dynm, kexp, genexp, subsys]

    output = []
    for df in dfs:
        if df is topo:
            lofo = "Toplogical Features"
        elif df is dynm:
            lofo = "Dynamic Features"
        elif df is kexp:
            lofo = "Gene expression and kcat"
        elif df is genexp:
            lofo = "Gene expression only"
        elif df is subsys:
            lofo = "RECON1 Subsystem only"
        else:
            return("ERROR: Not suitable df input")

        new_data, orig_data, new_classes, orig_classes = train_test_split(
            df, classes, test_size=0.3)

        feat = (new_data.shape[1]-10)
        while(feat < new_data.shape[1]-1):
            trees = 5
            while(trees <= 500):
                rfc = RandomForestClassifier(
                    n_estimators=trees, max_features=feat)
                rfc.fit(new_data, new_classes)
                trees = trees + 1500
            feat = feat + 20
            rfc_pred = rfc.predict(orig_data)
            mean_acc = rfc.score(orig_data, orig_classes)
            output.append([canc, targ, lofo, mean_acc])

    # Return data frame to be saved
    lofo_df = pd.DataFrame(output, columns=[
                           "Cancer", "Target",
                            "Held-out feature set",
                            "Mean class accuracy"])
    return lofo_df


def leave_one_cell_out(df2, canc, targ):
    """
    Leave one cell out outputs the mean accuracy obtained after holding out a single NCI-60 cancer cell line from the dataset.

    """

    # Split the index into Gene symbol and Cell Line
    df2 = df2.reset_index()
    _ = df2.pop('Genes')  # don't need gene labels
    cell_line = df2.pop("Cell Line")
    cell_line = pd.DataFrame(cell_line)

    # Temporarily remove the classes to do robust scaling
    classes = df2.pop(targ)
    classes = pd.DataFrame(classes, index=df2.index)

    # Robust scaling (since this is not done in the process script)
    num = RobustScaler().fit_transform(np.array(df2).astype(np.float))
    df2 = pd.DataFrame(num, columns=df2.columns, index=df2.index)

    # Unite the datasets together again
    df2 = pd.concat([cell_line, df2, classes], axis=1)
    groups = df2["Cell Line"].unique()

    # Leave one cell line out
    output = []
    for cell in groups:
        new_df = df2[~df2["Cell Line"].str.contains(str(cell))]

        # This time pop out for sure
        classes = new_df.pop(targ)
        _ = new_df.pop("Cell Line")

        # Train test and split as usual
        new_data, orig_data, new_classes, orig_classes = train_test_split(
            new_df, classes, test_size=0.3)

        # Now we can do random oversampling
        ros = RandomOverSampler()
        data, classes = ros.fit_sample(new_data, new_classes)

        feat = (data.shape[1]-10)
        while(feat < data.shape[1]-1):
            trees = 5
            while(trees <= 500):
                rfc = RandomForestClassifier(
                    n_estimators=trees, max_features=feat)
                rfc.fit(data, classes)
                trees = trees + 1500
            feat = feat + 20
            rfc_pred = rfc.predict(orig_data)
            mean_acc = rfc.score(orig_data, orig_classes)
            output.append([canc, targ, cell, mean_acc])

    # Return data frame to be saved
    loco = pd.DataFrame(output, columns=[
                        "Cancer", "Target", "Held-out cell line", "Mean class accuracy"])
    return loco


def hr_check(freq, cv_score):
    """
    """
    freq["10-fold CV Accuracy"] = cv_score
    return freq
