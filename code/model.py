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
    """Least squares with an L2 penalty on the standardised inputs."""

    def __init__(self, alpha=1.0, names=None):
        self.alpha = alpha
        self.names = names or []
        self.coef = []
        self.intercept = 0.0
        self.means = []
        self.devs = []

    def fit(self, x, y):
        if not x:
            raise ValueError("nothing to fit")
        if len(x) != len(y):
            raise ValueError("x and y disagree on length")

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
        return self

    def predict_one(self, row):
        total = self.intercept
        for j, value in enumerate(row):
            total += self.coef[j] * (value - self.means[j]) / self.devs[j]
        # PM2.5 cannot be negative, and an unclipped linear model
        # will happily say -4 on a clean day.
        return max(total, 0.0)

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
            "coef": self.coef,
            "intercept": self.intercept,
            "means": self.means,
            "devs": self.devs,
        }

    @classmethod
    def from_dict(cls, blob):
        model = cls(alpha=blob["alpha"], names=blob.get("names"))
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
