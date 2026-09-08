-- Migration 007 : synchronisation SharePoint (Graph)
-- 1) Nouvelles valeurs de référence (idempotentes, exécutées à chaque démarrage)
-- 2) Colonnes sp_item_id pour rendre l'import rejouable sans doublons
--    (ALTER TABLE échoue si la colonne existe : normal après la première exécution,
--     database.py journalise un simple avertissement)

INSERT OR IGNORE INTO ref_formats_session VALUES
    ('table_ronde', 'Table ronde', 60, 'bulle', 1);

INSERT OR IGNORE INTO ref_statuts_session VALUES
    ('en_discussion', 'En discussion',    '#ffc107', 25),
    ('paye',          'Payée',            '#20c997', 42),
    ('paye_cerfa',    'Payée avec Cerfa', '#20c997', 44),
    ('invite',        'Invité',           '#17a2b8', 46);

ALTER TABLE intervenants ADD COLUMN sp_item_id INTEGER;
ALTER TABLE sessions ADD COLUMN sp_item_id INTEGER;
ALTER TABLE sessions ADD COLUMN dispo_vendredi INTEGER DEFAULT 1;
ALTER TABLE sessions ADD COLUMN dispo_samedi INTEGER DEFAULT 1;
ALTER TABLE sessions ADD COLUMN dispo_dimanche INTEGER DEFAULT 1;
ALTER TABLE sessions ADD COLUMN creneau_souhaite TEXT;
ALTER TABLE sessions ADD COLUMN referent_id INTEGER REFERENCES utilisateurs(id);
ALTER TABLE sessions ADD COLUMN referent_nom TEXT;
ALTER TABLE salles ADD COLUMN sp_item_id INTEGER;
ALTER TABLE themes ADD COLUMN sp_item_id INTEGER;
ALTER TABLE themes ADD COLUMN couleur_texte_hex TEXT DEFAULT '#ffffff';
ALTER TABLE plages_horaires ADD COLUMN sp_item_id INTEGER;
ALTER TABLE plages_horaires ADD COLUMN heure_fin TEXT;
ALTER TABLE plages_horaires ADD COLUMN couleur_hex TEXT;
ALTER TABLE creneaux ADD COLUMN plage_id INTEGER REFERENCES plages_horaires(id);

CREATE INDEX IF NOT EXISTS idx_intervenants_sp ON intervenants(sp_item_id);
CREATE INDEX IF NOT EXISTS idx_sessions_sp ON sessions(edition_id, sp_item_id);
CREATE INDEX IF NOT EXISTS idx_salles_sp ON salles(edition_id, sp_item_id);
CREATE INDEX IF NOT EXISTS idx_plages_sp ON plages_horaires(edition_id, sp_item_id);
