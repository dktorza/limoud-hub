-- Migration 004 : marqueur de changement de mot de passe obligatoire
-- SQLite ne supporte pas "ADD COLUMN IF NOT EXISTS".
-- database.py entoure chaque migration d'un try/except : si la colonne existe déjà
-- l'erreur "duplicate column name" est attrapée et loggée (⚠), pas fatale.
ALTER TABLE utilisateurs ADD COLUMN doit_changer_mdp INTEGER DEFAULT 0;
