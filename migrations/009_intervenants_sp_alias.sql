-- Migration 009 : table de correspondance id SharePoint -> intervenant.
-- Plusieurs items SharePoint (doublons) peuvent pointer vers la même fiche ;
-- les lookups des sessions doivent tous être résolus.
CREATE TABLE IF NOT EXISTS intervenants_sp_alias (
    sp_item_id     INTEGER PRIMARY KEY,
    intervenant_id INTEGER NOT NULL REFERENCES intervenants(id),
    fusionne       INTEGER DEFAULT 0   -- 1 = cet item SP a été fusionné avec une fiche existante
);
