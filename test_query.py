import os
import sys

os.environ['FLASK_ENV'] = 'development'

from app import app, db
from models.faculty import Faculty

with app.app_context():
    try:
        # Check if table exists
        print("Testing Faculty query...")
        faculty_count = db.session.query(Faculty).count()
        print(f"✓ Total faculty in database: {faculty_count}")
        
        # Try the query from home route
        faculty_members = Faculty.query.filter_by(
            is_principal=False,
            is_active=True
        ).all()
        print(f"✓ Active non-principal faculty: {len(faculty_members)}")
        
        if faculty_members:
            for f in faculty_members[:5]:
                print(f"  - {f.name} ({f.designation})")
        else:
            print("  No faculty members found")
            
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
