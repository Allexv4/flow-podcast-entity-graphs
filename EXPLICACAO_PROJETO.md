# Guia de Explicação: Projeto Grafos de Co-ocorrência NER

Este documento serve como roteiro para sua apresentação ao professor. Ele detalha cada etapa técnica, as decisões de projeto e os conceitos teóricos aplicados.

---

## 1. O Que Dizer ao Professor (Pitch Inicial)

"Professor, este projeto implementa um pipeline completo de Análise de Dados e Teoria dos Grafos. Nós transformamos horas de conversa em áudio (via transcrições) em uma rede de conhecimento interconectada. O diferencial aqui é que o grafo não é apenas uma lista de nomes, mas uma representação de como entidades (Pessoas, Organizações e Lugares) se relacionam dentro do contexto do discurso do Lex Fridman Podcast #494, com Jensen Huang (CEO da NVIDIA), utilizando três métricas de proximidade distintas para validar a densidade da rede."

---

## 2. Anatomia do Projeto (A "Aula")

### A. Coleta e Preparação (Engenharia de Dados)
*   **Fonte:** YouTube Transcripts.
*   **Vídeo:** Jensen Huang: NVIDIA - The $4 Trillion Company & the AI Revolution | Lex Fridman Podcast #494
*   **Problema:** Legendas auto-geradas não têm pontuação nem parágrafos.
*   **Solução:** Criamos uma **Heurística de Silêncio**. Se o tempo entre duas frases é > 0.8s, inferimos uma *Sentença*. Se é > 2.0s, inferimos um *Parágrafo*. Isso é crucial para dar estrutura semântica ao texto bruto.

### B. Extração de Entidades (NER - Named Entity Recognition)
*   **Ferramenta:** spaCy (`en_core_web_lg`).
*   **Por que spaCy?** Escolhemos pelo **determinismo** (resultados reprodutíveis) e pela eficiência local (sem custos de API).
*   **Categorias:** `PER` (Pessoas), `ORG` (Organizações), `LOC` (Locais), `MISC` (Eventos/Miscelânea).
*   **Mapeamento de Labels:** O spaCy inglês usa labels como `PERSON`, `GPE`, `NORP` — nosso pipeline mapeia automaticamente para as categorias do projeto (`PER`, `LOC`, `MISC`).
*   **Unificação de Nós:** Fizemos uma normalização (NFC, Title Case) para que "Jensen Huang" e "jensen huang" fossem o mesmo nó no grafo.

### C. A Teoria dos Grafos em Prática
O coração do trabalho é a **Co-ocorrência**. Uma aresta é criada se duas entidades aparecem "perto" uma da outra. Testamos 3 distâncias:
1.  **Sentença (Rigorosa):** Só liga se estiverem na mesma frase. Gera grafos esparsos (49 nós, 57 arestas, 10 componentes).
2.  **Parágrafo (Semântica):** Liga se estiverem no mesmo bloco de assunto. Gera o "Componente Gigante" (95 nós, 1002 arestas, 1 componente — rede totalmente conexa).
3.  **K-Caracteres (Métrica Fixa):** Janela de 500 caracteres. É um meio-termo matemático que independe da estrutura do texto (87 nós, 283 arestas, 2 componentes).

### D. Métricas Topológicas (O que o gráfico nos diz?)
*   **Distribuição de Grau (Scale-Free):** O gráfico log-log mostra que a maioria das entidades aparece pouco, mas poucas entidades (hubs como NVIDIA, AI, CUDA) conectam quase todo o grafo. Isso é típico de redes sociais e de linguagem natural.
*   **Densidade:** Mostramos como a densidade aumenta conforme relaxamos a métrica de distância (0.048 Sentença → 0.224 Parágrafo).

---

## 3. Guia de Demonstração (O que Mostrar)

### 1. Mostre as Imagens Estáticas (`figures/`)
*   Aponte o **Grafo por Parágrafo**. Note como existem "clusters" (grupos).
*   Explique que o **tamanho do nó** representa o **Grau** (quantas conexões ele tem).
*   Aponte as cores: Azul = Pessoas, Vermelho = Organizações, Verde = Locais.
*   Destaque entidades centrais: NVIDIA, AI, CUDA, GPU, Jensen Huang.

### 2. A "Cereja do Bolo": Os Grafos Interativos
*   Abra os arquivos em `figures/interativo_*.html` no navegador.
*   **Destaque:** "Professor, aqui podemos navegar na rede em tempo real. Se eu clicar em um nó, vejo todas as conexões de uma determinada entidade citada no podcast. Podemos ver claramente como NVIDIA está no centro de tudo, conectada a AI, CUDA, GPU, TSMC..."
*   Use o dropdown "Select a Node by ID" para selecionar entidades específicas e ver sua vizinhança.

### 3. Mostre o Código de Geração (`execution/3_gerador_grafos.py`)
*   Se o professor pedir para ver o código, mostre como você usa a biblioteca `networkx` para criar o objeto `G = nx.Graph()` e como adiciona pesos às arestas (`weight`).

---

## 4. Possíveis Perguntas do Professor (Prepare-se!)

1.  **"Por que os grafos de sentença são tão vazios?"**
    *   *Resposta:* Porque em uma conversa técnica, raramente se cita o nome de duas entidades na mesma frase curta. A relação costuma se desenvolver ao longo de um parágrafo de fala. No nosso caso, o grafo de sentença tem apenas 57 arestas vs 1002 no parágrafo.
2.  **"Como você lidou com nomes repetidos?"**
    *   *Resposta:* Usamos normalização de texto e filtros no extrator NER para garantir que a mesma entidade não criasse múltiplos nós. Além disso, mapeamos as labels do spaCy inglês (PERSON, GPE, etc.) para nossas categorias (PER, LOC, etc.).
3.  **"O que o peso das arestas significa?"**
    *   *Resposta:* O número de vezes que aquelas duas entidades apareceram juntas. Quanto mais grosso o traço no grafo interativo, mais vezes elas foram citadas no mesmo contexto. Por exemplo, CUDA-Geforce tem peso 36, pois são frequentemente discutidos juntos.
4.  **"Por que o podcast está em inglês?"**
    *   *Resposta:* Este é o episódio específico indicado para análise. O pipeline foi adaptado para funcionar com modelos NLP em ambos idiomas (pt e en), selecionando automaticamente o modelo correto baseado na configuração.

---

## 5. Resumo Técnico do Stack
*   **Linguagem:** Python 3.10+
*   **Processamento de Texto:** spaCy (`en_core_web_lg`)
*   **Estrutura de Dados (Grafos):** NetworkX
*   **Visualização:** Matplotlib (estática) e PyVis (interativa)
*   **Configuração:** YAML
