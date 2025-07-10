from app.extensions import db
from datetime import datetime

class SearchKeywordAnalytics(db.Document):
    keyword = db.StringField(required=True, unique=True)
    count = db.IntField(default=1)
    last_searched = db.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'search_keyword_analytics',
        'indexes': [
            '-count',
            '-last_searched'
        ]
    }