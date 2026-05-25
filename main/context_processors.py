from .db import get_db

def pending_endorsements_count(request):
    if hasattr(request, 'session') and request.session.get('admin_logged_in'):
        try:
            db = get_db()
            count = 0
            for skill in db.skills.find():
                for endorser in skill.get('endorsers', []):
                    if endorser.get('approved', True) is False:
                        count += 1
            return {'pending_endorsements_count': count}
        except Exception:
            return {'pending_endorsements_count': 0}
    return {'pending_endorsements_count': 0}
