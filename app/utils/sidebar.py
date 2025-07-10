import json
import os
from flask import url_for

def load_sidebar_menu(app):
    sidebar_path = os.path.join(app.root_path, 'sidebar_menu.json')
    with open(sidebar_path, 'r') as f:
        return json.load(f)

def process_sidebar_menu(menu):
    for section in menu["mainMenu"]:
        for item in section["items"]:
            if "endpoint" in item:
                item["url"] = url_for(item["endpoint"])
            if "submenu" in item:
                for subitem in item["submenu"]:
                    if "endpoint" in subitem:
                        subitem["url"] = url_for(subitem["endpoint"])
    return menu

def sidebar_context(app):
    @app.context_processor
    def inject_sidebar():
        menu = load_sidebar_menu(app)
        processed_menu = process_sidebar_menu(menu)
        return {'sidebar_menu': processed_menu}
