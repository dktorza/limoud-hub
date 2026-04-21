PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS ref_statuts_edition (
    code            TEXT PRIMARY KEY,
    libelle         TEXT NOT NULL,
    couleur_hex     TEXT DEFAULT '#6c757d',
    ordre           INTEGER DEFAULT 0,
    est_actif_defaut INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO ref_statuts_edition VALUES
    ('en_preparation',       'En préparation',        '#ffc107', 10, 1),
    ('inscriptions_ouvertes','Inscriptions ouvertes',  '#17a2b8', 20, 0),
    ('active',               'En cours',              '#28a745', 30, 0),
    ('terminee',             'Terminée',              '#6c757d', 40, 0),
    ('archivee',             'Archivée',              '#343a40', 50, 0);

CREATE TABLE IF NOT EXISTS ref_types_lieux (
    code    TEXT PRIMARY KEY,
    libelle TEXT NOT NULL
);
INSERT OR IGNORE INTO ref_types_lieux VALUES
    ('hotel',            'Hôtel'),
    ('salle_conference', 'Salle de conférence'),
    ('synagogue',        'Synagogue'),
    ('campus',           'Campus'),
    ('centre_culturel',  'Centre culturel'),
    ('autre',            'Autre');

CREATE TABLE IF NOT EXISTS ref_formats_session (
    code               TEXT PRIMARY KEY,
    libelle            TEXT NOT NULL,
    duree_defaut_min   INTEGER DEFAULT 60,
    icone              TEXT DEFAULT '?',
    actif              INTEGER DEFAULT 1
);
INSERT OR IGNORE INTO ref_formats_session VALUES
    ('conference',    'Conférence / Lecture',     60,  'micro', 1),
    ('debat',         'Débat',                    60,  'bulle', 1),
    ('atelier',       'Atelier',                  60,  'outil', 1),
    ('etude_textes',  'Étude de textes',           60,  'livre', 1),
    ('projection',    'Projection / Film',         90,  'film',  1),
    ('office',        'Office religieux',           60,  'etoile',1),
    ('concert',       'Concert / Musique',          60,  'note',  1),
    ('stand',         'Stand',                    180,  'shop',  1),
    ('meditation',    'Méditation',                60,  'zen',   1),
    ('sport',         'Sport / Bien-être',          60,  'sport', 1),
    ('speed_dating',  'Speed dating',              60,  'coeur', 1),
    ('spectacle',     'Spectacle / Humour',        90,  'rire',  1),
    ('repas',         'Repas',                    120,  'assiette',1),
    ('autre',         'Autre',                     60,  'point', 1);

CREATE TABLE IF NOT EXISTS ref_niveaux_session (
    code    TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    ordre   INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO ref_niveaux_session VALUES
    ('tout_public', 'Tout public',  10),
    ('initie',      'Initié',       20),
    ('expert',      'Expert',       30);

CREATE TABLE IF NOT EXISTS ref_langues (
    code    TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    actif   INTEGER DEFAULT 1
);
INSERT OR IGNORE INTO ref_langues VALUES
    ('fr',    'Français', 1),
    ('en',    'Anglais',  1),
    ('he',    'Hébreu',   1),
    ('ar',    'Arabe',    1),
    ('autre', 'Autre',    1);

CREATE TABLE IF NOT EXISTS ref_civilites (
    code    TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    ordre   INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO ref_civilites VALUES
    ('M',   'Monsieur',    10),
    ('Mme', 'Madame',      20),
    ('Dr',  'Docteur',     30),
    ('Pr',  'Professeur',  40),
    ('Me',  'Maître',      50),
    ('Rav', 'Rav',         60),
    ('',    'Non précisé', 99);

CREATE TABLE IF NOT EXISTS ref_roles_session (
    code    TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    ordre   INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO ref_roles_session VALUES
    ('principal',      'Intervenant principal', 10),
    ('co_intervenant', 'Co-intervenant',        20),
    ('moderateur',     'Modérateur',            30),
    ('discutant',      'Discutant',             40),
    ('animateur',      'Animateur',             50),
    ('invite',         'Invité',                60);

CREATE TABLE IF NOT EXISTS ref_statuts_participation (
    code        TEXT PRIMARY KEY,
    libelle     TEXT NOT NULL,
    couleur_hex TEXT DEFAULT '#6c757d',
    ordre       INTEGER DEFAULT 0,
    est_final   INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO ref_statuts_participation VALUES
    ('a_contacter',       'À contacter',        '#6c757d', 10, 0),
    ('contacte',          'Contacté',           '#17a2b8', 20, 0),
    ('en_discussion',     'En discussion',      '#ffc107', 30, 0),
    ('formulaire_envoye', 'Formulaire envoyé',  '#fd7e14', 40, 0),
    ('formulaire_recu',   'Formulaire reçu',    '#20c997', 50, 0),
    ('confirme',          'Confirmé',           '#28a745', 60, 0),
    ('annule',            'Annulé',             '#dc3545', 70, 1),
    ('no_show',           'No show',            '#343a40', 80, 1);

CREATE TABLE IF NOT EXISTS ref_statuts_session (
    code        TEXT PRIMARY KEY,
    libelle     TEXT NOT NULL,
    couleur_hex TEXT DEFAULT '#6c757d',
    ordre       INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO ref_statuts_session VALUES
    ('brouillon', 'Brouillon', '#6c757d', 10),
    ('soumis',    'Soumis',    '#17a2b8', 20),
    ('valide',    'Validé',    '#ffc107', 30),
    ('programme', 'Programmé', '#28a745', 40),
    ('annule',    'Annulé',    '#dc3545', 50),
    ('reporte',   'Reporté',   '#fd7e14', 60),
    ('termine',   'Terminé',   '#343a40', 70);

CREATE TABLE IF NOT EXISTS ref_types_presence (
    code    TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    ordre   INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO ref_types_presence VALUES
    ('we_complet',          'Week-end complet',       10),
    ('vendredi_samedi',     'Vendredi + Samedi',      20),
    ('samedi_dimanche',     'Samedi + Dimanche',      30),
    ('vendredi_seul',       'Vendredi seulement',     40),
    ('samedi_seul',         'Samedi seulement',       50),
    ('dimanche_seul',       'Dimanche seulement',     60),
    ('juste_interventions', 'Pour ses interventions', 70),
    ('en_ligne',            'En ligne uniquement',    80);

CREATE TABLE IF NOT EXISTS ref_tranches_age (
    code    TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    age_min INTEGER,
    age_max INTEGER,
    ordre   INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO ref_tranches_age VALUES
    ('bebe',   'Bébé (0-3 ans)',      0,   3,  10),
    ('enfant', 'Enfant (4-12 ans)',   4,  12,  20),
    ('ado',    'Adolescent (13-17)', 13,  17,  30),
    ('jeune',  '18-35 ans',         18,  35,  40),
    ('adulte', 'Adulte (36+)',       36, 999,  50),
    ('senior', 'Senior (65+)',       65, 999,  60);

CREATE TABLE IF NOT EXISTS ref_connectiques (
    code    TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    ordre   INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO ref_connectiques VALUES
    ('hdmi',        'HDMI',        10),
    ('vga',         'VGA',         20),
    ('usb_c',       'USB-C',       30),
    ('displayport', 'DisplayPort', 40),
    ('aucune',      'Aucune',      50);

CREATE TABLE IF NOT EXISTS utilisateurs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    email               TEXT NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,
    nom                 TEXT NOT NULL,
    prenom              TEXT NOT NULL,
    telephone           TEXT,
    actif               INTEGER DEFAULT 1,
    mfa_active          INTEGER DEFAULT 0,
    mfa_secret          TEXT,
    mfa_telephone       TEXT,
    token_reinit_mdp    TEXT,
    token_reinit_expiry TEXT,
    nb_echecs_connexion INTEGER DEFAULT 0,
    bloque_jusqu_a      TEXT,
    derniere_connexion_at TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS organisations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    ville       TEXT,
    pays        TEXT DEFAULT 'France',
    logo_path   TEXT,
    email_contact TEXT,
    site_web    TEXT,
    actif       INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lieux (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL,
    adresse     TEXT,
    code_postal TEXT,
    ville       TEXT,
    pays        TEXT DEFAULT 'France',
    capacite    INTEGER,
    type_code   TEXT REFERENCES ref_types_lieux(code),
    site_web    TEXT,
    note        TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS editions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    organisation_id     INTEGER NOT NULL REFERENCES organisations(id),
    nom                 TEXT NOT NULL,
    slug                TEXT NOT NULL UNIQUE,
    annee               INTEGER NOT NULL,
    lieu_id             INTEGER REFERENCES lieux(id),
    date_debut          TEXT,
    date_fin            TEXT,
    theme_principal     TEXT,
    focus_pays          TEXT,
    focus_theme         TEXT,
    statut_code         TEXT DEFAULT 'en_preparation',
    couleur_principale  TEXT DEFAULT '#1a5276',
    couleur_secondaire  TEXT DEFAULT '#e97132',
    logo_path           TEXT,
    ha_organisation_slug TEXT,
    capacite_max        INTEGER,
    nb_salles           INTEGER,
    livret_publie       INTEGER DEFAULT 0,
    livret_path         TEXT,
    notes_internes      TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS themes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id  INTEGER REFERENCES editions(id),
    code        TEXT NOT NULL,
    libelle     TEXT NOT NULL,
    couleur_hex TEXT DEFAULT '#1a5276',
    icone_path  TEXT,
    ordre       INTEGER DEFAULT 0,
    actif       INTEGER DEFAULT 1
);
INSERT OR IGNORE INTO themes (edition_id, code, libelle, couleur_hex, ordre) VALUES
    (NULL, 'torah',         'Torah',                   '#8B4513', 10),
    (NULL, 'culture',       'Culture',                 '#e97132', 20),
    (NULL, 'israel',        'Israël',                  '#0057b7', 30),
    (NULL, 'media_societe', 'Média-Société',           '#6c3483', 40),
    (NULL, 'histoire',      'Histoire',                '#1a5276', 50),
    (NULL, 'philo_psycho',  'Philosophie-Psychologie', '#117864', 60),
    (NULL, 'interreligieux','Interreligieux',          '#784212', 70),
    (NULL, 'techno_science','Technologie-Science',     '#1b4f72', 80);

CREATE TABLE IF NOT EXISTS salles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id      INTEGER NOT NULL REFERENCES editions(id),
    nom             TEXT NOT NULL,
    capacite        INTEGER,
    etage           TEXT,
    type_salle      TEXT,
    equipement_av   INTEGER DEFAULT 0,
    equipement_sono INTEGER DEFAULT 0,
    equipement_video INTEGER DEFAULT 0,
    surface_m2      INTEGER,
    note            TEXT,
    actif           INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS intervenants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    civilite_code   TEXT REFERENCES ref_civilites(code),
    nom             TEXT NOT NULL,
    prenom          TEXT NOT NULL,
    nom_affichage   TEXT,
    email_principal     TEXT,
    email_secondaire    TEXT,
    tel_fixe            TEXT,
    tel_mobile          TEXT,
    adresse             TEXT,
    code_postal         TEXT,
    ville               TEXT,
    pays                TEXT DEFAULT 'France',
    site_web            TEXT,
    facebook            TEXT,
    twitter             TEXT,
    instagram           TEXT,
    linkedin            TEXT,
    youtube             TEXT,
    podcast_url         TEXT,
    email_livret_choix  TEXT DEFAULT 'aucun',
    nom_diffuse         INTEGER DEFAULT 1,
    fonction_titre      TEXT,
    mini_bio            TEXT,
    specialites         TEXT,
    institutions        TEXT,
    oeuvres_publications TEXT,
    photo_path              TEXT,
    accord_photo            INTEGER DEFAULT 1,
    accord_photo_video_com  INTEGER DEFAULT 0,
    accord_podcast          INTEGER DEFAULT 0,
    notes_internes      TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    created_by          INTEGER REFERENCES utilisateurs(id)
);

CREATE TABLE IF NOT EXISTS participations_intervenants (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    intervenant_id      INTEGER NOT NULL REFERENCES intervenants(id),
    edition_id          INTEGER NOT NULL REFERENCES editions(id),
    statut_code         TEXT DEFAULT 'a_contacter',
    type_presence_code  TEXT,
    logement_fourni     INTEGER DEFAULT 0,
    type_logement       TEXT,
    heure_arrivee       TEXT,
    heure_depart        TEXT,
    remuneration        INTEGER DEFAULT 0,
    montant_remuneration REAL DEFAULT 0,
    transport_pris_en_charge INTEGER DEFAULT 0,
    referent_id         INTEGER REFERENCES utilisateurs(id),
    propose_par         TEXT,
    invite_officiel     INTEGER DEFAULT 0,
    contraintes         TEXT,
    commentaires_equipe TEXT,
    suivi_post_limoud   TEXT,
    livres_a_vendre     TEXT,
    dedicace            INTEGER DEFAULT 0,
    ha_inscrit          INTEGER DEFAULT 0,
    ha_verified_at      TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    created_by          INTEGER REFERENCES utilisateurs(id),
    UNIQUE(intervenant_id, edition_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id      INTEGER NOT NULL REFERENCES editions(id),
    titre           TEXT NOT NULL,
    description     TEXT,
    theme_id        INTEGER REFERENCES themes(id),
    format_code     TEXT REFERENCES ref_formats_session(code),
    langue_code     TEXT DEFAULT 'fr',
    niveau_code     TEXT DEFAULT 'tout_public',
    duree_minutes   INTEGER DEFAULT 60,
    est_focus           INTEGER DEFAULT 0,
    est_pays_honneur    INTEGER DEFAULT 0,
    est_18_35           INTEGER DEFAULT 0,
    est_famille         INTEGER DEFAULT 0,
    est_shabbat         INTEGER DEFAULT 0,
    materiel_salle          TEXT,
    materiel_intervenant    TEXT,
    connectique_demandee    TEXT,
    connectique_apportee    TEXT,
    besoin_micro            INTEGER DEFAULT 0,
    besoin_video            INTEGER DEFAULT 0,
    besoin_sono             INTEGER DEFAULT 0,
    besoin_tableau          INTEGER DEFAULT 0,
    statut_code     TEXT DEFAULT 'brouillon',
    session_source_id INTEGER REFERENCES sessions(id),
    commentaire_equipe TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    created_by      INTEGER REFERENCES utilisateurs(id)
);

CREATE TABLE IF NOT EXISTS session_intervenants (
    session_id      INTEGER NOT NULL REFERENCES sessions(id),
    intervenant_id  INTEGER NOT NULL REFERENCES intervenants(id),
    role_code       TEXT DEFAULT 'principal',
    ordre_affichage INTEGER DEFAULT 1,
    PRIMARY KEY (session_id, intervenant_id)
);

CREATE TABLE IF NOT EXISTS creneaux (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(id),
    edition_id      INTEGER NOT NULL REFERENCES editions(id),
    salle_id        INTEGER REFERENCES salles(id),
    jour            TEXT NOT NULL,
    heure_debut     TEXT NOT NULL,
    heure_fin       TEXT NOT NULL,
    statut_code     TEXT DEFAULT 'planifie',
    note            TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS types_formulaires_ha (
    code                    TEXT PRIMARY KEY,
    libelle                 TEXT NOT NULL,
    categorie               TEXT,
    type_badge_defaut_code  TEXT,
    actif                   INTEGER DEFAULT 1
);
INSERT OR IGNORE INTO types_formulaires_ha VALUES
    ('we_4_etoiles',  'WE complet hôtel 4 étoiles', 'participant',  'participant_we',  1),
    ('we_2_etoiles',  'WE complet hôtel 2 étoiles', 'participant',  'participant_we',  1),
    ('we_sans_nuit',  'WE sans hébergement',         'participant',  'participant_we',  1),
    ('dimanche_seul', 'Dimanche seulement',          'participant',  'participant_dim', 1),
    ('benevole',      'Bénévole',                    'benevole',     'benevole',        1),
    ('intervenant',   'Intervenant',                 'intervenant',  'intervenant',     1),
    ('enfant',        'Enfant',                      'participant',  'enfant',          1),
    ('navette_aller', 'Transport aller',             'transport',    NULL,              1),
    ('navette_retour','Transport retour',            'transport',    NULL,              1),
    ('navette_ar',    'Transport aller-retour',      'transport',    NULL,              1),
    ('don_seul',      'Don seul',                    'autre',        NULL,              1),
    ('autre',         'Autre formulaire',            'autre',        NULL,              1);

CREATE TABLE IF NOT EXISTS formulaires_ha (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id      INTEGER NOT NULL REFERENCES editions(id),
    ha_form_slug    TEXT NOT NULL,
    ha_form_id      TEXT,
    type_code       TEXT NOT NULL REFERENCES types_formulaires_ha(code),
    libelle_interne TEXT,
    actif           INTEGER DEFAULT 1,
    ordre_synchro   INTEGER DEFAULT 0,
    derniere_synchro_at TEXT,
    UNIQUE(edition_id, ha_form_slug)
);

CREATE TABLE IF NOT EXISTS participants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id      INTEGER NOT NULL REFERENCES editions(id),
    formulaire_ha_id INTEGER REFERENCES formulaires_ha(id),
    ha_reference_commande   TEXT,
    ha_item_id              TEXT UNIQUE,
    ha_date_commande        TEXT,
    ha_statut_commande      TEXT,
    payeur_nom              TEXT,
    payeur_prenom           TEXT,
    payeur_email            TEXT,
    nom                     TEXT,
    prenom                  TEXT,
    civilite                TEXT,
    email                   TEXT,
    telephone               TEXT,
    date_naissance          TEXT,
    lieu_naissance          TEXT,
    tranche_age_code        TEXT REFERENCES ref_tranches_age(code),
    adresse_fiscale         TEXT,
    code_postal             TEXT,
    ville                   TEXT,
    type_billet             TEXT,
    numero_billet           TEXT,
    tarif_libelle           TEXT,
    montant_tarif           REAL,
    code_promo              TEXT,
    montant_code_promo      REAL,
    moyen_paiement          TEXT,
    statut_paiement         TEXT DEFAULT 'valide',
    chomer_chabbat          INTEGER DEFAULT 0,
    partage_chambre         INTEGER DEFAULT 0,
    partage_chambre_avec    TEXT,
    type_couchage           TEXT,
    contrainte_alimentaire  TEXT,
    handicap                TEXT,
    transport_aller         INTEGER DEFAULT 0,
    montant_transport_aller REAL DEFAULT 0,
    transport_retour        INTEGER DEFAULT 0,
    montant_transport_retour REAL DEFAULT 0,
    nursery                 INTEGER DEFAULT 0,
    lit_bebe                INTEGER DEFAULT 0,
    nb_enfants_moins_13     INTEGER DEFAULT 0,
    enfants_dates_naissance TEXT,
    souhaite_intervenir     INTEGER DEFAULT 0,
    coordonnees_intervention TEXT,
    volontaire_we           INTEGER DEFAULT 0,
    intervenant_id          INTEGER REFERENCES intervenants(id),
    est_benevole            INTEGER DEFAULT 0,
    role_benevole           TEXT,
    ha_options_json         TEXT,
    ha_custom_fields_json   TEXT,
    ha_raw_json             TEXT,
    ha_synced_at            TEXT,
    note_equipe             TEXT,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS types_badges (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id              INTEGER NOT NULL REFERENCES editions(id),
    code                    TEXT NOT NULL,
    libelle_affiche         TEXT NOT NULL,
    couleur_fond_hex        TEXT DEFAULT '#1a5276',
    couleur_texte_hex       TEXT DEFAULT '#FFFFFF',
    couleur_bande_hex       TEXT,
    texte_ligne3            TEXT,
    texte_ligne3_auto       INTEGER DEFAULT 1,
    afficher_organisation   INTEGER DEFAULT 0,
    afficher_dates          INTEGER DEFAULT 1,
    actif                   INTEGER DEFAULT 1,
    ordre_affichage         INTEGER DEFAULT 0,
    UNIQUE(edition_id, code)
);

CREATE TABLE IF NOT EXISTS badges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id      INTEGER NOT NULL REFERENCES editions(id),
    participant_id  INTEGER REFERENCES participants(id),
    intervenant_id  INTEGER REFERENCES intervenants(id),
    nom             TEXT NOT NULL,
    prenom          TEXT NOT NULL,
    type_badge_id   INTEGER REFERENCES types_badges(id),
    texte_ligne3    TEXT,
    nb_impressions      INTEGER DEFAULT 0,
    derniere_impression_at TEXT,
    imprime_par_id      INTEGER REFERENCES utilisateurs(id),
    pdf_path            TEXT,
    est_ponctuel        INTEGER DEFAULT 0,
    motif_ponctuel      TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS roles (
    code        TEXT PRIMARY KEY,
    libelle     TEXT NOT NULL,
    description TEXT,
    couleur_hex TEXT DEFAULT '#6c757d',
    est_systeme INTEGER DEFAULT 0,
    ordre       INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO roles VALUES
    ('super_admin',          'Super Administrateur',    'Accès total',                    '#dc3545', 1,   0),
    ('admin_organisation',   'Admin organisation',      'Gère une organisation',          '#e97132', 1,  10),
    ('admin_edition',        'Admin édition',           'Gère une édition',               '#ffc107', 1,  20),
    ('resp_intervenants',    'Resp. intervenants',      'Gère les intervenants',          '#28a745', 1,  30),
    ('editeur_intervenants', 'Éditeur intervenants',    'Modifie bio et infos publiques', '#20c997', 1,  40),
    ('lecteur_intervenants', 'Lecteur intervenants',    'Consultation liste',             '#17a2b8', 1,  50),
    ('resp_sessions',        'Resp. sessions',          'Gère toutes les sessions',       '#6610f2', 1,  60),
    ('editeur_sessions',     'Éditeur sessions',        'Crée et modifie sessions',       '#6f42c1', 1,  70),
    ('relecteur_sessions',   'Relecteur sessions',      'Peut commenter',                 '#e83e8c', 1,  80),
    ('resp_livret',          'Resp. livret',            'Génère et valide le livret',     '#fd7e14', 1,  90),
    ('editeur_livret',       'Éditeur livret',          'Modifie le livret',              '#007bff', 1, 100),
    ('relecteur_livret',     'Relecteur livret',        'Relit et commente',              '#6c757d', 1, 110),
    ('resp_badges',          'Resp. badges',            'Configure et génère badges',     '#1a5276', 1, 120),
    ('operateur_badges',     'Opérateur badges',        'Imprime des badges',             '#2e86c1', 1, 130),
    ('resp_inscriptions',    'Resp. inscriptions',      'Voit toutes les données HA',     '#145a32', 1, 140),
    ('lecteur_inscriptions', 'Lecteur inscriptions',    'Voit la liste participants',     '#1e8449', 1, 150),
    ('resp_planning',        'Resp. planning',          'Gère le planning et salles',     '#7d6608', 1, 160),
    ('coordinateur_national','Coordinateur national',   'Accès lecture multi-orga',       '#4a235a', 1, 170),
    ('benevole_saisie',      'Bénévole saisie',         'Accès limité',                   '#566573', 1, 180),
    ('lecteur',              'Lecteur simple',           'Consultation uniquement',        '#aab7b8', 1, 190);

CREATE TABLE IF NOT EXISTS utilisateur_roles (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    utilisateur_id      INTEGER NOT NULL REFERENCES utilisateurs(id),
    role_code           TEXT NOT NULL REFERENCES roles(code),
    organisation_id     INTEGER REFERENCES organisations(id),
    edition_id          INTEGER REFERENCES editions(id),
    actif               INTEGER DEFAULT 1,
    attribue_par        INTEGER REFERENCES utilisateurs(id),
    attribue_le         TEXT DEFAULT (datetime('now')),
    expire_le           TEXT,
    UNIQUE(utilisateur_id, role_code, organisation_id, edition_id)
);

CREATE TABLE IF NOT EXISTS permissions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role_code   TEXT NOT NULL REFERENCES roles(code),
    module      TEXT NOT NULL,
    action      TEXT NOT NULL,
    champ       TEXT,
    autorise    INTEGER NOT NULL DEFAULT 0,
    UNIQUE(role_code, module, action, champ)
);

INSERT OR IGNORE INTO permissions (role_code, module, action, champ, autorise)
SELECT 'super_admin', m, a, NULL, 1 FROM (
    SELECT 'intervenants' m, 'voir_liste' a UNION ALL
    SELECT 'intervenants','voir_fiche'   UNION ALL
    SELECT 'intervenants','creer'        UNION ALL
    SELECT 'intervenants','modifier'     UNION ALL
    SELECT 'intervenants','supprimer'    UNION ALL
    SELECT 'intervenants','exporter'     UNION ALL
    SELECT 'intervenants','voir_historique' UNION ALL
    SELECT 'sessions','voir_liste'       UNION ALL
    SELECT 'sessions','voir_fiche'       UNION ALL
    SELECT 'sessions','creer'            UNION ALL
    SELECT 'sessions','modifier'         UNION ALL
    SELECT 'sessions','supprimer'        UNION ALL
    SELECT 'sessions','valider'          UNION ALL
    SELECT 'sessions','partager'         UNION ALL
    SELECT 'badges','voir_liste'         UNION ALL
    SELECT 'badges','creer'              UNION ALL
    SELECT 'badges','imprimer'           UNION ALL
    SELECT 'badges','configurer'         UNION ALL
    SELECT 'participants','voir_liste'   UNION ALL
    SELECT 'participants','voir_fiche'   UNION ALL
    SELECT 'participants','exporter'     UNION ALL
    SELECT 'helloasso','synchroniser'    UNION ALL
    SELECT 'helloasso','voir_liste'      UNION ALL
    SELECT 'admin','voir_liste'          UNION ALL
    SELECT 'admin','configurer'          UNION ALL
    SELECT 'planning','voir_liste'       UNION ALL
    SELECT 'planning','modifier'         UNION ALL
    SELECT 'livret','voir_liste'         UNION ALL
    SELECT 'livret','modifier'           UNION ALL
    SELECT 'livret','valider'            UNION ALL
    SELECT 'livret','imprimer'
);

INSERT OR IGNORE INTO permissions (role_code, module, action, champ, autorise) VALUES
    ('lecteur_intervenants','intervenants','voir_liste',NULL,1),
    ('lecteur_intervenants','intervenants','voir_fiche',NULL,1),
    ('lecteur_intervenants','intervenants','voir_fiche','email_principal',0),
    ('lecteur_intervenants','intervenants','voir_fiche','email_secondaire',0),
    ('lecteur_intervenants','intervenants','voir_fiche','tel_fixe',0),
    ('lecteur_intervenants','intervenants','voir_fiche','tel_mobile',0),
    ('lecteur_intervenants','intervenants','voir_fiche','adresse',0),
    ('lecteur_intervenants','intervenants','voir_fiche','notes_internes',0),
    ('lecteur_intervenants','intervenants','voir_fiche','commentaires_equipe',0),
    ('lecteur_intervenants','intervenants','voir_fiche','remuneration',0),
    ('lecteur_intervenants','intervenants','voir_fiche','montant_remuneration',0);

CREATE TABLE IF NOT EXISTS livret_sections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id      INTEGER NOT NULL REFERENCES editions(id),
    code            TEXT NOT NULL,
    titre_section   TEXT NOT NULL,
    ordre_livret    INTEGER DEFAULT 0,
    type_gabarit    TEXT DEFAULT 'texte_libre',
    titre_page      TEXT,
    contenu_html    TEXT,
    image_path      TEXT,
    image_position  TEXT DEFAULT 'gauche',
    statut          TEXT DEFAULT 'brouillon',
    source_auto     TEXT,
    inclure_dans_livret INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    updated_by      INTEGER REFERENCES utilisateurs(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    utilisateur_id      INTEGER REFERENCES utilisateurs(id),
    organisation_id     INTEGER REFERENCES organisations(id),
    edition_id          INTEGER REFERENCES editions(id),
    action              TEXT NOT NULL,
    entite              TEXT,
    entite_id           INTEGER,
    champ_modifie       TEXT,
    ancienne_valeur     TEXT,
    nouvelle_valeur     TEXT,
    ip_address          TEXT,
    user_agent          TEXT,
    detail              TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_editions_organisation   ON editions(organisation_id);
CREATE INDEX IF NOT EXISTS idx_editions_annee          ON editions(annee);
CREATE INDEX IF NOT EXISTS idx_participations_interv   ON participations_intervenants(intervenant_id);
CREATE INDEX IF NOT EXISTS idx_participations_edition  ON participations_intervenants(edition_id);
CREATE INDEX IF NOT EXISTS idx_sessions_edition        ON sessions(edition_id);
CREATE INDEX IF NOT EXISTS idx_sessions_statut         ON sessions(statut_code);
CREATE INDEX IF NOT EXISTS idx_creneaux_session        ON creneaux(session_id);
CREATE INDEX IF NOT EXISTS idx_creneaux_edition_jour   ON creneaux(edition_id, jour);
CREATE INDEX IF NOT EXISTS idx_participants_edition    ON participants(edition_id);
CREATE INDEX IF NOT EXISTS idx_participants_email      ON participants(email);
CREATE INDEX IF NOT EXISTS idx_participants_ha_item    ON participants(ha_item_id);
CREATE INDEX IF NOT EXISTS idx_badges_edition          ON badges(edition_id);
CREATE INDEX IF NOT EXISTS idx_utilisateur_roles_user  ON utilisateur_roles(utilisateur_id);
CREATE INDEX IF NOT EXISTS idx_permissions_role        ON permissions(role_code, module);
CREATE INDEX IF NOT EXISTS idx_audit_log_entite        ON audit_log(entite, entite_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_utilisateur   ON audit_log(utilisateur_id);
CREATE INDEX IF NOT EXISTS idx_intervenants_nom        ON intervenants(nom, prenom);
