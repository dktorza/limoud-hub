import sys, os
sys.path.insert(0, '/home/qpyq4619/intranet.limoud.org')
os.chdir('/home/qpyq4619/intranet.limoud.org')

from app import create_app
from werkzeug.security import generate_password_hash
from database import get_db

EMAIL    = "denis.ktorza@limoud.org"
MOT_DE_PASSE = "Asher16051933!"
NOM      = "Ktorza"
PRENOM   = "Denis"

app = create_app('production')
with app.app_context():
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO organisations (nom, slug, ville) VALUES (?, ?, ?)",
        ('Limoud Paris', 'limoud-paris', 'Paris')
    )
    db.execute(
        "INSERT INTO utilisateurs (email, password_hash, nom, prenom, actif) VALUES (?, ?, ?, ?, 1)",
        (EMAIL, generate_password_hash(MOT_DE_PASSE), NOM, PRENOM)
    )
    user = db.execute(
        "SELECT id FROM utilisateurs WHERE email = ?", (EMAIL,)
    ).fetchone()
    db.execute(
        "INSERT INTO utilisateur_roles (utilisateur_id, role_code, actif) VALUES (?, 'super_admin', 1)",
        (user['id'],)
    )
    db.commit()
    print("Compte cree ! ID:", user['id'])
