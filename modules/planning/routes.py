from flask import Blueprint, render_template
from flask_login import login_required, current_user
from flask import flash, redirect, url_for

bp = Blueprint("planning", __name__, template_folder="templates")


@bp.route('/')
@login_required
def index():
    if not current_user.a_permission('planning', 'voir_liste'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('planning/index.html')
