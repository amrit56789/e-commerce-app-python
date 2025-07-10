from flask import render_template, redirect, url_for, g
from . import admin_api
from constants import DASHBOARD_WEB_URL

@admin_api.route(DASHBOARD_WEB_URL)
def dashboard():
    if g.current_user is None:
        return redirect(url_for('admin_api.login_page'))
    return render_template("admin/dashboardPage/dashboard.html", users=g.current_user)
