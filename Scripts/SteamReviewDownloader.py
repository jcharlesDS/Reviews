import os
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QSpinBox, QComboBox, QMessageBox, QHBoxLayout
)
import sys

# Fonction permettant de récupérér les reviews Steam par son API.
def get_reviews(appid, count=20, language="all"):
    url = f"https://store.steampowered.com/appreviews/{appid}"
    params = {
        "json": 1,
        "num_per_page": count,
        "language": language,
        "purchase_type": "all"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return []

    data = response.json()
    return data.get("reviews", [])

# Fonction sauvegardant les reviews collectés en fichiers texte
def save_reviews_to_txt(reviews, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    for i, review in enumerate(reviews):
        content = review.get('review', '').strip()
        voted_up = review.get('voted_up', None)
        if not content:
            continue

        rating = "👍" if voted_up else "👎"

        file_path = os.path.join(output_folder, f"review_{i+1}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Note : {rating}\n\n{content}")

# Interface graphique
class SteamReviewDownloader(QWidget):
    def __init__(self): # Fonction initiale de la fenêtre
        super().__init__()
        self.setWindowTitle("Télécharger des reviews Steam")
        self.setFixedWidth(500)
        self.setup_ui()

    def setup_ui(self): # Fonction organisant la structure de l'interface graphique
        layout = QVBoxLayout()

        self.appid_input = QLineEdit()
        layout.addWidget(QLabel("AppID du jeu Steam :"))
        layout.addWidget(self.appid_input)

        self.name_input = QLineEdit()
        layout.addWidget(QLabel("Nom du jeu (facultatif) :"))
        layout.addWidget(self.name_input)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["all", "english", "french", "german", "spanish", "russian", "japanese", "chinese"])
        layout.addWidget(QLabel("Langue des reviews :"))
        layout.addWidget(self.lang_combo)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1000)
        self.count_spin.setValue(20)
        layout.addWidget(QLabel("Nombre de reviews :"))
        layout.addWidget(self.count_spin)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_button = QPushButton("Choisir dossier")
        self.path_button.clicked.connect(self.choose_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.path_button)

        layout.addWidget(QLabel("Dossier de sortie :"))
        layout.addLayout(path_layout)

        btn_layout = QHBoxLayout()
        self.start_button = QPushButton("Lancer")
        self.start_button.clicked.connect(self.start_download)
        btn_layout.addWidget(self.start_button)

        self.reset_button = QPushButton("Réinitialiser")
        self.reset_button.clicked.connect(self.reset_fields)
        btn_layout.addWidget(self.reset_button)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def choose_folder(self): # Fonction permettant de choisir le dossier de sortie
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if folder:
            self.path_input.setText(folder)

    def start_download(self): # Fonction pour le téléchargement des reviews
        appid = self.appid_input.text().strip()
        if not appid.isdigit():
            QMessageBox.warning(self, "Erreur", "L'AppID doit être un nombre.")
            return

        name = self.name_input.text().strip() or appid
        count = self.count_spin.value()
        language = self.lang_combo.currentText()
        output_dir = self.path_input.text().strip()

        if not output_dir:
            QMessageBox.warning(self, "Erreur", "Veuillez choisir un dossier de sortie.")
            return

        full_path = os.path.join(output_dir, name)

        self.start_button.setEnabled(False)
        self.start_button.setText("Téléchargement...")

        try:
            reviews = get_reviews(appid, count, language)
            if not reviews:
                raise Exception("Aucune review récupérée.")
            save_reviews_to_txt(reviews, full_path)
            QMessageBox.information(self, "Succès", f"{len(reviews)} reviews enregistrées dans :\n{full_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
        finally:
            self.start_button.setEnabled(True)
            self.start_button.setText("Lancer")

    def reset_fields(self): # Fonction permettant de réinitialiser les champs utilisateurs
        self.appid_input.clear()
        self.name_input.clear()
        self.count_spin.setValue(20)
        self.lang_combo.setCurrentIndex(0)
        self.path_input.clear()

if __name__ == "__main__": # Fonction de lancement de l'application
    app = QApplication(sys.argv)
    window = SteamReviewDownloader()
    window.show()
    sys.exit(app.exec())
