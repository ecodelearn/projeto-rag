import matplotlib.pyplot as plt
from pathlib import Path

out = Path('/home/ecode/Documents/projetos/projeto-rag/assets/benchmark_overview.png')
out.parent.mkdir(parents=True, exist_ok=True)

labels = ['Baseline', 'Fusion', 'CRAG']
qualidade = [17.11, 17.56, 16.11]
latencia = [0.03, 9.37, 7.67]

fig, ax1 = plt.subplots(figsize=(8, 4.5))

bars = ax1.bar(labels, qualidade, color=['#4CAF50', '#FF9800', '#2196F3'], alpha=0.85)
ax1.set_ylabel('Score qualitativo (0-20)', fontsize=10)
ax1.set_ylim(0, 20)
ax1.set_title('projeto-rag: qualidade vs latencia (rodadas 4, 5 e 6)')

for b, v in zip(bars, qualidade):
    ax1.text(b.get_x() + b.get_width()/2, v + 0.3, f'{v:.2f}', ha='center', va='bottom', fontsize=9)

ax2 = ax1.twinx()
ax2.plot(labels, latencia, color='#333333', marker='o', linewidth=2)
ax2.set_ylabel('Latencia media (s)', fontsize=10)
ax2.set_ylim(0, max(latencia) * 1.25)

for x, y in zip(labels, latencia):
    ax2.annotate(f'{y:.2f}s', (x, y), textcoords='offset points', xytext=(0, 8), ha='center', fontsize=8)

fig.tight_layout()
fig.savefig(out, dpi=160)
print(out)
