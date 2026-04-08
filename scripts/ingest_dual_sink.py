from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen

import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path('/home/ecode/Documents/projetos/projeto-rag')
VAULT = Path('/home/ecode/Documents/projetos/obsidian/obsidian-vault')
CHROMA_PATH = ROOT / 'sources' / 'rag_memory' / '02 - RAG with memory' / 'chroma_db'
STATE_DIR = ROOT / 'analises' / 'ingest_state'

DEFAULT_MODEL = 'paraphrase-multilingual-MiniLM-L12-v2'

ALLOWED_FILE_EXTS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.csv',
    '.txt', '.json', '.xml', '.html', '.htm', '.yaml', '.yml', '.md'
}


@dataclass
class SourceItem:
    source_type: str  # web | file
    source_uri: str
    title: str
    content: str
    content_hash: str
    raw_path: str


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec='seconds')


def slugify(value: str) -> str:
    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9]+', '_', value)
    return value.strip('_') or 'source'


def clean_text_from_html(html: str) -> str:
    html = re.sub(r'(?is)<script[^>]*>.*?</script>', ' ', html)
    html = re.sub(r'(?is)<style[^>]*>.*?</style>', ' ', html)
    html = re.sub(r'(?is)<noscript[^>]*>.*?</noscript>', ' ', html)
    html = re.sub(r'(?i)</(p|div|li|h1|h2|h3|h4|h5|h6|section|article|tr|br)>', '\n', html)
    text = re.sub(r'(?s)<[^>]+>', ' ', html)
    text = unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def html_title(html: str, fallback: str) -> str:
    m = re.search(r'(?is)<title[^>]*>(.*?)</title>', html)
    if not m:
        return fallback
    title = clean_text_from_html(m.group(1)).strip()
    return title or fallback


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = (text or '').strip()
    if not text:
        return []
    if overlap >= chunk_size:
        raise ValueError('overlap deve ser menor que chunk_size')

    out: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        piece = text[start:end]

        if end < n:
            br = piece.rfind('\n\n')
            if br > int(len(piece) * 0.7):
                end = start + br + 2
            else:
                sp = piece.rfind('. ')
                if sp > int(len(piece) * 0.7):
                    end = start + sp + 2

        frag = text[start:end].strip()
        if frag:
            out.append(frag)

        if end >= n:
            break
        start = max(0, end - overlap)

    return out


def fetch_url(url: str, timeout: int = 20) -> tuple[str, str]:
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (RAG Ingest SOHO)'})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        ctype = (resp.headers.get('Content-Type') or '').lower()
    enc = 'utf-8'
    m = re.search(r'charset=([\w\-]+)', ctype)
    if m:
        enc = m.group(1)
    html = data.decode(enc, errors='ignore')
    return html, ctype


def normalize_url(base: str, href: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith('mailto:') or href.startswith('javascript:'):
        return None
    abs_url = urljoin(base, href)
    abs_url, _frag = urldefrag(abs_url)
    p = urlparse(abs_url)
    if p.scheme not in {'http', 'https'}:
        return None
    return abs_url


def extract_links(base_url: str, html: str) -> list[str]:
    links = []
    for href in re.findall(r'(?is)href\s*=\s*["\']([^"\']+)["\']', html):
        n = normalize_url(base_url, href)
        if n:
            links.append(n)
    return links


def crawl_web(start_url: str, source_name: str, max_pages: int, max_depth: int, allow_domain: str | None,
              sink_root: Path) -> tuple[list[SourceItem], list[dict]]:
    parsed = urlparse(start_url)
    domain = (allow_domain or parsed.netloc).lower()
    day = datetime.now().strftime('%Y-%m-%d')
    base_dir = sink_root / '10 Fontes Brutas' / 'Web' / slugify(source_name) / day
    pages_dir = base_dir / 'pages'
    pages_dir.mkdir(parents=True, exist_ok=True)

    visited: set[str] = set()
    q = deque([(start_url, 0)])
    items: list[SourceItem] = []
    manifest_rows: list[dict] = []

    while q and len(items) < max_pages:
        url, depth = q.popleft()
        if url in visited:
            continue
        visited.add(url)

        try:
            html, ctype = fetch_url(url)
            if 'text/html' not in ctype and '<html' not in html[:1000].lower():
                manifest_rows.append({'source_type': 'web', 'url_or_path': url, 'status': 'skip_non_html', 'fetched_at': now_iso()})
                continue

            title = html_title(html, fallback=url)
            text = clean_text_from_html(html)
            if len(text) < 120:
                manifest_rows.append({'source_type': 'web', 'url_or_path': url, 'title': title, 'status': 'skip_low_content', 'fetched_at': now_iso()})
                continue

            h = hashlib.sha256(text.encode('utf-8', errors='ignore')).hexdigest()
            fname = f"{slugify(urlparse(url).path or 'index')}_{h[:10]}.md"
            raw_path = pages_dir / fname
            raw_path.write_text(f'# {title}\n\nFonte: {url}\n\n{text}\n', encoding='utf-8')

            items.append(SourceItem(
                source_type='web',
                source_uri=url,
                title=title,
                content=text,
                content_hash=h,
                raw_path=str(raw_path),
            ))
            manifest_rows.append({
                'source_type': 'web',
                'url_or_path': url,
                'title': title,
                'fetched_at': now_iso(),
                'content_hash': h,
                'status': 'ok',
                'license_note': 'verificar termos de uso do site fonte',
            })

            if depth < max_depth:
                for lk in extract_links(url, html):
                    p = urlparse(lk)
                    if p.netloc.lower() != domain:
                        continue
                    if lk not in visited:
                        q.append((lk, depth + 1))

        except Exception as e:  # noqa: BLE001
            manifest_rows.append({'source_type': 'web', 'url_or_path': url, 'status': f'error:{e}', 'fetched_at': now_iso()})

    return items, manifest_rows


def load_markitdown():
    try:
        from markitdown import MarkItDown  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f'MarkItDown indisponivel: {e}')
    return MarkItDown


def file_text_fallback(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''


def gather_files(input_path: Path) -> Iterable[Path]:
    if input_path.is_file():
        yield input_path
        return
    for p in input_path.rglob('*'):
        if p.is_file() and p.suffix.lower() in ALLOWED_FILE_EXTS:
            yield p


def collect_files(input_path: Path, source_name: str, sink_root: Path) -> tuple[list[SourceItem], list[dict]]:
    day = datetime.now().strftime('%Y-%m-%d')
    base_dir = sink_root / '10 Fontes Brutas' / 'Documentos' / slugify(source_name) / day
    raw_dir = base_dir / 'files'
    raw_dir.mkdir(parents=True, exist_ok=True)

    MarkItDown = load_markitdown()
    md = MarkItDown(enable_plugins=True)

    items: list[SourceItem] = []
    manifest_rows: list[dict] = []

    for fp in gather_files(input_path):
        rel_name = fp.name
        try:
            target = raw_dir / rel_name
            if target.resolve() != fp.resolve():
                shutil.copy2(fp, target)

            content = ''
            try:
                content = (md.convert(str(fp)).text_content or '').strip()
            except Exception:
                content = file_text_fallback(fp).strip()

            if len(content) < 60:
                manifest_rows.append({'source_type': 'file', 'url_or_path': str(fp), 'title': rel_name, 'status': 'skip_low_content', 'fetched_at': now_iso()})
                continue

            h = hashlib.sha256(content.encode('utf-8', errors='ignore')).hexdigest()
            items.append(SourceItem(
                source_type='file',
                source_uri=str(fp),
                title=rel_name,
                content=content,
                content_hash=h,
                raw_path=str(target),
            ))

            manifest_rows.append({
                'source_type': 'file',
                'url_or_path': str(fp),
                'title': rel_name,
                'fetched_at': now_iso(),
                'content_hash': h,
                'status': 'ok',
                'license_note': 'uso local; validar direitos de distribuicao antes de publicar',
            })
        except Exception as e:  # noqa: BLE001
            manifest_rows.append({'source_type': 'file', 'url_or_path': str(fp), 'title': rel_name, 'status': f'error:{e}', 'fetched_at': now_iso()})

    return items, manifest_rows


def state_path(collection: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f'{slugify(collection)}.json'


def load_state(collection: str) -> dict:
    p = state_path(collection)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'collection': collection, 'sources': {}}


def save_state(collection: str, state: dict) -> None:
    p = state_path(collection)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def source_key(source_uri: str) -> str:
    return hashlib.sha1(source_uri.encode('utf-8', errors='ignore')).hexdigest()[:16]


def chunk_ids(collection: str, source_uri: str, count: int) -> list[str]:
    sk = source_key(source_uri)
    return [f'{collection}:{sk}:{i}' for i in range(count)]


def ensure_collection(client: chromadb.PersistentClient, name: str):
    try:
        return client.get_collection(name)
    except Exception:
        return client.create_collection(name=name, metadata={'description': 'Colecao gerada por ingest_dual_sink.py'})


def ingest_items(items: list[SourceItem], collection: str, chunk_size: int, overlap: int, model_name: str) -> dict:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    col = ensure_collection(client, collection)
    emb = SentenceTransformer(model_name)

    state = load_state(collection)
    src_state = state.setdefault('sources', {})

    stats = {'processed': 0, 'upserted_chunks': 0, 'skipped_unchanged': 0, 'errors': 0}

    for item in items:
        stats['processed'] += 1
        prev = src_state.get(item.source_uri)
        if prev and prev.get('content_hash') == item.content_hash:
            stats['skipped_unchanged'] += 1
            continue

        chunks = chunk_text(item.content, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            stats['errors'] += 1
            continue

        # Limpeza de chunks antigos do mesmo source
        prev_count = int(prev.get('chunk_count', 0)) if prev else 0
        if prev_count > 0:
            old_ids = chunk_ids(collection, item.source_uri, prev_count)
            try:
                col.delete(ids=old_ids)
            except Exception:
                pass

        ids = chunk_ids(collection, item.source_uri, len(chunks))
        vectors = emb.encode(chunks).tolist()
        now = now_iso()
        metadatas = [
            {
                'source_type': item.source_type,
                'source_uri': item.source_uri,
                'title': item.title[:500],
                'content_hash': item.content_hash,
                'ingested_at': now,
                'collection_version': re.search(r'(v\d+)$', collection).group(1) if re.search(r'(v\d+)$', collection) else 'v1',
                'chunk_id': i,
                'raw_path': item.raw_path,
            }
            for i, _ in enumerate(chunks)
        ]

        col.upsert(ids=ids, documents=chunks, embeddings=vectors, metadatas=metadatas)
        stats['upserted_chunks'] += len(chunks)

        src_state[item.source_uri] = {
            'content_hash': item.content_hash,
            'chunk_count': len(chunks),
            'title': item.title,
            'source_type': item.source_type,
            'last_ingested_at': now,
            'raw_path': item.raw_path,
        }

    save_state(collection, state)
    return stats


def append_manifest(manifest_path: Path, rows: list[dict]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open('a', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Ingestao dual sink (Obsidian bruto + Chroma) para web e arquivos')
    p.add_argument('--source-type', choices=['web', 'file'], required=True)
    p.add_argument('--source-name', required=True, help='slug logico da fonte (ex.: fastapi_docs, contratos_2026)')
    p.add_argument('--collection', required=True, help='nome da colecao de destino (ex.: docs_fastapi_v1)')

    p.add_argument('--url', help='URL inicial para crawl web')
    p.add_argument('--allow-domain', help='dominio permitido no crawl (default: dominio da URL inicial)')
    p.add_argument('--max-pages', type=int, default=80)
    p.add_argument('--max-depth', type=int, default=2)

    p.add_argument('--input-path', help='arquivo ou pasta para ingestao de documentos')

    p.add_argument('--chunk-size', type=int, default=1800)
    p.add_argument('--overlap', type=int, default=250)
    p.add_argument('--embedding-model', default=DEFAULT_MODEL)

    p.add_argument('--vault-root', default=str(VAULT))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    sink_root = Path(args.vault_root)

    if args.source_type == 'web':
        if not args.url:
            raise SystemExit('Para source-type=web, passe --url')
        items, rows = crawl_web(
            start_url=args.url,
            source_name=args.source_name,
            max_pages=max(1, args.max_pages),
            max_depth=max(0, args.max_depth),
            allow_domain=args.allow_domain,
            sink_root=sink_root,
        )
        manifest_path = sink_root / '10 Fontes Brutas' / 'Web' / slugify(args.source_name) / datetime.now().strftime('%Y-%m-%d') / 'manifest.jsonl'
    else:
        if not args.input_path:
            raise SystemExit('Para source-type=file, passe --input-path')
        inp = Path(args.input_path)
        if not inp.exists():
            raise SystemExit(f'input-path nao encontrado: {inp}')
        items, rows = collect_files(inp, source_name=args.source_name, sink_root=sink_root)
        manifest_path = sink_root / '10 Fontes Brutas' / 'Documentos' / slugify(args.source_name) / datetime.now().strftime('%Y-%m-%d') / 'manifest.jsonl'

    append_manifest(manifest_path, rows)

    stats = ingest_items(
        items=items,
        collection=args.collection,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        model_name=args.embedding_model,
    )

    summary = {
        'source_type': args.source_type,
        'source_name': args.source_name,
        'collection': args.collection,
        'vault_manifest': str(manifest_path),
        'items_collected': len(items),
        'stats': stats,
        'state_file': str(state_path(args.collection)),
        'timestamp': now_iso(),
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('interrompido pelo usuario', file=sys.stderr)
        raise
