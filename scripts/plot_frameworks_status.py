import matplotlib.pyplot as plt
from pathlib import Path

out = Path('/home/ecode/Documents/projetos/projeto-rag/assets/frameworks_status.png')
out.parent.mkdir(parents=True, exist_ok=True)

frameworks = ['Stack Atual', 'LightRAG', 'EasyRAG', 'RAG-Anything']
readiness = [1.0, 0.9, 0.2, 0.5]
colors = ['#4CAF50', '#2196F3', '#F44336', '#FF9800']
labels = ['Produção', 'Piloto funcional', 'Bloqueado', 'Parcial']

fig, ax = plt.subplots(figsize=(8, 4.5))
bars = ax.barh(frameworks, readiness, color=colors, alpha=0.9)
ax.set_xlim(0, 1.05)
ax.set_xlabel('Prontidão operacional (0 a 1)')
ax.set_title('Status de frameworks no projeto-rag (rodadas 7, 8 e 9)')

for b, v, lbl in zip(bars, readiness, labels):
    ax.text(v + 0.02, b.get_y() + b.get_height()/2, f'{lbl} ({v:.1f})', va='center', fontsize=9)

ax.grid(axis='x', linestyle='--', alpha=0.3)
fig.tight_layout()
fig.savefig(out, dpi=160)
print(out)
