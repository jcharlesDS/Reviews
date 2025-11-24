import os
import re
import sys
import sqlite3
import numpy as np
import matplotlib.pyplot as plt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QListWidget, QListWidgetItem, QCheckBox, QMessageBox, QSpinBox, QHBoxLayout
)
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.utils import resample
import seaborn as sns

class ClassifierComparisonApp(QWidget):
    def __init__(self): # Fonction initiale de la fenêtre
        super().__init__()
        self.setWindowTitle("Comparateur de Classifieurs")
        self.resize(800, 600)

        self.layout = QVBoxLayout()
        self.label = QLabel("Choisissez le dossier contenant les reviews (par tranche Metacritic)")
        self.layout.addWidget(self.label)

        self.tranche_list = QListWidget()
        self.tranche_list.setSelectionMode(QListWidget.MultiSelection)
        self.layout.addWidget(self.tranche_list)

        self.select_all_button = QPushButton("Tout sélectionner / Tout désélectionner")
        self.select_all_button.clicked.connect(self.toggle_all_tranches)
        self.layout.addWidget(self.select_all_button)

        self.load_button = QPushButton("Charger les tranches disponibles")
        self.load_button.clicked.connect(self.load_tranches)
        self.layout.addWidget(self.load_button)

        self.output_button = QPushButton("Choisir le dossier de sortie des résultats")
        self.output_button.clicked.connect(self.select_output_dir)
        self.layout.addWidget(self.output_button)

        size_layout = QHBoxLayout()
        self.size_label = QLabel("Taille minimale du contenu :")
        self.size_spinbox = QSpinBox()
        self.size_spinbox.setMinimum(0)
        self.size_spinbox.setMaximum(1000)
        self.size_spinbox.setValue(1)  # Valeur par défaut 
        size_layout.addWidget(self.size_label)
        size_layout.addWidget(self.size_spinbox)
        self.layout.addLayout(size_layout)

        self.oversampling_checkbox = QCheckBox("Activer l'oversampling")
        self.oversampling_checkbox.setChecked(True)
        self.layout.addWidget(self.oversampling_checkbox)

        self.reset_button = QPushButton("Réinitialiser")
        self.reset_button.clicked.connect(self.reset_app)
        self.layout.addWidget(self.reset_button)

        self.run_button = QPushButton("Lancer la comparaison des classifieurs")
        self.run_button.clicked.connect(self.run_comparison)
        self.layout.addWidget(self.run_button)

        self.setLayout(self.layout)
        self.output_dir = os.getcwd()

    def toggle_all_tranches(self): # Fonction permettant de sélectionner ou déselectionner toutes les tranches Metacritic pour l'analyse
        all_checked = all(self.tranche_list.item(i).checkState() == Qt.CheckState.Checked for i in range(self.tranche_list.count()))
        new_state = Qt.CheckState.Unchecked if all_checked else Qt.CheckState.Checked
        for i in range(self.tranche_list.count()):
            item = self.tranche_list.item(i)
            item.setCheckState(new_state)
            print(f"Tranche {item.text()} sélectionnée : {item.checkState() == Qt.CheckState.Checked}")


    def reset_app(self): # Fonction pour réinitialiser les champs
        self.tranche_list.clear()
        self.output_dir = os.getcwd()

    def select_output_dir(self): # Fonction pour choisir le dossier de sortie
        selected = QFileDialog.getExistingDirectory(self, "Choisir le dossier de sortie")
        if selected:
            self.output_dir = selected

    def load_tranches(self): # Fonction pour charger les tranches sur l'interface
        self.base_dir = QFileDialog.getExistingDirectory(self, "Choisir le dossier racine")
        if not self.base_dir:
            return

        self.tranche_list.clear()
        message_info = ""
        total_reviews = 0

        for name in sorted(os.listdir(self.base_dir)):
            if re.match(r"^\d{1,3}-\d{1,3}$", name):
                tranche_path = os.path.join(self.base_dir, name)
                count_reviews = 0
                for jeu in os.listdir(tranche_path):
                    jeu_path = os.path.join(tranche_path, jeu)
                    if not os.path.isdir(jeu_path):
                        continue
                    for file in os.listdir(jeu_path):
                        if file.startswith("review_") and file.endswith(".txt"):
                            count_reviews +=1

                total_reviews += count_reviews
                item = QListWidgetItem(name)
                item.setCheckState(Qt.Checked)
                self.tranche_list.addItem(item)
                message_info += f"Tranche {name} :  {count_reviews} reviews trouvées\n"

        if message_info:
            message_info += f"\nTOTAL : {total_reviews} reviews trouvées"
            QMessageBox.information(self, "Détail des tranches chargées", message_info)

    def load_data(self, selected_tranches): # Fonction chargeant les données à classifier
        X, y = [], []
        total_files = 0
        ignored_no_note = 0
        ignored_short = 0
        ignored_not_review = 0
        used_files = 0

        min_size = self.size_spinbox.value()  # récupère la taille minimale choisie

        for tranche in selected_tranches:
            tranche_path = os.path.join(self.base_dir, tranche)
            for jeu in os.listdir(tranche_path):
                jeu_path = os.path.join(tranche_path, jeu)
                if not os.path.isdir(jeu_path):
                    continue
                for file in os.listdir(jeu_path):
                    if not file.endswith(".txt"):
                        continue
                    total_files += 1
                    if not file.startswith("review_"):
                        ignored_not_review += 1
                        continue
                    path = os.path.join(jeu_path, file)
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if not lines or not lines[0].startswith("Note"):
                            ignored_no_note += 1
                            continue
                        label = 1 if "👍" in lines[0] else 0
                        content = " ".join(lines[1:]).strip()
                        if len(content) < min_size:
                            ignored_short += 1
                            continue
                        X.append(content)
                        y.append(label)
                        used_files += 1

        stats = {
            "total": total_files,
            "ignored_no_note": ignored_no_note,
            "ignored_short": ignored_short,
            "ignored_not_review": ignored_not_review,
            "used": used_files
        }
        return X, y, stats

    def save_results_to_db(self, results): # Fonction sauvegardant les informations dans une base de données et l'ouvre post-analyse
        db_path = os.path.join(self.output_dir, "resultats_classifieurs.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS performances (
                modele TEXT,
                precision REAL,
                rappel REAL,
                f1 REAL
            )
        """)
        c.execute("DELETE FROM performances")
        for model, scores in results.items():
            c.execute("INSERT INTO performances VALUES (?, ?, ?, ?)",
                      (model, scores['precision'], scores['recall'], scores['f1-score']))
        conn.commit()
        conn.close()
        
        if os.name == 'nt':
            os.system(f'start "" "{db_path}"')
        else:
            os.system(f'open "{db_path}"')

    def save_results_to_txt(self, results, stats): # Fonction sauvegardant les résultats dans un fichier txt.
        txt_path = os.path.join(self.output_dir, "resultats_classifieurs.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            for model, scores in results.items():
                f.write(f"Modèle : {model}\n")
                for metric, value in scores.items():
                    f.write(f"  {metric} : {value:.4f}\n")
                f.write("\n")
            f.write("Statistiques sur les fichiers :\n")
            f.write(f"  Fichiers totaux trouvés : {stats['total']}\n")
            f.write(f"  Fichiers ignorés (pas de Note) : {stats['ignored_no_note']}\n")
            f.write(f"  Fichiers ignorés (trop court) : {stats['ignored_short']}\n")
            f.write(f"  Fichiers ignorés (pas 'review_') : {stats['ignored_not_review']}\n")
            f.write(f"  Fichiers utilisés réellement : {stats['used']}\n")

    def run_comparison(self): # Fonction lançant l'analyse
        selected = [self.tranche_list.item(i).text() for i in range(self.tranche_list.count())
            if self.tranche_list.item(i).checkState() == Qt.Checked]

        if not selected:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner au moins une tranche.")
            return

        X, y, stats = self.load_data(selected)
        if len(X) < 10:
            QMessageBox.warning(self, "Erreur", "Pas assez de données pour entraîner les modèles.")
            return

        vectorizer = TfidfVectorizer(max_features=5000) # Vectorisation par le TF-IDF
        X_vect = vectorizer.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X_vect, y, test_size=0.2, random_state=42) # Séparation des données d'entrainement et de test. (ici, 80% train, 20% test)

        if self.oversampling_checkbox.isChecked(): # Oversampling (au cas où une classe à évaluer est clairement minoritaire, ici les avis négatifs)
            X_train_array = X_train.toarray()
            y_train_array = np.array(y_train)

            class_0_indices = np.where(y_train_array == 0)[0]
            class_1_indices = np.where(y_train_array == 1)[0]

            if len(class_0_indices) > 0 and len(class_1_indices) > 0:
                if len(class_0_indices) > len(class_1_indices):
                    maj, min_ = class_0_indices, class_1_indices
                else:
                    maj, min_ = class_1_indices, class_0_indices

                min_upsambled = resample(min_, replace=True, n_samples=len(maj), random_state=42)
                indices_final = np.concatenate((maj, min_upsambled))
                X_train = X_train_array[indices_final]
                y_train = y_train_array[indices_final]

        if isinstance(X_train, np.ndarray):
            X_test = X_test.toarray()

        # Modèles évalués
        models = {
            "Naive Bayes": MultinomialNB(),
            "SVM": SVC(),
            "Random Forest": RandomForestClassifier(),
            "Logistic Regression": LogisticRegression(max_iter=1000)
        }

        results = {}

        for name, model in models.items():
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
            results[name] = report['weighted avg']

            cm = confusion_matrix(y_test, y_pred) # Création de la matrice de confusion
            labels = ['Négatif', 'Positif']
            plt.figure(figsize=(6, 5))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=labels, yticklabels=labels, cbar_kws={'label' : 'Nombre de prédictions'})
            plt.title(f"Matrice de confusion - {name}")
            plt.xlabel("Prédit")
            plt.ylabel("Réel")
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, f"matrice_confusion_{name}.png"))
            plt.close()

        self.save_results_to_db(results) # Enregistrement des résultats dans la DB
        self.save_results_to_txt(results, stats) # Enregistrement des résultats dans le fichier txt

        plt.figure(figsize=(8, 5)) # Création du graphique comparant les mesures d'évaluations des modèles analysés 
        for metric in ["precision", "recall", "f1-score"]:
            vals = [results[model][metric] for model in results]
            plt.plot(list(results.keys()), vals, label=metric)

        plt.title("Performance des classifieurs")
        plt.ylim(0, 1)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "comparaison_classifieurs.png"))
        plt.show()

        QMessageBox.information(self, "Analyse terminée", f"Analyse terminée.\nFichiers utilisés : {stats['used']}\nIgnorés (trop courts) : {stats['ignored_short']}\nIgnorés (pas de Note) : {stats['ignored_no_note']}\nIgnorés (pas 'review_') : {stats['ignored_not_review']}")

if __name__ == '__main__': # Fonction de lancement de l'app
    app = QApplication(sys.argv)
    window = ClassifierComparisonApp()
    window.show()
    sys.exit(app.exec())
