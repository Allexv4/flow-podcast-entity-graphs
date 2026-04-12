"""
=============================================================================
Script 4: Plotagem de Resultados
=============================================================================
Gera visualizações comparativas dos 3 grafos de co-ocorrência.

Uso:
    python execution/4_plot_resultados.py

Entrada:  data/graphs/*.graphml, data/graphs/metrics_summary.json
Saída:    figures/*.png
=============================================================================
"""

import io
import json
from pathlib import Path
import sys

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np
import seaborn as sns

ROOT_DIR = Path(__file__).resolve().parent.parent
GRAPHS_DIR = ROOT_DIR / "data" / "graphs"
FIGURES_DIR = ROOT_DIR / "figures"

# Cores por tipo NER
NER_COLORS = {
    "PER": "#4A90D9",   # Azul
    "ORG": "#E74C3C",   # Vermelho
    "LOC": "#2ECC71",   # Verde
    "MISC": "#95A5A6",  # Cinza
}

# Estilo global
plt.rcParams.update({
    "figure.facecolor": "#1a1a2e",
    "axes.facecolor": "#16213e",
    "axes.edgecolor": "#e0e0e0",
    "axes.labelcolor": "#e0e0e0",
    "text.color": "#e0e0e0",
    "xtick.color": "#e0e0e0",
    "ytick.color": "#e0e0e0",
    "font.size": 11,
    "axes.titlesize": 14,
    "figure.titlesize": 16,
})


def load_graph(filename):
    path = GRAPHS_DIR / filename
    if not path.exists():
        print(f"  ⚠ Arquivo não encontrado: {path}")
        return None
    return nx.read_graphml(str(path))


def get_node_colors(G):
    return [NER_COLORS.get(G.nodes[n].get("label", "MISC"), "#95A5A6") for n in G.nodes()]


def get_node_sizes(G, base=50, scale=15):
    degrees = dict(G.degree())
    if not degrees:
        return []
    max_deg = max(degrees.values()) if degrees else 1
    return [base + (degrees[n] / max(max_deg, 1)) * scale * 30 for n in G.nodes()]


def get_edge_widths(G, max_width=3.0):
    weights = [G[u][v].get("weight", 1) for u, v in G.edges()]
    if not weights:
        return []
    max_w = max(weights)
    return [0.3 + (w / max(max_w, 1)) * max_width for w in weights]


def plot_graph(G, title, filename, ax=None):
    """Plota um grafo de co-ocorrência com layout spring."""
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))

    if G is None or G.number_of_nodes() == 0:
        ax.text(0.5, 0.5, "Sem dados", ha="center", va="center",
                fontsize=16, color="#e0e0e0", transform=ax.transAxes)
        ax.set_title(title, fontweight="bold")
        if standalone:
            plt.tight_layout()
            plt.savefig(FIGURES_DIR / filename, dpi=300, bbox_inches="tight")
            plt.close()
        return

    # Layout
    pos = nx.spring_layout(G, k=1.5/np.sqrt(max(G.number_of_nodes(), 1)),
                           iterations=50, seed=42)

    colors = get_node_colors(G)
    sizes = get_node_sizes(G)
    widths = get_edge_widths(G)

    # Desenhar arestas
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#ffffff",
                           alpha=0.15, width=widths)

    # Desenhar nós
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=colors,
                           node_size=sizes, alpha=0.85, edgecolors="#ffffff",
                           linewidths=0.5)

    # Labels apenas para nós com grau alto (top 20)
    degrees = dict(G.degree())
    if degrees:
        sorted_nodes = sorted(degrees, key=degrees.get, reverse=True)
        top_nodes = set(sorted_nodes[:20])
        labels = {n: n for n in top_nodes}
        nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
                                font_size=7, font_color="#ffffff",
                                font_weight="bold")

    ax.set_title(title, fontweight="bold", fontsize=14, pad=10)
    ax.axis("off")

    # Legenda
    patches = [mpatches.Patch(color=c, label=l) for l, c in NER_COLORS.items()]
    ax.legend(handles=patches, loc="lower right", fontsize=9,
              facecolor="#1a1a2e", edgecolor="#e0e0e0", labelcolor="#e0e0e0")

    if standalone:
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / filename, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"  💾 Salvo: {filename}")


def plot_metrics_comparison(metrics):
    """Gera gráfico de barras comparando métricas dos 3 grafos."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("Comparativo de Métricas dos Grafos de Co-ocorrência",
                 fontweight="bold", fontsize=16)

    names = [m["name"] for m in metrics]
    bar_colors = ["#4A90D9", "#E74C3C", "#2ECC71"]

    metric_keys = [
        ("nodes", "Número de Nós"),
        ("edges", "Número de Arestas"),
        ("density", "Densidade"),
        ("avg_degree", "Grau Médio"),
        ("avg_clustering", "Clustering Médio"),
        ("diameter", "Diâmetro (Comp. Gigante)"),
    ]

    for idx, (key, label) in enumerate(metric_keys):
        ax = axes[idx // 3][idx % 3]
        vals = [float(m.get(key, 0)) for m in metrics]
        bars = ax.bar(names, vals, color=bar_colors, alpha=0.85, edgecolor="#ffffff",
                      linewidth=0.5)
        ax.set_title(label, fontweight="bold", fontsize=12)
        ax.set_ylabel(label)

        # Adicionar valores sobre as barras
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01*max(vals) if max(vals) > 0 else 0.01,
                    f"{val:.4f}" if isinstance(val, float) and val < 1 else f"{val:.0f}",
                    ha="center", va="bottom", fontsize=9, fontweight="bold", color="#e0e0e0")

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "comparativo_metricas.png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  💾 Salvo: comparativo_metricas.png")


def plot_degree_distribution(graphs, names):
    """Plota distribuição de grau (log-log) dos 3 grafos sobrepostos."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 7))
    colors = ["#4A90D9", "#E74C3C", "#2ECC71"]

    for G, name, color in zip(graphs, names, colors):
        if G is None or G.number_of_nodes() == 0:
            continue
        degrees = [d for _, d in G.degree()]
        if not degrees:
            continue
        unique, counts = np.unique(degrees, return_counts=True)
        freq = counts / counts.sum()
        ax.scatter(unique, freq, color=color, alpha=0.7, s=40, label=name)
        # Linha de tendência
        if len(unique) > 1:
            ax.plot(unique, freq, color=color, alpha=0.4, linewidth=1)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Grau (k)", fontsize=12)
    ax.set_ylabel("P(k)", fontsize=12)
    ax.set_title("Distribuição de Grau (Log-Log)", fontweight="bold", fontsize=14)
    ax.legend(fontsize=10, facecolor="#1a1a2e", edgecolor="#e0e0e0", labelcolor="#e0e0e0")
    ax.grid(True, alpha=0.2, color="#ffffff")

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "distribuicao_grau.png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  💾 Salvo: distribuicao_grau.png")


def plot_top_entities(graphs, names):
    """Plota top-15 entidades por grau de centralidade em cada grafo."""
    fig, axes = plt.subplots(1, 3, figsize=(20, 8))
    fig.suptitle("Top-15 Entidades por Centralidade de Grau",
                 fontweight="bold", fontsize=16)
    colors = ["#4A90D9", "#E74C3C", "#2ECC71"]

    for idx, (G, name, color) in enumerate(zip(graphs, names, colors)):
        ax = axes[idx]
        if G is None or G.number_of_nodes() == 0:
            ax.text(0.5, 0.5, "Sem dados", ha="center", va="center", fontsize=14)
            ax.set_title(name)
            continue

        centrality = nx.degree_centrality(G)
        top = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:15]

        if not top:
            ax.text(0.5, 0.5, "Sem dados", ha="center", va="center", fontsize=14)
            ax.set_title(name)
            continue

        entities = [t[0] for t in top][::-1]
        values = [t[1] for t in top][::-1]
        ent_colors = [NER_COLORS.get(G.nodes[e].get("label", "MISC"), "#95A5A6")
                      for e in entities]

        ax.barh(entities, values, color=ent_colors, alpha=0.85,
                edgecolor="#ffffff", linewidth=0.5)
        ax.set_title(name, fontweight="bold", fontsize=13)
        ax.set_xlabel("Centralidade de Grau")

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "top_entidades.png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  💾 Salvo: top_entidades.png")


def main():
    print("=" * 70)
    print("SCRIPT 4: PLOTAGEM DE RESULTADOS")
    print("=" * 70)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Carregar grafos
    print("\n📂 Carregando grafos...")
    G_sent = load_graph("cooccurrence_sentence.graphml")
    G_para = load_graph("cooccurrence_paragraph.graphml")
    G_kchars = load_graph("cooccurrence_k_chars.graphml")

    graphs = [G_sent, G_para, G_kchars]
    names = ["Sentença", "Parágrafo", "K-Caracteres"]

    # 1. Grafos individuais
    print("\n🎨 Gerando visualizações dos grafos...")
    plot_graph(G_sent, "Grafo de Co-ocorrência — Sentença",
               "grafo_sentenca.png")
    plot_graph(G_para, "Grafo de Co-ocorrência — Parágrafo",
               "grafo_paragrafo.png")
    plot_graph(G_kchars, "Grafo de Co-ocorrência — K-Caracteres (K=500)",
               "grafo_k_caracteres.png")

    # 2. Métricas comparativas
    print("\n📊 Gerando comparativo de métricas...")
    metrics_path = GRAPHS_DIR / "metrics_summary.json"
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        plot_metrics_comparison(metrics)
    else:
        print("  ⚠ metrics_summary.json não encontrado. Pulando...")

    # 3. Distribuição de grau
    print("\n📈 Gerando distribuição de grau...")
    plot_degree_distribution(graphs, names)

    # 4. Top entidades
    print("\n🏆 Gerando top entidades por centralidade...")
    plot_top_entities(graphs, names)

    print("\n" + "=" * 70)
    print("TODAS AS FIGURAS GERADAS COM SUCESSO")
    print(f"📁 Diretório: {FIGURES_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
