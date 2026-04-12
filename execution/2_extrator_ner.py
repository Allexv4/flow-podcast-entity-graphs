"""
=============================================================================
Script 2: Extrator de Entidades Nomeadas (NER)
=============================================================================
Utiliza spaCy com o modelo pt_core_news_lg para extrair e classificar
entidades nomeadas das transcrições processadas.

Uso:
    python execution/2_extrator_ner.py

Entrada:  data/processed/{video_id}.txt
Saída:    data/ner_output/{video_id}_entities.json
=============================================================================
"""

import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import spacy
import yaml


# =============================================================================
# Configurações
# =============================================================================
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "videos.yaml"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
NER_OUTPUT_DIR = ROOT_DIR / "data" / "ner_output"

# Modelo spaCy para português
SPACY_MODEL = "pt_core_news_lg"


def load_config() -> dict:
    """Carrega a configuração do projeto."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_text(filepath: Path) -> str:
    """Carrega texto processado, removendo linhas de cabeçalho (começam com #)."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Remover cabeçalho (linhas que começam com #)
    content_lines = [line for line in lines if not line.startswith("#")]
    return "".join(content_lines).strip()


def normalize_entity(text: str) -> str:
    """
    Normaliza o texto de uma entidade para evitar duplicatas.

    - Remove artigos/preposições iniciais
    - Normaliza espaços
    - Aplica title case
    """
    text = text.strip()

    # Remover artigos/preposições iniciais comuns em português
    prefixes = [
        "o ", "a ", "os ", "as ",
        "um ", "uma ", "uns ", "umas ",
        "do ", "da ", "dos ", "das ",
        "no ", "na ", "nos ", "nas ",
        "ao ", "à ", "aos ", "às ",
    ]
    text_lower = text.lower()
    for prefix in prefixes:
        if text_lower.startswith(prefix) and len(text) > len(prefix) + 1:
            text = text[len(prefix):]
            break

    # Normalizar espaços
    text = re.sub(r"\s+", " ", text).strip()

    # Title case (mas preservar siglas em maiúsculo)
    words = text.split()
    normalized_words = []
    for word in words:
        if word.isupper() and len(word) >= 2:
            normalized_words.append(word)  # Preservar siglas (ex: UFRN, IBM)
        else:
            normalized_words.append(word.title())
    
    return " ".join(normalized_words)


def is_valid_entity(text: str, label: str, min_length: int = 2) -> bool:
    """
    Verifica se uma entidade extraída é válida.

    Descarta:
    - Entidades muito curtas
    - Entidades compostas apenas por números
    - Entidades que são apenas pontuação/símbolos
    - Tokens de ruído comuns em transcrições
    """
    if len(text) < min_length:
        return False

    if text.isdigit():
        return False

    if re.match(r"^[\W\d]+$", text):
        return False

    # Ruídos comuns em transcrições do YouTube
    noise_patterns = [
        r"^\[.*\]$",        # [Música], [Risos], etc.
        r"^(hum|uhm|ah|eh|né|tá|aí|ué|ahn)$",
    ]
    for pattern in noise_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return False

    return True


def segment_text(text: str) -> tuple[list[str], list[str]]:
    """
    Segmenta o texto em sentenças e parágrafos.

    Retorna:
        sentences: lista de sentenças
        paragraphs: lista de parágrafos
    """
    # Parágrafos: separados por linhas em branco
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Sentenças: usamos o nlp do spaCy internamente, mas aqui fazemos
    # a segmentação prévia para mapear IDs
    sentences = []
    for para in paragraphs:
        # Split por pontuação final seguida de espaço
        sents = re.split(r'(?<=[.!?])\s+', para)
        sentences.extend([s.strip() for s in sents if s.strip()])

    return sentences, paragraphs


def extract_entities(nlp, text: str, config: dict) -> dict:
    """
    Extrai entidades nomeadas do texto usando spaCy.

    Retorna um dicionário com todas as entidades e suas ocorrências,
    incluindo posições por sentença, parágrafo e caractere.
    """
    min_length = config.get("project", {}).get("min_entity_length", 2)
    allowed_labels = set(config.get("project", {}).get("ner_labels", ["PER", "ORG", "LOC", "MISC"]))

    # Segmentar texto
    sentences, paragraphs = segment_text(text)

    # Mapear posições de parágrafos e sentenças no texto original
    paragraph_spans = []
    search_start = 0
    for para in paragraphs:
        idx = text.find(para, search_start)
        if idx >= 0:
            paragraph_spans.append((idx, idx + len(para)))
            search_start = idx + len(para)

    sentence_spans = []
    search_start = 0
    for sent in sentences:
        idx = text.find(sent, search_start)
        if idx >= 0:
            sentence_spans.append((idx, idx + len(sent)))
            search_start = idx + len(sent)

    # Processar texto com spaCy (em chunks se muito grande)
    max_length = 100000
    all_entities_raw = []

    if len(text) <= max_length:
        doc = nlp(text)
        for ent in doc.ents:
            all_entities_raw.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            })
    else:
        # Processar em chunks respeitando parágrafos
        offset = 0
        for para in paragraphs:
            para_start = text.find(para, offset)
            doc = nlp(para)
            for ent in doc.ents:
                all_entities_raw.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": para_start + ent.start_char,
                    "end": para_start + ent.end_char,
                })
            offset = para_start + len(para)

    # Agrupar e filtrar entidades
    entity_map = defaultdict(lambda: {
        "text": "",
        "label": "",
        "count": 0,
        "occurrences": [],
    })

    for ent in all_entities_raw:
        raw_text = ent["text"]
        label = ent["label"]

        # Filtrar labels não desejadas
        if label not in allowed_labels:
            continue

        # Validar entidade
        if not is_valid_entity(raw_text, label, min_length):
            continue

        # Normalizar
        normalized = normalize_entity(raw_text)
        if not normalized or len(normalized) < min_length:
            continue

        # Determinar sentence_id e paragraph_id
        char_start = ent["start"]
        char_end = ent["end"]

        sentence_id = -1
        for sid, (s_start, s_end) in enumerate(sentence_spans):
            if s_start <= char_start < s_end:
                sentence_id = sid
                break

        paragraph_id = -1
        for pid, (p_start, p_end) in enumerate(paragraph_spans):
            if p_start <= char_start < p_end:
                paragraph_id = pid
                break

        # Adicionar ao mapa
        key = (normalized, label)
        entity_map[key]["text"] = normalized
        entity_map[key]["label"] = label
        entity_map[key]["count"] += 1
        entity_map[key]["occurrences"].append({
            "sentence_id": sentence_id,
            "paragraph_id": paragraph_id,
            "char_start": char_start,
            "char_end": char_end,
        })

    # Converter para lista e ordenar por frequência
    entities_list = sorted(entity_map.values(), key=lambda x: x["count"], reverse=True)

    return {
        "total_entities": len(entities_list),
        "total_mentions": sum(e["count"] for e in entities_list),
        "total_sentences": len(sentences),
        "total_paragraphs": len(paragraphs),
        "total_characters": len(text),
        "entities": entities_list,
    }


def main():
    """Pipeline principal de extração NER."""
    print("=" * 70)
    print("SCRIPT 2: EXTRAÇÃO DE ENTIDADES NOMEADAS (NER)")
    print("=" * 70)

    # Carregar configuração
    config = load_config()
    videos = config.get("videos", [])

    # Carregar modelo spaCy
    print(f"\n🔧 Carregando modelo spaCy: {SPACY_MODEL}")
    try:
        nlp = spacy.load(SPACY_MODEL)
        print(f"  ✓ Modelo carregado com sucesso")
    except OSError:
        print(f"  ✗ Modelo '{SPACY_MODEL}' não encontrado!")
        print(f"  → Execute: python -m spacy download {SPACY_MODEL}")
        sys.exit(1)

    # Desativar componentes desnecessários para performance
    # Manter apenas tok2vec, ner e o sentencizer
    disabled = [pipe for pipe in nlp.pipe_names if pipe not in ("tok2vec", "ner", "parser")]
    if disabled:
        print(f"  ℹ Componentes desativados para performance: {disabled}")

    # Garantir diretório de saída
    NER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_entities = 0
    total_mentions = 0

    for i, video in enumerate(videos, 1):
        video_id = video["id"]
        title = video.get("title", f"Video {video_id}")

        print(f"\n[{i}/{len(videos)}] 🔍 Processando: {title}")

        # Verificar se transcrição existe
        text_path = PROCESSED_DIR / f"{video_id}.txt"
        if not text_path.exists():
            print(f"  ⚠ Transcrição não encontrada: {text_path}. Pulando...")
            continue

        # Verificar se já foi processado
        output_path = NER_OUTPUT_DIR / f"{video_id}_entities.json"
        if output_path.exists():
            print(f"  ⏭ Já processado anteriormente. Pulando...")
            # Carregar para contar totais
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            total_entities += existing.get("total_entities", 0)
            total_mentions += existing.get("total_mentions", 0)
            continue

        # Carregar texto
        text = load_text(text_path)
        if not text:
            print(f"  ⚠ Texto vazio. Pulando...")
            continue

        print(f"  📄 Texto carregado: {len(text)} caracteres")

        # Extrair entidades
        result = extract_entities(nlp, text, config)

        # Adicionar metadados
        result["video_id"] = video_id
        result["video_title"] = title

        # Salvar resultado
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        total_entities += result["total_entities"]
        total_mentions += result["total_mentions"]

        print(f"  ✓ {result['total_entities']} entidades únicas ({result['total_mentions']} menções)")
        print(f"    → Sentenças: {result['total_sentences']} | Parágrafos: {result['total_paragraphs']}")

        # Mostrar top-5 entidades
        for j, ent in enumerate(result["entities"][:5], 1):
            print(f"    {j}. {ent['text']} ({ent['label']}) — {ent['count']}x")

        print(f"  💾 Salvo: {output_path}")

    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO DA EXTRAÇÃO NER")
    print("=" * 70)
    print(f"  📊 Total de entidades únicas: {total_entities}")
    print(f"  📊 Total de menções:          {total_mentions}")
    print(f"  📁 Saída: {NER_OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
