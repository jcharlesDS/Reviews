import os
import sys
import sqlite3
import subprocess
import matplotlib.pyplot as plt
from langdetect import detect
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QCheckBox, QScrollArea, QMessageBox,
    QHBoxLayout, QLineEdit
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from textblob import TextBlob
from textblob_fr import PatternTagger, PatternAnalyzer
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk

# Mesure pour l'analyse de sentiment des reviews en Anglais.
nltk.download("vader_lexicon")
sia = SentimentIntensityAnalyzer()

class SentimentApp(QWidget):
    def __init__(self): # Fonction initiale de la fenêtre
        super().__init__()
        self.setWindowTitle("Analyse NLP des Reviews Steam")
        self.resize(1000, 750)

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.btn_select_folder = QPushButton("Choisir le dossier de reviews")
        self.btn_select_folder.clicked.connect(self.select_folder)
        self.layout.addWidget(self.btn_select_folder)

        self.label_folder = QLabel("Aucun dossier sélectionné")
        self.layout.addWidget(self.label_folder)

        self.layout.addWidget(QLabel("Tranches Metacritic à inclure :"))

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.checkbox_container = QWidget()
        self.checkbox_layout = QVBoxLayout()
        self.checkbox_container.setLayout(self.checkbox_layout)
        self.scroll_area.setWidget(self.checkbox_container)
        self.layout.addWidget(self.scroll_area)

        self.checkbox_compare = QCheckBox("Comparer les sentiments par tranche Metacritic")
        self.layout.addWidget(self.checkbox_compare)

        self.path_layout = QHBoxLayout()
        self.output_path_field = QLineEdit()
        self.output_path_field.setPlaceholderText("Chemin de sortie (dossier)")
        self.path_layout.addWidget(self.output_path_field)
        self.btn_browse_output = QPushButton("Choisir...")
        self.btn_browse_output.clicked.connect(self.select_output_folder)
        self.path_layout.addWidget(self.btn_browse_output)
        self.layout.addLayout(self.path_layout)

        self.btn_analyze = QPushButton("Lancer l'analyse de sentiment")
        self.btn_analyze.clicked.connect(self.run_analysis)
        self.layout.addWidget(self.btn_analyze)

        # Zone scrollable pour les graphiques
        self.graph_area = QScrollArea()
        self.graph_area.setWidgetResizable(True)

        # Conteneur pour les deux graphiques
        self.graph_container = QWidget()
        self.graph_layout = QVBoxLayout(self.graph_container)

        self.graph_label_jeu = QLabel()
        self.graph_label_jeu.setAlignment(Qt.AlignCenter)

        self.graph_label_tranche = QLabel()
        self.graph_label_tranche.setAlignment(Qt.AlignCenter)

        self.graph_layout.addWidget(self.graph_label_jeu)
        self.graph_layout.addWidget(self.graph_label_tranche)

        # On place le conteneur dans la zone scrollable
        self.graph_area.setWidget(self.graph_container)
        self.graph_area.setFixedHeight(450)

        # Ajout à la fenêtre
        self.layout.addWidget(self.graph_area)

        self.review_root = None
        self.checkboxes = {}

    def select_folder(self): # Fonction permettant de choisir le dossier racine des reviews à analyser, permettant également de choisir les tranches metacritic détéctés à analyser.
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier de reviews")
        if folder:
            self.review_root = folder
            self.label_folder.setText(f"Dossier sélectionné : {folder}")

            self.checkboxes.clear()
            for i in reversed(range(self.checkbox_layout.count())):
                self.checkbox_layout.itemAt(i).widget().deleteLater()

            tranches = sorted([
                d for d in os.listdir(folder)
                if os.path.isdir(os.path.join(folder, d)) and "-" in d
            ])

            for tranche in tranches:
                cb = QCheckBox(tranche)
                cb.setChecked(True)
                self.checkbox_layout.addWidget(cb)
                self.checkboxes[tranche] = cb

    def select_output_folder(self): # Fonction pour choisir le dossier de sortie de l'analyse
        folder = QFileDialog.getExistingDirectory(self, "Choisir le dossier de sortie")
        if folder:
            self.output_path_field.setText(folder)

    def analyze_review(self, text): # Fonction spécialement dédié à l'analyse de la langue utilisé dans les reviews à analyser.
        try:
            lang = detect(text)
        except:
            return 0.0

        if lang == "en":
            score = sia.polarity_scores(text)
            return score["compound"]
        elif lang == "fr":
            blob = TextBlob(text, pos_tagger=PatternTagger(), analyzer=PatternAnalyzer())
            return blob.sentiment[0]
        return 0.0

    def run_analysis(self): # Fonction dédié à l'analyse
        if not self.review_root:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un dossier.")
            return

        output_dir = self.output_path_field.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "Erreur", "Veuillez spécifier un chemin de sortie.")
            return

        os.makedirs(output_dir, exist_ok=True)
        db_path = os.path.join(output_dir, "resultat_analyse_nlp.db")

        selected_tranches = [k for k, v in self.checkboxes.items() if v.isChecked()]
        if not selected_tranches:
            QMessageBox.warning(self, "Erreur", "Aucune tranche sélectionnée.")
            return

        results = {}
        tranche_sentiments = {}

        for tranche in selected_tranches:
            tranche_path = os.path.join(self.review_root, tranche)
            for game in os.listdir(tranche_path):
                game_path = os.path.join(tranche_path, game)
                if not os.path.isdir(game_path):
                    continue

                sentiments = []
                for fname in os.listdir(game_path):
                    if not fname.startswith("review_") or not fname.endswith(".txt"):
                        continue
                    try:
                        with open(os.path.join(game_path, fname), encoding="utf-8", errors="ignore") as f:
                            text = f.read().strip()
                            if text:
                                score = self.analyze_review(text)
                                sentiments.append(score)
                    except Exception as e:
                        print(f"Erreur lecture fichier {fname}: {e}")

                if sentiments:
                    avg_sentiment = sum(sentiments) / len(sentiments)
                    nb_reviews = len(sentiments)
                    try:
                        metacritic_score = int(tranche.split("-")[0]) + 5
                    except:
                        metacritic_score = 0
                    ecart = round(metacritic_score / 100 - avg_sentiment, 4)
                    results[game] = {
                        "tranche": tranche,
                        "sentiment_moyen": round(avg_sentiment, 4),
                        "nombre_reviews": nb_reviews,
                        "ecart": ecart
                    }

                    if tranche not in tranche_sentiments:
                        tranche_sentiments[tranche] = []
                    tranche_sentiments[tranche].append(avg_sentiment)

        # Enregistrement SQL
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resultats_sentiment (
                jeu TEXT PRIMARY KEY,
                tranche TEXT,
                sentiment_moyen REAL,
                nombre_reviews INTEGER,
                ecart_metacritic_sentiment REAL
            )
        """)
        for jeu, data in results.items():
            cur.execute("""
                INSERT OR REPLACE INTO resultats_sentiment 
                (jeu, tranche, sentiment_moyen, nombre_reviews, ecart_metacritic_sentiment)
                VALUES (?, ?, ?, ?, ?)
            """, (jeu, data['tranche'], data['sentiment_moyen'], data['nombre_reviews'], data['ecart']))
        conn.commit()
        conn.close()

        if results:
            self.display_game_graph(results, output_dir)

            if self.checkbox_compare.isChecked():
                self.display_tranche_graph(tranche_sentiments, output_dir)
            else:
                self.graph_label_tranche.clear()

            QMessageBox.information(self, "Succès", f"Analyse terminée ! Résultats enregistrés dans {db_path}")
            self.open_sqlite_db(db_path)
        else:
            QMessageBox.information(self, "Aucun résultat", "Aucune review valide trouvée.")

    def display_game_graph(self, data, output_dir): # Fonction d'affichage du graphique des sentiments moyen par jeu
        jeux = list(data.keys())
        sentiments = [data[j]["sentiment_moyen"] for j in jeux]

        height = max(5, 0.4 * len(jeux))
        plt.figure(figsize=(14, height))
        plt.barh(jeux, sentiments, color="mediumseagreen")
        plt.xlabel("Sentiment moyen")
        plt.title("Sentiment moyen par jeu")
        plt.tight_layout()

        image_path = os.path.join(output_dir, "graphique_sentiment_par_jeu.png")
        plt.savefig(image_path)
        self.graph_label_jeu.setPixmap(QPixmap(image_path).scaledToWidth(900, Qt.SmoothTransformation))

    def display_tranche_graph(self, tranche_sentiments, output_dir): # Fonction d'affichage du graphique des sentiments moyen par tranche Metacritic
        tranches = list(tranche_sentiments.keys())
        moyennes = [sum(lst)/len(lst) for lst in tranche_sentiments.values()]
        plt.figure(figsize=(12, 6))
        plt.bar(tranches, moyennes, color="cornflowerblue")
        plt.xlabel("Tranche Metacritic")
        plt.ylabel("Sentiment moyen")
        plt.title("Sentiment moyen par tranche Metacritic")
        plt.tight_layout()

        image_path = os.path.join(output_dir, "graphique_sentiment_par_tranche.png")
        plt.savefig(image_path)
        self.graph_label_tranche.setPixmap(QPixmap(image_path).scaledToWidth(900, Qt.SmoothTransformation))

    def open_sqlite_db(self, db_path): # Fonction d'ouverture de la base de données SQL post-analyse
        try:
            if sys.platform == "win32":
                os.startfile(db_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", db_path])
            else:
                subprocess.call(["xdg-open", db_path])
        except Exception as e:
            print(f"Erreur ouverture base : {e}")

if __name__ == "__main__": # Fonction de lancement de l'app
    app = QApplication(sys.argv)
    window = SentimentApp()
    window.show()
    sys.exit(app.exec())
