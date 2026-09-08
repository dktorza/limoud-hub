-- Migration 008 : dédoublonnage des thèmes.
-- La migration 001 insère les 8 thèmes par défaut à chaque démarrage (INSERT OR IGNORE)
-- sans contrainte d'unicité : la table gonflait de 8 lignes par redémarrage.

-- 1) Rattacher les sessions au premier exemplaire de chaque thème
UPDATE sessions SET theme_id = (
    SELECT MIN(t2.id) FROM themes t1 JOIN themes t2
        ON t1.code = t2.code AND IFNULL(t1.edition_id, 0) = IFNULL(t2.edition_id, 0)
    WHERE t1.id = sessions.theme_id
) WHERE theme_id IS NOT NULL;

-- 2) Conserver le sp_item_id éventuellement posé sur un doublon
UPDATE themes SET sp_item_id = (
    SELECT MAX(t2.sp_item_id) FROM themes t2
    WHERE t2.code = themes.code AND IFNULL(t2.edition_id, 0) = IFNULL(themes.edition_id, 0)
) WHERE sp_item_id IS NULL;

-- 3) Supprimer les doublons
DELETE FROM themes WHERE id NOT IN (
    SELECT MIN(id) FROM themes GROUP BY code, IFNULL(edition_id, 0)
);

-- 4) Empêcher la récidive : INSERT OR IGNORE devient réellement "ignore"
CREATE UNIQUE INDEX IF NOT EXISTS ux_themes_code_edition ON themes(code, IFNULL(edition_id, 0));
