from flask import Flask, render_template, request
import mysql.connector
import os

app = Flask(__name__, static_url_path='/static')

electoraldb = mysql.connector.connect(user=os.environ.get('DB_USER'), password=os.environ.get('DB_PASS'),
                              host='localhost', database='electoralsystem',
                              auth_plugin='mysql_native_password')




@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    if "viewdata" in request.form:
        return render_template('view_data.html')
    else:
        return render_template('errorpage.html')


@app.route('/viewdata', methods=['GET', 'POST'])
def viewdata():
    if "viewalldata" in request.form:
        return render_template('view_all_data.html', data=view_all_data())
    elif "test" in request.form:
        return render_template('fptp_seats_data.html', data=calculate_fptp_seats())
    elif "back" in request.form:
        return render_template('index.html')
    else:
        return render_template('errorpage.html')
    
@app.route('/viewalldata', methods=['GET', 'POST'])
def viewalldata():
    if "back" in request.form:
        return render_template('view_data.html')
    else:
        return render_template('errorpage.html')
    
@app.route('/fptpdata', methods=['GET', 'POST'])
def fptpdata():
    if "back" in request.form:
        return render_template('view_data.html')
    else:
        return render_template('errorpage.html')


@app.route('/errorpage', methods=['GET', 'POST'])
def errorpage():
    if "back" in request.form:
        return render_template('index.html')
    else:
        return render_template('errorpage.html')


def view_all_data():
    cur = electoraldb.cursor()
    cur.execute('SELECT c1.firstname, c1.surname, c1.gender, p1.partyName, co1.constituencyName, co1.constituencyType, co2.countyName, r1.regionName, co3.countryName, co1.sittingmp, e1.votes FROM candidate c1 JOIN party p1 ON c1.partyID = p1.partyID JOIN constituency co1 ON c1.constituencyID = co1.constituencyID JOIN county co2 ON co1.countyID = co2.countyID JOIN region r1 ON co1.regionID = r1.regionID JOIN country co3 ON co1.countryID = co3.countryID LEFT JOIN electionresults e1 ON co1.constituencyID = e1.constituencyID AND c1.partyID = e1.partyID;')
    data = cur.fetchall()
    return data


def calculate_fptp_seats():
    cur = electoraldb.cursor()

    # SQL query to get winning party in each constituency and count their seats
    # Labor and Labour Co-oprative are the same party and should be combined into one to have correct seat count
    cur.execute('''
                SELECT
                    CASE WHEN partyName IN ('Labour', 'Labour and Co-operative') THEN 'Labour' ELSE partyName END AS combinedParty,
                    COUNT(*) AS seat_count
                FROM (
                    SELECT e.constituencyID, p.partyName
                    FROM electionresults e
                    JOIN party p ON e.partyID = p.partyID
                    JOIN (
                        SELECT constituencyID, MAX(votes) AS winning_votes
                        FROM electionresults
                        GROUP BY constituencyID
                    ) AS w ON e.constituencyID = w.constituencyID AND e.votes = w.winning_votes
                ) AS winning_parties
                GROUP BY combinedParty
                ORDER BY seat_count DESC;
    ''')

    # Fetch the results
    fptp_results = cur.fetchall()
    # Prepare data for template
    seats_data = {}
    for party_name, seat_count in fptp_results:
        seats_data[party_name] = seat_count

    # Close the connection
    cur.close()
    return seats_data



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    #app.run()