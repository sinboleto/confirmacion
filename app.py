from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'  # Replace 'data.db' with your desired database name
db = SQLAlchemy(app)


# Create a model for your data
class Information(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(50))

    def __init__(self, name, email):
        self.name = name
        self.email = email


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']

        # Create a new Information object and save it to the database
        new_info = Information(name, email)
        db.session.add(new_info)
        db.session.commit()

    # Fetch all the stored information from the database
    infos = Information.query.all()

    return render_template('index.html', infos=infos)

if __name__ == '__main__':
    app.run(debug=True)
