-- Migration 004 : marqueur de changement de mot de passe obligatoire
ALTER TABLE utilisateurs ADD COLUMN doit_changer_mdp INTEGER DEFAULT 0;
