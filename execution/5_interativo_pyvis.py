"""
=============================================================================
Script 5: Visualizador Interativo de Grafos (PyVis)
=============================================================================
Lê os grafos gerados e cria páginas HTML interativas para você
navegar, dar zoom e clicar nos nós.

Uso:
    python execution/5_interativo_pyvis.py

Entrada:  data/graphs/*.graphml
Saída:    figures/interativo_*.html
=============================================================================
"""

import io
import sys

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import yaml
import networkx as nx
from pyvis.network import Network
from pathlib import Path
import webbrowser

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "videos.yaml"

def load_k_chars():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cfg.get("project", {}).get("k_chars", 4000)
    except Exception:
        return 4000

ROOT_DIR = Path(__file__).resolve().parent.parent
GRAPHS_DIR = ROOT_DIR / "data" / "graphs"
FIGURES_DIR = ROOT_DIR / "figures"

# Cores para cada tipo NER
NER_COLORS = {
    "PER": "#4A90D9",   # Azul
    "ORG": "#E74C3C",   # Vermelho
    "LOC": "#2ECC71",   # Verde
    "MISC": "#95A5A6",  # Cinza
}

NER_LABELS_PT = {
    "PER": "Pessoas",
    "ORG": "Organizações",
    "LOC": "Locais",
    "MISC": "Outros",
}


def generate_interactive(graph_name, html_filename, title):
    filepath = GRAPHS_DIR / graph_name
    if not filepath.exists():
        print(f"  ⚠ Grafo não encontrado: {filepath}")
        return None

    print(f"\n  🔨 Construindo: {title}")

    # Carregar o GraphML original
    G = nx.read_graphml(str(filepath))

    if G.number_of_nodes() == 0:
        print("  ⚠ Grafo vazio.")
        return None

    # Limitar nós para o grafo de parágrafo (pode ser MUITO grande)
    if G.number_of_nodes() > 300:
        print(f"  ℹ Grafo grande ({G.number_of_nodes()} nós). Filtrando top-200 por grau...")
        degrees = dict(G.degree())
        top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:200]
        G = G.subgraph(top_nodes).copy()
        print(f"  ℹ Filtrado para {G.number_of_nodes()} nós, {G.number_of_edges()} arestas")

    # Inicializar a rede PyVis
    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#0f0f23",
        font_color="#ffffff",
        select_menu=True,
        filter_menu=True,
    )

    # Transferir os nós e propriedades
    max_degree = max(dict(G.degree()).values()) if G.number_of_nodes() > 0 else 1

    for node, data in G.nodes(data=True):
        label_type = data.get("label", "MISC")
        color = NER_COLORS.get(label_type, "#95A5A6")
        label_pt = NER_LABELS_PT.get(label_type, "Outro")

        # Grau para setar o tamanho
        degree = G.degree(node)
        size = 8 + (degree / max(max_degree, 1)) * 50

        texto_hover = f"<b>{node}</b><br>Tipo: {label_pt} ({label_type})<br>Grau (conexões): {degree}"

        net.add_node(
            node,
            label=node,
            title=texto_hover,
            color=color,
            size=size,
            font={"size": max(8, min(14, 8 + degree))},
        )

    # Transferir as arestas
    max_weight = max(
        [G[u][v].get("weight", 1) for u, v in G.edges()],
        default=1,
    )
    # Converter weight para float caso venha como string do GraphML
    for u, v, data in G.edges(data=True):
        peso = data.get("weight", 1)
        if isinstance(peso, str):
            try:
                peso = float(peso)
            except ValueError:
                peso = 1.0
        # Normalizar espessura entre 0.5 e 6
        thickness = 0.5 + ((peso / max(float(max_weight), 1)) * 5.5)
        texto_aresta = f"Co-ocorrências: {int(peso)}"
        net.add_edge(u, v, value=thickness, title=texto_aresta, color="rgba(255,255,255,0.15)")

    # Configurar opções de física — estabilização rápida e parada
    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -80,
          "centralGravity": 0.015,
          "springLength": 120,
          "springConstant": 0.06,
          "avoidOverlap": 0.6
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based",
        "stabilization": {
          "enabled": true,
          "iterations": 200,
          "updateInterval": 50,
          "onlyDynamicEdges": false,
          "fit": true
        },
        "timestep": 0.5
      },
      "layout": {
        "improvedLayout": false
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "navigationButtons": true,
        "keyboard": true
      }
    }
    """)

    # Gerar arquivo HTML
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = str(FIGURES_DIR / html_filename)
    net.save_graph(output_path)

    # Pós-processamento: corrigir caminhos e injetar legenda
    _postprocess_html(output_path, title)

    print(f"  💾 Salvo: {html_filename}")
    return output_path


def _postprocess_html(html_path, title):
    """
    Pós-processa o HTML gerado pelo PyVis:
    1. Substitui referências locais a lib/ por versões CDN/inline
    2. Injeta legenda visual customizada
    """
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # --- 1. Corrigir referência ao utils.js (inlinar o conteúdo) ---
    utils_js_path = ROOT_DIR / "lib" / "bindings" / "utils.js"
    if utils_js_path.exists():
        with open(utils_js_path, "r", encoding="utf-8") as uf:
            utils_js_content = uf.read()
        html = html.replace(
            '<script src="lib/bindings/utils.js"></script>',
            f'<script type="text/javascript">\n{utils_js_content}\n</script>'
        )

    # --- 2. Substituir tom-select local por CDN ---
    html = html.replace(
        '<link href="lib/tom-select/tom-select.css" rel="stylesheet">',
        '<link href="https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/css/tom-select.css" rel="stylesheet">'
    )
    html = html.replace(
        '<script src="lib/tom-select/tom-select.complete.min.js"></script>',
        '<script src="https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/js/tom-select.complete.min.js"></script>'
    )

    # --- 3. Injetar legenda recolhível (toggle) ---
    legend_html = f"""
    <style>
      #legend-panel {{
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.35s ease, opacity 0.35s ease, padding 0.25s ease;
        opacity: 0;
        padding: 0 20px;
      }}
      #legend-panel.open {{
        max-height: 300px;
        opacity: 1;
        padding: 14px 20px;
      }}
      #legend-toggle {{
        cursor: pointer;
        user-select: none;
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 16px;
        border-radius: 10px;
        background: rgba(15,15,35,0.92);
        border: 1px solid rgba(255,255,255,0.18);
        color: #e0e0e0;
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
        font-weight: 600;
        backdrop-filter: blur(8px);
        box-shadow: 0 4px 18px rgba(0,0,0,0.45);
        transition: background 0.2s;
      }}
      #legend-toggle:hover {{ background: rgba(30,30,60,0.95); }}
      #legend-arrow {{ transition: transform 0.3s; font-size: 11px; }}
      #legend-arrow.open {{ transform: rotate(180deg); }}
    </style>

    <div id="graph-legend" style="
        position: fixed; bottom: 20px; left: 14px; z-index: 9999;
        font-family: 'Segoe UI', sans-serif; color: #fff;
    ">
      <!-- Cabeçalho clicável -->
      <div id="legend-toggle" onclick="toggleLegend()">
        <span style="font-size:15px;">📊</span>
        <span id="legend-title-short">Legenda</span>
        <span id="legend-arrow">▲</span>
      </div>

      <!-- Conteúdo expansível -->
      <div id="legend-panel" style="
          background: rgba(15,15,35,0.92);
          border: 1px solid rgba(255,255,255,0.15);
          border-top: none;
          border-radius: 0 0 10px 10px;
          box-shadow: 0 8px 24px rgba(0,0,0,0.45);
          backdrop-filter: blur(8px);
      ">
        <div style="font-size:13px; font-weight:700; margin-bottom:10px; color:#c8d6e5; line-height:1.4;">
            {title}
        </div>
        <div style="display:flex; flex-direction:column; gap:8px;">
            <span style="display:flex;align-items:center;gap:8px;">
                <span style="width:13px;height:13px;border-radius:50%;background:#4A90D9;flex-shrink:0;"></span>
                <span style="font-size:12px;">Pessoas (PER)</span>
            </span>
            <span style="display:flex;align-items:center;gap:8px;">
                <span style="width:13px;height:13px;border-radius:50%;background:#E74C3C;flex-shrink:0;"></span>
                <span style="font-size:12px;">Organizações (ORG)</span>
            </span>
            <span style="display:flex;align-items:center;gap:8px;">
                <span style="width:13px;height:13px;border-radius:50%;background:#2ECC71;flex-shrink:0;"></span>
                <span style="font-size:12px;">Locais (LOC)</span>
            </span>
            <span style="display:flex;align-items:center;gap:8px;">
                <span style="width:13px;height:13px;border-radius:50%;background:#95A5A6;flex-shrink:0;"></span>
                <span style="font-size:12px;">Outros (MISC)</span>
            </span>
        </div>
        <div style="font-size:11px; margin-top:10px; color:#777; border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;">
            Tamanho do nó = grau de conexões
        </div>
      </div><!-- /legend-panel -->
    </div><!-- /graph-legend -->

    <script>
      function toggleLegend() {{
        var panel = document.getElementById('legend-panel');
        var arrow = document.getElementById('legend-arrow');
        panel.classList.toggle('open');
        arrow.classList.toggle('open');
      }}
    </script>
    """
    html = html.replace("<body>", f"<body>{legend_html}", 1)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    print("=" * 70)
    print("SCRIPT 5: VISUALIZADOR INTERATIVO (PyVis)")
    print("=" * 70)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    k = load_k_chars()

    # Gerar interativo para TODOS os 3 grafos
    graphs_to_generate = [
        ("cooccurrence_sentence.graphml", "interativo_sentenca.html", "Grafo Interativo — Sentença"),
        ("cooccurrence_paragraph.graphml", "interativo_paragrafo.html", "Grafo Interativo — Parágrafo"),
        ("cooccurrence_k_chars.graphml", "interativo_k_chars.html", f"Grafo Interativo — K-Caracteres (K={k})"),
    ]

    generated = []
    for graph_file, html_file, title in graphs_to_generate:
        result = generate_interactive(graph_file, html_file, title)
        if result:
            generated.append(result)

    if generated:
        # Abrir o último grafo gerado no navegador
        print(f"\n  🌐 Abrindo no navegador: {generated[-1]}")
        webbrowser.open('file://' + str(Path(generated[-1]).resolve()))

    print("\n" + "=" * 70)
    print(f"VISUALIZAÇÕES INTERATIVAS GERADAS: {len(generated)}")
    print("=" * 70)


if __name__ == '__main__':
    main()
