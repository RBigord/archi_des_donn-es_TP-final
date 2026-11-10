# Conception et architecture des données — TP final

**Bachelor 3 · Ycode A2627_4672**

| | |
|---|---|
| **Membres** | Loulia Tsui, Mathis Valentin, Raphaël Bigord |
| **Sujet** | « Prêt’Outil », une outilthèque de quartier |
| **Dépôt** | _lien public du dépôt_ |
| **Date de rendu** | vendredi 13 novembre 2026, 23 h 59 |

---

## Sommaire

1. [Présentation du sujet](#0-présentation-du-sujet)
2. [Le cahier des charges](#1-le-cahier-des-charges)
3. [Le MCD](#2-le-mcd-modèle-conceptuel-de-données)
4. [Le MLD](#3-le-mld-modèle-logique-de-données)
5. [Ce que le schéma ne garantit pas](#4-ce-que-le-schéma-ne-garantit-pas)
6. [Le choix de la base — ADR](#5-le-choix-de-la-base--adr)
7. [Bonus — L'implémentation](#6-bonus--limplémentation)

---

## 0. Présentation du sujet

> _Décrire en quelques lignes le domaine, les utilisateurs et ce que l'application doit permettre._

&nbsp;

**Questions auxquelles la base doit répondre :**

1. _…_
2. _…_
3. _…_

&nbsp;

---

## 1. Le cahier des charges

### 1.1 Règles de gestion

> 8 à 12 règles, numérotées. Chaque règle doit permettre de déduire une cardinalité ou une contrainte (« au plus un », « au moins un », « toujours », « facultatif »).

| N° | Règle de gestion | Cardinalité / contrainte déduite |
|----|------------------|----------------------------------|
| RG1 | _…_ | _…_ |
| RG2 | _…_ | _…_ |
| RG3 | _…_ | _…_ |
| RG4 | _…_ | _…_ |
| RG5 | _…_ | _…_ |
| RG6 | _…_ | _…_ |
| RG7 | _…_ | _…_ |
| RG8 | _…_ | _…_ |
| RG9 | _…_ | _…_ |
| RG10 | _…_ | _…_ |
| RG11 | _…_ | _…_ |
| RG12 | _…_ | _…_ |

### 1.2 Questions qu'on s'est posées

> Les questions qui ont fait hésiter, et la réponse retenue (ex. : « une catégorie peut-elle être vide ? »).

| Question | Réponse retenue | Règle concernée |
|----------|-----------------|-----------------|
| _…_ | _…_ | RG_ |
| _…_ | _…_ | RG_ |
| _…_ | _…_ | RG_ |
| _…_ | _…_ | RG_ |

&nbsp;

---

## 2. Le MCD (Modèle Conceptuel de Données)

### 2.1 Schéma

> _Insérer le diagramme (image, Mermaid, Looping…)._

```mermaid
erDiagram
    %% À compléter
```

&nbsp;

### 2.2 Entités et identifiants

> Identifiant technique + identifiant métier quand il existe (n° SIRET, ISBN, e-mail, code produit…).

| Entité | Identifiant | Identifiant métier | Attributs principaux |
|--------|-------------|--------------------|----------------------|
| _…_ | _…_ | _…_ | _…_ |
| _…_ | _…_ | _…_ | _…_ |
| _…_ | _…_ | _…_ | _…_ |
| _…_ | _…_ | _…_ | _…_ |
| _…_ | _…_ | _…_ | _…_ |

### 2.3 Associations et cardinalités

> Chaque cardinalité doit s'appuyer sur une règle de gestion.

| Association | Entité A | Card. A | Entité B | Card. B | Règle(s) |
|-------------|----------|---------|----------|---------|----------|
| _…_ | _…_ | _,_ | _…_ | _,_ | RG_ |
| _…_ | _…_ | _,_ | _…_ | _,_ | RG_ |
| _…_ | _…_ | _,_ | _…_ | _,_ | RG_ |
| _…_ | _…_ | _,_ | _…_ | _,_ | RG_ |
| _…_ | _…_ | _,_ | _…_ | _,_ | RG_ |

### 2.4 Association(s) porteuse(s) de données

> Au moins une association qui porte des données (prix payé, avis, quantité, date…) et pourquoi la donnée est placée sur l'association plutôt que sur une entité.

| Association | Données portées | Pourquoi ici |
|-------------|-----------------|--------------|
| _…_ | _…_ | _…_ |

&nbsp;

---

## 3. Le MLD (Modèle Logique de Données)

**Base retenue :** _…_

### 3.1 Schéma logique

> _Relationnel : `TABLE(**clé**, attribut, #clé_étrangère)` — NoSQL : structure des documents / clés / tables._

```text
À compléter
```

&nbsp;

### 3.2 Passage MCD → MLD : où va chaque association, et pourquoi

> Relationnel : selon les règles de passage (1,n → clé étrangère ; n,n → table d'association ; 0,1/1,1 → …).
> NoSQL : imbriquée, référencée, une clé, une table par requête, une relation.

| Association du MCD | Traduction dans le MLD | Justification (règle de passage / requête servie) |
|--------------------|------------------------|---------------------------------------------------|
| _…_ | _…_ | _…_ |
| _…_ | _…_ | _…_ |
| _…_ | _…_ | _…_ |
| _…_ | _…_ | _…_ |
| _…_ | _…_ | _…_ |

> _Si plusieurs bases : donner le MLD de chaque base et préciser quelle donnée va où._

&nbsp;

---

## 4. Ce que le schéma ne garantit pas

> Les contraintes qu'on ne peut pas exprimer dans le schéma, et l'endroit où on les garantit (transaction, trigger, code applicatif, CHECK, validateur…).

| Contrainte non garantie par le schéma | Règle | Où on la garantit | Comment |
|---------------------------------------|-------|-------------------|---------|
| _…_ | RG_ | _transaction / trigger / code_ | _…_ |
| _…_ | RG_ | _…_ | _…_ |
| _…_ | RG_ | _…_ | _…_ |

&nbsp;

---

## 5. Le choix de la base — ADR

### ADR-001 : _Titre de la décision_

**Statut :** _Accepté_ · **Date :** _…_

#### Contexte

> Des faits : volume, forme des données, façon de les lire, fréquence des écritures, garanties attendues.

- _…_
- _…_
- _…_

&nbsp;

#### Options envisagées

> Au moins deux autres SGBD comparés au choix retenu.

| Critère | _Option 1 (retenue)_ | _Option 2_ | _Option 3_ |
|---------|----------------------|------------|------------|
| Forme des données | _…_ | _…_ | _…_ |
| Façon de les lire (requêtes) | _…_ | _…_ | _…_ |
| Écritures | _…_ | _…_ | _…_ |
| Garanties (ACID, cohérence…) | _…_ | _…_ | _…_ |
| Verdict | _…_ | _…_ | _…_ |

**Option 1 — _…_ :**
_…_

**Option 2 — _…_ :**
_…_

**Option 3 — _…_ :**
_…_

&nbsp;

#### Décision

> _Ce qu'on choisit, en une ou deux phrases, et la raison principale._

&nbsp;

#### Normalisation ou dénormalisation

> Décision dite et justifiée : qui tient la copie à jour, ou pourquoi il n'y a pas de copie.

- **Choix :** _normalisé / dénormalisé sur …_
- **Justification :** _…_
- **Qui tient la copie à jour :** _… (ou : pas de copie, parce que …)_

&nbsp;

#### Conséquences

**Ce que le choix facilite :**

- _…_

**Ce que le choix rend plus difficile :**

- _…_
- _…_

**Ce qui nous ferait revoir cette décision :**

- _…_
- _…_

&nbsp;

---

## 6. Bonus — L'implémentation

### 6.1 Structure du dépôt

```text
.
├── README.md
├── ...
```

### 6.2 Création de la base

> SQL ou schéma ORM, conforme à la conception (ou écart expliqué).

- **Fichier :** _…_
- **Écarts avec la conception :** _aucun / …_

### 6.3 Génération des données

> Script qui génère les données (plutôt qu'un fichier rempli à la main).

- **Script :** _…_
- **Volume généré :** _…_

### 6.4 Requêtes qui répondent aux questions du sujet

| Question | Fichier / requête |
|----------|-------------------|
| _…_ | _…_ |
| _…_ | _…_ |

### 6.5 Application

> Petite application qui lit ou écrit dans la base.

_…_

### 6.6 Lancer le projet

```bash
# À compléter : commandes pour tout lancer (aussi dans le README.md)
```
