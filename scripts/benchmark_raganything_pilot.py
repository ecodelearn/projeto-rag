from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path('/home/ecode/Documents/projetos/projeto-rag')
RAGANY = ROOT / 'frameworks' / 'rag-anything'
REPORT_MD = ROOT / 'analises' / 'benchmark-raganything-piloto-rodada-9.md'
REPORT_JSON = ROOT / 'analises' / 'benchmark-raganything-piloto-rodada-9.json'


def run(cmd: str):
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def main():
    checks = {}

    checks['repo_exists'] = RAGANY.exists()
    checks['requirements_exists'] = (RAGANY / 'requirements.txt').exists()

    code, out, err = run('python - <<\'PY\'\nimport importlib.util\nmods=["raganything","lightrag","docling","paddleocr","pypdf"]\nprint({m:(importlib.util.find_spec(m) is not None) for m in mods})\nPY')
    checks['python_modules'] = out if out else err

    code, out, err = run('command -v mineru >/dev/null 2>&1 && mineru --version || echo mineru_missing')
    checks['mineru'] = out if out else err

    code, out, err = run('command -v soffice >/dev/null 2>&1 && soffice --version || echo libreoffice_missing')
    checks['libreoffice'] = out if out else err

    code, out, err = run('nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null')
    checks['gpu_available'] = code == 0 and bool(out)
    checks['gpu_info'] = out if out else 'nao detectado'

    blockers = []
    if 'mineru_missing' in checks['mineru']:
        blockers.append('MinerU nao encontrado (necessario para pipeline multimodal padrao).')
    if 'libreoffice_missing' in checks['libreoffice']:
        blockers.append('LibreOffice ausente (impacta parsing de documentos Office).')
    if not checks['gpu_available']:
        blockers.append('Sem GPU dedicada detectada para cenarios multimodais pesados.')

    status = 'pilot_partial' if blockers else 'pilot_ready'

    lines = [
        '# Benchmark RAG-Anything Piloto - Rodada 9',
        '',
        '## Tipo de rodada',
        '- Viabilidade tecnica e prontidao de ambiente para framework multimodal externo.',
        '',
        f'- Status: **{status}**',
        '',
        '## Checagens',
        f"- Repo clonado: {checks['repo_exists']}",
        f"- requirements.txt: {checks['requirements_exists']}",
        f"- Modulos Python (raganything/lightrag/docling/paddleocr/pypdf): `{checks['python_modules']}`",
        f"- MinerU: `{checks['mineru']}`",
        f"- LibreOffice: `{checks['libreoffice']}`",
        f"- GPU detectada: {checks['gpu_available']} ({checks['gpu_info']})",
        '',
        '## Bloqueadores',
    ]

    if blockers:
        for b in blockers:
            lines.append(f'- {b}')
    else:
        lines.append('- Nenhum bloqueador critico identificado.')

    lines += [
        '',
        '## Recomendacao de proximo passo',
        '- Executar piloto funcional minimo com 1 PDF e query multimodal em ambiente com MinerU configurado.',
        '- Manter comparacao justa usando subset da mesma base (`sandeco_rag_book_v1`) quando possivel.',
        '- Registrar custos de operacao (tempo de parse + index + query) para comparar com LightRAG/stack atual.',
    ]

    REPORT_MD.write_text('\n'.join(lines), encoding='utf-8')
    REPORT_JSON.write_text(json.dumps({'status': status, 'checks': checks, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'relatorios: {REPORT_MD} | {REPORT_JSON}')


if __name__ == '__main__':
    main()
