"""Ridge regression, written out by hand.

Using scikit-learn here would be two lines instead of eighty, but
the daily job that has to keep running unattended until November
would then inherit numpy, scipy and a compiled BLAS. The ingest is
standard-library on purpose; the model is small enough to keep it
that way, so nothing in the critical path can break on a
dependency upgrade.

The fit is ordinary least squares with an L2 penalty, solved
through the normal equations. With a handful of features and fewer
than a thousand rows that is fast and, more importantly, exactly
reproducible from the numbers stored in data/model.json.
"""

import json
import math

# Features live on very different scales (log-PM around 4, sines
# between -1 and 1), and an L2 penalty is not scale invariant, so
# without standardising, the penalty would fall almost entirely on
# whichever column happened to be small.
_EPS = 1e-12


def _standardise(matrix):
    """Column means and standard deviations."""
    n, width = len(matrix), len(matrix[0])
    means = [sum(row[j] for row in matrix) / n for j in range(width)]
    devs = []
    for j in range(width):
        var = sum((row[j] - means[j]) ** 2 for row in matrix) / n
        devs.append(math.sqrt(var) or 1.0)  # constant column: leave as is
    return means, devs


def _solve(a, b):
    """Gaussian elimination with partial pivoting for a @ x = b."""
    n = len(a)
    aug = [list(a[i]) + [b[i]] for i in range(n)]

    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < _EPS:
            raise ValueError(f"singular system at column {col}")
        aug[col], aug[pivot] = aug[pivot], aug[col]

        for row in range(col + 1, n):
            factor = aug[row][col] / aug[col][col]
            if factor:
                for k in range(col, n + 1):
                    aug[row][k] -= factor * aug[col][k]

    out = [0.0] * n
    for row in range(n - 1, -1, -1):
        total = aug[row][n] - sum(aug[row][k] * out[k]
                                  for k in range(row + 1, n))
        out[row] = total / aug[row][row]
    return out


class Ridge:
    """Least squares with an L2 penalty on the standardised inputs.

    With `log_target` the fit happens on log1p(y) and predictions
    are mapped back with expm1. PM2.5 is roughly log-normal -- a
    clean day sits near 15 and a burning-season day near 200 -- so
    on the raw scale a single bad November day would dominate the
    squared error and drag the whole fit towards it. Working in
    logs makes the penalty proportional rather than absolute,
    which is also how the error is actually felt: being 10 out on
    a reading of 20 matters, being 10 out on 200 does not.
    """

    def __init__(self, alpha=1.0, names=None, log_target=False):
        self.alpha = alpha
        self.names = names or []
        self.log_target = log_target
        self.coef = []
        self.intercept = 0.0
        self.means = []
        self.devs = []
        self.residual_sd = None  # spread of the fit residuals

    def fit(self, x, y):
        if not x:
            raise ValueError("nothing to fit")
        if len(x) != len(y):
            raise ValueError("x and y disagree on length")

        if self.log_target:
            y = [math.log1p(max(v, 0.0)) for v in y]

        self.means, self.devs = _standardise(x)
        z = [[(row[j] - self.means[j]) / self.devs[j]
              for j in range(len(self.means))] for row in x]

        # Centring y lets us drop the intercept from the penalised
        # system and add it back afterwards, which is what we want:
        # shrinking the intercept would just bias every prediction.
        y_mean = sum(y) / len(y)
        centred = [v - y_mean for v in y]

        width = len(self.means)
        gram = [[sum(r[i] * r[j] for r in z) for j in range(width)]
                for i in range(width)]
        for i in range(width):
            gram[i][i] += self.alpha
        rhs = [sum(z[k][i] * centred[k] for k in range(len(z)))
               for i in range(width)]

        self.coef = _solve(gram, rhs)
        self.intercept = y_mean

        # Kept so the daily job can size an interval without
        # reloading the backtest. In-sample, so it understates the
        # real spread; predict.py prefers the backtest RMSE and
        # only falls back to this.
        fitted = [self._raw(row) for row in x]
        if len(y) > 1:
            gap = sum((a - b) ** 2 for a, b in zip(y, fitted)) / (len(y) - 1)
            self.residual_sd = math.sqrt(gap)
        return self

    def _raw(self, row):
        """The linear response, before any inverse transform."""
        total = self.intercept
        for j, value in enumerate(row):
            total += self.coef[j] * (value - self.means[j]) / self.devs[j]
        return total

    def predict_one(self, row):
        total = self._raw(row)
        if self.log_target:
            total = math.expm1(total)
        # PM2.5 cannot be negative, and an unclipped linear model
        # will happily say -4 on a clean day.
        return max(total, 0.0)

    def interval(self, row, sd, z=1.28):
        """A rough band around the point forecast.

        Under a log target the band has to be built in log space
        and mapped back, which makes it asymmetric -- wider above
        than below. That is the right shape: pollution spikes
        upward far more readily than it falls.
        """
        if not sd:
            return None
        middle = self._raw(row)
        low, high = middle - z * sd, middle + z * sd
        if self.log_target:
            low, high = math.expm1(low), math.expm1(high)
        return [max(low, 0.0), max(high, 0.0)]

    def predict(self, x):
        return [self.predict_one(row) for row in x]

    def weights(self):
        """Coefficients by name, largest influence first.

        These are on standardised inputs, so they are comparable
        across features -- useful for the report, not for physics.
        """
        pairs = zip(self.names or range(len(self.coef)), self.coef)
        return sorted(pairs, key=lambda kv: -abs(kv[1]))

    def to_dict(self):
        return {
            "alpha": self.alpha,
            "names": self.names,
            "log_target": self.log_target,
            "residual_sd": self.residual_sd,
            "coef": self.coef,
            "intercept": self.intercept,
            "means": self.means,
            "devs": self.devs,
        }

    @classmethod
    def from_dict(cls, blob):
        model = cls(alpha=blob["alpha"], names=blob.get("names"),
                    log_target=blob.get("log_target", False))
        model.residual_sd = blob.get("residual_sd")
        model.coef = blob["coef"]
        model.intercept = blob["intercept"]
        model.means = blob["means"]
        model.devs = blob["devs"]
        return model

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls.from_dict(json.load(f))
