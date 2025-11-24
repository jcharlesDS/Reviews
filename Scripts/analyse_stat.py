import sys
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QTextEdit
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.stats import pearsonr

# Interface graphique
class SteamReviewApp(QWidget): 
    def __init__(self): # Fonction initiale de la fenêtre
        super().__init__()
        self.setWindowTitle("Analyse des Reviews Steam")
        self.setGeometry(200, 200, 1000, 700)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.btn_load = QPushButton("Charger la base de données")
        self.btn_load.clicked.connect(self.load_data)
        self.layout.addWidget(self.btn_load)

        self.btn_export = QPushButton("Exporter les résultats")
        self.btn_export.clicked.connect(self.export_results)
        self.layout.addWidget(self.btn_export)

        self.btn_export_graph = QPushButton("Exporter le graphique en PNG")
        self.btn_export_graph.clicked.connect(self.export_graph)
        self.layout.addWidget(self.btn_export_graph)

        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        self.layout.addWidget(self.text_output)

        self.canvas = FigureCanvas(Figure(figsize=(10, 5)))
        self.layout.addWidget(self.canvas)

        self.ax = self.canvas.figure.subplots()

    def load_data(self): # Fonction de chargement de la base de données
        file_path, _ = QFileDialog.getOpenFileName(self, "Choisir une base SQLite", "", "Base de données (*.db)")
        if not file_path:
            return

        conn = sqlite3.connect(file_path)
        df = pd.read_sql_query("SELECT * FROM jeux", conn)
        conn.close()

        # Nettoyage des évaluations Steam
        steam_eval_map = {
            "extrêmement négatives": -4,
            "très négatives": -3,
            "négatives": -2,
            "plutôt négatives": -1,
            "moyennes": 0,
            "positives": 1,
            "plutôt positives": 2,
            "très positives": 3,
            "extrêmement positives": 4
        }

        # Nettoyage + colonnes calculées
        df["evaluation_steam"] = df["evaluation_steam"].str.lower().str.strip()
        df["evaluation_score"] = df["evaluation_steam"].map(steam_eval_map)
        df["note_metacritic"] = pd.to_numeric(df["note_metacritic"], errors="coerce")
        df["reviews_pos"] = pd.to_numeric(df["reviews_pos"], errors="coerce")
        df["reviews_total"] = pd.to_numeric(df["reviews_total"], errors="coerce")

        df["positive_ratio"] = df["reviews_pos"] / df["reviews_total"]
        df["positive_ratio"] = df["positive_ratio"].fillna(0)
        df["metacritic_tranche"] = (df["note_metacritic"] // 10) * 10

        # Statistiques texte
        desc_metacritic = df["note_metacritic"].describe()
        desc_eval = df["evaluation_steam"].describe()
        corr, p = pearsonr(df["note_metacritic"], df["evaluation_score"])

        summary = df.groupby("metacritic_tranche").agg({
            "reviews_total": "sum",
            "reviews_pos": "sum",
            "reviews_neg": "sum",
            "positive_ratio": "mean"
        }).reset_index()

        # Affichage stats texte
        self.text_output.clear()
        self.text_output.append("--- Statistiques note Metacritic ---")
        self.text_output.append(str(desc_metacritic))
        self.text_output.append("\n--- Statistiques évaluation Steam ---")
        self.text_output.append(str(desc_eval))
        self.text_output.append(f"\nCorrélation Metacritic / Éval Steam : {corr:.2f} (p={p:.3f})")
        self.text_output.append("\n--- Résumé par tranche Metacritic ---")
        self.text_output.append(str(summary))

        # Affichage graphique : ratio positif par tranche
        self.ax.clear()
        df.groupby("metacritic_tranche")["positive_ratio"].mean().plot(kind="bar", ax=self.ax, color="green")
        self.ax.set_title("Ratio moyen de reviews positives par tranche Metacritic")
        self.ax.set_xlabel("Tranche Metacritic")
        self.ax.set_ylabel("Ratio de reviews positives")
        self.ax.set_ylim(0, 1)
        self.canvas.draw()

        self.df = df

    def export_results(self): # Fonction d'exportation des resultats d'analyse
        if not hasattr(self, "df"):
            self.text_output.append("Aucune donnée à exporter. Chargez une base d'abord.")
            return
        
        # Sauvegarder les informations
        summary = self.df.groupby("metacritic_tranche").agg({
            "reviews_total": "sum",
            "reviews_pos": "sum",
            "reviews_neg": "sum",
            "positive_ratio": "mean"
        }).reset_index()

        csv_path, _ = QFileDialog.getSaveFileName(self, "Exporter le résumé en CSV", "", "CSV Files (*.csv)")
        if csv_path:
            summary.to_csv(csv_path, index=False , sep=";")
            self.text_output.append(f"Résumé exporté : {csv_path}")

        # Exporter les stats textuelles
        txt_path, _ = QFileDialog.getSaveFileName(self, "Exporter les stats texte", "", "Texte (*.txt)")
        if txt_path:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(self.text_output.toPlainText())
            self.text_output.append(f"Stats texte exportées : {txt_path}")
    
    def export_graph(self): # Fonction d'exportation du graphique
        if not hasattr(self, "df"):
            self.text_output.append("Aucune donnée à exporter.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Exporter le graphique", "", "Image PNG (*.png)")
        if path:
            self.canvas.figure.savefig(path)
            self.text_output.append(f"Graphique exporté : {path}")



if __name__ == "__main__": # Fonction de lancement de l'app
    app = QApplication(sys.argv)
    window = SteamReviewApp()
    window.show()
    sys.exit(app.exec())
