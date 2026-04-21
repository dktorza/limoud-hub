-- Migration 005 : permissions par défaut pour tous les rôles système
-- Utilise INSERT OR IGNORE : idempotent, ne crase pas les surcharges manuelles.

-- ─────────────────────────────────────────────
-- admin_organisation : tout sauf gestion rôles système
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('admin_organisation','admin','voir_liste',NULL,1),
  ('admin_organisation','admin','creer',NULL,1),
  ('admin_organisation','admin','modifier',NULL,1),
  ('admin_organisation','intervenants','voir_liste',NULL,1),
  ('admin_organisation','intervenants','voir_fiche',NULL,1),
  ('admin_organisation','intervenants','creer',NULL,1),
  ('admin_organisation','intervenants','modifier',NULL,1),
  ('admin_organisation','intervenants','supprimer',NULL,1),
  ('admin_organisation','intervenants','exporter',NULL,1),
  ('admin_organisation','intervenants','voir_contacts',NULL,1),
  ('admin_organisation','sessions','voir_liste',NULL,1),
  ('admin_organisation','sessions','voir_fiche',NULL,1),
  ('admin_organisation','sessions','creer',NULL,1),
  ('admin_organisation','sessions','modifier',NULL,1),
  ('admin_organisation','sessions','supprimer',NULL,1),
  ('admin_organisation','sessions','exporter',NULL,1),
  ('admin_organisation','planning','voir_liste',NULL,1),
  ('admin_organisation','planning','modifier',NULL,1),
  ('admin_organisation','participants','voir_liste',NULL,1),
  ('admin_organisation','participants','voir_fiche',NULL,1),
  ('admin_organisation','participants','creer',NULL,1),
  ('admin_organisation','participants','modifier',NULL,1),
  ('admin_organisation','participants','supprimer',NULL,1),
  ('admin_organisation','participants','exporter',NULL,1),
  ('admin_organisation','helloasso','voir_liste',NULL,1),
  ('admin_organisation','helloasso','modifier',NULL,1),
  ('admin_organisation','badges','voir_liste',NULL,1),
  ('admin_organisation','badges','imprimer',NULL,1),
  ('admin_organisation','badges','modifier',NULL,1),
  ('admin_organisation','livret','voir_liste',NULL,1),
  ('admin_organisation','livret','modifier',NULL,1),
  ('admin_organisation','livret','exporter',NULL,1);

-- ─────────────────────────────────────────────
-- admin_edition : accès complet à son édition, pas l'admin global
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('admin_edition','intervenants','voir_liste',NULL,1),
  ('admin_edition','intervenants','voir_fiche',NULL,1),
  ('admin_edition','intervenants','creer',NULL,1),
  ('admin_edition','intervenants','modifier',NULL,1),
  ('admin_edition','intervenants','supprimer',NULL,1),
  ('admin_edition','intervenants','exporter',NULL,1),
  ('admin_edition','intervenants','voir_contacts',NULL,1),
  ('admin_edition','sessions','voir_liste',NULL,1),
  ('admin_edition','sessions','voir_fiche',NULL,1),
  ('admin_edition','sessions','creer',NULL,1),
  ('admin_edition','sessions','modifier',NULL,1),
  ('admin_edition','sessions','supprimer',NULL,1),
  ('admin_edition','sessions','exporter',NULL,1),
  ('admin_edition','planning','voir_liste',NULL,1),
  ('admin_edition','planning','modifier',NULL,1),
  ('admin_edition','participants','voir_liste',NULL,1),
  ('admin_edition','participants','voir_fiche',NULL,1),
  ('admin_edition','participants','creer',NULL,1),
  ('admin_edition','participants','modifier',NULL,1),
  ('admin_edition','participants','exporter',NULL,1),
  ('admin_edition','helloasso','voir_liste',NULL,1),
  ('admin_edition','badges','voir_liste',NULL,1),
  ('admin_edition','badges','imprimer',NULL,1),
  ('admin_edition','livret','voir_liste',NULL,1),
  ('admin_edition','livret','modifier',NULL,1),
  ('admin_edition','livret','exporter',NULL,1);

-- ─────────────────────────────────────────────
-- resp_intervenants
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('resp_intervenants','intervenants','voir_liste',NULL,1),
  ('resp_intervenants','intervenants','voir_fiche',NULL,1),
  ('resp_intervenants','intervenants','creer',NULL,1),
  ('resp_intervenants','intervenants','modifier',NULL,1),
  ('resp_intervenants','intervenants','exporter',NULL,1),
  ('resp_intervenants','intervenants','voir_contacts',NULL,1),
  ('resp_intervenants','sessions','voir_liste',NULL,1),
  ('resp_intervenants','sessions','voir_fiche',NULL,1);

-- ─────────────────────────────────────────────
-- editeur_intervenants : sans contacts sensibles ni notes
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('editeur_intervenants','intervenants','voir_liste',NULL,1),
  ('editeur_intervenants','intervenants','voir_fiche',NULL,1),
  ('editeur_intervenants','intervenants','modifier',NULL,1),
  ('editeur_intervenants','intervenants','voir_fiche','notes_internes',0),
  ('editeur_intervenants','intervenants','voir_fiche','commentaires_equipe',0),
  ('editeur_intervenants','intervenants','voir_fiche','remuneration',0),
  ('editeur_intervenants','sessions','voir_liste',NULL,1);

-- ─────────────────────────────────────────────
-- lecteur_intervenants : lecture seule, sans champs sensibles
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('lecteur_intervenants','intervenants','voir_liste',NULL,1),
  ('lecteur_intervenants','intervenants','voir_fiche',NULL,1),
  ('lecteur_intervenants','intervenants','voir_fiche','email_principal',0),
  ('lecteur_intervenants','intervenants','voir_fiche','email_secondaire',0),
  ('lecteur_intervenants','intervenants','voir_fiche','tel_mobile',0),
  ('lecteur_intervenants','intervenants','voir_fiche','tel_fixe',0),
  ('lecteur_intervenants','intervenants','voir_fiche','adresse',0),
  ('lecteur_intervenants','intervenants','voir_fiche','notes_internes',0),
  ('lecteur_intervenants','intervenants','voir_fiche','commentaires_equipe',0),
  ('lecteur_intervenants','intervenants','voir_fiche','remuneration',0);

-- ─────────────────────────────────────────────
-- resp_sessions
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('resp_sessions','sessions','voir_liste',NULL,1),
  ('resp_sessions','sessions','voir_fiche',NULL,1),
  ('resp_sessions','sessions','creer',NULL,1),
  ('resp_sessions','sessions','modifier',NULL,1),
  ('resp_sessions','sessions','supprimer',NULL,1),
  ('resp_sessions','sessions','exporter',NULL,1),
  ('resp_sessions','planning','voir_liste',NULL,1),
  ('resp_sessions','planning','modifier',NULL,1),
  ('resp_sessions','intervenants','voir_liste',NULL,1);

-- ─────────────────────────────────────────────
-- editeur_sessions
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('editeur_sessions','sessions','voir_liste',NULL,1),
  ('editeur_sessions','sessions','voir_fiche',NULL,1),
  ('editeur_sessions','sessions','creer',NULL,1),
  ('editeur_sessions','sessions','modifier',NULL,1);

-- ─────────────────────────────────────────────
-- relecteur_sessions
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('relecteur_sessions','sessions','voir_liste',NULL,1),
  ('relecteur_sessions','sessions','voir_fiche',NULL,1);

-- ─────────────────────────────────────────────
-- resp_livret
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('resp_livret','livret','voir_liste',NULL,1),
  ('resp_livret','livret','modifier',NULL,1),
  ('resp_livret','livret','exporter',NULL,1),
  ('resp_livret','sessions','voir_liste',NULL,1),
  ('resp_livret','sessions','voir_fiche',NULL,1),
  ('resp_livret','intervenants','voir_liste',NULL,1),
  ('resp_livret','intervenants','voir_fiche',NULL,1);

-- ─────────────────────────────────────────────
-- editeur_livret
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('editeur_livret','livret','voir_liste',NULL,1),
  ('editeur_livret','livret','modifier',NULL,1);

-- ─────────────────────────────────────────────
-- resp_badges
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('resp_badges','badges','voir_liste',NULL,1),
  ('resp_badges','badges','imprimer',NULL,1),
  ('resp_badges','badges','modifier',NULL,1),
  ('resp_badges','badges','creer',NULL,1),
  ('resp_badges','participants','voir_liste',NULL,1);

-- ─────────────────────────────────────────────
-- operateur_badges
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('operateur_badges','badges','voir_liste',NULL,1),
  ('operateur_badges','badges','imprimer',NULL,1);

-- ─────────────────────────────────────────────
-- resp_inscriptions
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('resp_inscriptions','participants','voir_liste',NULL,1),
  ('resp_inscriptions','participants','voir_fiche',NULL,1),
  ('resp_inscriptions','participants','creer',NULL,1),
  ('resp_inscriptions','participants','modifier',NULL,1),
  ('resp_inscriptions','participants','supprimer',NULL,1),
  ('resp_inscriptions','participants','exporter',NULL,1),
  ('resp_inscriptions','helloasso','voir_liste',NULL,1),
  ('resp_inscriptions','helloasso','modifier',NULL,1),
  ('resp_inscriptions','intervenants','voir_liste',NULL,1);

-- ─────────────────────────────────────────────
-- lecteur_inscriptions
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('lecteur_inscriptions','participants','voir_liste',NULL,1);

-- ─────────────────────────────────────────────
-- resp_planning
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('resp_planning','planning','voir_liste',NULL,1),
  ('resp_planning','planning','modifier',NULL,1),
  ('resp_planning','sessions','voir_liste',NULL,1),
  ('resp_planning','sessions','voir_fiche',NULL,1),
  ('resp_planning','sessions','modifier',NULL,1);

-- ─────────────────────────────────────────────
-- coordinateur_national : lecture sur tout
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('coordinateur_national','intervenants','voir_liste',NULL,1),
  ('coordinateur_national','intervenants','voir_fiche',NULL,1),
  ('coordinateur_national','sessions','voir_liste',NULL,1),
  ('coordinateur_national','sessions','voir_fiche',NULL,1),
  ('coordinateur_national','participants','voir_liste',NULL,1),
  ('coordinateur_national','planning','voir_liste',NULL,1),
  ('coordinateur_national','livret','voir_liste',NULL,1),
  ('coordinateur_national','badges','voir_liste',NULL,1);

-- ─────────────────────────────────────────────
-- benevole_saisie
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('benevole_saisie','intervenants','voir_liste',NULL,1),
  ('benevole_saisie','intervenants','voir_fiche',NULL,1),
  ('benevole_saisie','sessions','voir_liste',NULL,1),
  ('benevole_saisie','sessions','voir_fiche',NULL,1);

-- ─────────────────────────────────────────────
-- lecteur
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO permissions (role_code,module,action,champ,autorise) VALUES
  ('lecteur','intervenants','voir_liste',NULL,1),
  ('lecteur','sessions','voir_liste',NULL,1);
