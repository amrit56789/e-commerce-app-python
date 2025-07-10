from app import db
from constants import ALL_ROLES

class Role(db.Document):
    name = db.StringField(required=True, unique=True)

    @staticmethod
    def initialize_roles():
        for role_name in ALL_ROLES:
            if not Role.objects(name=role_name):
                Role(name=role_name).save()