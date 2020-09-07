from flask import Flask, redirect, render_template


def get_model():
    from . import model_firestore
    model = model_firestore
    return model

app = Flask(__name__)

# Setup the data model.
with app.app_context():
    model = get_model()
    model.init_app(app)


app.config.update(
    TESTING=True,
    SECRET_KEY=b'_5#y2L"F4Q8z\n\xec]/'
)

app.config['UPLOAD_FOLDER'] = '/path/to/upload'

# Register the Bookshelf CRUD blueprint.
from .crud import crud
app.register_blueprint(crud)

# Add a default root route.
@app.route("/")
def index():
    return redirect('/logon')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
