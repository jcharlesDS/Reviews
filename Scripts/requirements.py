import importlib
import subprocess
import sys

# Liste des modules à vérifier et à installer si besoin
modules = {
    "requests": "requests",
    "PySide6": "PySide6",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "scipy": "scipy",
    "langdetect": "langdetect",
    "textblob": "textblob",
    "textblob_fr": "textblob-fr",
    "nltk": "nltk",
    "vaderSentiment": "vaderSentiment",
    "sklearn": "scikit-learn",
    "seaborn": "seaborn",
    "numpy": "numpy"
}

# Fonction de vérification et d'installation des modules requis pour le projet
def installer_module(module_name, pip_name):
    try:
        importlib.import_module(module_name)
        print(f"{module_name} est déjà installé.")
    except ImportError:
        print(f"Installation de {module_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])

if __name__ == "__main__":
    for module_name, pip_name in modules.items():
        installer_module(module_name, pip_name)

    # Téléchargement des données NLTK si nécessaire
    try:
        import nltk
        nltk.download("vader_lexicon")
        nltk.download("punkt") # Pas nécessairement obligatoire pour le projet mais peut l'être pour certaines machines
        print("Téléchargement des données NLTK terminé.")
    except ImportError:
        print("NLTK n'a pas été trouvé pour le téléchargement des données.")
