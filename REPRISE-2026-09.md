# Reprise du développement - septembre 2026

Corrections du 08/09/2026 :
1. .vscode/sftp.json retiré du dépôt (mot de passe SFTP en clair) ; modèle sftp.json.example ajouté.
2. .gitignore créé (.env, __pycache__, bases SQLite, data/, zips).
3. modules/sharepoint/client.py réécrit sur Microsoft Graph v1.0 (interface inchangée).
   A tester sur /sharepoint/test, puis ajuster LIST_MAPPINGS avec les noms internes des colonnes.
4. WeasyPrint retiré de requirements.txt (non utilisé).
5. README passé en 0.2.0.
