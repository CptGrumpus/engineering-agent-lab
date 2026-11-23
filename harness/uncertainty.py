"""Probabilistic uncertainty: sampling, Sobol sensitivity indices, failure probability, FORM and importance sampling.

Inputs are independent random variables given as frozen scipy.stats distributions. Everything maps through the
standard-normal space u (x_i = F_i^-1(Phi(u_i))), so FORM and importance sampling work for any marginal.

- sample: n points by scrambled Sobol (quasi-random) or plain Monte Carlo.
- sobol_indices: first-order (Saltelli 2010) and total (Jansen 1999) indices from the A, B, AB_i scheme, n (d + 2)
  model calls, with bootstrap confidence intervals.
- failure_probability: the fraction of samples with g <= 0 and its Wilson 95 % interval.
- form: the Hasofer-Lind / Rackwitz-Fiessler design point, beta and Phi(-beta).
- importance_sampling: Monte Carlo centred on the design point, for probabilities too small to sample directly.

Verified in tests/test_uncertainty.py against closed forms: the Ishigami function's indices, and linear limit states
in normal and lognormal variables (where FORM is exact).
"""

from __future__ import annotations

import math
from typing import Callable, Sequence

import numpy as np
from scipy import stats
from scipy.stats import qmc

Model = Callable[[np.ndarray], np.ndarray]          # (n, d) inputs -> (n,) outputs


def _to_x(u: np.ndarray, dists: Sequence) -> np.ndarray:
    p = stats.norm.cdf(u)
    return np.column_stack([d.ppf(p[:, i]) for i, d in enumerate(dists)])


def _unit(n: int, d: int, seed: int, method: str) -> np.ndarray:
    if method == "sobol":
        m = max(1, math.ceil(math.log2(max(n, 2))))
        return qmc.Sobol(d, scramble=True, seed=seed).random_base2(m)[:n]
    if method == "random":
        return np.random.default_rng(seed).random((n, d))
    raise ValueError(f"unknown sampling method {method!r}")


def sample(dists: Sequence, n: int, seed: int = 0, method: str = "sobol") -> np.ndarray:
    """n samples (n, d) of the independent inputs."""
    uu = _unit(n, len(dists), seed, method)
    uu = np.clip(uu, 1e-12, 1 - 1e-12)
    return np.column_stack([d.ppf(uu[:, i]) for i, d in enumerate(dists)])


def sobol_indices(model: Model, dists: Sequence, n: int, seed: int = 0, n_boot: int = 200,
                  method: str = "sobol") -> dict:
    """First-order S1 and total ST indices of model(x) with their 95 % bootstrap intervals; n (d + 2) calls."""
    d = len(dists)
    uu = np.clip(_unit(n, 2 * d, seed, method), 1e-12, 1 - 1e-12)
    A = np.column_stack([dd.ppf(uu[:, i]) for i, dd in enumerate(dists)])
    B = np.column_stack([dd.ppf(uu[:, d + i]) for i, dd in enumerate(dists)])
    fA, fB = model(A), model(B)
    fAB = np.empty((d, n))
    for i in range(d):
        ABi = A.copy()
        ABi[:, i] = B[:, i]
        fAB[i] = model(ABi)

    def est(idx):
        a, b, ab = fA[idx], fB[idx], fAB[:, idx]
        var = np.var(np.concatenate([a, b]))
        s1 = np.mean(b * (ab - a), axis=1) / var
        st = 0.5 * np.mean((a - ab) ** 2, axis=1) / var
        return s1, st

    s1, st = est(np.arange(n))
    rng = np.random.default_rng(seed + 1)
    boot = [est(rng.integers(0, n, n)) for _ in range(n_boot)]
    b1, bt = np.array([b[0] for b in boot]), np.array([b[1] for b in boot])
    return {"S1": s1, "ST": st, "S1_ci": np.percentile(b1, [2.5, 97.5], axis=0).T,
            "ST_ci": np.percentile(bt, [2.5, 97.5], axis=0).T, "n_calls": n * (d + 2),
            "mean": float(np.mean(np.concatenate([fA, fB]))), "var": float(np.var(np.concatenate([fA, fB])))}


def failure_probability(g: np.ndarray) -> dict:
    """P(g <= 0) from samples, with the Wilson 95 % interval (sound at zero failures)."""
    g = np.asarray(g)
    n, k = len(g), int(np.sum(g <= 0))
    z = 1.959964
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return {"pf": p, "failures": k, "n": n,
            "ci": (0.0 if k == 0 else max(0.0, c - h), 1.0 if k == n else min(1.0, c + h))}


def form(g: Callable[[np.ndarray], float], dists: Sequence, u0: np.ndarray | None = None, tol: float = 1e-6,
         max_iter: int = 100, h: float = 1e-5) -> dict:
    """HL-RF iteration in u space with central-difference gradients. g takes one x vector (d,)."""
    d = len(dists)
    u = np.zeros(d) if u0 is None else np.asarray(u0, float)
    gx = lambda uu: float(g(_to_x(uu[None, :], dists)[0]))          # noqa: E731
    calls = 0
    for it in range(max_iter):
        g0 = gx(u)
        grad = np.array([(gx(u + h * e) - gx(u - h * e)) / (2 * h) for e in np.eye(d)])
        calls += 1 + 2 * d
        nrm = float(grad @ grad)
        if nrm == 0:
            raise RuntimeError("zero gradient in FORM")
        u_new = (grad @ u - g0) / nrm * grad
        if np.linalg.norm(u_new - u) < tol * max(1.0, np.linalg.norm(u_new)):
            u = u_new
            break
        u = u_new
    else:
        raise RuntimeError("FORM did not converge")
    beta = float(np.linalg.norm(u)) * (1 if gx(np.zeros(d)) > 0 else -1)
    return {"beta": beta, "pf": float(stats.norm.cdf(-beta)), "u_star": u, "x_star": _to_x(u[None, :], dists)[0],
            "alpha": -u / max(np.linalg.norm(u), 1e-300), "iterations": it + 1, "calls": calls}


def importance_sampling(g: Model, dists: Sequence, u_star: np.ndarray, n: int, seed: int = 0) -> dict:
    """P(g <= 0) by sampling u ~ N(u_star, I); weights phi(u) / phi(u - u_star). Returns the estimate, its
    coefficient of variation and a normal-approximation 95 % interval."""
    rng = np.random.default_rng(seed)
    u_star = np.asarray(u_star, float)
    u = rng.standard_normal((n, len(dists))) + u_star
    w = np.exp(-u @ u_star + 0.5 * u_star @ u_star)
    ind = (np.asarray(g(_to_x(u, dists))) <= 0).astype(float)
    terms = ind * w
    pf = float(terms.mean())
    se = float(terms.std(ddof=1) / math.sqrt(n))
    return {"pf": pf, "cov": se / pf if pf > 0 else math.inf, "ci": (max(0.0, pf - 1.96 * se), pf + 1.96 * se),
            "n": n, "hits": int(ind.sum())}
