-- Migration 006 : plages horaires par édition (créneaux ouverts/fermés)
-- Les plages remplacent la liste CRENEAUX_HORAIRES codée en dur dans planning/routes.py.
-- Si la table est vide pour une édition, le planning repasse sur la liste par défaut.

CREATE TABLE IF NOT EXISTS plages_horaires (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id  INTEGER NOT NULL REFERENCES editions(id),
    jour        TEXT NOT NULL,        -- Vendredi | Samedi | Dimanche
    heure_debut TEXT NOT NULL,        -- HH:MM
    ouvert      INTEGER DEFAULT 1,    -- 1 = ouvert, 0 = fermé (pause repas, etc.)
    note        TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(edition_id, jour, heure_debut)
);

CREATE INDEX IF NOT EXISTS idx_plages_edition_jour
    ON plages_horaires(edition_id, jour);
