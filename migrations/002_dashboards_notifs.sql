PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS dashboard_widgets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,
    titre       TEXT NOT NULL,
    description TEXT,
    template    TEXT NOT NULL,
    data_fn     TEXT NOT NULL,
    icone       TEXT DEFAULT '?',
    actif       INTEGER DEFAULT 1
);

INSERT OR IGNORE INTO dashboard_widgets (code, titre, description, template, data_fn, icone) VALUES
    ('transport_liste',        'Transports',                'Participants ayant demandé un transport',     'widgets/transport_liste.html',        'widgets.transport_liste',        'bus'),
    ('enfants_inscrits',       'Enfants inscrits',          'Liste des enfants par tranche âge',          'widgets/enfants_inscrits.html',       'widgets.enfants_inscrits',       'enfant'),
    ('chomer_chabbat',         'Chomer Chabbat',            'Participants observants pour placement',      'widgets/chomer_chabbat.html',         'widgets.chomer_chabbat',         'etoile'),
    ('contraintes_alimentaires','Contraintes alimentaires', 'Résumé pour le traiteur',                    'widgets/contraintes_alimentaires.html','widgets.contraintes_alimentaires','assiette'),
    ('intervenants_a_confirmer','Intervenants à confirmer', 'Intervenants dont le statut nécessite action','widgets/intervenants_a_confirmer.html','widgets.intervenants_a_confirmer','micro'),
    ('sessions_non_planifiees','Sessions non planifiées',   'Sessions validées sans créneau assigné',     'widgets/sessions_non_planifiees.html', 'widgets.sessions_non_planifiees','calendrier'),
    ('badges_a_imprimer',      'Badges à imprimer',         'Participants sans badge généré',             'widgets/badges_a_imprimer.html',      'widgets.badges_a_imprimer',      'badge'),
    ('arrivees_du_jour',       'Arrivées du jour',          'Participants attendus aujourd hui',          'widgets/arrivees_du_jour.html',       'widgets.arrivees_du_jour',       'hotel'),
    ('scan_accueil_recent',    'Activité accueil',          'Derniers scans de badges en temps réel',     'widgets/scan_accueil_recent.html',    'widgets.scan_accueil_recent',    'scan'),
    ('intervenants_presents',  'Intervenants présents',     'Intervenants scannés à l accueil',          'widgets/intervenants_presents.html',  'widgets.intervenants_presents',  'check'),
    ('inscriptions_helloasso', 'Inscriptions HelloAsso',    'Compteur inscriptions en temps réel',        'widgets/inscriptions_helloasso.html', 'widgets.inscriptions_helloasso', 'stats'),
    ('livret_avancement',      'Avancement du livret',      'Etat des sections du livret',                'widgets/livret_avancement.html',      'widgets.livret_avancement',      'livre'),
    ('nursery_bebes',          'Nursery / Bébés',           'Familles avec bébé et besoins nursery',      'widgets/nursery_bebes.html',          'widgets.nursery_bebes',          'bebe');

CREATE TABLE IF NOT EXISTS dashboard_roles_widgets (
    role_code   TEXT NOT NULL REFERENCES roles(code),
    widget_code TEXT NOT NULL REFERENCES dashboard_widgets(code),
    ordre       INTEGER DEFAULT 0,
    taille      TEXT DEFAULT 'moitie',
    actif       INTEGER DEFAULT 1,
    PRIMARY KEY (role_code, widget_code)
);

INSERT OR IGNORE INTO dashboard_roles_widgets (role_code, widget_code, ordre, taille) VALUES
    ('resp_inscriptions',    'transport_liste',           10, 'plein'),
    ('resp_inscriptions',    'inscriptions_helloasso',    20, 'moitie'),
    ('resp_inscriptions',    'arrivees_du_jour',          30, 'moitie'),
    ('resp_badges',          'scan_accueil_recent',       10, 'plein'),
    ('resp_badges',          'badges_a_imprimer',         20, 'moitie'),
    ('operateur_badges',     'scan_accueil_recent',       10, 'plein'),
    ('operateur_badges',     'badges_a_imprimer',         20, 'moitie'),
    ('resp_intervenants',    'intervenants_a_confirmer',  10, 'plein'),
    ('resp_intervenants',    'intervenants_presents',     20, 'moitie'),
    ('resp_intervenants',    'sessions_non_planifiees',   30, 'moitie'),
    ('resp_sessions',        'sessions_non_planifiees',   10, 'plein'),
    ('resp_sessions',        'intervenants_a_confirmer',  20, 'moitie'),
    ('resp_planning',        'sessions_non_planifiees',   10, 'plein'),
    ('resp_livret',          'livret_avancement',         10, 'plein'),
    ('editeur_livret',       'livret_avancement',         10, 'plein'),
    ('admin_edition',        'inscriptions_helloasso',    10, 'moitie'),
    ('admin_edition',        'intervenants_a_confirmer',  20, 'moitie'),
    ('admin_edition',        'sessions_non_planifiees',   30, 'moitie'),
    ('admin_edition',        'badges_a_imprimer',         40, 'moitie'),
    ('admin_edition',        'livret_avancement',         50, 'moitie'),
    ('admin_edition',        'transport_liste',           60, 'plein'),
    ('lecteur_inscriptions', 'inscriptions_helloasso',    10, 'plein');

CREATE TABLE IF NOT EXISTS notifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id      INTEGER REFERENCES editions(id),
    utilisateur_id  INTEGER REFERENCES utilisateurs(id),
    role_cible      TEXT REFERENCES roles(code),
    type_notif      TEXT NOT NULL,
    titre           TEXT NOT NULL,
    message         TEXT,
    lien            TEXT,
    icone           TEXT DEFAULT 'bell',
    priorite        TEXT DEFAULT 'normale',
    entite          TEXT,
    entite_id       INTEGER,
    lue             INTEGER DEFAULT 0,
    lue_at          TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    created_by      INTEGER REFERENCES utilisateurs(id)
);

CREATE INDEX IF NOT EXISTS idx_notifs_user
    ON notifications(utilisateur_id, lue, created_at);
CREATE INDEX IF NOT EXISTS idx_notifs_role
    ON notifications(role_cible, lue, created_at);

CREATE TABLE IF NOT EXISTS scans_accueil (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id      INTEGER NOT NULL REFERENCES editions(id),
    badge_id        INTEGER REFERENCES badges(id),
    participant_id  INTEGER REFERENCES participants(id),
    intervenant_id  INTEGER REFERENCES intervenants(id),
    nom_scanne      TEXT,
    prenom_scanne   TEXT,
    type_badge      TEXT,
    point_scan      TEXT DEFAULT 'accueil_principal',
    operateur_id    INTEGER REFERENCES utilisateurs(id),
    statut_scan     TEXT DEFAULT 'valide',
    notifs_envoyees INTEGER DEFAULT 0,
    scan_at         TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_scans_edition
    ON scans_accueil(edition_id, scan_at);
CREATE INDEX IF NOT EXISTS idx_scans_intervenant
    ON scans_accueil(intervenant_id, scan_at);

CREATE TABLE IF NOT EXISTS ref_types_envoi (
    code    TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    canal   TEXT NOT NULL
);
INSERT OR IGNORE INTO ref_types_envoi VALUES
    ('convocation_intervenant', 'Convocation intervenant',    'email'),
    ('lien_formulaire',         'Lien formulaire session',    'email'),
    ('info_transport',          'Information transport',      'les_deux'),
    ('rappel_badge',            'Rappel port du badge',       'sms'),
    ('alerte_planning',         'Alerte changement planning', 'les_deux'),
    ('message_libre',           'Message libre',              'les_deux'),
    ('notification_arrivee',    'Notification arrivee',       'sms'),
    ('recap_session',           'Récapitulatif session',      'email');

CREATE TABLE IF NOT EXISTS envois (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id      INTEGER REFERENCES editions(id),
    type_code       TEXT REFERENCES ref_types_envoi(code),
    canal           TEXT NOT NULL,
    utilisateur_id  INTEGER REFERENCES utilisateurs(id),
    participant_id  INTEGER REFERENCES participants(id),
    intervenant_id  INTEGER REFERENCES intervenants(id),
    adresse         TEXT NOT NULL,
    sujet           TEXT,
    corps           TEXT NOT NULL,
    corps_html      TEXT,
    statut          TEXT DEFAULT 'en_attente',
    envoye_at       TEXT,
    erreur          TEXT,
    envoye_par      INTEGER REFERENCES utilisateurs(id),
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_envois_edition
    ON envois(edition_id, statut, created_at);
CREATE INDEX IF NOT EXISTS idx_envois_intervenant
    ON envois(intervenant_id, created_at);

CREATE TABLE IF NOT EXISTS templates_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id  INTEGER REFERENCES editions(id),
    type_code   TEXT REFERENCES ref_types_envoi(code),
    canal       TEXT NOT NULL,
    langue_code TEXT DEFAULT 'fr',
    nom         TEXT NOT NULL,
    sujet       TEXT,
    corps       TEXT NOT NULL,
    corps_html  TEXT,
    actif       INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tokens_formulaire_intervenant (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    intervenant_id  INTEGER NOT NULL REFERENCES intervenants(id),
    edition_id      INTEGER NOT NULL REFERENCES editions(id),
    token           TEXT NOT NULL UNIQUE,
    expire_at       TEXT NOT NULL,
    utilise         INTEGER DEFAULT 0,
    utilise_at      TEXT,
    created_by      INTEGER REFERENCES utilisateurs(id),
    created_at      TEXT DEFAULT (datetime('now'))
);
