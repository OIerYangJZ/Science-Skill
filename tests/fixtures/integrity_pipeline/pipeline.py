"""Planted: preprocessing fitted in one function, split in another (L1); model chosen by its test score (L2);
two arms with different seed lists (R3)."""
from sklearn.decomposition import PCA
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import MinMaxScaler

SEEDS_A = [1, 2, 3]
SEEDS_B = [7, 8, 9]


def preprocess(features):
    scaled = MinMaxScaler().fit_transform(features)
    return PCA(n_components=10).fit_transform(scaled)


def preprocess_train_only(X_train, X_other):
    scaler = MinMaxScaler().fit(X_train)            # control: fitted on training data only
    return scaler.transform(X_train), scaler.transform(X_other)


def pick_k(features, labels, seed):
    X_tr, X_test, y_tr, y_test = train_test_split(features, labels, random_state=seed)
    best_k, best_acc = None, -1.0
    for k in (1, 3, 5, 7):
        acc = accuracy_score(y_test, KNeighborsClassifier(k).fit(X_tr, y_tr).predict(X_test))
        if acc > best_acc:
            best_k, best_acc = k, acc
    return best_k, best_acc
