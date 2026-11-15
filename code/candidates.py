"""The models on the leaderboard, all behind one small interface.

A candidate is fitted on a list of features.Sample rows and then
asked about more of them. Nothing else is shared, so a candidate can
be one number (persistence), a ratio (CAMS rescaled), a linear fit
(ridge), a look-up of similar days (analogs) or a forest of trees,
and code/lab.py scores them all the same way, on the same days.

There are two families, and they are kept apart on purpose.

  standard library   baselines, CAMS rescaled, ridge, ridge with
                     smoke terms, analogs. Any of these could ship,
                     because the daily job runs them with nothing
                     installed.
  scikit-learn       random forest, gradient boosting, a small
                     neural network. Benchmarks. They answer whether
                     a non-linear model would buy anything on this
                     much data. One that clearly won would be a
                     reason to change the pipeline's dependencies on
                     purpose, not something to slip in.

scikit-learn is imported inside fit(), never at the top of the file,
so importing this module costs nothing and works without it.
"""

import math
import warnings
from statistics import median

import evaluate
from model import _standardise

# The two burning-season terms the week 7 comparison liked best.
SMOKE = ("burn_fire", "burn_wind_u")


class Fitted:
    """A fitted candidate. predict() takes one Sample."""

    def __init__(self, one, many=None):
        self._one = one
        self._many = many

    def predict(self, sample):
        return self._one(sample)

    def predict_many(self, samples):
        if self._many:
            return self._many(samples)
        return [self._one(s) for s in samples]


class Candidate:
    key = ""
    label = ""
    kind = ""          # baseline, linear, analog, tree, neural, ensemble
    about = ""         # one plain sentence for the page
    extra = ()         # interaction terms on top of the plain inputs
    sklearn = False    # needs scikit-learn to fit
    shippable = False  # the daily job could run it as things stand
    # Days between refits in the lab's walk-forward. Anything that
    # could ship is tested the way the daily job would run it, which
    # is a fresh fit every morning.
    refit_every = 1

    def fit(self, train):
        raise NotImplementedError

    def describe(self):
        return {"key": self.key, "label": self.label, "kind": self.kind,
                "about": self.about, "sklearn": self.sklearn,
                "shippable": self.shippable}


# --- baselines ---------------------------------------------------

class Persistence(Candidate):
    key, label, kind = "persistence", "Persistence", "baseline"
    about = "Tomorrow repeats the newest reading the forecast has."

    def fit(self, train):
        return Fitted(lambda s: s.persistence_op)


class Climatology(Candidate):
    key, label, kind = "climatology", "Climatology", "baseline"
    about = "The station's average over every earlier day."

    def fit(self, train):
        mean = sum(s.y for s in train) / len(train)
        return Fitted(lambda s: mean)


class RawCams(Candidate):
    key, label, kind = "raw_cams", "Raw CAMS", "baseline"
    about = "The global forecast as published, uncorrected."

    def fit(self, train):
        return Fitted(lambda s: s.raw.get("cams"))


# --- standard library models ------------------------------------

class CamsRescale(Candidate):
    """CAMS, times how far off it has been here lately.

    The simplest correction there is, and the one a forecaster with
    a spreadsheet would try first. A median rather than a mean, so
    one smoky day does not set the ratio for a month.
    """

    key, label, kind = "cams_rescale", "CAMS rescaled", "linear"
    about = "CAMS times its recent ratio to the station (last 30 days)."
    shippable = True
    WINDOW = 30

    def fit(self, train):
        ratios = [s.y / s.raw["cams"] for s in train[-self.WINDOW:]
                  if s.raw.get("cams")]
        ratio = median(ratios)
        return Fitted(lambda s: s.raw["cams"] * ratio)


class RidgeModel(Candidate):
    """evaluate.fit, exactly as the daily job runs it."""

    key, label, kind = "ridge", "Ridge regression", "linear"
    about = "The shipped model: a penalised linear fit in log space."
    shippable = True

    def __init__(self, key=None, label=None, about=None, extra=()):
        self.key = key or self.key
        self.label = label or self.label
        self.about = about or self.about
        self.extra = tuple(extra)

    def fit(self, train):
        model = evaluate.fit(train)
        return Fitted(lambda s: model.predict_one(s.x))


def nearest(train, target, k):
    """The k training rows closest to `target`, closest first.

    Distance is Euclidean on the standardised inputs, the same
    scaling the ridge fit uses, so a degree of temperature and a
    doubling of the fire count are put on comparable footing.
    Returns [(distance, sample)].
    """
    means, devs = _standardise([s.x for s in train])
    width = len(means)

    def z(x):
        return [(x[j] - means[j]) / devs[j] for j in range(width)]

    goal = z(target.x)
    scored = []
    for s in train:
        row = z(s.x)
        d = math.sqrt(sum((a - b) ** 2 for a, b in zip(row, goal)))
        scored.append((d, s))
    scored.sort(key=lambda t: (t[0], t[1].day))
    return scored[:k]


class Analogs(Candidate):
    """Find the past days that looked most like tomorrow.

    Forecasters call these analogs. The prediction is the average,
    in log space, of what the station measured on the k closest
    days. k is chosen inside each fit on the most recent fifth of
    the training rows, the same way ridge chooses its penalty.
    """

    key, label, kind = "analogs", "Analog days", "analog"
    about = "Averages the most similar past days on the same inputs."
    shippable = True
    K_GRID = (5, 10, 20)
    K_EVERY = 7   # days a chosen k is kept before it is chosen again

    def __init__(self):
        self._k, self._k_day = None, None

    def fit(self, train):
        # Choosing k compares every recent row with every older one,
        # which is most of the cost of a fit. The fit itself is
        # redone daily; k is re-chosen weekly, and from scratch
        # whenever the training window moves backwards, as it does at
        # the start of each walk.
        newest = train[-1].day
        held = None if self._k_day is None else (newest - self._k_day).days
        if self._k is None or held is None or not 0 <= held < self.K_EVERY:
            self._k, self._k_day = self._choose_k(train), newest
        k = self._k
        means, devs = _standardise([s.x for s in train])
        width = len(means)
        points = [([(s.x[j] - means[j]) / devs[j] for j in range(width)],
                   math.log1p(s.y)) for s in train]

        def one(sample):
            goal = [(sample.x[j] - means[j]) / devs[j] for j in range(width)]
            dist = sorted((sum((a - b) ** 2 for a, b in zip(p, goal)), v)
                          for p, v in points)
            near = [v for _, v in dist[:k]]
            return math.expm1(sum(near) / len(near))

        fitted = Fitted(one)
        fitted.k = k
        return fitted

    def _choose_k(self, train):
        cut = int(len(train) * 0.8)
        if cut < 20 or len(train) - cut < 5:
            return 10
        head, tail = train[:cut], train[cut:]
        means, devs = _standardise([s.x for s in head])
        width = len(means)
        base = [[(s.x[j] - means[j]) / devs[j] for j in range(width)]
                for s in head]
        logs = [math.log1p(s.y) for s in head]
        errors = {k: 0.0 for k in self.K_GRID}
        for s in tail:
            goal = [(s.x[j] - means[j]) / devs[j] for j in range(width)]
            order = sorted(range(len(base)), key=lambda i: sum(
                (a - b) ** 2 for a, b in zip(base[i], goal)))
            for k in self.K_GRID:
                near = [logs[i] for i in order[:k]]
                errors[k] += abs(math.expm1(sum(near) / len(near)) - s.y)
        return min(self.K_GRID, key=lambda k: (errors[k], k))


# --- scikit-learn benchmarks -------------------------------------

class SklearnModel(Candidate):
    """A scikit-learn regressor fitted on log1p(PM2.5).

    Refitted weekly in the lab. A forest refitted every day of a
    walk-forward takes several minutes on its own, and these are
    benchmarks, not candidates to ship.
    """

    sklearn = True
    refit_every = 7

    def make(self):
        raise NotImplementedError

    def fit(self, train):
        import numpy as np

        x = np.array([s.x for s in train], dtype=float)
        y = np.log1p(np.array([s.y for s in train], dtype=float))
        model = self.make()
        with warnings.catch_warnings():
            # The network warns when lbfgs stops at its iteration cap.
            # On five hundred rows that is the cap doing its job.
            warnings.simplefilter("ignore")
            model.fit(x, y)

        def many(samples):
            if not samples:
                return []
            got = model.predict(np.array([s.x for s in samples], dtype=float))
            return [max(float(np.expm1(v)), 0.0) for v in got]

        return Fitted(lambda s: many([s])[0], many)


class RandomForest(SklearnModel):
    key, label, kind = "random_forest", "Random forest", "tree"
    about = "Two hundred decision trees, averaged."

    def make(self):
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(n_estimators=200, min_samples_leaf=3,
                                     max_features=0.5, random_state=0,
                                     n_jobs=-1)


class GradientBoosting(SklearnModel):
    key, label, kind = "gradient_boosting", "Gradient boosting", "tree"
    about = "Small trees fitted one after another, each on what is left."

    def make(self):
        from sklearn.ensemble import HistGradientBoostingRegressor
        return HistGradientBoostingRegressor(
            max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
            min_samples_leaf=10, l2_regularization=1.0, random_state=0)


class NeuralNet(SklearnModel):
    key, label, kind = "neural_net", "Neural network", "neural"
    about = "One hidden layer of sixteen units, heavily regularised."

    def make(self):
        from sklearn.compose import TransformedTargetRegressor
        from sklearn.neural_network import MLPRegressor
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        net = MLPRegressor(hidden_layer_sizes=(16,), alpha=3.0,
                           solver="lbfgs", max_iter=1000, random_state=0)
        return TransformedTargetRegressor(
            regressor=make_pipeline(StandardScaler(), net),
            transformer=StandardScaler())


# --- the line-up -------------------------------------------------

class Ensemble(Candidate):
    """The average of other candidates, taken in log space.

    Not fitted itself. code/lab.py builds it from its members'
    predictions on the days all of them have one.
    """

    key, label, kind = "ensemble", "Ensemble", "ensemble"
    about = "The average of ridge, analogs, forest, boosting and network."
    members = ("ridge", "analogs", "random_forest", "gradient_boosting",
               "neural_net")
    sklearn = True

    def fit(self, train):
        raise TypeError("the ensemble is combined, not fitted")

    @staticmethod
    def combine(values):
        logs = [math.log1p(v) for v in values]
        return math.expm1(sum(logs) / len(logs))


def lineup(shipped_extra=()):
    """Every candidate, baselines first, the shipped model marked.

    `shipped_extra` is the interaction set the daily job fits with,
    so the leaderboard's ridge is always the model that is actually
    shipping. The smoke variant is left out if that is what ships.
    """
    ridge = RidgeModel(label="Ridge regression (shipped)",
                       extra=shipped_extra)
    out = [Persistence(), Climatology(), RawCams(), CamsRescale(), ridge]
    if tuple(shipped_extra) != SMOKE:
        out.append(RidgeModel(
            key="ridge_smoke", label="Ridge + smoke terms", extra=SMOKE,
            about="Ridge, letting fires and the westerly count for more "
                  "in burning season."))
    out += [Analogs(), RandomForest(), GradientBoosting(), NeuralNet(),
            Ensemble()]
    return out


def sklearn_available():
    try:
        import sklearn  # noqa: F401
    except ImportError:
        return False
    return True
