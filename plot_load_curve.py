import os
os.environ['TF_USE_LEGACY_KERAS'] = '1'

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- Path ---
BASE = '/home/yahya/project/LSTM'
LOG_PATH = os.path.join(BASE, 'mse_log.csv')
OUTPUT_PATH = '/home/yahya/project/load_curve.png'

# --- Load real session data ---
df = pd.read_csv(LOG_PATH)
df['time_rel'] = df['timestamp'] - df['timestamp'].iloc[0]  # seconds from start

mse_normal   = df[df['status'] == 'NORMAL']['mse'].values
mse_anomalie = df[df['status'] == 'ANOMALIE']['mse'].values
threshold    = df['threshold'].iloc[0]

print(f"📊 Session : {len(df)} échantillons | "
      f"Normal: {len(mse_normal)} | Anomalie: {len(mse_anomalie)} | Seuil: {threshold:.4f}")

# ============================================================
# FIGURE
# ============================================================
fig, axes = plt.subplots(2, 1, figsize=(14, 10))
fig.patch.set_facecolor('#0d1117')

# --- Subplot 1 : MSE Timeline ---
ax1 = axes[0]
ax1.set_facecolor('#161b22')

normal_mask   = df['status'] == 'NORMAL'
anomalie_mask = df['status'] == 'ANOMALIE'

ax1.plot(df.loc[normal_mask, 'time_rel'].to_numpy(),   df.loc[normal_mask,   'mse'].to_numpy(),
         color='#58a6ff', linewidth=0.8, label='MSE — Normal', alpha=0.85)
ax1.scatter(df.loc[anomalie_mask, 'time_rel'].to_numpy(), df.loc[anomalie_mask, 'mse'].to_numpy(),
            color='#f85149', s=12, label='MSE — Anomalie détectée', zorder=5)
ax1.axhline(y=threshold, color='#f85149', linewidth=2, linestyle='--',
            label=f'Seuil Zero-Trust = {threshold:.2f}')
ax1.fill_between(df['time_rel'].to_numpy(), df['mse'].to_numpy(), threshold,
                 where=(df['mse'] > threshold).to_numpy(), color='#f85149', alpha=0.25)

ax1.set_title('Courbe de Charge Réelle — Erreur de Reconstruction MSE (Session Live)',
              color='#e6edf3', fontsize=14, fontweight='bold', pad=12)
ax1.set_xlabel('Temps (secondes depuis le démarrage)', color='#8b949e', fontsize=11)
ax1.set_ylabel('Erreur MSE', color='#8b949e', fontsize=11)
ax1.tick_params(colors='#8b949e')
for spine in ax1.spines.values():
    spine.set_edgecolor('#30363d')
ax1.legend(facecolor='#21262d', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=10)
ax1.grid(True, color='#21262d', linewidth=0.5, alpha=0.7)

# Stats annotation
ax1.annotate(
    f"Anomalies: {len(mse_anomalie)}  |  Max MSE: {df['mse'].max():.2f}  |  Moy. normale: {mse_normal.mean():.4f}",
    xy=(0.01, 0.97), xycoords='axes fraction',
    color='#8b949e', fontsize=9, va='top',
    bbox=dict(boxstyle='round,pad=0.3', facecolor='#21262d', edgecolor='#30363d'))

# --- Subplot 2 : Distribution ---
ax2 = axes[1]
ax2.set_facecolor('#161b22')

if len(mse_normal) > 0:
    ax2.hist(mse_normal, bins=80, color='#58a6ff', alpha=0.75,
             label=f'Normal (N={len(mse_normal):,})', density=True, edgecolor='none')
if len(mse_anomalie) > 0:
    ax2.hist(mse_anomalie, bins=40, color='#f85149', alpha=0.80,
             label=f'Anomalie (N={len(mse_anomalie):,})', density=True, edgecolor='none')

ax2.axvline(x=threshold, color='#f85149', linewidth=2.5, linestyle='--',
            label=f'Seuil = {threshold:.2f}')

ax2.set_title('Distribution des Erreurs MSE — Données Réelles de Session',
              color='#e6edf3', fontsize=14, fontweight='bold', pad=12)
ax2.set_xlabel('Erreur MSE', color='#8b949e', fontsize=11)
ax2.set_ylabel('Densité', color='#8b949e', fontsize=11)
ax2.tick_params(colors='#8b949e')
for spine in ax2.spines.values():
    spine.set_edgecolor('#30363d')
ax2.legend(facecolor='#21262d', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=10)
ax2.grid(True, color='#21262d', linewidth=0.5, alpha=0.7)

# Global title
fig.suptitle('Zero-Trust Plausibility Monitor — Auto-encodeur LSTM — CARLA + ROS 2 (Données Réelles)',
             color='#e6edf3', fontsize=14, fontweight='bold', y=1.01)

plt.tight_layout(pad=2.5)
plt.savefig(OUTPUT_PATH, dpi=160, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f"\n Image sauvegardée : {OUTPUT_PATH}")
