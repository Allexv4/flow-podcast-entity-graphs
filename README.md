# Grafos de Co-ocorrência com NER — Transcrições de Podcasts YouTube

> Projeto desenvolvido como "Trabalho 01" da disciplina de Algoritmos e Estrutura de Dados II (DCA3702) da UFRN.

## 👤 Integrantes
- **José Alex Araújo de Santana** — Matrícula: 20220011457

---

## 📖 Descrição das Atividades

O objetivo deste projeto é construir grafos de co-ocorrência baseados em Entidades Nomeadas (NER) extraídas da transcrição do episódio #494 do *Lex Fridman Podcast* com **Jensen Huang** (CEO da NVIDIA). O pipeline foi dividido em cinco etapas principais, cada uma executada por um script dedicado.

### 1. Pipeline de Coleta de Dados (`1_coleta_dados.py`)
Utilizamos a biblioteca `youtube-transcript-api` para extrair as legendas diretamente do vídeo selecionado no YouTube do canal *Lex Fridman*. Foram filtradas legendas em Inglês.
Como as legendas auto-geradas muitas vezes vêm fragmentadas e sem pontuação, implementamos uma heurística de reconstrução: baseamo-nos nas "pausas" (gaps de tempo) entre um trecho e outro para inferir o que seria um final de sentença (pausas curtas > 0.8s) e uma quebra de parágrafo (pausas longas > 2.0s). O resultado limpo e normalizado (NFC) foi salvo na pasta `data/processed`.

### 2. Extração de Entidades (NER) (`2_extrator_ner.py`)
Para o reconhecimento das entidades, utilizamos a biblioteca NLP **spaCy** com o modelo robusto para a língua inglesa `en_core_web_lg`. A escolha pelo spaCy em detrimento de uma API de LLM (Large Language Model) baseou-se em três fatores:
- **Determinismo:** O modelo entrega o mesmo resultado garantido toda vez que roda (sem variações aleatórias).
- **Offline e Gratuito:** Processamento local sem dependência de rate limits de API ou requisições de rede.
- **Velocidade:** Processa o grande volume de texto das entrevistas longas de forma muito mais eficiente.

As categorias filtradas foram: Pessoas (`PER`), Organizações (`ORG`), Localidades (`LOC`) e Miscelâneas (`MISC`). As labels nativas do spaCy inglês (como `PERSON`, `GPE`, `NORP`, etc.) são mapeadas para as categorias do projeto. O texto das entidades passou por uma normalização (remoção de artigos, *title case*) para unificação de nós, registrando exatamente a linha (sentença e parágrafo) e a posição inicial no arquivo onde ocorreram.

### 3. Formação dos Grafos de Co-ocorrência (`3_gerador_grafos.py`)
Os grafos foram gerados utilizando a biblioteca `networkx` e salvos no formato GraphML (`data/graphs/`). Para explorar o peso semântico das conexões, calculamos co-ocorrências (arestas) considerando três distâncias (janelas) distintas:

- **Distância 1: Sentença.** Duas entidades co-ocorrem se ambas foram citadas na MESMA frase. Esta distância traz ligações de alta precisão (estavam num contexto super amarrado), mas resulta em um grafo consideravelmente mais **esparso**.
- **Distância 2: Parágrafo.** Considera toda a ideia discutida no bloco de texto. Ele é bem mais conexo que o de sentenças, ligando entidades pelo contexto temático próximo.
- **Distância 3: $K$-Caracteres ($K=4000$).** Uma janela deslizante que engloba 4.000 caracteres (equivalente a aproximadamente 3–5 minutos de áudio do podcast), atravessando pontuações e fronteiras de frase/parágrafo. É uma granularidade controlável que evita as perversidades de parágrafos gigantes e mantém a proximidade baseada exclusivamente no comprimento textual — gerando uma janela semanticamente coerente para conversas longas.

### 4. Plotagem de Resultados (`4_plot_resultados.py`)
Gera visualizações estáticas dos grafos e gráficos comparativos das métricas topológicas.

### 5. Visualizador Interativo (`5_interativo_pyvis.py`)
Gera páginas HTML interativas utilizando a biblioteca **PyVis** para navegação em tempo real pelos grafos, com funcionalidades de zoom, seleção de nós, filtragem e destaque de vizinhanças.

---

## 📊 Resultados e Imagens

### Grafos e Visualização de Topologia
*(Imagens extraídas em alta resolução. Nós: Pessoas em azul, Organizações em vermelho, Locais em verde, MISC em cinza. O diâmetro do nó é proporcional ao Grau).*

<div align="center">
  <h4>Grafo por Sentença</h4>
  <img src="figures/grafo_sentenca.png" alt="Grafo Sentença" width="800"/>
  <br><br>
  <h4>Grafo por Parágrafo</h4>
  <img src="figures/grafo_paragrafo.png" alt="Grafo Parágrafo" width="800"/>
  <br><br>
  <h4>Grafo por K-Caracteres (K=4000)</h4>
  <img src="figures/grafo_k_caracteres.png" alt="Grafo K-Caracteres" width="800"/>
</div>

<br>

### Top Entidades e Distribuição
<div align="center">
  <img src="figures/top_entidades.png" alt="Top Entidades" width="1000"/>
  <br><br>
  <img src="figures/distribuicao_grau.png" alt="Distribuição de Grau" width="800"/>
</div>

<br>

### Comparativo Analítico de Métricas

<div align="center">
  <img src="figures/comparativo_metricas.png" alt="Comparativo Métricas" width="800"/>
</div>

| Métrica | Sentença | Parágrafo | K-Chars (K=4000) |
| --- | --- | --- | --- |
| **Nós Totais** | 49 | 95 | 95 |
| **Arestas Totais** | 57 | 1002 | 771 |
| **Densidade** | 0.048 | 0.224 | 0.173 |
| **Grau Médio** | 2.33 | 21.09 | 16.23 |
| **Clustering Médio** | 0.333 | 0.906 | 0.800 |
| **Componentes Conexos** | 10 | 1 | 1 |
| **Diâmetro** | 4 | 4 | 3 |

---

## 🔍 Análise Crítica

### Sentença vs Parágrafo vs K-Caracteres
Como visto pelos resultados plotados em `comparativo_metricas.png`, a restrição gerada pela barreira da **sentença** faz com que entidades fiquem "ilhadas" mais facilmente (nota-se 10 componentes independentes vs apenas 1 no grafo de parágrafo). Já na modelagem via **parágrafos**, o aumento substancial do Grau Médio (de 2.33 para 21.09) indica que criar *clusters* discursivos (em que tudo no parágrafo se relaciona) aumenta substancialmente a conectividade do "componente gigante". A modelagem por $K=500$ cria uma alternativa controlável para evitar as perversidades de parágrafos gigantes que perdem semântica — mantendo a proximidade baseada única e exclusivamente no comprimento textual.

### Insights sobre o Conteúdo
No episódio analisado, Jensen Huang (CEO da NVIDIA) discute em profundidade a revolução da IA, a arquitetura de GPUs, CUDA e a cadeia de suprimentos de semicondutores. As entidades mais centrais no grafo são **NVIDIA**, **AI**, **CUDA** e **GPU**, refletindo com precisão os temas dominantes da conversa. Observam-se *clusters* temáticos claros:
- **Cluster de Hardware:** NVIDIA, GPU, CPU, Grace Blackwell, NVLink, TSMC
- **Cluster de IA/Software:** AI, CUDA, LLM, Claude, Codex, GPT
- **Cluster Geopolítico:** China, Taiwan, United States

### Distribuição de Grau (Scale-Free)
Notou-se pelas plotagens da Distribuição de Grau ($log\text{-}log$) que ela segue visualmente uma tendência clara de rede "livre de escala" (*Scale-Free* ou Lei da Potência) **principalmente** nas vizinhanças maiores (parágrafo). Um conjunto seleto e agudo de entidades é mencionado recorrentemente guiando a retórica do episódio, em contraposição à esmagadora e volumosa "cauda longa" das entidades citadas uma única vez incidentalmente ao decorrer das 3+ horas ininterruptas de conversa.

### Limitações
- Erros sistemáticos herdados das legendas auto-geradas do YouTube (o NLP, por mais forte e determinístico que seja, ainda engole entidades erroneamente grafadas).
- A segmentação de entidades pode juntar menções erradas por falta rigorosa no "Entity Resolution" (ex: "Jensen" e "Jensen Huang" podem gerar nós separados).
- Siglas técnicas como AI, GPU, CPU são classificadas como ORG pelo spaCy, quando na realidade são conceitos/tecnologias.

---

## 🎥 Apresentação
> 🔗 [Link do Vídeo da Apresentação no Loom](#) (https://www.loom.com/share/dd06c1ac95a24edb93080ce63d1f4603)

---

## 🔧 Como Reproduzir

### 1. Instalação (Ambiente Python 3.10+)
Clone o repositório e baixe as bibliotecas e o modelo de processamento de texto:
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

### 2. Execução do Pipeline (Ordem recomendada)
```bash
# 1. Coletar os dados do vídeo declarado em config/videos.yaml
python execution/1_coleta_dados.py

# 2. O extrator gerará os JSONs de NER em data/ner_output
python execution/2_extrator_ner.py

# 3. Este script varre os JSONs e cospe as topologias dos 3 grafos.
python execution/3_gerador_grafos.py

# 4. Desenha localmente as imagens das topologias e gráficos de atributos.
python execution/4_plot_resultados.py

# 5. Gera os grafos interativos (HTML) para navegação no browser.
python execution/5_interativo_pyvis.py
```

## 📚 Referências
- Documentação do YouTube Transcript API
- Documentação NER: spaCy NLP framework (`en_core_web_lg`)
- Ivanovitchm/DataStructure classes & Datasets de grafos
- [Lex Fridman Podcast #494 — Jensen Huang: NVIDIA](https://youtu.be/vif8NQcjVf0)
