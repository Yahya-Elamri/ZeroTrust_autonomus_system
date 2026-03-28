# Résumé du Projet : Système de Détection d'Anomalies pour Véhicules Autonomes

> **Domaine :** Cybersécurité des Véhicules Autonomes  
> **Technologies :** CARLA Simulator, ROS 2 (Humble), TensorFlow/Keras, Python  
> **Date :** Mars 2026  

---

## 1. Contexte et Objectif

Le projet vise à développer et valider un **système de détection d'anomalies en temps réel** capable de protéger un véhicule autonome contre des attaques de type *spoofing* (usurpation de données capteurs). L'approche adoptée repose sur le paradigme **Zero-Trust** : chaque donnée sensorielle reçue est considérée comme potentiellement malveillante et doit être validée contre un modèle de comportement physique légitime avant d'être acceptée.

Le capteur ciblé est l'**IMU (Inertial Measurement Unit)**, qui fournit les données d'accélération linéaire et de vitesse angulaire du véhicule.

---

## 2. Architecture Globale du Système

Le système est composé de **quatre composants principaux**, chacun ayant un rôle précis dans le pipeline :

```
[Simulateur CARLA] ──► [Collecteur de Données (ROS 2)]
                                    │
                                    ▼
                         [Dataset CSV : Conduite Saine]
                                    │
                                    ▼
                    [Entraînement Auto-encodeur LSTM]
                                    │
                          ┌─────────┴──────────┐
                          │                    │
                   [Modèle .h5]          [Scaler .gz]
                          │
                          ▼
                 [Calibration du Seuil (99ème percentile)]
                          │
                          ▼
                   [config.json : Seuil = 2.52]
                          │
                          ▼
         [Nœud d'Inférence ROS 2 (Moniteur Zero-Trust)]
                          │
              ┌───────────┴────────────┐
              │                        │
   /carla/hero/imu              /security/alerts
 (Données IMU live)            (Alertes anomalies)
              │
              ▼
    [Injecteur d'Attaque] ──► Simulation spoofing IMU
```

---

## 3. Composants du Projet

### 3.1 — Collecte de Données : `data/data_collector.py`

Ce script ROS 2 constitue la **première étape du pipeline**. Il joue le rôle d'un nœud subscriber qui écoute le topic `/carla/hero/imu` et enregistre les données de conduite normale dans un fichier CSV.

**Fonctionnement :**
- Souscrit au topic IMU du véhicule autonome `hero` dans CARLA
- Extrait à chaque message : l'horodatage, les 3 axes d'accélération (`accel_x/y/z`) et les 3 axes de vitesse angulaire (`ang_vel_x/y/z`)
- Sauvegarde chaque échantillon dans `healthy_driving_data.csv`

**Résultat :** Un dataset de **~3.2 MB** de données de conduite saine, représentant le comportement physique normal du véhicule. Ce dataset sert de **référence de vérité terrain** pour l'entraînement du modèle.

---

### 3.2 — Entraînement du Modèle : `LSTM/train_plausibility_monitor.py`

Ce script entraîne un **auto-encodeur LSTM** (Long Short-Term Memory) sur le dataset de conduite saine. Le modèle apprend à **reconstruire** des séquences temporelles normales. L'idée clé : un comportement anormal sera mal reconstruit, générant une erreur élevée.

**Pipeline d'entraînement :**
1. **Chargement des données** depuis `healthy_driving_data.csv` (6 features)
2. **Normalisation** via `StandardScaler` (variable critique pour la stabilité numérique) — le scaler est sauvegardé dans `scaler.gz`
3. **Création de séquences** par fenêtre glissante de **10 timesteps** (forme finale : `[N, 10, 6]`)
4. **Architecture du modèle :**
   - *Encodeur* : LSTM(32, relu) → compresse la séquence en vecteur latent
   - *Vecteur latent* : RepeatVector(10) → reconstruction de la dimension temporelle
   - *Décodeur* : LSTM(32, relu) + TimeDistributed(Dense(6)) → reconstruction des 6 features
5. **Compilation** : optimiseur Adam, fonction de perte MSE
6. **Entraînement** : 20 époques, batch_size=32, validation_split=0.1

**Résultat :** Le modèle entraîné est sauvegardé sous `plausibility_model.h5` (~206 KB).

---

### 3.3 — Calibration du Seuil : `LSTM/calibrate_threshold.py`

Ce script calcule de manière **statistiquement rigoureuse** le seuil de détection d'anomalies, évitant ainsi de le fixer arbitrairement.

**Méthode :**
1. Recharge le dataset de conduite saine et le scaler
2. Recrée les séquences de 10 pas de temps
3. Fait prédire le modèle sur ces séquences (comportement normal)
4. Calcule l'**erreur de reconstruction MSE** pour chaque séquence
5. Fixe le seuil au **99ème percentile** de la distribution des erreurs

> **Seuil calculé : 2.5208** — Toute erreur MSE supérieure à ce seuil déclenche une alerte.

Le seuil, ainsi que tous les paramètres de configuration, sont sauvegardés dans `config.json`.

---

### 3.4 — Nœud d'Inférence ROS 2 : `LSTM/plausibility_inference_node.py`

C'est le **cœur opérationnel** du système. Ce nœud ROS 2 tourne en temps réel sur le véhicule et évalue en continu la plausibilité physique de chaque donnée IMU reçue.

**Architecture du nœud (`PlausibilityDetector`) :**

| Élément | Détail |
|---|---|
| Nom ROS 2 | `plausibility_detector` |
| Topic souscrit | `/carla/hero/imu` (messages `sensor_msgs/Imu`) |
| Topic publié | `/security/alerts` (messages `std_msgs/String`) |
| Fenêtre glissante | `deque(maxlen=10)` — structure efficace O(1) |
| Seuil | Chargé dynamiquement depuis `config.json` (2.52) |

**Logique de détection (Zero-Trust) :**
1. À chaque message IMU reçu, les 6 valeurs sont extraites et normalisées via le scaler
2. L'échantillon normalisé est ajouté au buffer circulaire (fenêtre de 10)
3. Dès que la fenêtre est pleine, le modèle reconstruit la séquence
4. L'**erreur MSE** entre la séquence réelle et sa reconstruction est calculée
5. Si `MSE > seuil` → **alerte publiée** sur `/security/alerts` avec le message d'erreur détaillé
6. Sinon → log normal avec throttle (1 seconde) pour éviter le spam

**Gestion des erreurs :**
- Fallback sur seuil par défaut (1.5) si `config.json` est absent
- Correction de conflit Protobuf/TensorFlow via `TF_USE_LEGACY_KERAS=1`

---

### 3.5 — Injecteur d'Attaque : `attack/attack_injector.py`

Ce script simule une **cyberattaque de type spoofing IMU** pour valider l'efficacité du moniteur de détection. Il publie intentionnellement des données physiquement impossibles sur le même topic IMU que le véhicule.

**Mécanisme d'attaque :**
- Nœud ROS 2 (`attack_injector`) qui publie sur `/carla/hero/imu`
- Injection d'accélérations extrêmes : `accel_x = accel_y = accel_z = 100.0 m/s²` (physiquement impossible pour un véhicule normal)
- Fréquence d'injection : **10 Hz** (toutes les 0.1 secondes)

**But :** Vérifier que le nœud `PlausibilityDetector` détecte bien ces données aberrantes et publie les alertes correspondantes sur `/security/alerts`.

---

### 3.6 — Scripts de Lancement : `lunching_scripts.md`

Ce fichier documente la **séquence complète de démarrage** de l'environnement de simulation et de test.

| Étape | Commande | Description |
|---|---|---|
| 1 | `./CarlaUE4.sh -RenderOffScreen` | Lancement du serveur CARLA (mode serveur) |
| 2 | `python3 config.py -m Town01` | Chargement de la carte Town01 (PythonAPI) |
| 3 | `python3 generate_traffic.py -n 20 -w 10` | Génération du trafic ambiant (TM) |
| 4 | `ros2 launch carla_ros_bridge ...` | Spawning du véhicule ego et du bridge ROS 2 |
| 5 | `ros2 topic pub .../enable_autopilot` | Activation de l'autonomie complète (Traffic Manager) |
| 6 | `python3 plausibility_inference_node.py` | Lancement du moniteur Zero-Trust (LSTM) |
| 7 | `rviz2 -d ...` | Visualisation des données et des alertes sécurité |

---

## 4. Fichiers Générés et Artefacts

| Fichier | Type | Description |
|---|---|---|
| `data/healthy_driving_data.csv` | Dataset | ~3.2 MB de données de conduite saine (télémétrie IMU brute) |
| `LSTM/plausibility_model.h5` | Modèle ML | Auto-encodeur LSTM entraîné (~206 KB) |
| `LSTM/scaler.gz` | Preprocesseur | StandardScaler ajusté sur les données d'entraînement |
| `LSTM/config.json` | Configuration | Seuil calibré (2.52) + paramètres du modèle |

---

## 5. Modèle de Détection : Auto-encodeur LSTM

### Principe

Un **auto-encodeur** est un réseau de neurones entraîné à **reconstruire son entrée**. En l'entraînant **uniquement sur des données normales**, il apprend la distribution du comportement physique sain. Face à une donnée anormale (attaque), il est incapable de la reconstruire correctement, ce qui se traduit par une **erreur MSE élevée**.

### Architecture

```
Entrée : [batch, 10 timesteps, 6 features]
        │
        ▼
   LSTM(32, relu)          ← Encodeur : compresse en 32 dimensions
        │
        ▼
   RepeatVector(10)        ← Réplication du vecteur latent
        │
        ▼
   LSTM(32, relu)          ← Décodeur : reconstruction temporelle
        │
        ▼
TimeDistributed(Dense(6))  ← Reconstruction des 6 features
        │
        ▼
Sortie : [batch, 10 timesteps, 6 features]
```

### Décision

```
MSE(séquence_réelle, séquence_reconstruite) > 2.52  ──►  🚨 ANOMALIE DÉTECTÉE
MSE(séquence_réelle, séquence_reconstruite) ≤ 2.52  ──►  ✅ Physique OK
```

---

## 6. Validation et Tests

Le système a été validé selon le scénario suivant :

1. **Démarrage de l'environnement** : CARLA + ROS 2 + véhicule autonome
2. **Lancement du moniteur** : `plausibility_inference_node.py` en écoute sur le topic IMU
3. **Conduite normale** : Le véhicule roule normalement → MSE faible → aucune alerte
4. **Déclenchement de l'attaque** : `attack_injector.py` injecte `100 m/s²` d'accélération fictive
5. **Détection** : Le MSE dépasse largement le seuil (2.52) → une alerte est immédiatement publiée sur `/security/alerts`

> **Résultat :** Le système détecte correctement l'attaque IMU spoofing et publie des alertes en temps réel, confirmant la validité de l'approche Zero-Trust basée sur un auto-encodeur LSTM.

---

## 7. Technologies et Bibliothèques Utilisées

| Technologie | Version/Usage |
|---|---|
| **CARLA Simulator** | 0.9.16 — Simulation de conduite autonome |
| **ROS 2** | Humble — Middleware robotique temps réel |
| **TensorFlow / Keras** | Mode Legacy Keras — Entraînement et inférence LSTM |
| **scikit-learn** | StandardScaler — Normalisation des données |
| **joblib** | Sérialisation du scaler |
| **NumPy / Pandas** | Traitement des données et des séquences |
| **Python** | 3.x — Langage de développement principal |

---

## 8. Points Techniques Notables

- **Efficacité de la fenêtre glissante** : Utilisation de `collections.deque(maxlen=10)` pour un buffer circulaire en O(1), plus performant qu'un `list.pop(0)` en O(n).
- **Compatibilité TensorFlow** : Variable d'environnement `TF_USE_LEGACY_KERAS=1` pour résoudre un conflit Protobuf dans l'environnement ROS 2.
- **Seuil statistique** : Le choix du 99ème percentile garantit que 99% des comportements normaux ne déclenchent **pas** de faux positifs.
- **Throttle des logs** : `throttle_duration_sec=1.0` sur les logs normaux pour éviter la saturation des terminaux en production.
- **Configuration dynamique** : Séparation entre le code (`plausibility_inference_node.py`) et la configuration (`config.json`) pour faciliter la recalibration sans redéploiement.

---

*Résumé rédigé le 24 mars 2026*
