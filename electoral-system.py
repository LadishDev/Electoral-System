from flask import Flask, render_template, request
import mysql.connector
import os

app = Flask(__name__, static_url_path='/static')

electoraldb = mysql.connector.connect(user=os.environ.get('DB_USER'), password=os.environ.get('DB_PASS'),
                              host='localhost', database='electoralsystem',
                              auth_plugin='mysql_native_password')


@app.route('/', methods=['GET', 'POST'])
def index():
    if "viewdata" in request.form:
        return render_template('viewdata.html')
    else:
        return render_template('errorpage.html')

@app.route('/viewdata', methods=['GET', 'POST'])
def viewdata():
    if "viewalldata" in request.form:
        return render_template('test.html')
    elif "back" in request.form:
        return render_template('index.html')
    else:
        return render_template('errorpage.html')

@app.route('/errorpage', methods=['GET', 'POST'])
def errorpage():
    if "back" in request.form:
        return render_template('index.html')
    else:
        return render_template('errorpage.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    #app.run()