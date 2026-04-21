from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint("livret", __name__, template_folder="templates")


@bp.route('/')
@login_required
def index():
    if not current_user.a_permission('livret', 'voir_liste'):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('livret/index.html')
