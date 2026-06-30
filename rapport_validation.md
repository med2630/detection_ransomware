# Rapport de Validation : Détection Comportementale de Ransomwares par IA

## 1. Introduction et Objectif
Ce rapport démontre le bon fonctionnement et l'intégration de bout en bout de la solution de détection comportementale de ransomwares. L'objectif est de valider le pipeline complet, allant de l'activité utilisateur sur le système de fichiers jusqu'à la génération et l'affichage d'une alerte critique sur le tableau de bord, suite à une prédiction réalisée par un modèle de Machine Learning (Random Forest).

## 2. Architecture Globale et Pipeline de Détection
Notre solution repose sur plusieurs composants travaillant en synergie :
- **Activité utilisateur / Simulateur** : L'utilisateur ou un malware modifie des fichiers dans le dossier surveillé (`watched_folder`).
- **Détection (Watchdog & Psutil)** : Le script `monitor.py` intercepte ces modifications en temps réel via l'OS et relève simultanément l'empreinte processeur (CPU) et mémoire (RAM) du système.
- **Serveur Central et API (Flask)** : Les données brutes interceptées sont envoyées à l'API Flask (`app.py`).
- **Stockage (MySQL)** : Les événements sont persistés dans la base de données relationnelle.
- **Feature Engineering & Prédiction (Random Forest)** : Les données sont agrégées sur des fenêtres temporelles pour extraire le comportement global. Le modèle pré-entraîné (`model.pkl`) analyse ces *features* et retourne un label de classification (Normal, Suspect, ou Ransomware).
- **Alerte et Visualisation (Dashboard)** : Si un comportement ransomware est détecté, une alerte est générée en base de données. Le tableau de bord web (`dashboard.html`) interroge régulièrement l'API et affiche ces informations et alertes en temps réel à l'administrateur.

---

## 3. Déroulement de la Validation

### Étape 1 : Vérifications préalables
Avant de lancer le système, nous avons vérifié la présence de l'ensemble des fichiers critiques (`app.py`, `monitor.py`, `model.pkl`, `simulate.py`), l'installation des dépendances nécessaires et la configuration de la connexion à la base de données MySQL.

> **[INSÉRER CAPTURE D'ÉCRAN 1 ICI]**
> *Légende : Terminal affichant l'arborescence complète du projet et la validation de l'installation des dépendances Python.*

### Étape 2 : Démarrage du module de surveillance (Monitor)
Le script `monitor.py` a été exécuté avec succès. Il a correctement ciblé le répertoire `watched_folder` et s'est mis en attente d'événements systèmes sans générer d'erreur.

> **[INSÉRER CAPTURE D'ÉCRAN 2 ICI]**
> *Légende : Terminal affichant l'exécution de `monitor.py` et le démarrage de la surveillance du dossier cible.*

### Étape 3 : Démarrage du serveur central (Flask)
L'API Flask a été lancée via `app.py`. Les logs confirment que le modèle de Machine Learning `model.pkl` a été correctement chargé en mémoire et que la connexion à la base de données MySQL a été établie avec succès. Des tests de requêtes sur les routes de l'API (`/health`, `/metrics`, `/events`) ont retourné des statuts valides au format JSON.

> **[INSÉRER CAPTURE D'ÉCRAN 3 ICI]**
> *Légende : Terminal affichant les logs de démarrage de Flask, validant le chargement du modèle et la connexion MySQL.*

> **[INSÉRER CAPTURE D'ÉCRAN 4 ICI]**
> *Légende : Réponses JSON obtenues suite aux requêtes de test via `curl` sur les différents endpoints de l'API.*

### Étape 4 : Accès à l'interface de surveillance (Dashboard)
Le tableau de bord a été ouvert dans le navigateur web. L'interface se charge correctement et le mécanisme d'actualisation automatique s'effectue toutes les 5 secondes en communiquant avec l'API.

> **[INSÉRER CAPTURE D'ÉCRAN 5 ICI]**
> *Légende : Interface du Dashboard dans son état initial (zéro événement, aucune alerte).*

### Étape 5 : Test de fonctionnement normal
Afin de valider la réactivité du système face à une utilisation standard, plusieurs opérations classiques (création, modification, renommage, suppression de fichiers texte) ont été réalisées manuellement dans le `watched_folder`. 
Ces actions ont été instantanément captées par le moniteur. L'IA a classifié ces comportements comme **NORMAL**.

> **[INSÉRER CAPTURE D'ÉCRAN 6 ICI]**
> *Légende : Terminal du moniteur affichant la capture en temps réel des événements normaux (created, modified, etc.) et les métriques système associées.*

> **[INSÉRER CAPTURE D'ÉCRAN 7 ICI]**
> *Légende : Interface du Dashboard affichant la mise à jour des événements et confirmant la prédiction de type "NORMAL".*

### Étape 6 : Simulation d'une attaque Ransomware
Un script de simulation (`simulate.py`) a été exécuté pour reproduire le comportement caractéristique d'un ransomware (renommage massif de fichiers et augmentation soudaine de l'utilisation des ressources système).
Le moniteur a enregistré une avalanche d'événements. Le modèle de Machine Learning a analysé ces caractéristiques (fréquence élevée, type d'actions) et a identifié avec succès l'attaque en cours. Le tableau de bord a immédiatement remonté l'alerte **CRITICAL** sans nécessiter de rafraîchissement manuel.

> **[INSÉRER CAPTURE D'ÉCRAN 8 ICI]**
> *Légende : Terminal affichant l'exécution du script `simulate.py`.*

> **[INSÉRER CAPTURE D'ÉCRAN 9 ICI]**
> *Légende : Interface du Dashboard affichant clairement le passage en état d'alerte, la prédiction indiquant une compromission (Ransomware), et l'apparition de l'alerte CRITICAL.*

### Étape 7 : Vérification de la persistance des données
Après arrêt des composants, une requête SQL a été effectuée dans la base de données MySQL pour vérifier l'intégrité des données stockées. La table `file_events` s'est bien enrichie de tous les événements captés, et la table `alerts` contient l'enregistrement exact de l'attaque simulée.

> **[INSÉRER CAPTURE D'ÉCRAN 10 ICI]**
> *Légende : Console MySQL confirmant l'insertion réussie de l'alerte critique et des événements fichiers dans la base de données.*

---

## 4. Bilan et Perspectives

### Performances et Synthèse
Les tests réalisés prouvent que la chaîne de bout en bout est opérationnelle. Le modèle d'intelligence artificielle est capable de différencier avec précision et en temps réel une activité utilisateur normale d'un comportement hostile de type ransomware, prouvant l'efficacité de l'extraction de *features* couplée à l'algorithme Random Forest.

### Limites Actuelles et Améliorations Envisageables
- **Limites** : Le système se base actuellement sur des fenêtres temporelles statiques. De plus, la simulation de l'attaque, bien que représentative, reste algorithmique et pourrait différer de la signature matérielle de certains ransomwares polymorphes sophistiqués.
- **Améliorations futures** : 
  - Bloquer automatiquement le processus malveillant (via `psutil`) dès la détection de l'alerte critique au lieu de se limiter à la notification.
  - Enrichir le modèle avec de nouvelles *features* (entropie des fichiers modifiés) pour réduire les faux positifs.
  - Déployer l'application via des conteneurs Docker pour simplifier l'orchestration.
