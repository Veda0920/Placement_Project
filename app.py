from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_socketio import SocketIO, emit
from mysql.connector import Error
from db_connection import get_db_connection
from datetime import datetime
created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

connection = get_db_connection()

app = Flask(__name__)

socketio = SocketIO(app)
app.secret_key=""

@app.route("/")
def home():
    return render_template("register.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        print("POST request received")
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        
        print(f"Received: {username}, {password}, {email}")

        if not username or not password or not email:
            flash('All fields are required!', 'error')
            return redirect(url_for('register'))

        # Database interaction
        connection = get_db_connection()
        if connection and connection.is_connected():
            try:
                cursor = connection.cursor()
                query = """
                INSERT INTO user (UserName, Password, Email)
                VALUES (%s, %s, %s)
                """
                cursor.execute(query, (username, password, email))
                connection.commit()
                print("Data inserted successfully")
                flash('Registration successful!', 'success')
                return redirect(url_for('login'))  # Redirect to login page
            except Error as e:
                print(f"Database error: {e}")
                flash(f'Error: {e}', 'error')
            finally:
                if cursor:
                    cursor.close()
                connection.close()
        else:
            flash('Database connection failed!', 'error')

    return render_template('register.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Check if fields are empty
        if not username or not password:
            flash("Username and Password are required!", "error")
            return redirect(url_for("login"))

        # Database connection and authentication
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM user WHERE UserName = %s AND Password = %s"
                cursor.execute(query, (username, password))
                user = cursor.fetchone()  # Fetch the user details
                if user and user["UserName"] == "Admin":
                    session["username"] = user["UserName"]
                    session["password"] = user["Password"]
                    return redirect(url_for("admin_dashboard"))  # Redirect to admin dashboard
                if user:
                    session["username"] = user["UserName"]
                    session["password"] = user["Password"]
                    return redirect(url_for("dashboard"))  # Redirect to dashboard
                else:
                    flash("Invalid username or password!", "error")
            except Error as e:
                flash(f"Database error: {e}", "error")
            finally:
                cursor.close()
                connection.close()
        else:
            flash("Database connection failed!", "error")

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    # Check if the user is logged in
    if "username" in session:
        return render_template("dashboard.html")
    else:
        flash("You must be logged in to access this page!", "error")
        return redirect(url_for("login"))
    
@app.route('/profile', methods=["GET", "POST"])
def profile():
    if "username" not in session:
        return redirect(url_for('login'))
    
    # Handle form submission
    if request.method == "POST":
        bio = request.form.get('bio', '')  # Default to empty string if missing
        skills = request.form.get('skills', '')
        linkedin = request.form.get('linkedin', '')
        github = request.form.get('github', '')
        portfolio = request.form.get('portfolio', None)  # Default to None
        
        # Get the username from the session
        username = session['username']
        
        # Database interaction
        connection = get_db_connection()
        if connection and connection.is_connected():
            try:
                cursor = connection.cursor()
                
                # Insert profile data into the database with username
                query = """
                INSERT INTO profile (UserName, bio, skills, linkedin, github, portfolio)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    bio = VALUES(bio),
                    skills = VALUES(skills),
                    linkedin = VALUES(linkedin),
                    github = VALUES(github),
                    portfolio = VALUES(portfolio)
                """
                cursor.execute(query, (username, bio, skills, linkedin, github, portfolio))
                connection.commit()
                flash('Profile updated successfully!', 'success')
            except Error as e:
                flash(f'Database error: {e}', 'error')
            finally:
                if cursor:
                    cursor.close()
                connection.close()
        else:
            flash('Database connection failed!', 'error')
        
        return redirect(url_for('profile'))  # Redirect to the profile page
    
    # If GET request, return the profile page (you can pass data to pre-fill form)
    return render_template("profile.html")

@app.route('/view_profile', methods=["GET"])
def view_profile():
    if "username" not in session:
        return redirect(url_for('login'))

    # Fetch user's profile from the database using username
    connection = get_db_connection()
    profile_data = None
    
    if connection and connection.is_connected():
        try:
            cursor = connection.cursor(dictionary=True)  # Use dictionary cursor to fetch data as dict
            username = session['username']
            
            # Fetch profile data based on username
            query_profile = "SELECT * FROM profile WHERE UserName = %s"
            cursor.execute(query_profile, (username,))
            profile_data = cursor.fetchone()
                
        except Error as e:
            flash(f'Database error: {e}', 'error')
        finally:
            if cursor:
                cursor.close()
            connection.close()
    else:
        flash('Database connection failed!', 'error')

    # Render the view_profile.html template with profile data
    return render_template("view_profile.html", profile=profile_data)

@app.route('/placements')
def placements():
    try:
        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch all placement drives
        query = "SELECT * FROM placement_drives ORDER BY date ASC"
        cursor.execute(query)
        drives = cursor.fetchall()
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        drives = []
    finally:
        cursor.close()
        conn.close()

    return render_template('placements.html', drives=drives)   

@app.route('/apply/<int:drive_id>', methods=['GET','POST'])
def apply(drive_id):
    if "username" not in session:
        return redirect(url_for('login'))

    user_name = session.get('username')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Ensure drive_id is valid
        cursor.execute("SELECT id FROM placement_drives WHERE id = %s", (drive_id,))
        drive = cursor.fetchone()

        if not drive:
            flash("Invalid placement drive!", "danger")
            return redirect(url_for('placements'))

        # Check if the user has already applied for the same drive_id
        cursor.execute("SELECT * FROM applications WHERE UserName = %s AND drive_id = %s", (user_name, drive_id))
        existing_application = cursor.fetchone()

        if existing_application:
            flash("You have already applied for this drive!", "warning")
            return redirect(url_for('dashboard'))
        else:
            # Insert new application record
            cursor.execute(
                "INSERT INTO applications (UserName, drive_id) VALUES (%s, %s)",
                (user_name, drive_id)
            )
            flash(f"You have successfully applied to Drive ID: {drive_id}!", "success")

        conn.commit()

    except Error as e:
        flash(f"Database error: {e}", "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('placements'))

@app.route('/applications')
def applications():
    if "username" not in session:
        return redirect(url_for('login'))

    user_name = session.get('username')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch all applications for the user
        query = """
        SELECT p.id, p.company_name, p.date, p.location, p.description, p.requirements
        FROM placement_drives p
        JOIN applications a ON p.id = a.drive_id
        WHERE a.UserName = %s
        ORDER BY p.date ASC
        """
        cursor.execute(query, (user_name,))
        applications = cursor.fetchall()
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        applications = []
    finally:
        cursor.close()
        conn.close()

    return render_template('applications.html', applications=applications)

# Notifications Route
@app.route('/notifications')
def notifications():
    if "username" not in session:
        return redirect(url_for('login'))
    user_name = session.get('username')

    try:
        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch unread notifications for the user
        query = """
        SELECT * FROM notifications
        WHERE UserName = %s AND is_read = FALSE
        ORDER BY created_at DESC
        """
        cursor.execute(query, (user_name,))
        notifications = cursor.fetchall()

        # Mark notifications as read
        cursor.execute("UPDATE notifications SET is_read = TRUE WHERE UserName = %s", (user_name,))
        conn.commit()
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        notifications = []
    finally:
        cursor.close()
        conn.close()

    return render_template('notifications.html', notifications=notifications)

# Logout Route
@app.route("/logout")
def logout():
    session.clear()  # Clear the session
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))  # Redirect to the login page


@app.route("/admin_dashboard")
def admin_dashboard():
    # Check if the user is logged in and is an admin
    if "username" in session and session.get("username") == "Admin":
        return render_template("admin_dashboard.html")
    else:
        flash("You must be logged in as an admin to access this page!", "error")
        return redirect(url_for("login"))

@app.route('/create_drive', methods=['GET', 'POST'])
def create_drive():
    if request.method == 'POST':
        # Retrieve form data
        company_name = request.form.get('company').strip()
        date = request.form.get('date').strip()
        location = request.form.get('location').strip()
        description = request.form.get('description').strip()
        JobRole= request.form.get('JobRole').strip()
        requirements = request.form.get('requirements').strip() or None  # Optional field

        try:
            # Connect to the database
            conn = get_db_connection() 
            cursor = conn.cursor(dictionary=True)  # Ensures results are dictionaries

            # Insert data into the placement_drives table
            query = """
            INSERT INTO placement_drives (company_name, date, location, description,JobRole, requirements)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (company_name, date, location, description, JobRole,requirements))
            drive_id = cursor.lastrowid  # Fetch the last inserted drive ID
            conn.commit()

            flash('Placement drive created successfully!', 'success')

            # Fetch all users (ensure UserName is selected)
            cursor.execute("SELECT UserName FROM user")
            users = cursor.fetchall()

            # Insert notifications for all users
            notification_message = f"A new placement drive by {company_name} (ID: {drive_id}) has been created!"
            socketio.emit('new_notification', {'message': notification_message})
            for user in users:
                user_name = user['UserName']  # Ensure UserName is fetched correctly
                cursor.execute(
                    "INSERT INTO notifications (UserName, message) VALUES (%s, %s)",
                    (user_name, notification_message)
                )

            conn.commit()  # Commit notification inserts

        except Error as e:
            flash(f'Database error: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('create_drive'))

    # Fetch all placement drives from the database
    try:
        conn = get_db_connection() 
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM placement_drives ORDER BY date DESC"
        cursor.execute(query)
        drives_list = cursor.fetchall()
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        drives_list = []
    finally:
        cursor.close()
        conn.close()

    return render_template('create_drive.html', drives_list=drives_list)

@app.route('/view_applications')
def view_applications():
    # Check if the user is logged in and is an admin
    if "username" not in session or session.get("username") != "Admin":
        flash("You must be logged in as an admin to access this page!", "error")
        return redirect(url_for("login"))
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch only username, company name, and date
        query = """
        SELECT u.UserName, p.company_name, p.date
        FROM applications a, user u, placement_drives p
        WHERE a.UserName = u.UserName AND a.drive_id = p.id
        ORDER BY p.date ASC
        """
        cursor.execute(query)
        applications = cursor.fetchall()
    except Error as e:
        flash(f'Database error: {e}', 'danger')
        applications = []
    finally:
        cursor.close()
        conn.close()

    return render_template('view_applications.html', applications=applications)

if __name__ == "__main__":
    app.run(debug=True)