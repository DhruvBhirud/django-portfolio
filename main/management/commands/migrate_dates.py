from django.core.management.base import BaseCommand
from main.db import get_db
from main.admin_views import parse_fuzzy_date

class Command(BaseCommand):
    help = 'Migrate string dates in education and experience collections to datetime objects for sorting.'

    def handle(self, *args, **options):
        db = get_db()
        
        # Migrate Education
        self.stdout.write("Migrating Education...")
        for edu in db.education.find():
            updates = {}
            start_date_str = edu.get('start_date', '')
            end_date_str = edu.get('end_date', '')
            
            if start_date_str:
                updates['start_date_dt'] = parse_fuzzy_date(start_date_str)
            if end_date_str:
                updates['end_date_dt'] = parse_fuzzy_date(end_date_str)
                
            if updates:
                db.education.update_one({'_id': edu['_id']}, {'$set': updates})
                
        # Migrate Experience
        self.stdout.write("Migrating Experience...")
        for exp in db.experience.find():
            updates = {}
            start_date_str = exp.get('start_date', '')
            end_date_str = exp.get('end_date', '')
            
            if start_date_str:
                updates['start_date_dt'] = parse_fuzzy_date(start_date_str)
            if end_date_str:
                updates['end_date_dt'] = parse_fuzzy_date(end_date_str)
                
            if updates:
                db.experience.update_one({'_id': exp['_id']}, {'$set': updates})
                
        self.stdout.write(self.style.SUCCESS("Successfully migrated dates!"))
