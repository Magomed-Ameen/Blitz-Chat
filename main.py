import time
import os
import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("firebase_config.json")
firebase_admin.initialize_app(
    cred, {
        "databaseURL":
        "https://blitzchat-30890-default-rtdb.europe-west1.firebasedatabase.app"
      
    })

from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps

# Firebase config for frontend
FIREBASE_CONFIG = {
    'apiKey': os.environ.get('FIREBASE_API_KEY', 'AIzaSyCgY0qvuCml114ujVhzUyfz2eZ4L0k4LKo'),
    'authDomain': os.environ.get('FIREBASE_AUTH_DOMAIN', 'blitzchat-30890.firebaseapp.com'),
    'databaseURL': os.environ.get('FIREBASE_DATABASE_URL', 'https://blitzchat-30890-default-rtdb.europe-west1.firebasedatabase.app'),
    'projectId': os.environ.get('FIREBASE_PROJECT_ID', 'blitzchat-30890'),
    'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', 'blitzchat-30890.appspot.com')
}

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here-change-this')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('log_in'))
        return f(*args, **kwargs)
    return decorated_function

def check_user_access(requested_username):
    """Check if the logged-in user can access the requested username's data"""
    if 'username' not in session:
        return False
    return session['username'] == requested_username

users_dict = {}


@app.route('/')
def home():
  return redirect(url_for('log_in'))


@app.route('/create_profile', methods=['GET', 'POST'])
def create_profile():
  if request.method == "POST":
    full_name = request.form['full_name']
    username = request.form['username']
    password = request.form['password']
    # Check if user already exists in Firebase
    user_ref = db.reference(f"users/{username}")
    if user_ref.get() is not None:
      flash('Username already exists. Choose another one.')
      return redirect(url_for("create_profile"))

    # Save user to Firebase
    user_ref.set({
        "full_name": full_name,
        "password": password,  # You can hash this later
        "contacts": {},
        "invites_sent": {},
        "invites_received": {}
    })

    session['username'] = username  # Create user session
    flash("Profile created successfully.")
    return redirect(url_for("chat_window", username=username))

  return render_template("create_profile.html")


@app.route('/log_in', methods=['GET', 'POST'])
def log_in():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    user_ref = db.reference(f"users/{username}")
    user = user_ref.get()

    if user and user['password'] == password:
      session['username'] = username  # Create user session
      flash('LOGGED IN')
      return redirect(url_for("chat_window", username=username))
    else:
      flash('Invalid Combination of credentials')
      return redirect(url_for('log_in'))
  return render_template('log_in.html')


@app.route('/send_invite',methods=['POST'])
@login_required
def send_invite():
  sender=request.form['sender']
  recipient=request.form['recipient']
  users_ref=db.reference('users')
  recipient_ref=users_ref.child(recipient)

  if not recipient_ref.get():
    return "Recipient not found",404
  users_ref.child(sender).child('invites_sent').update({recipient: True})
  recipient_ref.child('invites_received').update({sender: True})

  return "Invite Sent",200



@app.route('/accept_invite',methods=['POST'])
@login_required
def accept_invite():
  user = request.form['user']
  sender = request.form['sender']  # the one who sent the invite

  users_ref = db.reference('users')
  # Add to contacts
  users_ref.child(user).child('contacts').update({sender: True})
  users_ref.child(sender).child('contacts').update({user: True})

  # Remove invite
  users_ref.child(user).child('invites_received').child(sender).delete()
  users_ref.child(sender).child('invites_sent').child(user).delete()

  flash(f"You are now connected with {sender}!")
  return redirect(url_for('chat_window', username=user))






@app.route('/chat_window/<username>')
@login_required
def chat_window(username):
  # Check if the logged-in user is trying to access their own chat window
  if not check_user_access(username):
    flash('Access denied. Please log in with the correct account.')
    return redirect(url_for('log_in'))
  user_ref = db.reference(f'users/{username}')
  user_data = user_ref.get()

  if not user_data:
      flash('User data not found.')
      return redirect(url_for('log_in'))

  # Build full contact info
  contacts_usernames = user_data.get('contacts', {})
  contacts = {}

  for contact_username in contacts_usernames:
      contact_ref = db.reference(f'users/{contact_username}')
      contact_data = contact_ref.get()
      if contact_data:
          contacts[contact_username] = contact_data.get('full_name', contact_username)

  invites_received = user_data.get('invites_received', {})
  invites_sent = user_data.get('invites_sent', {})

  return render_template(
      'chat_window.html',
      username=username,
      contacts=contacts,
      invites_received=invites_received,
      invites_sent=invites_sent,
      firebase_config=FIREBASE_CONFIG
  )

@app.route('/chat/<username>/<contact>', methods=['GET', 'POST'])
@login_required
def chat(username, contact):
    # Check if the logged-in user is trying to access their own chat
    if not check_user_access(username):
        flash('Access denied. Please log in with the correct account.')
        return redirect(url_for('log_in'))
    
    # Check if the contact is actually in the user's contact list
    user_ref = db.reference(f'users/{username}')
    user_data = user_ref.get()
    if not user_data or contact not in user_data.get('contacts', {}):
        flash('You can only chat with your contacts.')
        return redirect(url_for('chat_window', username=username))
    chat_id = "_".join(sorted([username, contact]))
    chat_ref = db.reference(f'messages/{chat_id}')

    if request.method == 'POST':
        message_text = request.form['message']
        new_msg = {
            'sender': username,
            'text': message_text,
            'timestamp': {'.sv': 'timestamp'}


        }
        chat_ref.push(new_msg)
        return redirect(url_for('chat', username=username, contact=contact))

    # Get messages
    messages = chat_ref.get() or {}

    return render_template('chat.html', username=username, contact=contact, messages=messages, firebase_config=FIREBASE_CONFIG)
  


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.')
    return redirect(url_for('log_in'))

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000, debug=True)
