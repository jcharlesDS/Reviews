import os
import sqlite3
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QFileDialog, QLineEdit, QLabel, QMessageBox, QHBoxLayout, QGridLayout
)

# Interface graphique
class DatabaseApp(QWidget):
    def __init__(self): # Fonction initiale de la fenêtre (permettre de remplir la BDD)
        super().__init__()
        self.setWindowTitle("Base de données Steam - Jeux Vidéo")
        self.db_path = None
        self.conn = None

        self.layout = QVBoxLayout(self)

        self.fields = {
            "Nom": QLineEdit(),
            "AppID": QLineEdit(),
            "Note Metacritic": QLineEdit(),
            "Évaluation Steam": QLineEdit(),
            "Reviews Capturés": QLineEdit(),
            "Reviews Positives": QLineEdit(),
            "Reviews Négatives": QLineEdit(),
            "Review-Bomb / Controverses": QLineEdit(),
        }

        form_layout = QGridLayout()
        for i, (label, widget) in enumerate(self.fields.items()):
            form_layout.addWidget(QLabel(label + ":"), i, 0)
            form_layout.addWidget(widget, i, 1)

        self.layout.addLayout(form_layout)

        self.add_button = QPushButton("Ajouter")
        self.reset_button = QPushButton("Réinitialiser")

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.add_button)
        btn_layout.addWidget(self.reset_button)
        self.layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.layout.addWidget(self.table)

        self.add_button.clicked.connect(self.add_entry)
        self.reset_button.clicked.connect(self.reset_database)

        self.choose_or_create_database()
        self.load_data()

    def choose_or_create_database(self): # Fonction permettant de créer ou d'utiliser une bdd déjà existante
        db_path, _ = QFileDialog.getSaveFileName(
            self, "Choisir ou créer une base de données", "", "Base de données SQLite (*.db)"
        )
        if not db_path:
            QMessageBox.critical(self, "Erreur", "Aucun fichier sélectionné.")
            exit()

        self.db_path = db_path
        new_db = not os.path.exists(db_path)
        self.conn = sqlite3.connect(self.db_path)

        if new_db:
            self.initialize_database()

    def initialize_database(self): # Fonction d'initialisation de la base de données
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jeux (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                app_id TEXT,
                note_metacritic TEXT,
                evaluation_steam TEXT,
                reviews_total INTEGER,
                reviews_pos INTEGER,
                reviews_neg INTEGER,
                controverses TEXT
            )
        """)
        self.conn.commit()

    def add_entry(self): # Fonction pour ajouter une valeur/entrée dans la base de données
        values = []
        for key, widget in self.fields.items():
            val = widget.text().strip()
            values.append(val if val != "" else None)

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO jeux (
                    nom, app_id, note_metacritic, evaluation_steam,
                    reviews_total, reviews_pos, reviews_neg, controverses
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                values[0],
                values[1],
                values[2],
                values[3],
                int(values[4]) if values[4] else 0,
                int(values[5]) if values[5] else 0,
                int(values[6]) if values[6] else 0,
                values[7],
            ))
            self.conn.commit()

            for widget in self.fields.values():
                widget.clear()

            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur est survenue : {e}")

    def load_data(self): # Fonction permettant de récupérer les informations déjà existantes dans une database (spécifique à notre base de données)
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jeux")
        rows = cursor.fetchall()

        self.table.setRowCount(len(rows))
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nom", "AppID", "Metacritic", "Steam", "Reviews Capturés",
            "Positives", "Négatives", "Controverses"
        ])

        for row_idx, row in enumerate(rows):
            for col_idx, val in enumerate(row):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(val)))

    def reset_database(self): # Fonction permettant de reinitialiser les données
        confirm = QMessageBox.question(self, "Réinitialiser", "Effacer toutes les données ?")
        if confirm == QMessageBox.Yes:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM jeux")
            self.conn.commit()
            self.load_data()

if __name__ == "__main__": # Fonction de lancement de l'application
    app = QApplication([])
    window = DatabaseApp()
    window.show()
    app.exec()
