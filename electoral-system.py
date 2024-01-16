from flask import Flask, render_template, request, redirect
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
        host='localhost',
        database='electoralsystem',
        auth_plugin='mysql_native_password'
    )
    print("Connected to the database.")
    # if electionresults in db doesnt exist then run the script to create it
    cur = electoraldb.cursor()
    cur.execute("SHOW TABLES LIKE 'electionresults';")
    result = cur.fetchone()
    cur.close()
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
        return render_template('view_data.html', data=fptp_seats())
    elif "sprelection" in request.form:  
        return render_template('spr_election.html')
    elif "lrelection" in request.form:
        return render_template('lr_election.html')
    elif "dhondt" in request.form:
        return render_template('dhondt.html')
    elif "webster" in request.form:
        return render_template('webster.html')
    else:
        return render_template('index.html')
    
@app.route('/viewalldata', methods=['GET', 'POST'])
def viewalldata():
    if "back" in request.form:
        return render_template('index.html')
    else:
        return render_template('errorpage.html')

@app.route('/sprelection', methods=['GET', 'POST'])
def sprelection():
    if "electionspr" in request.form:
        return render_template('view_data.html', data=election_spr("All Seats"))
    elif "electionsprthreshold" in request.form:
        return render_template('view_data.html', data=election_spr("All Seats", 5))
    elif "electionsprcounty" in request.form:
        return render_template('view_data.html', data=election_spr("County"))
    elif "electionsprregion" in request.form:
        return render_template('view_data.html', data=election_spr("Region"))
    elif "electionsprcountry" in request.form:
        return render_template('view_data.html', data=election_spr("Country"))
    elif "back" in request.form:
        return render_template('index.html')
    else:
        return render_template('spr_election.html')
    
@app.route('/lrelection', methods=['GET', 'POST'])
def lrelection():
    if "lrelectioncounty" in request.form:
        return render_template('view_data.html', data=election_lr("County"))
    elif "lrelectionregion" in request.form:
        return render_template('view_data.html', data=election_lr("Region"))
    elif "lrelectioncountry" in request.form:
        return render_template('view_data.html', data=election_lr("Country"))
    elif "back" in request.form:
        return render_template('index.html')
    else:
        return render_template('lr_election.html')
    
@app.route('/sortdatapage', methods=['GET', 'POST'])
def sprelectiondata():
    if "back" in request.form:
        return redirect(request.referrer)
    else:
        return render_template('errorpage.html')
    
@app.route('/sortbydatapage', methods=['GET', 'POST'])
def lrelectiondata():
    if "back" in request.form:
        return redirect(request.referrer)
    else:
        return render_template('errorpage.html')
    
@app.route('/dhondt', methods=['GET', 'POST'])
def dhont():
    if "dhondtcounty" in request.form:
        return render_template('view_data.html', data=election_dhondt("County"))
    elif "dhondtregion" in request.form:
        return render_template('view_data.html', data=election_dhondt("Region"))
    elif "dhondtcountry" in request.form:
        return render_template('view_data.html', data=election_dhondt("Country"))
    elif "back" in request.form:
        return render_template('index.html')
    else:
        return render_template('dhondt.html')
    
@app.route('/webster', methods=['GET', 'POST'])
def webster():
    if "webstercounty" in request.form:
        return render_template('view_data.html', data=election_webster("County"))
    elif "websterregion" in request.form:
        return render_template('view_data.html', data=election_webster("Region"))
    elif "webstercountry" in request.form:
        return render_template('view_data.html', data=election_webster("Country"))
    elif "back" in request.form:
        return render_template('index.html')
    else:
        return render_template('webster.html')
    

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

def fptp_seats():
    # dictionary to store the data
    page_info = {}
    page_info['page_title'] = "First Past The Post Data"
    page_info['page_description'] = "First Past The Post"
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
                different_from_winner AS 'Seats Difference from Winner'
            FROM 
                electionresults
            WHERE 
                systemName = 'First Past The Post';   
    ''')

    # Fetch the results
    data = cur.fetchall()
    cur.close()

    # Convert the data to a dictionary
    data_dict = {row[0]: {'votes': row[1], 'seats': row[2], 'percentage_seats': row[3], 'percentage_votes': row[4], 'difference_in_seats_votes': row[5], 'difference_from_winner': row[6]} for row in data}

    # Sort the dictionary by the number of seats won
    data_dict = dict(sorted(data_dict.items(), key=lambda item: item[1]['seats'], reverse=True))

    # Get the winning party and the difference in seats from the winner for the page info summary
    winning_party = next(iter(data_dict))
    winning_party_difference = data_dict[next(iter(data_dict))]['difference_from_winner']
    page_info['system_winner'] = winning_party
    page_info['different_from_winner'] = winning_party_difference

    return page_info, data_dict

def election_spr(level=None, threshold=None):
    operation_name = f"{level} - Threshold {threshold}%" if threshold else level
    page_info = {'page_title': "Proportional Representation Data", 'page_description': operation_name}
    cur = electoraldb.cursor()

    system_name = "Proportional Representation"
    if level != "All Seats":
        system_name += f" - {level}"
    elif threshold:
        system_name += " Threshold"

    if level not in ["All Seats", "County", "Region", "Country"]:
        raise ValueError("Invalid level specified. Please choose from: 'All Seats', 'County', 'Region', 'Country'")

    cur.execute(f'''
                SELECT 
                    partyName AS Party,
                    votes AS Votes, 
                    seats AS 'Seats Won', 
                    percentage_seats AS 'Percentage Of Seats',
                    percentage_votes AS 'Percentage of Votes', 
                    difference_in_seats_votes AS 'Difference in Percentages',
                    different_from_winner AS 'Difference from Winner'
                FROM 
                    electionresults
                WHERE 
                    systemName = '{system_name}'
                ''')
    data = cur.fetchall()
    cur.close()
    data_dict = {row[0]: {'votes': row[1], 'seats': row[2], 'percentage_seats': row[3], 'percentage_votes': row[4], 'difference_in_seats_votes': row[5], 'difference_from_winner': row[6]} for row in data}
    data_dict = dict(sorted(data_dict.items(), key=lambda item: item[1]['seats'], reverse=True))

    # Get the winning party and the difference in seats from the winner for the page info summary
    winning_party = next(iter(data_dict))
    winning_party_difference = data_dict[next(iter(data_dict))]['difference_from_winner']
    page_info['system_winner'] = winning_party
    page_info['different_from_winner'] = winning_party_difference

    return page_info, data_dict

# General Election seats allocations based on Largest Remainder ( County, Region, Country )
def election_lr(level=None):
    operation_name = f"{level}" if level is not None else level
    # dictionary to store the data
    page_info = {}
    page_info['page_title'] = "Largest Remainder Data"
    page_info['page_description'] = operation_name

    # Get data from the database based on the level
    cur = electoraldb.cursor()
    cur.execute(f'''
            SELECT 
                systemName AS `System`,
                partyName AS Party,
                votes AS Votes, 
                seats AS 'Seats Won', 
                percentage_seats AS 'Percentage Of Seats',
                percentage_votes AS 'Percentage of Votes', 
                difference_in_seats_votes AS 'Difference in Percentages',
                different_from_winner AS 'Difference from Winner'
            FROM
                electionresults
            WHERE
                systemName = 'Largest Remainder - {level}'
            ''')
    
    # Fetch the results
    data = cur.fetchall()
    cur.close()
    # Convert the data to a dictionary
    data_dict = {row[1]: {'votes': row[2], 'seats': row[3], 'percentage_seats': row[4], 'percentage_votes': row[5], 'difference_in_seats_votes': row[6], 'difference_from_winner': row[7]} for row in data}
    #Order the dictionary by the number of seats won
    data_dict = dict(sorted(data_dict.items(), key=lambda item: item[1]['seats'], reverse=True))
    
    # Get the winning party and the difference in seats from the winner for the page info summary
    winning_party = next(iter(data_dict))
    winning_party_difference = data_dict[next(iter(data_dict))]['difference_from_winner']
    page_info['system_winner'] = winning_party
    page_info['different_from_winner'] = winning_party_difference
    
    return page_info, data_dict

# General Election seats allocations based on D'Hondt method ( County, Region, Country )
def election_dhondt(level=None):
    operation_name = f"{level}" if level is not None else level
    # dictionary to store the data
    page_info = {}
    page_info['page_title'] = "D'Hondt Data"
    page_info['page_description'] = operation_name
    
    # Get data from the database based on the level
    cur = electoraldb.cursor()
    cur.execute(f'''
            SELECT 
                systemName AS `System`,
                partyName AS Party,
                votes AS Votes, 
                seats AS 'Seats Won', 
                percentage_seats AS 'Percentage Of Seats',
                percentage_votes AS 'Percentage of Votes', 
                difference_in_seats_votes AS 'Difference in Percentages',
                different_from_winner AS 'Difference from Winner'
            FROM
                electionresults
            WHERE
                systemName = 'D''Hondt - {level}'
            ''')
    data = cur.fetchall()
    cur.close()
    # Convert the data to a dictionary
    data_dict = {row[1]: {'votes': row[2], 'seats': row[3], 'percentage_seats': row[4], 'percentage_votes': row[5], 'difference_in_seats_votes': row[6], 'difference_from_winner': row[7]} for row in data}
    #Order the dictionary by the number of seats won
    data_dict = dict(sorted(data_dict.items(), key=lambda item: item[1]['seats'], reverse=True))

    # Get the winning party and the difference in seats from the winner for the page info summary
    winning_party = next(iter(data_dict))
    winning_party_difference = data_dict[next(iter(data_dict))]['difference_from_winner']
    page_info['system_winner'] = winning_party
    page_info['different_from_winner'] = winning_party_difference

    return page_info, data_dict

def election_webster(level=None):
    operation_name = f"{level}" if level is not None else level
    # dictionary to store the data
    page_info = {}
    page_info['page_title'] = "Webster Data"
    page_info['page_description'] = operation_name

    # Get data from the database based on the level
    cur = electoraldb.cursor()
    cur.execute(f'''
            SELECT 
                systemName AS `System`,
                partyName AS Party,
                votes AS Votes, 
                seats AS 'Seats Won', 
                percentage_seats AS 'Percentage Of Seats',
                percentage_votes AS 'Percentage of Votes', 
                difference_in_seats_votes AS 'Difference in Percentages',
                different_from_winner AS 'Difference from Winner'
            FROM
                electionresults
            WHERE
                systemName = 'Webster - {level}'
            ''')
    data = cur.fetchall()
    cur.close()
    data_dict = {row[1]: {'votes': row[2], 'seats': row[3], 'percentage_seats': row[4], 'percentage_votes': row[5], 'difference_in_seats_votes': row[6], 'difference_from_winner': row[7]} for row in data}
    data_dict = dict(sorted(data_dict.items(), key=lambda item: item[1]['seats'], reverse=True))

    # Get the winning party and the difference in seats from the winner for the page info summary
    winning_party = next(iter(data_dict))
    winning_party_difference = data_dict[next(iter(data_dict))]['difference_from_winner']
    page_info['system_winner'] = winning_party
    page_info['different_from_winner'] = winning_party_difference

    return page_info, data_dict

#  A system of your own
def election_own():
    pass  # TODO


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    #app.run()