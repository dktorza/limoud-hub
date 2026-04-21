-- Migration 003 : durées de sessions configurables par édition
CREATE TABLE IF NOT EXISTS ref_durees_session (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_id  INTEGER NOT NULL REFERENCES editions(id),
    duree_min   INTEGER NOT NULL,
    libelle     TEXT NOT NULL,
    ordre       INTEGER DEFAULT 0,
    actif       INTEGER DEFAULT 1,
    UNIQUE(edition_id, duree_min)
);