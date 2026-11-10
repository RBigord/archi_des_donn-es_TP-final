-- =====================================================================
-- Prêt'Outil — schéma PostgreSQL
-- Conforme au MLD du rendu (partie 3) et aux garanties de la partie 4.
-- =====================================================================

-- Nécessaire pour mélanger "=" (texte) et "&&" (intervalles) dans un
-- même index GiST : c'est ce qui permet la contrainte EXCLUDE (RG7).
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ---------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------

-- RG1 : numéro d'adhérent unique, e-mail unique.
CREATE TABLE adherent (
    num_adherent     varchar(10)  PRIMARY KEY,
    email            varchar(255) NOT NULL UNIQUE,
    nom              varchar(100) NOT NULL,
    prenom           varchar(100) NOT NULL,
    telephone        varchar(30),
    est_benevole     boolean      NOT NULL DEFAULT false,   -- RG9 : le bénévole est un adhérent
    date_inscription date         NOT NULL DEFAULT current_date
);

CREATE TABLE annee (
    annee integer PRIMARY KEY CHECK (annee BETWEEN 2000 AND 2100)
);

-- COTISER (n,n) -> table à part. La clé composée garantit
-- au plus une cotisation par adhérent et par an (RG2).
CREATE TABLE cotisation (
    num_adherent  varchar(10)  NOT NULL REFERENCES adherent (num_adherent),
    annee         integer      NOT NULL REFERENCES annee (annee),
    montant_paye  numeric(6,2) NOT NULL CHECK (montant_paye >= 0),
    date_paiement date         NOT NULL,
    PRIMARY KEY (num_adherent, annee)
);

-- RG3 : une catégorie peut être vide (aucune contrainte côté catégorie).
CREATE TABLE categorie (
    code_categorie varchar(20)  PRIMARY KEY,
    libelle        varchar(100) NOT NULL
);

-- APPARTENIR (1,1 — 0,n) -> clé étrangère NOT NULL côté modèle (RG3).
CREATE TABLE modele (
    id_modele            integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reference_fabricant  varchar(50)  NOT NULL UNIQUE,
    libelle              varchar(150) NOT NULL,
    marque               varchar(100) NOT NULL,
    habilitation_requise boolean      NOT NULL DEFAULT false,   -- RG10
    code_categorie       varchar(20)  NOT NULL REFERENCES categorie (code_categorie)
);

-- HABILITER (n,n) -> table à part, porte la date de formation (RG10).
CREATE TABLE habilitation (
    num_adherent   varchar(10) NOT NULL REFERENCES adherent (num_adherent),
    id_modele      integer     NOT NULL REFERENCES modele (id_modele),
    date_formation date        NOT NULL,
    PRIMARY KEY (num_adherent, id_modele)
);

CREATE TABLE local (
    code_local varchar(20)  PRIMARY KEY,
    nom        varchar(100) NOT NULL,
    adresse    varchar(255) NOT NULL
);

-- CORRESPONDRE et RANGER (1,1 — 0,n) -> clés étrangères NOT NULL (RG4, RG5).
-- Pas de colonne "statut" : il est calculé depuis les emprunts (voir l'ADR).
CREATE TABLE exemplaire (
    code_barres varchar(20) PRIMARY KEY,                                  -- RG4
    date_achat  date        NOT NULL,
    id_modele   integer     NOT NULL REFERENCES modele (id_modele),
    code_local  varchar(20) NOT NULL REFERENCES local (code_local)
);

-- EFFECTUER, CONCERNER (1,1) -> clés NOT NULL ; CONTRÔLER (0,1) -> clé nullable.
-- L'avis (RG11) et l'état au retour (RG9) sont des colonnes facultatives.
CREATE TABLE emprunt (
    id_emprunt         integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    num_adherent       varchar(10) NOT NULL REFERENCES adherent (num_adherent),
    code_barres        varchar(20) NOT NULL REFERENCES exemplaire (code_barres),
    date_debut         date        NOT NULL,
    date_retour_prevue date        NOT NULL,
    date_retour_reelle date,                      -- NULL tant que l'outil n'est pas rendu
    etat_retour        varchar(10),
    controle_par       varchar(10) REFERENCES adherent (num_adherent),
    note_avis          smallint,
    commentaire_avis   text,

    -- RG8 : retour prévu au plus 14 jours après le début.
    CONSTRAINT ck_duree_max_14j
        CHECK (date_retour_prevue BETWEEN date_debut AND date_debut + 14),
    CONSTRAINT ck_retour_apres_debut
        CHECK (date_retour_reelle IS NULL OR date_retour_reelle >= date_debut),

    -- RG9 : l'état fait partie d'une liste fermée, et un retour est
    -- toujours contrôlé : date de retour, état et contrôleur vont ensemble.
    CONSTRAINT ck_etat_retour
        CHECK (etat_retour IN ('bon', 'use', 'a_reparer')),
    CONSTRAINT ck_retour_controle
        CHECK ((date_retour_reelle IS NULL) = (etat_retour IS NULL)
           AND (date_retour_reelle IS NULL) = (controle_par IS NULL)),

    -- RG11 : au plus un avis (colonnes uniques), note de 1 à 5,
    -- seulement après le retour, et pas de commentaire sans note.
    CONSTRAINT ck_note_avis
        CHECK (note_avis BETWEEN 1 AND 5),
    CONSTRAINT ck_avis_apres_retour
        CHECK (note_avis IS NULL OR date_retour_reelle IS NOT NULL),
    CONSTRAINT ck_commentaire_avec_note
        CHECK (commentaire_avis IS NULL OR note_avis IS NOT NULL),

    -- RG7 : deux emprunts du même exemplaire ne se chevauchent jamais.
    -- La période va du début au retour prévu, ou au retour réel s'il a eu
    -- lieu plus tôt (un outil rendu en avance redevient libre).
    -- LEAST ignore les NULL : tant que l'outil n'est pas rendu, on prend
    -- la date de retour prévue.
    CONSTRAINT ex_pas_de_chevauchement
        EXCLUDE USING gist (
            code_barres WITH =,
            daterange(date_debut, LEAST(date_retour_reelle, date_retour_prevue), '[]') WITH &&
        )
);

-- Index pour les questions du sujet.
CREATE INDEX ix_emprunt_adherent_en_cours ON emprunt (num_adherent) WHERE date_retour_reelle IS NULL;
CREATE INDEX ix_emprunt_retard            ON emprunt (date_retour_prevue) WHERE date_retour_reelle IS NULL;
CREATE INDEX ix_emprunt_debut             ON emprunt (date_debut);
CREATE INDEX ix_exemplaire_local          ON exemplaire (code_local);
CREATE INDEX ix_exemplaire_modele         ON exemplaire (id_modele);

-- ---------------------------------------------------------------------
-- Triggers : ce qu'un CHECK ne peut pas garantir, parce qu'il faut
-- lire une autre table (partie 4.2 du rendu).
-- ---------------------------------------------------------------------

-- Trigger 1 — règles liées à l'adhérent : RG6 (3 emprunts en cours au plus)
-- et RG2 (cotisation de l'année de l'emprunt payée).
CREATE FUNCTION fn_emprunt_regles_adherent() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    nb_en_cours integer;
BEGIN
    -- Verrouille la ligne de l'adhérent : deux emprunts lancés en même
    -- temps par le même adhérent passent l'un après l'autre, sinon les deux
    -- compteraient 2 emprunts en cours et en créeraient 4.
    PERFORM 1 FROM adherent WHERE num_adherent = NEW.num_adherent FOR UPDATE;

    -- RG2
    IF NOT EXISTS (
        SELECT 1 FROM cotisation
        WHERE num_adherent = NEW.num_adherent
          AND annee = EXTRACT(YEAR FROM NEW.date_debut)::integer
    ) THEN
        RAISE EXCEPTION 'RG2 : l''adhérent % n''a pas payé sa cotisation pour %',
            NEW.num_adherent, EXTRACT(YEAR FROM NEW.date_debut)::integer
            USING ERRCODE = 'check_violation';
    END IF;

    -- RG6 (seulement pour un emprunt en cours : un emprunt historique,
    -- déjà rendu, ne compte pas)
    IF NEW.date_retour_reelle IS NULL THEN
        SELECT count(*) INTO nb_en_cours
        FROM emprunt
        WHERE num_adherent = NEW.num_adherent
          AND date_retour_reelle IS NULL;

        IF nb_en_cours >= 3 THEN
            RAISE EXCEPTION 'RG6 : l''adhérent % a déjà % emprunts en cours (3 au plus)',
                NEW.num_adherent, nb_en_cours
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_emprunt_regles_adherent
    BEFORE INSERT ON emprunt
    FOR EACH ROW EXECUTE FUNCTION fn_emprunt_regles_adherent();

-- Trigger 2 — RG10 : un modèle qui demande une habilitation ne peut être
-- emprunté que par un adhérent formé avant le début de l'emprunt.
CREATE FUNCTION fn_emprunt_habilitation() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_id_modele integer;
    v_requise   boolean;
BEGIN
    SELECT m.id_modele, m.habilitation_requise
      INTO v_id_modele, v_requise
    FROM exemplaire x
    JOIN modele m ON m.id_modele = x.id_modele
    WHERE x.code_barres = NEW.code_barres;

    IF v_requise AND NOT EXISTS (
        SELECT 1 FROM habilitation
        WHERE num_adherent = NEW.num_adherent
          AND id_modele = v_id_modele
          AND date_formation <= NEW.date_debut
    ) THEN
        RAISE EXCEPTION 'RG10 : l''adhérent % n''est pas habilité pour le modèle de l''exemplaire %',
            NEW.num_adherent, NEW.code_barres
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_emprunt_habilitation
    BEFORE INSERT OR UPDATE OF code_barres, num_adherent, date_debut ON emprunt
    FOR EACH ROW EXECUTE FUNCTION fn_emprunt_habilitation();

-- Trigger 3 — RG9 : celui qui contrôle le retour doit être bénévole.
CREATE FUNCTION fn_emprunt_controle_benevole() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.controle_par IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM adherent
        WHERE num_adherent = NEW.controle_par
          AND est_benevole
    ) THEN
        RAISE EXCEPTION 'RG9 : % n''est pas bénévole, il ne peut pas contrôler un retour',
            NEW.controle_par
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_emprunt_controle_benevole
    BEFORE INSERT OR UPDATE OF controle_par ON emprunt
    FOR EACH ROW EXECUTE FUNCTION fn_emprunt_controle_benevole();
