"""Start the development server: python run.py  ->  http://localhost:5000/api/health"""

from app import create_app

if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
