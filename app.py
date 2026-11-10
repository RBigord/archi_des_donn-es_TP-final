"""Prêt'Outil — petite application en ligne de commande.

Elle lit et écrit dans la base PostgreSQL. Les règles de gestion ne sont pas
recodées ici : c'est la base (contraintes et triggers) qui refuse un emprunt
interdit, et l'application affiche simplement la raison.

Exemples :
    python app.py en-cours A00012
    python app.py emprunter A00012 EX00042 --jours 7
    python app.py rendre 6512 --etat bon --benevole A00003 --note 5
    python app.py retards
    python app.py demo-limite
"""

import argparse
import os
import sys
from datetime import date, timedelta

import psycopg
from psycopg import errors


def connexion():
    return psycopg.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "pretoutil"),
        user=os.getenv("PGUSER", "pretoutil"),
        password=os.getenv("PGPASSWORD", "pretoutil"),
    )


def message_erreur(exc):
    """Traduit une erreur de la base en message lisible."""
    if isinstance(exc, errors.ExclusionViolation):
        return "RG7 : cet exemplaire est déjà emprunté ou réservé sur cette période."
    diag = exc.diag
    if isinstance(exc, errors.CheckViolation) and diag.constraint_name:
        return f"Contrainte {diag.constraint_name} non respectée ({diag.message_primary})."
    return diag.message_primary or str(exc)


def tableau(lignes, entetes):
    if not lignes:
        print("  (aucune ligne)")
        return
    largeurs = [max(len(str(v)) for v in col) for col in zip(entetes, *lignes)]
    print("  " + "  ".join(h.ljust(l) for h, l in zip(entetes, largeurs)))
    print("  " + "  ".join("-" * l for l in largeurs))
    for ligne in lignes:
        print("  " + "  ".join(str("" if v is None else v).ljust(l) for v, l in zip(ligne, largeurs)))


# --------------------------------------------------------------------------
# Écritures
# --------------------------------------------------------------------------

def inserer_emprunt(cur, adherent, exemplaire, debut, jours):
    cur.execute(
        """INSERT INTO emprunt (num_adherent, code_barres, date_debut, date_retour_prevue)
           VALUES (%s, %s, %s, %s) RETURNING id_emprunt""",
        (adherent, exemplaire, debut, debut + timedelta(days=jours)),
    )
    return cur.fetchone()[0]


def cmd_emprunter(args):
    debut = args.debut or date.today()
    with connexion() as conn, conn.cursor() as cur:
        try:
            # Une transaction par emprunt : si deux adhérents réservent le même
            # exemplaire au même moment, EXCLUDE refuse la seconde (RG7).
            id_emprunt = inserer_emprunt(cur, args.adherent, args.exemplaire, debut, args.jours)
        except psycopg.Error as exc:
            print(f"Emprunt refusé. {message_erreur(exc)}")
            return 1
        print(f"Emprunt n° {id_emprunt} enregistré : {args.exemplaire} pour {args.adherent}, "
              f"du {debut} au {debut + timedelta(days=args.jours)}.")
    return 0


def cmd_rendre(args):
    with connexion() as conn, conn.cursor() as cur:
        try:
            cur.execute(
                """UPDATE emprunt
                   SET date_retour_reelle = %s, etat_retour = %s, controle_par = %s,
                       note_avis = %s, commentaire_avis = %s
                   WHERE id_emprunt = %s AND date_retour_reelle IS NULL""",
                (args.date or date.today(), args.etat, args.benevole,
                 args.note, args.commentaire, args.id_emprunt),
            )
        except psycopg.Error as exc:
            print(f"Retour refusé. {message_erreur(exc)}")
            return 1
        if cur.rowcount == 0:
            print(f"Aucun emprunt en cours avec le n° {args.id_emprunt}.")
            return 1
    print(f"Retour de l'emprunt n° {args.id_emprunt} enregistré (état : {args.etat}, "
          f"contrôlé par {args.benevole}).")
    return 0


# --------------------------------------------------------------------------
# Lectures
# --------------------------------------------------------------------------

def cmd_en_cours(args):
    with connexion() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT e.id_emprunt, e.code_barres, m.libelle, e.date_debut, e.date_retour_prevue,
                      CASE WHEN e.date_retour_prevue < current_date THEN 'EN RETARD' ELSE '' END
               FROM emprunt e
               JOIN exemplaire x ON x.code_barres = e.code_barres
               JOIN modele m ON m.id_modele = x.id_modele
               WHERE e.num_adherent = %s AND e.date_retour_reelle IS NULL
               ORDER BY e.date_debut""",
            (args.adherent,),
        )
        print(f"Emprunts en cours de {args.adherent} :")
        tableau(cur.fetchall(), ["n°", "exemplaire", "modèle", "début", "retour prévu", ""])
    return 0


def cmd_retards(_args):
    with connexion() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT e.id_emprunt, e.code_barres, a.num_adherent, a.prenom || ' ' || a.nom,
                      e.date_retour_prevue, current_date - e.date_retour_prevue
               FROM emprunt e JOIN adherent a ON a.num_adherent = e.num_adherent
               WHERE e.date_retour_reelle IS NULL AND e.date_retour_prevue < current_date
               ORDER BY 6 DESC"""
        )
        print("Emprunts en retard aujourd'hui :")
        tableau(cur.fetchall(), ["n°", "exemplaire", "adhérent", "nom", "retour prévu", "jours"])
    return 0


# --------------------------------------------------------------------------
# Démonstration : le 4e emprunt est refusé (RG6)
# --------------------------------------------------------------------------

def cmd_demo_limite(_args):
    with connexion() as conn, conn.cursor() as cur:
        # Un adhérent à jour de cotisation, sans emprunt en cours.
        cur.execute(
            """SELECT a.num_adherent, a.prenom || ' ' || a.nom
               FROM adherent a
               JOIN cotisation c ON c.num_adherent = a.num_adherent
                                AND c.annee = EXTRACT(YEAR FROM current_date)
               WHERE NOT EXISTS (SELECT 1 FROM emprunt e
                                 WHERE e.num_adherent = a.num_adherent
                                   AND e.date_retour_reelle IS NULL)
               ORDER BY a.num_adherent LIMIT 1"""
        )
        adherent, nom = cur.fetchone()

        # 4 exemplaires libres aujourd'hui, sans habilitation requise.
        cur.execute(
            """SELECT x.code_barres, m.libelle
               FROM exemplaire x JOIN modele m ON m.id_modele = x.id_modele
               WHERE NOT m.habilitation_requise
                 AND NOT EXISTS (
                     SELECT 1 FROM emprunt e
                     WHERE e.code_barres = x.code_barres
                       AND (daterange(e.date_debut, LEAST(e.date_retour_reelle, e.date_retour_prevue), '[]')
                              && daterange(current_date, current_date + 7, '[]')
                            OR (e.date_retour_reelle IS NULL AND e.date_retour_prevue < current_date)))
               ORDER BY x.code_barres LIMIT 4"""
        )
        outils = cur.fetchall()

        print(f"Adhérent choisi : {adherent} ({nom}), aucun emprunt en cours.\n")
        for i, (code, libelle) in enumerate(outils, start=1):
            # Un point de sauvegarde par emprunt : l'échec du 4e n'annule pas
            # les 3 premiers dans la transaction de démonstration.
            try:
                with conn.transaction():
                    id_emprunt = inserer_emprunt(cur, adherent, code, date.today(), 7)
                print(f"  Emprunt {i} : {code} ({libelle}) -> accepté (n° {id_emprunt})")
            except psycopg.Error as exc:
                print(f"  Emprunt {i} : {code} ({libelle}) -> REFUSÉ")
                print(f"      {message_erreur(exc)}")

        conn.rollback()
        print("\nDémonstration annulée (ROLLBACK) : la base n'a pas été modifiée.")
    return 0


# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Prêt'Outil — emprunter et rendre un outil.")
    sous = p.add_subparsers(dest="commande", required=True)

    e = sous.add_parser("emprunter", help="enregistrer un emprunt")
    e.add_argument("adherent", help="numéro d'adhérent, ex. A00012")
    e.add_argument("exemplaire", help="code-barres, ex. EX00042")
    e.add_argument("--debut", type=date.fromisoformat, help="date de début (AAAA-MM-JJ), par défaut aujourd'hui")
    e.add_argument("--jours", type=int, default=7, help="durée en jours (14 au plus, RG8)")
    e.set_defaults(func=cmd_emprunter)

    r = sous.add_parser("rendre", help="enregistrer le retour d'un outil")
    r.add_argument("id_emprunt", type=int)
    r.add_argument("--etat", required=True, choices=["bon", "use", "a_reparer"])
    r.add_argument("--benevole", required=True, help="numéro du bénévole qui contrôle (RG9)")
    r.add_argument("--date", type=date.fromisoformat, help="date de retour, par défaut aujourd'hui")
    r.add_argument("--note", type=int, help="avis facultatif, de 1 à 5 (RG11)")
    r.add_argument("--commentaire")
    r.set_defaults(func=cmd_rendre)

    c = sous.add_parser("en-cours", help="emprunts en cours d'un adhérent")
    c.add_argument("adherent")
    c.set_defaults(func=cmd_en_cours)

    sous.add_parser("retards", help="emprunts en retard aujourd'hui").set_defaults(func=cmd_retards)
    sous.add_parser("demo-limite", help="montre que le 4e emprunt est refusé (RG6)").set_defaults(func=cmd_demo_limite)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
