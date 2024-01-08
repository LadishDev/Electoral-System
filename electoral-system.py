from flask import Flask, render_template, request
import mysql.connector
import os

app = Flask(__name__, static_url_path='/static')

electoraldb = mysql.connector.connect(user=os.environ.get('DB_USER'), password=os.environ.get('DB_PASS'),
                              host='100.102.58.61', database='electoralsystem',
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
    elif "fptpseats" in request.form:
        return render_template('fptp_seats_data.html', data=calculate_fptp_seats())
    elif "sprelection" in request.form:  
        return render_template('spr_election.html')
    elif "lrelection" in request.form:
        return render_template('lr_election.html')
    elif "dhondt" in request.form:
        return render_template('dhondt.html')
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

@app.route('/sprelection', methods=['GET', 'POST'])
def sprelection():
    if "electionspr" in request.form:
        return render_template('spr_election_data.html', data=calculate_election_spr("All Seats"))
    elif "electionsprthreshold" in request.form:
        return render_template('spr_election_data.html', data=calculate_election_spr("All Seats", 5))
    elif "electionsprcounty" in request.form:
        return render_template('spr_election_data.html', data=calculate_election_spr("County"))
    elif "electionsprregion" in request.form:
        return render_template('spr_election_data.html', data=calculate_election_spr("Region"))
    elif "electionsprcountry" in request.form:
        return render_template('spr_election_data.html', data=calculate_election_spr("Country"))
    elif "back" in request.form:
        return render_template('view_data.html')
    else:
        return render_template('errorpage.html')

@app.route('/sprelectiondata', methods=['GET', 'POST'])
def sprelectiondata():
    if "back" in request.form:
        return render_template('spr_election.html')
    else:
        return render_template('errorpage.html')
    
@app.route('/lrelection', methods=['GET', 'POST'])
def lrelection():
    if "lrelectioncounty" in request.form:
        return render_template('lr_election_data.html', data=calculate_election_lr("County"))
    elif "lrelectionregion" in request.form:
        return render_template('lr_election_data.html', data=calculate_election_lr("Region"))
    elif "lrelectioncountry" in request.form:
        return render_template('lr_election_data.html', data=calculate_election_lr("Country"))
    elif "back" in request.form:
        return render_template('view_data.html')
    else:
        return render_template('errorpage.html')
    
@app.route('/lrelectiondata', methods=['GET', 'POST'])
def lrelectiondata():
    if "back" in request.form:
        return render_template('lr_election.html')
    else:
        return render_template('errorpage.html')
    
@app.route('/dhondt', methods=['GET', 'POST'])
def dhont():
    if "dhondtcounty" in request.form:
        return render_template('dhondt_data.html', data=calculate_election_dhondt("County"))
    elif "dhondtregion" in request.form:
        return render_template('dhondt_data.html', data=calculate_election_dhondt("Region"))
    elif "dhondtcountry" in request.form:
        return render_template('dhondt_data.html', data=calculate_election_dhondt("Country"))
    elif "back" in request.form:
        return render_template('view_data.html')
    else:
        return render_template('errorpage.html')
    
@app.route('/dhondtdata', methods=['GET', 'POST'])
def dhondtdata():
    if "back" in request.form:
        return render_template('dhondt.html')
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


def calculate_election_spr(level=None, threshold=None):

    # Get data from the database
    cur = electoraldb.cursor(dictionary=True)

    # Determine the appropriate SQL query based on the specified level
    if level == "All Seats":
        query = '''
            SELECT partyName, SUM(votes) AS total_votes
            FROM electionresults e
            JOIN party p ON e.partyID = p.partyID
            GROUP BY partyName
            ORDER BY total_votes DESC;
        '''
        if threshold:
            query = f'''
                SELECT partyName, SUM(votes) AS total_votes
                FROM electionresults e
                JOIN party p ON e.partyID = p.partyID
                GROUP BY partyName
                HAVING (SUM(votes) / (SELECT SUM(votes) FROM electionresults)) * 100 > {threshold}
                ORDER BY total_votes DESC;
            '''
        group_by_column = 'partyName'
    elif level in ["County", "Region", "Country"]:
        column_name = level.lower() + "Name"
        query = f'''
            SELECT {column_name}, SUM(e.votes) AS total_votes
            FROM electionresults e
            JOIN constituency con ON e.constituencyID = con.constituencyID
            JOIN {level.lower()} l ON con.{level.lower()}ID = l.{level.lower()}ID
            GROUP BY {column_name}
            ORDER BY total_votes DESC;
        '''
        group_by_column = column_name
    else:
        raise ValueError("Invalid level specified")

    # Execute the SQL query
    cur.execute(query)

    # Fetch the results
    pr_results = cur.fetchall()
    cur.close()

    # Calculate the sum of total votes
    total_votes_sum = sum(float(result['total_votes']) for result in pr_results)

    # Prepare data for template
    proportional_data = {}
    for result in pr_results:
        name = result[group_by_column]
        total_votes = float(result['total_votes'])
        percentage_seats = (total_votes / total_votes_sum) * 100
        proportional_data[name] = f"{percentage_seats:.2f}%"

    return level, proportional_data

# General Election seats allocations based on Largest Remainder ( County, Region, Country )
def calculate_election_lr(level=None):

    # Get data from the database
    cur = electoraldb.cursor(dictionary=True)

    # Determine the column names and join table based on the specified level
    if level == "County":
        column_name = "c.countyName"
        join_table = "county c"
        join_condition = "con.countyID = c.countyID"
    elif level == "Region":
        column_name = "r.regionName"
        join_table = "region r"
        join_condition = "con.regionID = r.regionID"
    elif level == "Country":
        column_name = "co.countryName"
        join_table = "country co"
        join_condition = "con.countryID = co.countryID"
    else:
        raise ValueError("Invalid level specified. Please choose from: 'County', 'Region', 'Country'")

    # SQL query to get all the votes for each party by the specified level
    cur.execute(f'''
        SELECT {column_name} AS geo_name, SUM(e.votes) AS total_votes
        FROM electionresults e
        JOIN constituency con ON e.constituencyID = con.constituencyID
        JOIN {join_table} ON {join_condition}
        GROUP BY geo_name
        ORDER BY total_votes DESC;
    ''')

    # Fetch the results
    pr_results = cur.fetchall()
    cur.close()

    # Calculate the sum of total votes
    total_votes_sum = sum(float(result['total_votes']) for result in pr_results)

    # Calculate the Hare Quota
    hare_quota = total_votes_sum / 650

    # allocated seats = total votes per party / Hare Quota and store remainder in a dictionary
    allocated_seats = {}
    for result in pr_results:
        name = result['geo_name']
        total_votes = float(result['total_votes'])
        allocated_seats[name] = {
            'seats': int(total_votes / hare_quota),
            'remainder': total_votes % hare_quota
        }

    # Sort the allocated seats by the remainder in descending order
    allocated_seats = dict(sorted(allocated_seats.items(), key=lambda item: item[1]['remainder'], reverse=True))

    # remaining seats are allocated to parties with the highest remainders
    # and if you reach the bottom with seats left, allocate the seats at the top
    remaining_seats = 650 - sum(allocated_seats[name]['seats'] for name in allocated_seats)
    allocated_remainder = {name: allocated_seats[name]['seats'] for name in allocated_seats}

    for name in sorted(allocated_seats.keys(), key=lambda x: allocated_seats[x]['remainder'], reverse=True)[:remaining_seats]:
        allocated_remainder[name] += 1

    # Combine the operations to calculate allocated seats, remainder, and final result
    data = {name: {
                'allocated_seats': allocated_seats[name]['seats'],
                'remainder': allocated_seats[name]['remainder'],
                'allocated_remaining_seats': (allocated_remainder[name] - allocated_seats[name]['seats']),
                'final_result': allocated_seats[name]['seats'] + (allocated_remainder[name] - allocated_seats[name]['seats'])
            } 
            for name in allocated_seats}

    return level, data


# General Election seats allocations based on D'Hondt method ( County, Region, Country )
def calculate_election_dhondt(level=None):
    # Get data from the database based on the level
    if level == "County":
        query = '''
            SELECT c.countyName AS geo_name, SUM(e.votes) AS total_votes
            FROM electionresults e
            JOIN constituency con ON e.constituencyID = con.constituencyID
            JOIN county c ON con.countyID = c.countyID
            GROUP BY geo_name
            ORDER BY total_votes DESC;
        '''
    elif level == "Region":
        query = '''
            SELECT r.regionName AS geo_name, SUM(e.votes) AS total_votes
            FROM electionresults e
            JOIN constituency con ON e.constituencyID = con.constituencyID
            JOIN region r ON con.regionID = r.regionID
            GROUP BY geo_name
            ORDER BY total_votes DESC;
        '''
    elif level == "Country":
        query = '''
            SELECT co.countryName AS geo_name, SUM(e.votes) AS total_votes
            FROM electionresults e
            JOIN constituency con ON e.constituencyID = con.constituencyID
            JOIN country co ON con.countryID = co.countryID
            GROUP BY geo_name
            ORDER BY total_votes DESC;
        '''
    else:
        raise ValueError("Invalid level. Use 'County', 'Region', or 'Country'.")

    # Get data from the database
    cur = electoraldb.cursor(dictionary=True)
    cur.execute(query)

    # Fetch the results
    pr_results = cur.fetchall()
    cur.close()

    # Sort the results by total votes in descending order
    pr_results = sorted(pr_results, key=lambda x: x['total_votes'], reverse=True)

    # Number of seats available (you can replace this with the actual number of seats)
    num_seats = 650

    # Initialize a dictionary to store allocated seats for each level
    allocated_seats = {}

    # Allocate seats using D'Hondt method
    for result in pr_results:
        name = result['geo_name']
        total_votes = result['total_votes']
        allocated_seats[name] = {
            'seats': 0,
            'votes_per_seat': total_votes,
        }

    # Allocate seats proportionally
    for i in range(num_seats):
        # Calculate the next allocation based on the D'Hondt method
        next_allocation = max(allocated_seats, key=lambda x: allocated_seats[x]['votes_per_seat'])
        allocated_seats[next_allocation]['seats'] += 1
        allocated_seats[next_allocation]['votes_per_seat'] = total_votes / (allocated_seats[next_allocation]['seats'] + 1)

    # Prepare data for template
    data = {name: allocated_seats[name]['seats'] for name in allocated_seats}

    return level, data





#  A system of your own

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    #app.run()