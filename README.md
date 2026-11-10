# Prêt’Outil — une outilthèque de quartier

TP final de **Conception et architecture des données** (Bachelor 3, Ynov).
Loulia Tsui, Mathis Valentin, Raphaël Bigord.

La conception est dans [Conception_et_architecture_des_données.md](Conception_et_architecture_des_données.md) : le cahier des charges, le MCD, le MLD, les garanties et l’ADR.

## Contenu du dépôt

| Fichier | Rôle |
|---------|------|
| `schema.sql` | Création de la base PostgreSQL : tables, contraintes `CHECK` et `EXCLUDE`, 3 triggers |
| `seed.py` | Génère les données avec Faker (800 adhérents, 300 exemplaires, ~6 000 emprunts par an) |
| `queries.sql` | Les 5 requêtes qui répondent aux questions du sujet |
| `app.py` | Application en ligne de commande : emprunter, rendre, voir les retards |
| `docker-compose.yml`, `Dockerfile`, `requirements.txt` | Lancement de l’ensemble |

## Prérequis

Docker et Docker Compose. Rien d’autre à installer.

## Lancer le projet

```bash
docker compose up --build
```

Cette commande :

1. démarre PostgreSQL 16 et exécute `schema.sql` au premier démarrage ;
2. lance `seed.py`, qui remplit la base puis affiche le nombre de lignes générées ;
3. affiche l’aide de l’application.

Laisser tourner ce terminal (la base reste démarrée) et ouvrir un second terminal pour la suite.

## Lancer les 5 requêtes du sujet

```bash
docker compose exec db psql -U pretoutil -d pretoutil -f /queries/queries.sql
```

> Sous Git Bash (Windows), préfixer par `MSYS_NO_PATHCONV=1` pour que le chemin `/queries/...` ne soit pas converti.

## Utiliser l’application

```bash
# Montrer qu'un 4e emprunt est refusé (RG6). La démonstration est annulée à la fin.
docker compose run --rm app demo-limite

# Emprunter un outil (par défaut à partir d'aujourd'hui, pour 7 jours)
docker compose run --rm app emprunter A00002 EX00001 --jours 7

# Voir les emprunts en cours d'un adhérent
docker compose run --rm app en-cours A00002

# Rendre un outil : état, bénévole qui contrôle, avis facultatif
docker compose run --rm app rendre <n°_emprunt> --etat bon --benevole A00006 --note 5

# Emprunts en retard aujourd'hui
docker compose run --rm app retards
```

Quand une règle est violée, c’est la base qui refuse, et l’application affiche la raison :

| Essai | Message |
|-------|---------|
| 4ᵉ emprunt en cours | `RG6 : l'adhérent … a déjà 3 emprunts en cours (3 au plus)` |
| Adhérent sans cotisation de l’année | `RG2 : l'adhérent … n'a pas payé sa cotisation pour 2026` |
| Modèle dangereux sans formation | `RG10 : l'adhérent … n'est pas habilité pour le modèle …` |
| Outil déjà emprunté sur la période | `RG7 : cet exemplaire est déjà emprunté ou réservé sur cette période.` |
| Emprunt de plus de 14 jours (`--jours 20`) | `Contrainte ck_duree_max_14j non respectée` |
| Retour contrôlé par un non-bénévole | `RG9 : … n'est pas bénévole, il ne peut pas contrôler un retour` |
| Note d’avis hors de 1 à 5 | `Contrainte ck_note_avis non respectée` |

Les numéros d’adhérents bénévoles, sans cotisation, etc. dépendent des données générées. Pour en trouver :

```bash
docker compose exec db psql -U pretoutil -d pretoutil -c "SELECT num_adherent FROM adherent WHERE est_benevole LIMIT 5"
```

## Regénérer les données

```bash
docker compose run --rm seed
```

Le script vide les tables avant de les remplir : on peut le relancer autant de fois qu’on veut.

## Repartir de zéro

```bash
docker compose down -v      # supprime aussi le volume de la base
docker compose up --build   # schema.sql est réexécuté
```

La base est aussi accessible depuis la machine sur le port **5433** (utilisateur, mot de passe et base : `pretoutil`).
