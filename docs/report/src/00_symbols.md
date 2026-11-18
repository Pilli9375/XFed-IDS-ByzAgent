| Symbol | Meaning |
|---|---|
| α | Dirichlet concentration parameter that sets label skew across silos (smaller means more skewed) |
| β (class weights) | Parameter of effective-number class weighting |
| β (trimmed mean) | Fraction of values trimmed at each end of every coordinate |
| μ | FedProx proximal coefficient |
| f | Number of malicious silos (attackers) |
| n | Number of silos; also a sample size where stated |
| k | Number of top-ranked features compared (as in Jaccard@k) |
| K | Number of classes |
| τ | Kendall's rank correlation; weighted τ is the top-weighted form |
| ρ | Spearman rank correlation |
| r | Pearson or partial correlation coefficient |
| δ | Glass's effect size |
| p_k | Vector of silo shares for family k, drawn from a Dirichlet distribution |
| w_t | Global model weights after round t |
| η | Server learning rate (FedAdam, FedYogi, FedAvgM) |
| φ_j | SHAP attribution of feature j |
| E[f] | Expected model output over the SHAP background |
| J@k | Jaccard index of two top-k feature sets |
| t | Pre-screen threshold on the training-loss ratio |
<!-- numcheck: ignore -->
