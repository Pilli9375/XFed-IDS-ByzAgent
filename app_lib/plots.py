"""Plotly figure builders.

Every chart in the app is built here so hover behaviour, fonts, margins,
and palette stay identical across sections. Plotly over matplotlib for
one reason that matters in a live demo: hover tooltips let a panel member
read an exact value off the chart instead of squinting at an axis.

All figures are transparent-background so the app's own surface shows
through, and all use a fixed template rather than Plotly's default (which
ships a white paper background and a blue/orange palette that clashes).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from app_lib import theme

HOVER = dict(
    bgcolor=theme.SURFACE_HI,
    bordercolor=theme.BORDER_HI,
    font=dict(family=theme.PLOTLY_FONT, size=13, color=theme.TEXT),
)


def _base_layout(fig: go.Figure, height: int, showlegend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height,
        showlegend=showlegend,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=theme.PLOTLY_FONT, size=13, color=theme.TEXT_MUTED),
        margin=dict(l=8, r=18, t=28, b=8),
        hoverlabel=HOVER,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=theme.TEXT_MUTED, size=12),
            orientation="h",
            yanchor="bottom", y=1.02, xanchor="right", x=1,
        ),
        modebar=dict(
            bgcolor="rgba(0,0,0,0)",
            color=theme.TEXT_FAINT,
            activecolor=theme.ACCENT,
        ),
    )
    fig.update_xaxes(
        gridcolor=theme.BORDER, zeroline=False,
        linecolor=theme.BORDER_HI, tickfont=dict(size=12),
        title_font=dict(size=13, color=theme.TEXT_FAINT),
    )
    fig.update_yaxes(
        gridcolor=theme.BORDER, zeroline=False,
        linecolor=theme.BORDER_HI, tickfont=dict(size=12),
        title_font=dict(size=13, color=theme.TEXT_FAINT),
    )
    return fig


def class_confidence(names: list[str], probs: np.ndarray) -> go.Figure:
    """Horizontal confidence bars, one color per family."""
    order = np.argsort(probs)
    y = [names[i] for i in order]
    x = [float(probs[i]) for i in order]
    colors = [theme.family_color(n) for n in y]

    fig = go.Figure(
        go.Bar(
            x=x, y=y, orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v:.1%}" for v in x],
            textposition="outside",
            textfont=dict(size=12, color=theme.TEXT_MUTED),
            hovertemplate="<b>%{y}</b><br>Confidence %{x:.2%}<extra></extra>",
            cliponaxis=False,
        )
    )
    fig.update_xaxes(range=[0, 1.13], tickformat=".0%", title_text="Softmax confidence")
    return _base_layout(fig, 380)


def shap_contributions(
    names: list[str], values: list[float], raw: list[float | None]
) -> go.Figure:
    """Diverging SHAP bars. Raw feature values ride along in the tooltip --
    the thing a panel actually asks about ('what was that value?')."""
    order = np.argsort(values)
    y = [names[i] for i in order]
    x = [values[i] for i in order]
    r = [raw[i] for i in order]
    colors = [theme.ALERT if v > 0 else theme.ACCENT for v in x]

    custom = [["—" if v is None else f"{v:,.4g}"] for v in r]
    fig = go.Figure(
        go.Bar(
            x=x, y=y, orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            customdata=custom,
            hovertemplate=(
                "<b>%{y}</b><br>SHAP %{x:+.4f} (logit)"
                "<br>Raw value %{customdata[0]}<extra></extra>"
            ),
        )
    )
    fig.add_vline(x=0, line_width=1.4, line_color=theme.BORDER_HI)
    fig.update_xaxes(title_text="SHAP contribution (logit)")
    return _base_layout(fig, 480)


def agreement_vs_alpha(
    alphas: list[float],
    median: list[float],
    q25: list[float],
    q75: list[float],
    per_seed: pd.DataFrame,
    seed_col: str,
    title: str,
    chance: float | None = None,
) -> go.Figure:
    """Median line + IQR ribbon + per-seed dots. The ribbon is a real
    percentile spread, not a fitted CI -- said so in the tooltip too, so
    the caveat travels with the chart."""
    labels = [f"α={a:g}" for a in alphas]
    x = list(range(len(alphas)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x + x[::-1], y=q75 + q25[::-1],
        fill="toself", fillcolor=f"rgba(76,201,240,0.14)",
        line=dict(color="rgba(0,0,0,0)"), hoverinfo="skip",
        showlegend=False, name="IQR",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=median, mode="lines+markers",
        line=dict(color=theme.ACCENT, width=3),
        marker=dict(size=11, color=theme.ACCENT,
                    line=dict(width=2, color=theme.BG)),
        customdata=np.stack([q25, q75], axis=-1),
        hovertemplate=(
            "<b>%{x}</b><br>Median %{y:.3f}"
            "<br>IQR %{customdata[0]:.3f} – %{customdata[1]:.3f}"
            "<extra></extra>"
        ),
        name="Median", showlegend=False,
    ))

    for a in alphas:
        rows = per_seed[per_seed["alpha"] == a]
        xa = alphas.index(a)
        fig.add_trace(go.Scatter(
            x=[xa] * len(rows), y=rows[seed_col],
            mode="markers",
            marker=dict(size=7, color=theme.TEXT, opacity=0.75,
                        line=dict(width=0)),
            customdata=rows[["seed"]].to_numpy(),
            hovertemplate="Seed %{customdata[0]}<br>%{y:.3f}<extra></extra>",
            showlegend=False,
        ))

    if chance is not None:
        fig.add_hline(
            y=chance, line_dash="dash", line_color=theme.ALERT, line_width=1.6,
            annotation_text=f"chance ≈ {chance:.3f}",
            annotation_position="bottom right",
            annotation_font=dict(color=theme.ALERT, size=12),
        )

    fig.update_xaxes(tickmode="array", tickvals=x, ticktext=labels)
    fig.update_yaxes(range=[0, 1])
    fig.update_layout(title=dict(
        text=title, font=dict(size=15, color=theme.TEXT), x=0, xanchor="left",
    ))
    return _base_layout(fig, 420)


def faithfulness_auc(models: list[str], deletion: list[float], insertion: list[float]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=models, y=deletion, name="Deletion AUC (lower better)",
        marker=dict(color=theme.ALERT, line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>Deletion AUC %{y:.3f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=models, y=insertion, name="Insertion AUC (higher better)",
        marker=dict(color=theme.POSITIVE, line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>Insertion AUC %{y:.3f}<extra></extra>",
    ))
    fig.update_layout(barmode="group", bargap=0.28, bargroupgap=0.08)
    fig.update_yaxes(title_text="AUC")
    return _base_layout(fig, 400, showlegend=True)


def floor_comparison(
    labels: list[str], medians: list[float], q25: list[float], q75: list[float]
) -> go.Figure:
    """Instability floor vs federated agreement, with IQR error bars. The
    overlap IS the point -- the chart has to make that visible."""
    colors = [theme.ALERT, theme.ACCENT]
    fig = go.Figure(go.Bar(
        x=medians, y=labels, orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        error_x=dict(
            type="data", symmetric=False,
            array=[h - m for h, m in zip(q75, medians)],
            arrayminus=[m - l for m, l in zip(medians, q25)],
            color=theme.TEXT_FAINT, thickness=1.6, width=7,
        ),
        customdata=np.stack([q25, q75], axis=-1),
        hovertemplate=(
            "<b>%{y}</b><br>Median %{x:.3f}"
            "<br>IQR %{customdata[0]:.3f} – %{customdata[1]:.3f}<extra></extra>"
        ),
    ))
    fig.update_xaxes(title_text="Jaccard@10 (median, IQR bars)", range=[0, 1])
    return _base_layout(fig, 260)


def per_family_grouped(df: pd.DataFrame, metric: str, title: str) -> go.Figure:
    """Grouped bars: family on x, one series per alpha."""
    alphas = sorted(df["alpha"].unique())
    families = sorted(df["family"].unique())
    fig = go.Figure()
    for i, a in enumerate(alphas):
        sub = df[df["alpha"] == a].set_index("family").reindex(families)
        fig.add_trace(go.Bar(
            x=families, y=sub[metric], name=f"α={a:g}",
            marker=dict(color=theme.SERIES[i % len(theme.SERIES)], line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>α=" + f"{a:g}" + "<br>%{y:.3f}<extra></extra>",
        ))
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.06,
                      title=dict(text=title, font=dict(size=15, color=theme.TEXT),
                                 x=0, xanchor="left"))
    fig.update_yaxes(range=[0, 1])
    return _base_layout(fig, 400, showlegend=True)


def silo_heatmap(matrix: pd.DataFrame, alpha: float, seed: int) -> go.Figure:
    """Per-silo per-family flow counts. Makes non-IID skew visible at a
    glance in a way a table cannot."""
    sub = matrix[(matrix["alpha"] == alpha) & (matrix["seed"] == seed)]
    if sub.empty:
        return _base_layout(go.Figure(), 300)
    piv = sub.pivot_table(index="silo", columns="family", values="n",
                          fill_value=0, aggfunc="sum")
    fig = go.Figure(go.Heatmap(
        z=np.log10(piv.to_numpy() + 1),
        x=list(piv.columns), y=[f"Silo {i}" for i in piv.index],
        customdata=piv.to_numpy(),
        colorscale=[[0, theme.SURFACE], [0.35, theme.ACCENT_DIM], [1, theme.ACCENT]],
        hovertemplate="<b>%{y}</b><br>%{x}<br>%{customdata:,} flows<extra></extra>",
        colorbar=dict(
            title=dict(text="log₁₀(flows)", font=dict(size=11, color=theme.TEXT_FAINT)),
            tickfont=dict(size=11, color=theme.TEXT_FAINT),
            outlinewidth=0, thickness=12, len=0.85,
        ),
        xgap=2, ygap=2,
    ))
    return _base_layout(fig, 420)


# --- Client Trust Monitor (trust check / ByzAgent) -----------------------
# Decision severity: 0=trust, 1=downweight, 2=quarantine. Fixed 3-color scale
# (not a continuous colorbar) since these are categories, not a magnitude.

DECISION_COLOR_SCALE = [
    [0.0, theme.POSITIVE], [0.34, theme.POSITIVE],
    [0.34, theme.WARN], [0.67, theme.WARN],
    [0.67, theme.ALERT], [1.0, theme.ALERT],
]
DECISION_NAME_BY_SEVERITY = {0: "trust", 1: "downweight", 2: "quarantine"}


def decision_grid_heatmap(pivot: pd.DataFrame, malicious_silos: list[int]) -> go.Figure:
    """Silo x round grid, one cell per decision. `pivot` is silo-indexed
    (0..9) x round-columned, values in {0,1,2,NaN}. Malicious silos (read
    from that condition's attack_config.json, never hardcoded here) get a
    marker on their row label so the grid itself shows flagged-vs-malicious
    at a glance."""
    z = pivot.to_numpy(dtype=float)
    rounds = list(pivot.columns)
    silos = list(pivot.index)
    y_labels = [f"silo {s}" + ("  ⚠" if s in malicious_silos else "") for s in silos]
    text = [
        [DECISION_NAME_BY_SEVERITY.get(v, "") if not np.isnan(v) else "no data" for v in row]
        for row in z
    ]

    fig = go.Figure(go.Heatmap(
        z=z, x=[f"R{r}" for r in rounds], y=y_labels,
        zmin=0, zmax=2, colorscale=DECISION_COLOR_SCALE, showscale=False,
        text=text,
        hovertemplate="<b>%{y}</b>, round %{x}<br>decision: %{text}<extra></extra>",
        xgap=2, ygap=2,
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickfont=dict(size=10))
    return _base_layout(fig, 70 + 30 * len(silos))


def clean_vs_attack_lift(df: pd.DataFrame) -> go.Figure:
    """Dumbbell chart: clean-run flag rate and attack-condition flag rate
    for the same silo, connected by a line, with the lift value printed
    next to the attack-side marker. Never renders one side without the
    other -- df is expected to always carry both columns (see
    trust_loaders.clean_vs_attack_table)."""
    df = df.sort_values("silo").reset_index(drop=True)
    y_labels = [f"silo {int(s)}" for s in df["silo"]]

    fig = go.Figure()
    for i, row in df.iterrows():
        line_color = theme.ALERT if row["malicious"] else theme.BORDER_HI
        fig.add_trace(go.Scatter(
            x=[row["clean_flag_rate"], row["attack_flag_rate"]],
            y=[y_labels[i], y_labels[i]],
            mode="lines", line=dict(color=line_color, width=2),
            showlegend=False, hoverinfo="skip",
        ))

    fig.add_trace(go.Scatter(
        x=df["clean_flag_rate"], y=y_labels, mode="markers",
        marker=dict(color=theme.TEXT_MUTED, size=11, symbol="circle",
                    line=dict(color=theme.BG, width=1)),
        name="Clean-run flag rate",
        hovertemplate="<b>%{y}</b><br>clean flag rate %{x:.2f}<extra></extra>",
    ))
    marker_colors = [theme.ALERT if m else theme.ACCENT for m in df["malicious"]]
    fig.add_trace(go.Scatter(
        x=df["attack_flag_rate"], y=y_labels, mode="markers+text",
        marker=dict(color=marker_colors, size=13, symbol="diamond",
                    line=dict(color=theme.BG, width=1)),
        text=[f"  lift {l:+.2f}" for l in df["lift"]],
        textposition="middle right",
        textfont=dict(size=11, color=theme.TEXT_MUTED),
        name="Attack-condition flag rate",
        hovertemplate="<b>%{y}</b><br>attack flag rate %{x:.2f}<extra></extra>",
    ))

    fig.update_xaxes(range=[-0.05, 1.35], tickformat=".0%",
                      title_text="Flag rate (downweight | quarantine)")
    return _base_layout(fig, 60 + 34 * len(df), showlegend=True)


STAT_LABELS = {
    "update_norm": "update_norm",
    "cosine_to_global": "cosine_to_global",
    "cosine_to_peer_mean": "cosine_to_peer_mean",
    "train_loss": "train_loss",
    "val_accuracy": "val_accuracy",
}


def stat_small_multiples(df: pd.DataFrame) -> go.Figure:
    """5 behavioral stats over rounds for one silo, as small multiples
    (not overlaid on one axis -- the stats live on wildly different
    scales, e.g. train_loss ~0.01-0.1 vs update_norm ~1-6)."""
    from plotly.subplots import make_subplots

    stats = list(STAT_LABELS.keys())
    fig = make_subplots(rows=1, cols=len(stats), subplot_titles=[STAT_LABELS[s] for s in stats])
    for i, s in enumerate(stats):
        fig.add_trace(
            go.Scatter(
                x=df["round"], y=df[s], mode="lines+markers",
                line=dict(color=theme.SERIES[i % len(theme.SERIES)], width=2),
                marker=dict(size=5), showlegend=False,
                hovertemplate=f"round %{{x}}<br>{s}=%{{y:.4f}}<extra></extra>",
            ),
            row=1, col=i + 1,
        )
    fig.update_xaxes(title_text="round", tickfont=dict(size=10), title_font=dict(size=11))
    fig = _base_layout(fig, 300)
    fig.update_annotations(font=dict(size=11, color=theme.TEXT_MUTED))
    return fig
