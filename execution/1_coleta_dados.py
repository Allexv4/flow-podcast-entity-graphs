"""
=============================================================================
Script 1: Coleta de Dados — Transcrições do YouTube
=============================================================================
Baixa transcrições de vídeos do YouTube (Flow Podcast) e salva em formato
estruturado para processamento posterior.

Uso:
    python execution/1_coleta_dados.py

Entrada:  config/videos.yaml
Saída:    data/raw/{video_id}.json       (dados brutos com timestamps)
          data/processed/{video_id}.txt  (texto limpo segmentado em parágrafos)
=============================================================================
"""

import io
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

# Fix Windows console encoding for emoji/unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import yaml
from youtube_transcript_api import YouTubeTranscriptApi


# =============================================================================
# Configurações
# =============================================================================
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "videos.yaml"
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

# Thresholds para reconstrução de parágrafos a partir de legendas auto-geradas
GAP_PARAGRAPH = 2.0   # segundos de pausa -> novo parágrafo
GAP_SENTENCE = 0.8    # segundos de pausa -> nova sentença (ponto final)


def load_config() -> dict:
    """Carrega a configuração do projeto a partir do YAML."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalize_text(text: str) -> str:
    """Normaliza texto Unicode (NFC) e limpa espaços extras."""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def reconstruct_text(segments: list[dict]) -> str:
    """
    Reconstrói texto contínuo a partir de segmentos de legenda do YouTube.
    Usa os gaps de tempo entre segmentos para inferir quebras de parágrafo e sentença.
    """
    if not segments:
        return ""

    paragraphs = []
    current_paragraph = []
    current_sentence = []

    for i, seg in enumerate(segments):
        text = normalize_text(seg.get("text", ""))
        if not text or text in ("[Música]", "[Music]", "[Aplausos]", "[Risos]"):
            continue

        current_sentence.append(text)

        if i < len(segments) - 1:
            current_end = seg.get("start", 0) + seg.get("duration", 0)
            next_start = segments[i + 1].get("start", 0)
            gap = next_start - current_end

            if gap >= GAP_PARAGRAPH:
                sentence = " ".join(current_sentence)
                if not sentence.endswith((".", "!", "?", ":", ";")):
                    sentence += "."
                current_paragraph.append(sentence)
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
                current_sentence = []
            elif gap >= GAP_SENTENCE:
                sentence = " ".join(current_sentence)
                if not sentence.endswith((".", "!", "?", ":", ";")):
                    sentence += "."
                current_paragraph.append(sentence)
                current_sentence = []

    # Adicionar resíduos
    if current_sentence:
        sentence = " ".join(current_sentence)
        if not sentence.endswith((".", "!", "?", ":", ";")):
            sentence += "."
        current_paragraph.append(sentence)
    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))

    return "\n\n".join(paragraphs)


def fetch_transcript(video_id: str, language: str = "pt") -> list[dict] | None:
    """
    Tenta obter a transcrição de um vídeo do YouTube.
    Usa a nova API (v1.2+): YouTubeTranscriptApi().fetch()
    """
    ytt = YouTubeTranscriptApi()

    # Tentar com idiomas preferenciais
    lang_codes = [language, f"{language}-BR", "pt", "pt-BR"]

    try:
        result = ytt.fetch(video_id, languages=lang_codes)
        segments = result.to_raw_data()
        print(f"  [OK] Legenda obtida: {len(segments)} segmentos")
        return segments
    except Exception as e1:
        print(f"  [!] Falha com idiomas {lang_codes}: {e1}")

        # Fallback: tentar listar idiomas disponíveis e pegar qualquer um
        try:
            transcript_list = ytt.list(video_id)
            available = []
            for t in transcript_list:
                available.append(t.language_code)

            if available:
                print(f"  [!] Idiomas disponíveis: {available}")
                # Tentar o primeiro disponível
                result = ytt.fetch(video_id, languages=[available[0]])
                segments = result.to_raw_data()
                print(f"  [OK] Usando legenda em '{available[0]}': {len(segments)} segmentos")
                return segments
        except Exception as e2:
            print(f"  [X] Erro ao listar/buscar legendas: {e2}")

    return None


def save_raw(video_id: str, title: str, segments: list[dict]) -> None:
    """Salva dados brutos (JSON com timestamps) em data/raw/."""
    raw_path = RAW_DIR / f"{video_id}.json"
    data = {
        "video_id": video_id,
        "title": title,
        "total_segments": len(segments),
        "segments": segments,
    }
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [S] Dados brutos salvos: {raw_path.name}")


def save_processed(video_id: str, title: str, text: str) -> None:
    """Salva texto processado (segmentado em parágrafos) em data/processed/."""
    processed_path = PROCESSED_DIR / f"{video_id}.txt"
    header = f"# Titulo: {title}\n# Video ID: {video_id}\n\n"
    with open(processed_path, "w", encoding="utf-8") as f:
        f.write(header + text)

    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    sentences = text.count(".") + text.count("!") + text.count("?")
    chars = len(text)
    print(f"  [S] Texto processado: {processed_path.name}")
    print(f"      -> {len(paragraphs)} paragrafos, ~{sentences} sentencas, {chars} caracteres")


def main():
    """Pipeline principal de coleta de dados."""
    print("=" * 70)
    print("SCRIPT 1: COLETA DE DADOS - TRANSCRICOES DO YOUTUBE")
    print("=" * 70)

    config = load_config()
    videos = config.get("videos", [])
    language = config.get("project", {}).get("language", "pt")

    print(f"\n[i] {len(videos)} videos configurados para coleta")
    print(f"[i] Idioma preferencial: {language}\n")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0

    for i, video in enumerate(videos, 1):
        video_id = video["id"]
        title = video.get("title", f"Video {video_id}")
        print(f"\n[{i}/{len(videos)}] {title}")
        print(f"         ID: {video_id}")

        # Verificar se já foi coletado
        processed_path = PROCESSED_DIR / f"{video_id}.txt"
        if processed_path.exists():
            print(f"  [>>] Ja coletado anteriormente. Pulando...")
            success_count += 1
            continue

        # Buscar transcrição
        segments = fetch_transcript(video_id, language)

        if segments is None:
            fail_count += 1
            continue

        # Salvar dados brutos
        save_raw(video_id, title, segments)

        # Reconstruir e salvar texto processado
        text = reconstruct_text(segments)
        if text.strip():
            save_processed(video_id, title, text)
            success_count += 1
        else:
            print(f"  [!] Texto vazio apos processamento. Pulando...")
            fail_count += 1

        # Rate limiting
        if i < len(videos):
            time.sleep(1.5)

    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO DA COLETA")
    print("=" * 70)
    print(f"  Sucesso: {success_count}/{len(videos)}")
    print(f"  Falhas:  {fail_count}/{len(videos)}")
    print(f"  Dados brutos:     {RAW_DIR}")
    print(f"  Dados processados: {PROCESSED_DIR}")
    print("=" * 70)

    if success_count == 0:
        print("\n[X] Nenhum video foi coletado com sucesso!")
        sys.exit(1)


if __name__ == "__main__":
    main()
