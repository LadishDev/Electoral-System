from flask import Flask, render_template, request
import mysql.connector
import os
import atexit
import subprocess

app = Flask(__name__, static_url_path='/static')

# Initialize the database connection
electoraldb = None

try:
    electoraldb = mysql.connector.connect(
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASS'),
        host='100.102.58.61',
        database='electoralsystem',
        auth_plugin='mysql_native_password'
    )
    print("Connected to the database.")
    # if electionresults in db doesnt exist then run the script to create it
    cur = electoraldb.cursor()
    cur.execute("SHOW TABLES LIKE 'electionresults'")
    result = cur.fetchone()
    if result:
        print("electionresults table exists")
    else:
        print("electionresults table does not exist")
        subprocess.call(["python", "calculations.py"])
        print("electionresults table created")

except mysql.connector.Error as err:
    print(f"Error: {err}")
    # Handle the error (you might want to log it or provide a meaningful response to the user)
    print("Exiting the system due to database connection error.")
    exit(1)

# Function to close the database connection
def close_db():
    global electoraldb
    if electoraldb and electoraldb.is_connected():
        electoraldb.close()
        print("Disconnected from the database.")

# Register the function to be called on exit
atexit.register(close_db)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route('/home', methods=['GET', 'POST'])
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
    else:
        return render_template('errorpage.html')
    
@app.route('/viewalldata', methods=['GET', 'POST'])
def viewalldata():
    if "back" in request.form:
        return render_template('index.html')
    else:
        return render_template('errorpage.html')
    
@app.route('/fptpdata', methods=['GET', 'POST'])
def fptpdata():
    if "back" in request.form:
        return render_template('index.html')
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
        return render_template('index.html')
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
        return render_template('index.html')
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
        return render_template('index.html')
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
    cur.execute('''
                SELECT c1.firstname, c1.surname, c1.gender, p1.partyName, co1.constituencyName, co1.constituencyType, co2.countyName, r1.regionName, co3.countryName, co1.sittingmp, c1.votes 
                FROM candidate c1 
                JOIN party p1 ON c1.partyID = p1.partyID 
                JOIN constituency co1 ON c1.constituencyID = co1.constituencyID 
                JOIN county co2 ON co1.countyID = co2.countyID 
                JOIN region r1 ON co1.regionID = r1.regionID 
                JOIN country co3 ON co1.countryID = co3.countryID;
                ''')
    
    data = cur.fetchall()
    return data



def calculate_fptp_seats():
    cur = electoraldb.cursor()

    # SQL query to get winning constituency in each region and sum their votes
    cur.execute('''
            SELECT 
                partyName AS Party,
                votes AS Votes,
                seats AS 'Seats Won',
                percentage_seats AS 'Percentage Of Seats',
                percentage_votes AS 'Percentage of Votes',
                difference_in_seats_votes AS 'Difference in Percentages',
                seats_from_diff_winner AS 'Seats Difference from Winner'
            FROM 
                electionresults
            WHERE 
                `system` = 'First Past The Post';   
    ''')

    # Fetch the results
    data = cur.fetchall()
    cur.close()

    # Convert the data to a dictionary
    data_dict = {row[0]: {'votes': row[1], 'seats': row[2], 'percentage_seats': row[3], 'percentage_votes': row[4], 'difference_in_seats_votes': row[5], 'seats_from_diff_winner': row[6]} for row in data}

    # Sort the dictionary by the number of seats won
    sorted_data = dict(sorted(data_dict.items(), key=lambda item: item[1]['seats'], reverse=True))
    return sorted_data



def calculate_election_spr(level=None, threshold=None):
    cur = electoraldb.cursor(dictionary=True)

    # Determine the appropriate SQL query based on the specified level
    if level == "All Seats":
        query = '''
            SELECT partyName, SUM(votes) AS total_votes
            FROM candidate cd
            JOIN party p ON cd.partyID = p.partyID
            GROUP BY partyName
            ORDER BY total_votes DESC;
        '''
        if threshold:
            query = f'''
                SELECT partyName, SUM(votes) AS total_votes
                FROM candidate cd
                JOIN party p ON cd.partyID = p.partyID
                GROUP BY partyName
                HAVING (SUM(votes) / (SELECT SUM(votes) FROM candidate)) * 100 > {threshold}
                ORDER BY total_votes DESC;
            '''
        group_by_column = 'partyName'
    elif level in ["County", "Region", "Country"]:
        column_name = level.lower() + "Name"
        query = f'''
            SELECT {column_name}, SUM(cd.votes) AS total_votes
            FROM candidate cd
            JOIN party p ON cd.partyID = p.partyID
            JOIN constituency con ON cd.constituencyID = con.constituencyID
            JOIN {level.lower()} l ON con.{level.lower()}ID = l.{level.lower()}ID
            GROUP BY {column_name}
            ORDER BY total_votes DESC;
        '''
        group_by_column = column_name
    else:
        raise ValueError("Invalid level specified")

    # Execute the SQL query
    cur.execute(query)
    pr_results = cur.fetchall()

    # Execute a SQL query to get the total number of unique constituencies
    cur.execute("SELECT COUNT(DISTINCT constituencyName) FROM constituency")
    total_seats = cur.fetchone()['COUNT(DISTINCT constituencyName)']
    cur.close()

    # Calculate the sum of total votes
    total_votes_sum = sum(float(result['total_votes']) for result in pr_results)

    # Calculate seats and prepare data for template
    proportional_data = {}
    for result in pr_results:
        name = result[group_by_column]
        total_votes = int(result['total_votes'])
        seats = int(total_votes / total_votes_sum * total_seats)
        proportional_data[name] = {
            'votes': total_votes,
            'seats': seats,
            'percentage_votes': f"{(total_votes / total_votes_sum) * 100:.2f}%",
            'percentage_seats': f"{(seats / total_seats) * 100:.2f}%",
            'difference_in_seats_votes': str(round(abs((seats / total_seats * 100) - (total_votes / total_votes_sum * 100)), 2)) + '%',
            'seats_from_diff_winner': 0,  # Calculated this later
            'has_most_seats': 0 # Calculated this later
        }

    # Assign remaining seats
    remaining_seats = total_seats - sum(data['seats'] for data in proportional_data.values())
    for name, data in sorted(proportional_data.items(), key=lambda item: item[1]['votes'] % 1, reverse=True):
        if remaining_seats <= 0:
            break
        data['seats'] += 1
        remaining_seats -= 1

    # Update 'has_most_seats' field and calculate 'seats_from_diff_winner'
    most_seats_party = max(proportional_data, key=lambda x: proportional_data[x]['seats'])
    most_seats = proportional_data[most_seats_party]['seats']
    for name, data in proportional_data.items():
        data['has_most_seats'] = 'Yes' if name == most_seats_party else 'No'
        data['seats_from_diff_winner'] = most_seats - data['seats'] if name != most_seats_party else 0

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
        SELECT {column_name} AS geo_name, SUM(cd.votes) AS total_votes
        FROM candidate cd
        JOIN constituency con ON cd.constituencyID = con.constituencyID
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
            SELECT c.countyName AS geo_name, SUM(cd.votes) AS total_votes
            FROM candidate cd
            JOIN constituency con ON cd.constituencyID = con.constituencyID
            JOIN county c ON con.countyID = c.countyID
            GROUP BY geo_name
            ORDER BY total_votes DESC;
        '''
    elif level == "Region":
        query = '''
            SELECT r.regionName AS geo_name, SUM(cd.votes) AS total_votes
            FROM candidate cd
            JOIN constituency con ON cd.constituencyID = con.constituencyID
            JOIN region r ON con.regionID = r.regionID
            GROUP BY geo_name
            ORDER BY total_votes DESC;
        '''
    elif level == "Country":
        query = '''
            SELECT co.countryName AS geo_name, SUM(cd.votes) AS total_votes
            FROM candidate cd
            JOIN constituency con ON cd.constituencyID = con.constituencyID
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