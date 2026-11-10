"""Génère un jeu de données réaliste pour Prêt'Outil.

Les données sont générées (Faker), pas écrites à la main. Le script respecte
les règles de gestion : les triggers et les contraintes de schema.sql
refuseraient sinon les lignes.

Volumes visés (sujet) : ~300 exemplaires dans 2 locaux, 800 adhérents,
~6 000 emprunts par an, sur l'année dernière et l'année en cours.

Le script vide les tables avant de les remplir : on peut le relancer.
"""

import os
import random
from collections import defaultdict
from datetime import date, timedelta

import psycopg
from faker import Faker

SEED = 42
NB_ADHERENTS = 800
NB_EXEMPLAIRES = 300
PART_BENEVOLES = 0.05

fake = Faker("fr_FR")
Faker.seed(SEED)
random.seed(SEED)

AUJOURDHUI = date.today()
ANNEE = AUJOURDHUI.year
DEBUT_HISTORIQUE = date(ANNEE - 1, 1, 1)

LOCAUX = [
    ("LOC-NORD", "Local Nord", "12 rue des Artisans"),
    ("LOC-SUD", "Local Sud", "3 place du Marché"),
]

# (code, libellé, [(marque, libellé du modèle, habilitation requise)])
CATALOGUE = [
    ("PERC", "Perçage et vissage", [
        ("Bosch", "Perceuse PSB 500", False),
        ("Makita", "Visseuse DF333", False),
        ("Bosch", "Perforateur PBH 2100", False),
        ("Ryobi", "Perceuse R18PD", False),
    ]),
    ("DECO", "Découpe", [
        ("Stihl", "Tronçonneuse MS 180", True),
        ("Bosch", "Scie sauteuse PST 700", False),
        ("Makita", "Scie circulaire HS7601", True),
        ("Dremel", "Outil multifonction 3000", False),
    ]),
    ("JARD", "Jardin", [
        ("Honda", "Tondeuse HRG 416", False),
        ("Stihl", "Taille-haie HS 45", True),
        ("Black+Decker", "Coupe-bordures GL250", False),
        ("Ryobi", "Souffleur RBL18", False),
        ("Stihl", "Débroussailleuse FS 55", True),
    ]),
    ("NETT", "Nettoyage", [
        ("Kärcher", "Nettoyeur haute pression K4", False),
        ("Kärcher", "Aspirateur WD 3", False),
        ("Kärcher", "Nettoyeur vapeur SC 3", False),
    ]),
    ("ACCE", "Accès en hauteur", [
        ("Hailo", "Échelle 3 plans 3x9", False),
        ("Zarges", "Escabeau 6 marches", False),
        ("Altrex", "Échafaudage roulant RS 44", True),
    ]),
    ("PEIN", "Peinture et ponçage", [
        ("Wagner", "Pistolet à peinture W 590", False),
        ("Bosch", "Ponceuse PEX 300", False),
        ("Festool", "Ponceuse girafe LHS 225", False),
    ]),
    ("MACO", "Maçonnerie", [
        ("Altrade", "Bétonnière 140 L", False),
        ("Hilti", "Marteau-piqueur TE 500", True),
    ]),
    # RG3 : une catégorie peut être vide (créée avant l'achat des outils).
    ("SOUD", "Soudure", []),
]

ETATS = ["bon", "use", "a_reparer"]
POIDS_ETATS = [80, 15, 5]


def connexion():
    return psycopg.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "pretoutil"),
        user=os.getenv("PGUSER", "pretoutil"),
        password=os.getenv("PGPASSWORD", "pretoutil"),
    )


def date_entre(debut, fin):
    return debut + timedelta(days=random.randint(0, max(0, (fin - debut).days)))


def generer_adherents():
    adherents = []
    for i in range(1, NB_ADHERENTS + 1):
        adherents.append((
            f"A{i:05d}",
            fake.unique.email(),
            fake.last_name(),
            fake.first_name(),
            fake.phone_number(),
            random.random() < PART_BENEVOLES,
            date_entre(date(ANNEE - 3, 1, 1), DEBUT_HISTORIQUE - timedelta(days=1)),
        ))
    return adherents


def generer_cotisations(adherents):
    """RG2 : au plus une cotisation par an. ~85 % des adhérents paient chaque année.
    Les bénévoles paient toujours (ils doivent pouvoir emprunter et contrôler)."""
    cotisations = []
    for num, *_, est_benevole, inscription in adherents:
        for annee in (ANNEE - 1, ANNEE):
            if inscription.year > annee:
                continue
            if est_benevole or random.random() < 0.85:
                debut_paiement = max(date(annee, 1, 1), inscription)
                fin_paiement = min(date(annee, 2, 28), AUJOURDHUI)
                montant = random.choice([20.00, 20.00, 20.00, 10.00])  # 10 € = tarif réduit
                cotisations.append((num, annee, montant, date_entre(debut_paiement, fin_paiement)))
    return cotisations


def main():
    adherents = generer_adherents()
    benevoles = [a[0] for a in adherents if a[5]]
    cotisations = generer_cotisations(adherents)
    cotisants = defaultdict(set)  # année -> adhérents à jour
    for num, annee, *_ in cotisations:
        cotisants[annee].add(num)

    with connexion() as conn, conn.cursor() as cur:
        cur.execute("""
            TRUNCATE emprunt, exemplaire, local, habilitation, modele,
                     categorie, cotisation, annee, adherent
            RESTART IDENTITY CASCADE
        """)

        cur.executemany(
            "INSERT INTO adherent VALUES (%s, %s, %s, %s, %s, %s, %s)", adherents)
        cur.executemany(
            "INSERT INTO annee VALUES (%s)", [(a,) for a in (ANNEE - 1, ANNEE, ANNEE + 1)])
        cur.executemany(
            "INSERT INTO cotisation VALUES (%s, %s, %s, %s)", cotisations)

        # Catalogue
        modeles = []  # (id_modele, habilitation_requise)
        for code, libelle, liste in CATALOGUE:
            cur.execute("INSERT INTO categorie VALUES (%s, %s)", (code, libelle))
            for marque, lib, habil in liste:
                cur.execute(
                    """INSERT INTO modele (reference_fabricant, libelle, marque,
                                           habilitation_requise, code_categorie)
                       VALUES (%s, %s, %s, %s, %s) RETURNING id_modele""",
                    (fake.unique.bothify("??-####").upper(), lib, marque, habil, code))
                modeles.append((cur.fetchone()[0], habil))

        # RG10 : ~25 % des adhérents sont formés à 1 ou 2 modèles dangereux,
        # avant le début de l'historique.
        dangereux = [m for m, h in modeles if h]
        habilitations = []
        habilites = defaultdict(set)  # id_modele -> adhérents habilités
        for num, *_ in adherents:
            if random.random() < 0.25:
                for m in random.sample(dangereux, random.randint(1, 2)):
                    habilitations.append((num, m, date_entre(date(ANNEE - 3, 1, 1), DEBUT_HISTORIQUE)))
                    habilites[m].add(num)
        cur.executemany("INSERT INTO habilitation VALUES (%s, %s, %s)", habilitations)

        cur.executemany("INSERT INTO local VALUES (%s, %s, %s)", LOCAUX)

        # Exemplaires : les outils courants ont plus d'exemplaires.
        # Un modèle peut n'avoir aucun exemplaire (RG4) : on en laisse un sans.
        modeles_avec_exemplaires = modeles[:-1]
        poids = [1 if h else 3 for _, h in modeles_avec_exemplaires]
        exemplaires = []
        for i in range(1, NB_EXEMPLAIRES + 1):
            id_modele, habil = random.choices(modeles_avec_exemplaires, weights=poids)[0]
            exemplaires.append((
                f"EX{i:05d}",
                date_entre(date(ANNEE - 4, 1, 1), DEBUT_HISTORIQUE),
                id_modele,
                random.choice(LOCAUX)[0],
                habil,
            ))
        cur.executemany(
            "INSERT INTO exemplaire VALUES (%s, %s, %s, %s)", [e[:4] for e in exemplaires])

        # Emprunts : pour chaque exemplaire, une suite d'emprunts qui ne se
        # chevauchent pas (RG7), de 1 à 14 jours (RG8).
        emprunts = []
        en_cours = defaultdict(int)  # RG6
        for code_barres, _, id_modele, _, habil in exemplaires:
            curseur = DEBUT_HISTORIQUE + timedelta(days=random.randint(0, 15))
            while curseur <= AUJOURDHUI:
                debut = curseur
                prevue = debut + timedelta(days=random.randint(1, 14))
                candidats = cotisants[debut.year]
                if habil:
                    candidats = candidats & habilites[id_modele]  # RG10
                if not candidats:
                    curseur += timedelta(days=7)
                    continue

                retour = prevue + timedelta(days=random.choice([0, 0, 0, -1, -2, 1, 3]))
                retour = max(retour, debut)
                if retour < AUJOURDHUI:
                    # Emprunt terminé : rendu, contrôlé par un bénévole (RG9),
                    # avec parfois un avis (RG11).
                    num = random.choice(sorted(candidats))
                    note = random.choices([None, 5, 4, 3, 2, 1], [70, 12, 10, 4, 2, 2])[0]
                    commentaire = fake.sentence(nb_words=8) if note and random.random() < 0.5 else None
                    emprunts.append((
                        num, code_barres, debut, prevue, retour,
                        random.choices(ETATS, POIDS_ETATS)[0],
                        random.choice(benevoles), note, commentaire,
                    ))
                    curseur = max(retour, prevue) + timedelta(days=random.randint(1, 20))
                else:
                    # Emprunt en cours (parfois en retard), si l'adhérent
                    # n'en a pas déjà 3 (RG6).
                    libres = [n for n in sorted(candidats) if en_cours[n] < 3]
                    if libres and random.random() < 0.6:
                        num = random.choice(libres)
                        en_cours[num] += 1
                        emprunts.append((num, code_barres, debut, prevue,
                                         None, None, None, None, None))
                    break

        emprunts.sort(key=lambda e: e[2])
        cur.executemany(
            """INSERT INTO emprunt (num_adherent, code_barres, date_debut, date_retour_prevue,
                                    date_retour_reelle, etat_retour, controle_par,
                                    note_avis, commentaire_avis)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            emprunts)

        conn.commit()

        print("Données générées :")
        for table in ("adherent", "cotisation", "categorie", "modele", "habilitation",
                      "local", "exemplaire", "emprunt"):
            cur.execute(f"SELECT count(*) FROM {table}")
            print(f"  {table:<13} {cur.fetchone()[0]:>6}")
        cur.execute("SELECT count(*) FROM emprunt WHERE date_retour_reelle IS NULL")
        print(f"  dont emprunts en cours : {cur.fetchone()[0]}")


if __name__ == "__main__":
    main()
