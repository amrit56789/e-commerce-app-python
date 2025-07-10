from flask import render_template
from . import admin_api

@admin_api.route('/settings')
def settings():
    return render_template('admin/settings.html')
