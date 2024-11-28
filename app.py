from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from flask_migrate import Migrate



app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///files.db'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar', 'docx', 'mp3', 'wav', 'flac', 'aac', 'ogg', 'mp4', 'avi', 'mov', 'wmv', 'mkv', 'csv', 'xlsx', 'xls', 'ppt', 'pptx', 'psd', 'ai', 'js', 'css', 'db', 'sql'}

db = SQLAlchemy(app)
# Initialize Flask-Migrate
migrate = Migrate(app, db)
# Database model for uploaded files
class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(150), nullable=False)
    filetype = db.Column(db.String(50), nullable=False)
    filepath = db.Column(db.String(150), nullable=False)
    uploader = db.Column(db.String(100), nullable=False)

# Initialize the database only if it's not initialized yet
with app.app_context():
    db.create_all()

# Allowed file extensions check
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Add your registration logic here (e.g., store in DB)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Add login logic here (e.g., verify credentials)
        session['username'] = username
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    files = File.query.all()
    return render_template('dashboard.html', files=files)
@app.route('/upload')
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    files = File.query.all()
    return render_template('upload.html')

@app.route('/upload', methods=['POST','GET'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Ensure the upload folder exists
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        file.save(filepath)
        
        new_file = File(filename=filename, filetype=file.content_type, filepath=filepath, uploader=session['username'])
        db.session.add(new_file)
        db.session.commit()
        return redirect(url_for('upload'))
        

@app.route('/delete/<int:file_id>', methods=['GET','POST'])
def delete_file(file_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    file = File.query.get_or_404(file_id)
    if file.uploader == session['username']:
        os.remove(file.filepath)  # Remove file from the server
        db.session.delete(file)   # Remove file from the database
        db.session.commit()
    
    return redirect(url_for('dashboard'))

@app.route('/download/<int:file_id>', methods=['GET'])
def download_file(file_id):
    file = File.query.get_or_404(file_id)
    return send_from_directory(app.config['UPLOAD_FOLDER'], file.filename)
@app.route('/logout')
def logout():
    # Remove the username from the session
    session.pop('username', None)
    return redirect(url_for('index'))  # Redirect to the home page or any other page
@app.route('/about')
def about():
    return render_template('about_us.html')

if __name__ == '__main__':
    app.run(debug=True)
