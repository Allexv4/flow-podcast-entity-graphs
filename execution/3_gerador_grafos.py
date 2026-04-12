"""
=============================================================================
Script 3: Gerador de Grafos de Co-ocorrência
=============================================================================
Constrói 3 grafos de co-ocorrência de entidades nomeadas usando
distâncias diferentes: sentença, parágrafo e k-caracteres.

Uso:
    python execution/3_gerador_grafos.py

Entrada:  data/ner_output/{video_id}_entities.json
Saída:    data/graphs/cooccurrence_sentence.graphml
          data/graphs/cooccurrence_paragraph.graphml
          data/graphs/cooccurrence_k_chars.graphml
=============================================================================
"""

import io
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import networkx as nx
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "videos.yaml"
NER_OUTPUT_DIR = ROOT_DIR / "data" / "ner_output"
GRAPHS_DIR = ROOT_DIR / "data" / "graphs"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_entities(videos):
    all_data = []
    for video in videos:
        fp = NER_OUTPUT_DIR / f"{video['id']}_entities.json"
        if fp.exists():
            with open(fp, "r", encoding="utf-8") as f:
                all_data.append(json.load(f))
    return all_data


def _build_graph_by_grouping(all_data, group_key):
    """Helper genérico para construir grafo agrupando por sentence_id ou paragraph_id."""
    G = nx.Graph()
    edge_w = defaultdict(int)
    node_freq = defaultdict(int)
    node_labels = {}

    for vdata in all_data:
        groups = defaultdict(set)
        for ent in vdata.get("entities", []):
            txt, lbl = ent["text"], ent["label"]
            node_labels[txt] = lbl
            for occ in ent.get("occurrences", []):
                gid = occ.get(group_key, -1)
                if gid >= 0:
                    groups[gid].add(txt)
                    node_freq[txt] += 1

        for gid, ents in groups.items():
            if len(ents) >= 2:
                for e1, e2 in combinations(sorted(ents), 2):
                    edge_w[(e1, e2)] += 1

    for (e1, e2), w in edge_w.items():
        G.add_edge(e1, e2, weight=w)
    for node in G.nodes():
        G.nodes[node]["label"] = node_labels.get(node, "MISC")
        G.nodes[node]["frequency"] = node_freq.get(node, 0)
    return G


def build_graph_by_sentence(all_data):
    return _build_graph_by_grouping(all_data, "sentence_id")


def build_graph_by_paragraph(all_data):
    return _build_graph_by_grouping(all_data, "paragraph_id")


def build_graph_by_k_chars(all_data, k=500):
    G = nx.Graph()
    edge_w = defaultdict(int)
    node_freq = defaultdict(int)
    node_labels = {}

    for vdata in all_data:
        occs = []
        for ent in vdata.get("entities", []):
            txt, lbl = ent["text"], ent["label"]
            node_labels[txt] = lbl
            for occ in ent.get("occurrences", []):
                cs = occ.get("char_start", -1)
                if cs >= 0:
                    occs.append({"text": txt, "char_start": cs})
                    node_freq[txt] += 1

        occs.sort(key=lambda x: x["char_start"])
        n = len(occs)
        for i in range(n):
            for j in range(i + 1, n):
                dist = occs[j]["char_start"] - occs[i]["char_start"]
                if dist > k:
                    break
                e1, e2 = occs[i]["text"], occs[j]["text"]
                if e1 != e2:
                    pair = tuple(sorted([e1, e2]))
                    edge_w[pair] += 1

    for (e1, e2), w in edge_w.items():
        G.add_edge(e1, e2, weight=w)
    for node in G.nodes():
        G.nodes[node]["label"] = node_labels.get(node, "MISC")
        G.nodes[node]["frequency"] = node_freq.get(node, 0)
    return G


def compute_metrics(G, name):
    m = {
        "name": name,
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": round(nx.density(G), 6),
        "avg_degree": round(sum(dict(G.degree()).values()) / max(G.number_of_nodes(), 1), 2),
        "avg_clustering": round(nx.average_clustering(G), 4) if G.number_of_nodes() > 0 else 0,
        "connected_components": nx.number_connected_components(G),
    }
    if G.number_of_nodes() > 0:
        gcc = max(nx.connected_components(G), key=len)
        sg = G.subgraph(gcc)
        m["giant_component_nodes"] = sg.number_of_nodes()
        m["giant_component_edges"] = sg.number_of_edges()
        try:
            m["diameter"] = nx.diameter(sg)
        except nx.NetworkXError:
            m["diameter"] = -1
    else:
        m["giant_component_nodes"] = 0
        m["giant_component_edges"] = 0
        m["diameter"] = 0

    print(f"\n  📊 Métricas — {name}:")
    for k2, v in m.items():
        if k2 != "name":
            print(f"     {k2.replace('_',' ').title():<25} {v}")
    return m


def main():
    print("=" * 70)
    print("SCRIPT 3: GERAÇÃO DE GRAFOS DE CO-OCORRÊNCIA")
    print("=" * 70)

    config = load_config()
    videos = config.get("videos", [])
    k = config.get("project", {}).get("k_chars", 500)

    print(f"\n🔧 Parâmetro K (k-caracteres): {k}")
    print(f"📂 Carregando entidades de {len(videos)} vídeos...")
    all_data = load_all_entities(videos)
    print(f"  ✓ {len(all_data)} arquivos carregados")

    if not all_data:
        print("  ✗ Nenhum dado encontrado! Execute 2_extrator_ner.py primeiro.")
        sys.exit(1)

    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    all_metrics = []

    # Grafo 1: Sentença
    print("\n" + "-" * 50)
    print("🔹 Grafo 1: Co-ocorrência por SENTENÇA")
    G1 = build_graph_by_sentence(all_data)
    all_metrics.append(compute_metrics(G1, "Sentença"))
    nx.write_graphml(G1, str(GRAPHS_DIR / "cooccurrence_sentence.graphml"))
    print(f"  💾 Salvo: cooccurrence_sentence.graphml")

    # Grafo 2: Parágrafo
    print("\n" + "-" * 50)
    print("🔹 Grafo 2: Co-ocorrência por PARÁGRAFO")
    G2 = build_graph_by_paragraph(all_data)
    all_metrics.append(compute_metrics(G2, "Parágrafo"))
    nx.write_graphml(G2, str(GRAPHS_DIR / "cooccurrence_paragraph.graphml"))
    print(f"  💾 Salvo: cooccurrence_paragraph.graphml")

    # Grafo 3: K-caracteres
    print("\n" + "-" * 50)
    print(f"🔹 Grafo 3: Co-ocorrência por K-CARACTERES (K={k})")
    G3 = build_graph_by_k_chars(all_data, k=k)
    all_metrics.append(compute_metrics(G3, f"K-Caracteres (K={k})"))
    nx.write_graphml(G3, str(GRAPHS_DIR / "cooccurrence_k_chars.graphml"))
    print(f"  💾 Salvo: cooccurrence_k_chars.graphml")

    # Salvar métricas
    with open(GRAPHS_DIR / "metrics_summary.json", "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, ensure_ascii=False, indent=2)

    # Tabela comparativa
    print("\n" + "=" * 70)
    print("RESUMO COMPARATIVO DOS GRAFOS")
    print("=" * 70)
    header = f"{'Métrica':<25} {'Sentença':>12} {'Parágrafo':>12} {'K-Chars':>12}"
    print(header)
    print("-" * len(header))
    for key in ["nodes", "edges", "density", "avg_degree", "avg_clustering",
                 "connected_components", "diameter"]:
        vals = [str(m.get(key, "N/A")) for m in all_metrics]
        print(f"  {key.replace('_',' ').title():<23} {vals[0]:>12} {vals[1]:>12} {vals[2]:>12}")
    print("=" * 70)


if __name__ == "__main__":
    main()
