from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash, send_file, abort, current_app
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import shutil
from flask_migrate import Migrate
import time

# Set up paths and configurations
UPLOAD_FOLDER = 'uploads'  # This should be a valid folder path where files and folders are uploaded
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///files.db'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Use the correct folder path
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'webp', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar', 'docx', 'mp3', 'wav', 'flac', 'aac', 'ogg', 'mp4', 'avi', 'mov', 'wmv', 'mkv', 'csv', 'xlsx', 'xls', 'ppt', 'pptx', 'psd', 'ai', 'js', 'css', 'db', 'sql'}
app.config['MAX_CONTENT_LENGTH'] = 50000 * 1024 * 1024

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define File and Folder models
class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100))
    filetype = db.Column(db.String(50))
    uploader = db.Column(db.String(50))

class Folder(db.Model):
    __tablename__ = 'folder'

    id = db.Column(db.Integer, primary_key=True)  # Ensure this field is defined
    folder_name = db.Column(db.String(100), nullable=False)
    uploader = db.Column(db.String(100), nullable=False)
    path = db.Column(db.String(200), nullable=False)

    def __init__(self, folder_name, uploader, path):
        self.folder_name = folder_name
        self.uploader = uploader
        self.path = path

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
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        session['username'] = username
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    files = File.query.all()
    folders = Folder.query.all()  # Fetch folders from the database
    return render_template('dashboard.html', files=files, folders=folders)

@app.route('/upload')
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('upload.html')

@app.route('/upload_file', methods=['POST','GET'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('upload'))

    file = request.files['file']

    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('upload'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        new_file = File(
            filename=filename,
            filetype=file.content_type,
            uploader=session.get('username', 'Unknown')
        )
        db.session.add(new_file)
        db.session.commit()

        flash('File uploaded successfully', 'success')
        return redirect(url_for('dashboard'))

    flash('File type not allowed', 'error')
    return redirect(url_for('upload'))

@app.route('/delete_file/<int:file_id>', methods=['POST', 'GET'])
def delete_file(file_id):
    file = File.query.get(file_id)
    if file and file.uploader == session['username']:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(file)
        db.session.commit()
        flash('File deleted successfully!', 'success')
    else:
        flash('File not found or unauthorized access', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/download_file/<int:file_id>')
def download_file(file_id):
    # Fetch file from the database
    file = File.query.get_or_404(file_id)

    # Get the directory from the app config
    directory = app.config['UPLOAD_FOLDER']
    
    # Ensure the file exists in the directory
    file_path = os.path.join(directory, file.filename)
    if not os.path.exists(file_path):
        return "File not found", 404

    # Return the file from the directory
    return send_from_directory(directory, file.filename, as_attachment=True)

@app.route('/upload_folder', methods=['POST'])
def upload_folder():
    # Automatically generate a folder name using the current timestamp and uploader's username
    uploader = session['username']
    timestamp = str(int(time.time()))
    folder_name = f"{uploader}_{timestamp}"

    # Set the base path where folders will be stored
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], uploader)
    folder_path = os.path.join(base_path, folder_name)

    # Create the directory if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Create a new folder record in the database
    new_folder = Folder(
        folder_name=folder_name,
        uploader=uploader,
        path=folder_path
    )

    # Add the folder record to the database
    db.session.add(new_folder)
    db.session.commit()

    flash('Folder uploaded successfully!', 'success')
    return redirect(url_for('dashboard'))
@app.route('/open_folder/<int:folder_id>')
def open_folder(folder_id):
    folder = Folder.query.get(folder_id)
    if folder:
        files = os.listdir(folder.path)  # Get files from the folder's path
        return render_template('folder_contents.html', folder=folder, folder_id=folder.id, files=files)
    else:
        flash('Folder not found!', 'danger')
        return redirect(url_for('index'))

from flask import after_this_request

@app.route('/download_folder/<int:folder_id>')
def download_folder(folder_id):
    # Retrieve the folder from the database
    folder = Folder.query.get(folder_id)
    if not folder:
        flash('Folder not found!', 'danger')
        return redirect(url_for('view_folders'))
    
    # Check if the folder path exists and is valid
    folder_path = folder.path
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        flash('Folder does not exist on the server!', 'danger')
        return redirect(url_for('view_folders'))
    
    # Create a zip file in the temporary directory
    zip_filename = f"{folder.folder_name}.zip"
    zip_filepath = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)
    shutil.make_archive(zip_filepath.replace('.zip', ''), 'zip', folder_path)

    # Use `after_this_request` to clean up the zip file after the response
    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(zip_filepath):
                os.remove(zip_filepath)
        except Exception as e:
            print(f"Error cleaning up zip file: {e}")
        return response

    # Serve the zip file for download
    try:
        return send_file(zip_filepath, as_attachment=True)
    except Exception as e:
        flash(f"Error while sending the file: {str(e)}", 'danger')
        return redirect(url_for('index'))


@app.route('/delete_folder/<int:folder_id>', methods=['POST','GET'])
def delete_folder(folder_id):
    folder = Folder.query.get(folder_id)
    if folder:
        db.session.delete(folder)
        db.session.commit()
        flash('Folder deleted successfully!', 'success')
    else:
        flash('Folder not found!', 'danger')
    return redirect(url_for('index'))

@app.route('/folders')
def view_folders():
    folders = Folder.query.all()
    return render_template('view_folders.html', folders=folders)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about_us.html')

if __name__ == '__main__':
    app.run(debug=True)
