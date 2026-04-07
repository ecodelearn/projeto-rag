import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path('/home/ecode/Documents/projetos/projeto-rag')
DATA = ROOT / 'analises' / 'avaliacao-qualitativa-cega-rodada-6.json'
OUT = ROOT / 'assets' / 'quality_radar.png'
OUT.parent.mkdir(parents=True, exist_ok=True)

payload = json.loads(DATA.read_text(encoding='utf-8'))
avg_dims = payload['avg_dims']

categories = ['precisao', 'cobertura', 'clareza', 'aderencia_contexto']
labels = ['Precisão', 'Cobertura', 'Clareza', 'Aderência']
angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
angles += angles[:1]

fig = plt.figure(figsize=(6.2, 6.2))
ax = plt.subplot(111, polar=True)

styles = {
    'baseline': ('#4CAF50', 'Baseline'),
    'fusion': ('#FF9800', 'Fusion'),
    'crag': ('#2196F3', 'CRAG'),
}

for key in ['baseline', 'fusion', 'crag']:
    vals = [avg_dims[key][c] for c in categories]
    vals += vals[:1]
    color, name = styles[key]
    ax.plot(angles, vals, color=color, linewidth=2, label=name)
    ax.fill(angles, vals, color=color, alpha=0.15)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(labels)
ax.set_ylim(0, 5)
ax.set_yticks([1, 2, 3, 4, 5])
ax.set_yticklabels(['1', '2', '3', '4', '5'])
ax.set_title('Qualidade por critério (rodada 6)', pad=20)
ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.12))

fig.tight_layout()
fig.savefig(OUT, dpi=160)
print(OUT)
