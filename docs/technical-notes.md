# Technical notes and illustrative calculations

These are original explanatory derivations for the proposal. They specialize standard linear identifiability and experimental-design ideas; they are **not claimed as new theorems**. They do not establish biological model correctness. The historical design connection is explicit in [IdentiFlow](https://academic.oup.com/bioinformatics/article/36/Supplement_1/i482/5870467) and [transductive linear bandits](https://papers.neurips.cc/paper_files/paper/2019/hash/8ba6c657b03fc7c8dd4dff8e45defcd2-Abstract.html).

## 1. Why controls alone cannot identify an unrestricted response

Consider two possible recipient mechanisms with the same control distribution. For a perturbation variable `P` and identical noise `epsilon`, let:

\[
Y_+=\epsilon+P,\qquad Y_-=\epsilon-P.
\]

When `P=0`, all unperturbed observations agree. When `P=1`, the responses differ by two units. Source-context observations can also be identical in both worlds unless an assumption connects source and recipient mechanisms. Thus unperturbed recipient data plus source experiments do not identify an arbitrary recipient effect.

This is a counterexample to *unrestricted* identification, not a proof that useful zero-shot prediction is impossible. Biological invariances, informative baseline measurements, or valid structural assumptions can exclude one of the two worlds. The project measures which assumptions are empirically useful.

## 2. Identification of a particular query can require less than a full model

Assume exact, fixed source features, known recipient baseline, noiseless acquired effects `y_A`, and a correct linear model:

\[
y_A=\Phi_A\theta,\qquad f(q)=\phi_q^T\theta.
\]

The query is identified from these observations if and only if `phi_q` belongs to the row space of `Phi_A`.

**Argument.** If `phi_q = Phi_A^T a`, the query equals `a^T y_A`, which is observed. If it lies outside the row space, there is a vector `v` in the null space of `Phi_A` with `phi_q^T v != 0`. Parameters `theta` and `theta + c v` agree on all acquired observations but disagree on the query. With unrestricted `c`, uncertainty in that direction is unbounded.

Repeating an existing measurement improves precision but does not enlarge this row space. A new intervention may add a missing direction. Conversely, acquiring a new intervention inside an already observed span may provide less value than reducing noise on an important direction.

With an unknown baseline, use augmented measurement rows `z_p=(phi_p,1)` and `z_0=(0,1)`. The relevant query is `c_q=(phi_q,0)`, and the same row-space argument applies to the augmented design. Ridge invertibility is not proof of identification: its penalty supplies extra assumptions.

## 3. Shared controls induce correlated errors

Let `m_p` and `m_0` be scalar means for a perturbation and its shared control. Suppose separate perturbed pools and the control pool are independent, with per-cell variances `v_p` and `v_0`, and counts `n_p` and `n_0`. For `d_p=m_p-m_0`:

\[
\operatorname{Var}(d_p)=v_p/n_p+v_0/n_0,
\]

\[
\operatorname{Cov}(d_p,d_j)=v_0/n_0\quad(p\ne j).
\]

The multigene analogue replaces scalar variances with covariance matrices. If the control pool is also shared between source features, those feature errors are correlated too. Independent guide, plate, or batch effects require additional covariance terms.

This explains why measuring more different perturbations cannot always average away baseline uncertainty. It also explains why the objective matters: a common control term cancels in a difference between two effects, but remains in their mean or their absolute effects. The proposed primary effect-estimation objective therefore differs from a pure within-context ranking objective.

## 4. A nuisance-aware design criterion

For the ideal scalar Gaussian model with known variances, define weights `w_p=n_p/v_p` and `w_0=n_0/v_0`. The information matrix for `(theta,mu_0)` is:

\[
I=\begin{pmatrix}
\sum_p w_p\phi_p\phi_p^T & \sum_p w_p\phi_p\\
(\sum_p w_p\phi_p)^T & w_0+\sum_p w_p
\end{pmatrix}.
\]

Eliminating the baseline gives:

\[
M_\theta=\sum_p w_p\phi_p\phi_p^T-
\frac{(\sum_p w_p\phi_p)(\sum_p w_p\phi_p)^T}{w_0+\sum_p w_p}.
\]

For an identified query, ideal estimation variance is `phi_q^T M_theta^+ phi_q`, where `+` denotes a pseudoinverse. A query outside the identifiable subspace has unbounded uncertainty in the unrestricted model; the pseudoinverse expression alone must not be used to assign it zero uncertainty.

A starting policy minimizes the maximum query variance subject to:

\[
\sum_p c_{\rm setup,p}\mathbf{1}[n_p>0]
+\sum_p c_{\rm cell,p}n_p+c_{\rm control}n_0\le B.
\]

Discrete allocation, setup costs, learned features, and transfer bias make this a different practical problem from continuous allocation with exact features. They do not automatically make a proposed solver novel.

## 5. Reproducible toy examples

Run from the repository root with a Python interpreter:

```sh
python docs/evidence/design_demo.py
```

The committed [output](evidence/design-demo.json) uses exact rational arithmetic. It contains no fitted model and no biological data.

| Calculation | Result | Interpretation |
| --- | --- | --- |
| Only feature `(1,0)` is measured; query is `(0,1)`. | Parameters `(0,1)` and `(0,-1)` fit the measurements equally but predict `+1` and `-1`. | Precision on one direction cannot identify a different direction. |
| Known baseline, two orthogonal features, per-cell variances `1` and `9`, query `(1,1)`, 100 equally priced cells. | Equal allocation gives variance `0.20`; allocation `25:75` gives `0.16`. | Even after spanning the query, depth allocation matters. |
| Two perturbed means each have variance `1/50`; a shared control has variance `4/20`. | Variance of the mean effect is `0.21`; falsely ignoring covariance gives `0.11`. | Treating shared controls as independent understates uncertainty. |
| Estimate the mean of two effects with 120 equally priced cells, perturbation variances `1,1`, control variance `4`. | Equal allocation `40:40:40` gives `0.1125`; allocation `20:20:80` gives `0.075`. | For this estimand and noise model, extra controls are particularly useful. |

The optimal allocations follow the standard rule `n_i proportional to sqrt(a_i)` for minimizing `sum(a_i/n_i)` at fixed total count. These examples motivate the study; they are not evidence of a new method's superiority.

## 6. Where the mathematics stops applying

- Source response features are measured, not exact. Ordinary regression may suffer errors-in-variables bias.
- Recipient rewiring can violate the transfer relation. More precise data cannot remove structural misspecification.
- Captured cells may share guides or batches. Effective sample size can be much smaller than cell count.
- Estimated variances and adaptive actions require appropriate sequential analysis; a fixed-design Gaussian interval is not automatically valid after adaptive selection or stopping.
- Destructive assays do not pair the same cell before and after treatment. This proposal targets population contrasts, not individual counterfactual cell trajectories.

Report ideal-model bounds separately from empirical calibration under these violations. A confidence set for a wrong response model is not a causal guarantee.
