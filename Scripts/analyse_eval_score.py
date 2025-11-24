import os
import sqlite3
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QScrollArea, QCheckBox
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
import matplotlib.pyplot as plt
from sklearn.metrics import precision_score, recall_score, f1_score
from langdetect import detect
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

class ScoreEvaluationApp(QWidget): # Fonction initiale de la fenêtre
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calcul des scores d'évaluations")
        self.setGeometry(100, 100, 800, 600)

        self.layout = QVBoxLayout(self)

        self.tranche_checkboxes = []
        self.setup_tranche_selection()

        self.start_button = QPushButton("Lancer l'évaluation")
        self.start_button.clicked.connect(self.evaluate_scores)
        self.layout.addWidget(self.start_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        self.layout.addWidget(self.scroll_area)

    def setup_tranche_selection(self): # Fonction permettant de choisir les tranches Metacritic à analyser
        label = QLabel("Sélectionnez les tranches Metacritic à inclure :")
        self.layout.addWidget(label)
        for i in range(0, 100, 10):
            tranche = f"{i}-{i+10}"
            checkbox = QCheckBox(tranche)
            checkbox.setChecked(True)
            self.tranche_checkboxes.append(checkbox)
            self.layout.addWidget(checkbox)

    def evaluate_scores(self): # Fonction calculant les mesures d'évaluations (précision, rappel, f-mesure) et les enregistre dans une nouvelle base de données
        selected_tranches = [cb.text() for cb in self.tranche_checkboxes if cb.isChecked()]
        dossier_racine = QFileDialog.getExistingDirectory(self, "Sélectionnez le dossier de reviews")
        if not dossier_racine:
            return

        output_db_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer les résultats", "resultats_scores_evaluation.db", "SQL DB (*.db)")
        if not output_db_path:
            return

        conn = sqlite3.connect(output_db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS resultats (tranche TEXT, precision REAL, rappel REAL, f_mesure REAL)")
        conn.commit()

        global_y_true, global_y_pred = [], []
        scores_par_tranche = {}

        for tranche in selected_tranches:
            tranche_path = os.path.join(dossier_racine, tranche)
            if not os.path.isdir(tranche_path):
                continue

            y_true, y_pred = [], []

            for jeu in os.listdir(tranche_path):
                chemin_jeu = os.path.join(tranche_path, jeu)
                if not os.path.isdir(chemin_jeu):
                    continue

                for review in os.listdir(chemin_jeu):
                    if not review.startswith("review_") or not review.endswith(".txt"):
                        continue

                    review_path = os.path.join(chemin_jeu, review)
                    try:
                        with open(review_path, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            if not lines:
                                continue

                            note_line = lines[0].strip()
                            review_text = " ".join(line.strip() for line in lines[1:] if line.strip())

                            if "👍" in note_line:
                                y_true.append(1)
                            elif "👎" in note_line:
                                y_true.append(0)
                            else:
                                continue

                            try:
                                lang = detect(review_text)

                                if lang == 'fr':
                                    sentiment = TextBlob(review_text).sentiment.polarity
                                    y_pred.append(1 if sentiment > 0 else 0)

                                elif lang == 'en':
                                    score = analyzer.polarity_scores(review_text)["compound"]
                                    y_pred.append(1 if score > 0 else 0)

                                else:
                                    y_pred.append(0)

                            except Exception:
                                y_pred.append(0)

                    except Exception as e:
                        print(f"Erreur avec le fichier {review_path} : {e}")
                        continue

            if y_true and y_pred:
                precision = precision_score(y_true, y_pred)
                recall = recall_score(y_true, y_pred)
                f1 = f1_score(y_true, y_pred)
                scores_par_tranche[tranche] = (precision, recall, f1)

                global_y_true.extend(y_true)
                global_y_pred.extend(y_pred)

                c.execute("INSERT INTO resultats VALUES (?, ?, ?, ?)", (tranche, precision, recall, f1))
                conn.commit()

        # Résultats globaux
        if global_y_true and global_y_pred:
            precision = precision_score(global_y_true, global_y_pred)
            recall = recall_score(global_y_true, global_y_pred)
            f1 = f1_score(global_y_true, global_y_pred)
            scores_par_tranche["Global"] = (precision, recall, f1)
            c.execute("INSERT INTO resultats VALUES (?, ?, ?, ?)", ("Global", precision, recall, f1))
            conn.commit()

        conn.close()

        self.show_scores_chart(scores_par_tranche)

    def show_scores_chart(self, scores_par_tranche): # Fonction permettant d'afficher les résultats des calculs de mesures d'évaluations
        tranches = list(scores_par_tranche.keys())
        precisions = [scores_par_tranche[t][0] for t in tranches]
        rappels = [scores_par_tranche[t][1] for t in tranches]
        f1s = [scores_par_tranche[t][2] for t in tranches]

        fig, ax = plt.subplots(figsize=(10, 6))
        x = range(len(tranches))

        ax.plot(x, precisions, label="Précision", marker='o')
        ax.plot(x, rappels, label="Rappel", marker='s')
        ax.plot(x, f1s, label="F-mesure", marker='^')
        ax.set_xticks(x)
        ax.set_xticklabels(tranches, rotation=45)
        ax.set_ylim(0, 1.05)
        ax.set_title("Mesures d'évaluations par tranche Metacritic")
        ax.set_ylabel("Score")
        ax.set_xlabel("Tranche Metacritic")
        ax.legend()
        plt.tight_layout()

        img_path = QFileDialog.getSaveFileName(self, "Enregistrer le graphique", "graphique_scores_eval.png", "Images PNG (*.png)")[0]
        if img_path:
            plt.savefig(img_path)
            plt.close()

            image = QImage(img_path)
            self.image_label.setPixmap(QPixmap.fromImage(image))

if __name__ == "__main__": # Fonction de lancement de l'app
    import sys
    app = QApplication(sys.argv)
    window = ScoreEvaluationApp()
    window.show()
    sys.exit(app.exec())
