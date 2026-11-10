-- =====================================================================
-- Prêt'Outil — les 5 questions du sujet
-- Chaque requête lit ses paramètres dans un CTE "params" : changer la
-- valeur en haut de la requête suffit pour l'essayer sur d'autres cas.
-- =====================================================================

\echo
\echo '== Q1. Outils du local LOC-NORD libres dans les 3 prochains jours =='
-- Un exemplaire est libre s'il n'a aucun emprunt dont la période touche
-- la période demandée (même calcul de période que la contrainte EXCLUDE),
-- et s'il n'est pas encore dehors en retard (sinon il n'est pas au local).
WITH params AS (
    SELECT 'LOC-NORD'::varchar   AS code_local,
           current_date          AS du,
           current_date + 3      AS au
)
SELECT x.code_barres, m.libelle AS modele, c.libelle AS categorie,
       m.habilitation_requise
FROM params p
JOIN exemplaire x ON x.code_local = p.code_local
JOIN modele m     ON m.id_modele = x.id_modele
JOIN categorie c  ON c.code_categorie = m.code_categorie
WHERE NOT EXISTS (
    SELECT 1 FROM emprunt e
    WHERE e.code_barres = x.code_barres
      AND (
            daterange(e.date_debut, LEAST(e.date_retour_reelle, e.date_retour_prevue), '[]')
              && daterange(p.du, p.au, '[]')
         OR (e.date_retour_reelle IS NULL AND e.date_retour_prevue < current_date)
      )
)
ORDER BY c.libelle, m.libelle, x.code_barres;


\echo
\echo '== Q2. Emprunts en retard aujourd''hui =='
SELECT e.id_emprunt, e.code_barres, m.libelle AS modele,
       a.num_adherent, a.prenom || ' ' || a.nom AS adherent, a.telephone,
       e.date_retour_prevue,
       current_date - e.date_retour_prevue AS jours_de_retard
FROM emprunt e
JOIN adherent a   ON a.num_adherent = e.num_adherent
JOIN exemplaire x ON x.code_barres = e.code_barres
JOIN modele m     ON m.id_modele = x.id_modele
WHERE e.date_retour_reelle IS NULL
  AND e.date_retour_prevue < current_date
ORDER BY jours_de_retard DESC, e.id_emprunt;


\echo
\echo '== Q3. Les 10 modèles les plus empruntés de l''année =='
WITH params AS (
    SELECT EXTRACT(YEAR FROM current_date)::integer AS annee
)
SELECT m.libelle AS modele, m.marque, c.libelle AS categorie,
       count(*) AS nb_emprunts
FROM params p
JOIN emprunt e    ON e.date_debut >= make_date(p.annee, 1, 1)
                 AND e.date_debut <  make_date(p.annee + 1, 1, 1)
JOIN exemplaire x ON x.code_barres = e.code_barres
JOIN modele m     ON m.id_modele = x.id_modele
JOIN categorie c  ON c.code_categorie = m.code_categorie
GROUP BY m.id_modele, m.libelle, m.marque, c.libelle
ORDER BY nb_emprunts DESC, m.libelle
LIMIT 10;


\echo
\echo '== Q4. Historique de l''exemplaire EX00001 : qui, quand, dans quel état =='
WITH params AS (
    SELECT 'EX00001'::varchar AS code_barres
)
SELECT e.date_debut, e.date_retour_prevue, e.date_retour_reelle,
       a.num_adherent, a.prenom || ' ' || a.nom AS emprunteur,
       COALESCE(e.etat_retour, '(en cours)') AS etat_retour,
       b.prenom || ' ' || b.nom AS controle_par,
       e.note_avis
FROM params p
JOIN emprunt e       ON e.code_barres = p.code_barres
JOIN adherent a      ON a.num_adherent = e.num_adherent
LEFT JOIN adherent b ON b.num_adherent = e.controle_par
ORDER BY e.date_debut DESC;


\echo
\echo '== Q5. Adhérents dont la cotisation expire ce mois-ci =='
-- Une cotisation couvre une année civile (RG2) : elle expire le 31 décembre.
-- On liste les adhérents dont la dernière cotisation expire dans le mois
-- demandé et qui n'ont pas encore payé l'année suivante.
-- En novembre, la liste est vide : remplacer current_date par
-- date '2026-12-01' pour voir les relances de décembre.
WITH params AS (
    SELECT date_trunc('month', current_date)::date AS mois
)
SELECT a.num_adherent, a.prenom || ' ' || a.nom AS adherent, a.email,
       c.annee, make_date(c.annee, 12, 31) AS date_expiration
FROM params p
JOIN cotisation c ON make_date(c.annee, 12, 31) >= p.mois
                 AND make_date(c.annee, 12, 31) <  (p.mois + interval '1 month')::date
JOIN adherent a   ON a.num_adherent = c.num_adherent
WHERE NOT EXISTS (
    SELECT 1 FROM cotisation n
    WHERE n.num_adherent = c.num_adherent
      AND n.annee = c.annee + 1
)
ORDER BY a.nom, a.prenom;
