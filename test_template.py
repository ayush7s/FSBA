from app import app, db
from models.faculty import Faculty

with app.app_context():
    # Test the home route
    try:
        notices = []
        announcements = []
        faculty_members = Faculty.query.filter_by(is_principal=False, is_active=True).all()
        print(f"Faculty members loaded: {len(faculty_members)}")
        
        # Try to render the template
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('index.html')
        
        # Try to render
        html = template.render(
            notices=notices,
            announcements=announcements,
            faculty_members=faculty_members
        )
        print(f"✓ Template rendered successfully! Length: {len(html)}")
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
