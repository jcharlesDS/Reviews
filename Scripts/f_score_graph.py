import matplotlib.pyplot as plt
import numpy as np

tranches = ['30-40', '90-100', 'Toutes'] # Les tranches étudiés
models = ['Naive Bayes', 'SVM', 'Random Forest', 'Logistic Regression'] # Les modèles analysés

# F1-scores
f1_scores = {
    'Naive Bayes': [0.6801, 0.8431, 0.8029],
    'SVM': [0.6358, 0.9218, 0.7294],
    'Random Forest': [0.6969, 0.9218, 0.7298],
    'Logistic Regression': [0.7474, 0.9084, 0.7775]
}

x = np.arange(len(tranches))  # positions des tranches
width = 0.2  # largeur des barres

fig, ax = plt.subplots(figsize=(10, 6))
for i, model in enumerate(models):
    ax.bar(x + i * width, f1_scores[model], width, label=model)

ax.set_ylabel('F1-score')
ax.set_title('F1-score des modèles par tranche Metacritic')
ax.set_xticks(x + width * 1.5)
ax.set_xticklabels(tranches)
ax.legend()
ax.grid(axis='y', linestyle='--', alpha=0.7)

plt.tight_layout()
plt.show()
