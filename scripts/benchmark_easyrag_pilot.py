from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path('/home/ecode/Documents/projetos/projeto-rag')
EASYRAG = ROOT / 'frameworks' / 'easyrag'
REPORT_MD = ROOT / 'analises' / 'benchmark-easyrag-piloto-rodada-8.md'
REPORT_JSON = ROOT / 'analises' / 'benchmark-easyrag-piloto-rodada-8.json'


def run(cmd: str):
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def main():
    checks = {}

    checks['repo_exists'] = EASYRAG.exists()

    code, out, err = run('nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null')
    checks['gpu_available'] = code == 0 and bool(out)
    checks['gpu_info'] = out if out else 'nao detectado'

    req_file = EASYRAG / 'requirements.txt'
    checks['requirements_exists'] = req_file.exists()
    req_count = 0
    if req_file.exists():
        req_count = len([l for l in req_file.read_text(encoding='utf-8', errors='ignore').splitlines() if l.strip() and not l.strip().startswith('#')])
    checks['requirements_count'] = req_count

    cfg_file = EASYRAG / 'src' / 'configs' / 'easyrag.yaml'
    checks['config_exists'] = cfg_file.exists()
    cfg_text = cfg_file.read_text(encoding='utf-8', errors='ignore') if cfg_file.exists() else ''
    checks['uses_glm'] = 'glm-4' in cfg_text
    checks['has_dummy_keys'] = 'your-keys' in cfg_text

    # smoke import without full install
    smoke_cmd = (
        'python - <<\'PY\'\n'
        'import importlib.util\n'
        'mods=["llama_index","qdrant_client","rank_bm25","jieba"]\n'
        'out={}\n'
        'for m in mods:\n'
        '    out[m]=importlib.util.find_spec(m) is not None\n'
        'print(out)\n'
        'PY'
    )
    code, out, err = run(smoke_cmd)
    checks['dependency_smoke'] = out if out else err

    blockers = []
    if not checks['gpu_available']:
        blockers.append('Sem GPU dedicada detectada para o perfil recomendado do EasyRAG (>=16GB).')
    if checks['has_dummy_keys']:
        blockers.append('Config padrao do EasyRAG depende de chaves GLM (llm_keys com placeholder).')
    if checks['uses_glm']:
        blockers.append('Pipeline de referencia do EasyRAG esta acoplado a GLM-4 no config padrao.')

    status = 'pilot_blocked' if blockers else 'pilot_ready'

    lines = [
        '# Benchmark EasyRAG Piloto - Rodada 8',
        '',
        '## Tipo de rodada',
        '- Rodada de viabilidade tecnica e prontidao de execucao local (framework externo).',
        '',
        f'- Status: **{status}**',
        '',
        '## Checagens',
        f"- Repo clonado: {checks['repo_exists']}",
        f"- GPU detectada: {checks['gpu_available']} ({checks['gpu_info']})",
        f"- requirements.txt: {checks['requirements_exists']} ({checks['requirements_count']} dependencias listadas)",
        f"- Config com GLM: {checks['uses_glm']}",
        f"- Chaves placeholder no config: {checks['has_dummy_keys']}",
        f"- Smoke de dependencias: `{checks['dependency_smoke']}`",
        '',
        '## Bloqueadores',
    ]

    if blockers:
        for b in blockers:
            lines.append(f'- {b}')
    else:
        lines.append('- Nenhum bloqueador critico identificado para piloto.')

    lines += [
        '',
        '## Recomendacao de proximo passo',
        '- Executar piloto funcional em ambiente com GPU e stack dedicada para EasyRAG.',
        '- Adaptar config para provider OpenAI (ou provider local equivalente), mantendo mesma suite de perguntas da pesquisa.',
        '- So comparar com rodadas anteriores apos paridade minima de setup (corpus, perguntas, criterio de avaliacao).',
    ]

    REPORT_MD.write_text('\n'.join(lines), encoding='utf-8')
    REPORT_JSON.write_text(json.dumps({'status': status, 'checks': checks, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'relatorios: {REPORT_MD} | {REPORT_JSON}')


if __name__ == '__main__':
    main()
