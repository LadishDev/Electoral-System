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
        return render_template('lr_election_data.html', data=calculate_election_lr_by_county())
    elif "lrelectionregion" in request.form:
        return render_template('lr_election_data.html', data=calculate_election_lr_by_region())
    elif "lrelectioncountry" in request.form:
        return render_template('lr_election_data.html', data=calculate_election_lr_by_country())
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
    operation_name = level

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

    return operation_name, proportional_data


# General Election seats allocations based on Largest Remainder (By County)
def calculate_election_lr_by_county():
    operation_name = "County"

    # Get data from the database
    cur = electoraldb.cursor(dictionary=True)

    # SQL query to get all the votes for each party by county
    cur.execute('''
        SELECT c.countyName, SUM(e.votes) AS total_votes
        FROM electionresults e
        JOIN constituency con ON e.constituencyID = con.constituencyID
        JOIN county c ON con.countyID = c.countyID
        GROUP BY c.countyName
        ORDER BY total_votes DESC;
    ''')

    # Fetch the results
    pr_results = cur.fetchall()
    cur.close()

    # Calculate the sum of total votes
    total_votes_sum = sum(float(result['total_votes']) for result in pr_results)
    print(total_votes_sum)

    # Calculate the Hare Quota
    hare_quota = total_votes_sum / 650

    # Calculate whole number of seats allocated ( Whole number of votes for a party / Hare Quota )
    seats_allocated = {}
    for result in pr_results:
        county_name = result['countyName']
        total_votes = float(result['total_votes'])
        seats_allocated[county_name] = total_votes // hare_quota
    
    # Calculate the remainder ( Total votes for a party - (Whole number of seats allocated * Hare Quota) )
    remainder = {}
    for result in pr_results:
        county_name = result['countyName']
        total_votes = float(result['total_votes'])
        remainder[county_name] = total_votes - (seats_allocated[county_name] * hare_quota)

    # Sort the remainder in descending order
    sorted_remainder = sorted(remainder.items(), key=lambda x: x[1], reverse=True)

    # Allocate the remaining seats
    for i in range(650 - round(sum(seats_allocated.values()))):
        county_name = sorted_remainder[i][0]
        seats_allocated[county_name] += 1
        
    # Prepare data for template 
    data_by_county = {}
    for county_name, seat_count in seats_allocated.items():
        data_by_county[county_name] = int(seat_count)
    
    return operation_name, data_by_county


# General Election seats allocations based on Largest Remainder (By Region)
def calculate_election_lr_by_region():
    operation_name = "Region"

    # Get data from the database
    cur = electoraldb.cursor(dictionary=True)

    # SQL query to get all the votes for each party by region
    cur.execute('''
        SELECT r.regionName, SUM(e.votes) AS total_votes
        FROM electionresults e
        JOIN constituency con ON e.constituencyID = con.constituencyID
        JOIN region r ON con.regionID = r.regionID
        GROUP BY r.regionName
        ORDER BY total_votes DESC;
    ''')

    # Fetch the results
    pr_results = cur.fetchall()
    cur.close()

    # Calculate the sum of total votes
    total_votes_sum = sum(float(result['total_votes']) for result in pr_results)

    # Calculate the Hare Quota
    hare_quota = total_votes_sum / 650

    # Calculate whole number of seats allocated ( Whole number of votes for a party / Hare Quota )
    seats_allocated = {}
    for result in pr_results:
        region_name = result['regionName']
        total_votes = float(result['total_votes'])
        seats_allocated[region_name] = total_votes // hare_quota
    
    # Calculate the remainder ( Total votes for a party - (Whole number of seats allocated * Hare Quota) )
    remainder = {}
    for result in pr_results:
        region_name = result['regionName']
        total_votes = float(result['total_votes'])
        remainder[region_name] = total_votes - (seats_allocated[region_name] * hare_quota)

    # Sort the remainder in descending order
    sorted_remainder = sorted(remainder.items(), key=lambda x: x[1], reverse=True)

    # Allocate the remaining seats
    for i in range(650 - round(sum(seats_allocated.values()))):
        region_name = sorted_remainder[i][0]
        seats_allocated[region_name] += 1
        
    # Prepare data for template 
    data_by_region = {}
    for region_name, seat_count in seats_allocated.items():
        data_by_region[region_name] = int(seat_count)
    
    return operation_name, data_by_region

# General Election seats allocations based on Largest Remainder (By Country)
def calculate_election_lr_by_country():
    operation_name = "Country"

    # Get data from the database
    cur = electoraldb.cursor(dictionary=True)

    # SQL query to get all the votes for each party by country

    cur.execute('''
        SELECT co.countryName, SUM(e.votes) AS total_votes
        FROM electionresults e
        JOIN constituency con ON e.constituencyID = con.constituencyID
        JOIN country co ON con.countryID = co.countryID
        GROUP BY co.countryName
        ORDER BY total_votes DESC;
    ''')

    # Fetch the results
    pr_results = cur.fetchall()
    cur.close()

    # Calculate the sum of total votes
    total_votes_sum = sum(float(result['total_votes']) for result in pr_results)

    # Calculate the Hare Quota
    hare_quota = total_votes_sum / 650

    # Calculate whole number of seats allocated ( Whole number of votes for a party / Hare Quota )
    seats_allocated = {}
    for result in pr_results:
        country_name = result['countryName']
        total_votes = float(result['total_votes'])
        seats_allocated[country_name] = total_votes // hare_quota
    
    # Calculate the remainder ( Total votes for a party - (Whole number of seats allocated * Hare Quota) )
    remainder = {}
    for result in pr_results:
        country_name = result['countryName']
        total_votes = float(result['total_votes'])
        remainder[country_name] = total_votes - (seats_allocated[country_name] * hare_quota)
    
    # Sort the remainder in descending order
    sorted_remainder = sorted(remainder.items(), key=lambda x: x[1], reverse=True)

    # Allocate the remaining seats
    for i in range(650 - round(sum(seats_allocated.values()))):
        country_name = sorted_remainder[i][0]
        seats_allocated[country_name] += 1

    # Prepare data for template
    data_by_country = {}
    for country_name, seat_count in seats_allocated.items():
        data_by_country[country_name] = int(seat_count)

    return operation_name, data_by_country


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    #app.run()