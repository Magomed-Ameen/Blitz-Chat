from flask import Flask, render_template, request, redirect, url_for, flash
app= Flask(__name__)
app.secret_key = 'secret_key'

users_dict ={}
@app.route('/')

def home():
  return redirect(url_for('log_in'))

@app.route('/create_profile', methods=['GET','POST'])
def create_profile():
  if request.method == "POST":
    full_name=request.form['full_name']
    username=request.form['username']
    password=request.form['password']
    if username in users_dict:
      flash('Usernamr exists,CHOOSE ANOTHER ONE')
      return redirect(url_for("signup"))
    users_dict[username]={"full_name": full_name, "password": password}
    flash("Profile IS CREATED")
    return redirect(url_for("chat_window",username=username))

  return render_template("create_profile.html")


@app.route('/log_in',methods=['GET','POST'])
def log_in():
  if request.method=='POST':
    username=request.form['username']
    password=request.form['password']
    user=users_dict.get(username)
    if user and user['password']==password:
      flash('LOGGED IN')
      return redirect(url_for("chat_window",username=username))
    else:
      flash('Invalid Combination of credentials')
      return redirect(url_for('log_in'))
  return render_template('log_in.html')

@app.route('/chat_window/<username>')
def chat_window(username):
  return render_template('chat_window.html',username=username)
  

if __name__=='__main__':
  app.run(host='0.0.0.0', port=5000, debug=True)


    




  
  
  



  