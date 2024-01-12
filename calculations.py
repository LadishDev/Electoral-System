import mysql.connector
import os

# Connect to the database
electoraldb = mysql.connector.connect(
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASS'),
        host='100.102.58.61',
        database='electoralsystem',
        auth_plugin='mysql_native_password'
    )
print("Connected to the database.")

## Create table called 'electionresults' in the database
cur = electoraldb.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS electionresults (
        systemName VARCHAR(255) NOT NULL,
        partyName VARCHAR(255) NOT NULL,
        votes INT NOT NULL,
        seats INT NOT NULL,
        percentage_seats VARCHAR(255) NOT NULL,
        percentage_votes VARCHAR(255) NOT NULL,
        difference_in_seats_votes VARCHAR(255) NOT NULL,
        different_from_winner VARCHAR(3) NOT NULL
    );
''')

def calculate_fptp():
    # SQL query to get winning constituency in each region and sum their votes
    cur.execute('''
            SELECT
                p.partyName AS Party,
                c.constituencyName AS Constituency,
                cd.votes AS Votes
            FROM
                candidate cd
            JOIN
                party p ON cd.partyID = p.partyID
            JOIN
                constituency c ON cd.constituencyID = c.constituencyID;
    ''')

    # Fetch the results
    data = cur.fetchall()

    # Create array of constituencies
    totalConstituencies = 0
    seats = 0
    constituencies = []
    partiesVotes = {}
    partiesSeats = {}

    for y in data:
        if y[1] not in constituencies:
            totalConstituencies += 1
            constituencies.append(y[1])

    for x in data:
        if x[0] not in partiesVotes:
            partiesVotes[x[0]] = 0

    for x in data:
        if x[0] not in partiesSeats:
            partiesSeats[x[0]] = 0

    for x in constituencies:
        constituencyVotes = 0
        winningParty = ""
        winningVotes = 0
        for y in data:
            if y[1] == x:
                constituencyVotes += y[2]
                if y[2] > winningVotes:
                    winningParty = y[0]
                    winningVotes = y[2]

        partiesVotes[winningParty] += winningVotes
        partiesSeats[winningParty] += 1

    for x in data:
        partiesVotes[x[0]] += x[2]

    total_votes = sum(partiesVotes.values())
    most_seats = max(partiesSeats, key=partiesSeats.get)

    data_unsorted = {
        party: {
            'votes': partiesVotes[party], 
            'seats': partiesSeats[party], 
            'percentage_seats': "{:.2f}%".format(partiesSeats[party] / totalConstituencies * 100),  
            'percentage_votes': "{:.2f}%".format(partiesVotes[party] / total_votes * 100),
            'difference_in_seats_votes': "{:.2f}%".format(abs((partiesSeats[party] / totalConstituencies - partiesVotes[party] / total_votes) * 100)),
            'different_from_winner': 'Yes' if party == most_seats else 'No'
        } 
        for party in partiesSeats.keys()
    }
    ## Insert data into the table
    for party in data_unsorted.keys():
        cur.execute('''
            INSERT INTO electionresults VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        ''', (
            'First Past The Post',  # replace with actual system name
            party,
            data_unsorted[party]['votes'],
            data_unsorted[party]['seats'],
            data_unsorted[party]['percentage_seats'],
            data_unsorted[party]['percentage_votes'],
            data_unsorted[party]['difference_in_seats_votes'],
            data_unsorted[party]['different_from_winner']
        ))

    electoraldb.commit()

def calculate_spr(level=None, threshold=None):
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
            SELECT {column_name}, partyName, SUM(cd.votes) AS total_votes
            FROM candidate cd
            JOIN party p ON cd.partyID = p.partyID
            JOIN constituency con ON cd.constituencyID = con.constituencyID
            JOIN {level.lower()} l ON con.{level.lower()}ID = l.{level.lower()}ID
            GROUP BY {column_name}, partyName
            ORDER BY total_votes DESC;
        '''
        group_by_column = column_name
    else:
        raise ValueError("Invalid level specified")

    # Execute the SQL query
    cur.execute(query)
    pr_results = cur.fetchall()

    if level == "All Seats":
        # Execute a SQL query to get the total number of unique constituencies
        cur.execute("SELECT COUNT(DISTINCT constituencyName) FROM constituency")
        total_seats = cur.fetchone()['COUNT(DISTINCT constituencyName)']

    # Calculate the sum of total votes
    total_votes_sum = sum(float(result['total_votes']) for result in pr_results)

    # Calculate seats and prepare data for template
    proportional_data = {}
    for result in pr_results:
        name = result[group_by_column]
        party = result['partyName']
        total_votes = int(result['total_votes'])

        if level == "All Seats":
            name = "All"
            seats = int(total_votes / total_votes_sum * total_seats)
            if name not in proportional_data:
                proportional_data[name] = {}
            proportional_data[name][party] = {
                'votes': total_votes,
                'seats': seats,
                'percentage_votes': f"{(total_votes / total_votes_sum) * 100:.2f}%",
                'percentage_seats': f"{(seats / total_seats) * 100:.2f}%",
                'difference_in_seats_votes': f"{abs((seats / total_seats * 100) - (total_votes / total_votes_sum * 100)):.2f}%",
                'different_from_winner': 0,  # Calculated this later
            }

            # Assign remaining seats
            remaining_seats = total_seats - sum(data['seats'] for data in proportional_data[name].values())
            for party, data in sorted(proportional_data[name].items(), key=lambda item: item[1]['votes'] % 1, reverse=True):
                if remaining_seats <= 0:
                    break   
                data['seats'] += 1
                remaining_seats -= 1

            # Update 'has_most_seats' field and calculate 'seats_from_diff_winner'
            most_seats_party = max(proportional_data[name], key=lambda x: proportional_data[name][x]['seats'])
            most_seats = proportional_data[name][most_seats_party]['seats']
            for party, data in proportional_data[name].items():
                data['has_most_seats'] = 'Yes' if party == most_seats_party else 'No'
                data['seats_from_diff_winner'] = most_seats - data['seats'] if party != most_seats_party else 0

        elif level in ["County", "Region", "Country"]:
            # Execute a SQL query to get the total number of unique constituencies for the current geographical area
            cur.execute(f"SELECT COUNT(DISTINCT constituencyName) FROM constituency WHERE {level.lower()}ID = (SELECT {level.lower()}ID FROM {level.lower()} WHERE {group_by_column} = '{name}')")
            total_seats = cur.fetchone()['COUNT(DISTINCT constituencyName)']

            seats = int(total_votes / total_votes_sum * total_seats)

            # If the geographical area name is not yet in the dictionary, add it
            if name not in proportional_data:
                proportional_data[name] = {}

            proportional_data[name][party] = {
                'votes': total_votes,
                'seats': seats,
                'percentage_votes': f"{(total_votes / total_votes_sum) * 100:.2f}%",
                'percentage_seats': f"{(seats / total_seats) * 100:.2f}%",
                'difference_in_seats_votes': f"{abs((seats / total_seats * 100) - (total_votes / total_votes_sum * 100)):.2f}%",
                'different_from_winner': 0,  # Calculated this later
            }

            # Assign remaining seats
            remaining_seats = total_seats - sum(data['seats'] for data in proportional_data[name].values())
            for party, data in sorted(proportional_data[name].items(), key=lambda item: item[1]['votes'] % 1, reverse=True):
                if remaining_seats <= 0:
                    break   
                data['seats'] += 1
                remaining_seats -= 1

            # Update 'has_most_seats' field and calculate 'seats_from_diff_winner'
            most_seats_party = max(proportional_data[name], key=lambda x: proportional_data[name][x]['seats'])
            most_seats = proportional_data[name][most_seats_party]['seats']
            for party, data in proportional_data[name].items():
                data['has_most_seats'] = 'Yes' if party == most_seats_party else 'No'
                data['seats_from_diff_winner'] = most_seats - data['seats'] if party != most_seats_party else 0


    # Now that we have the data we need to store it in the database            
    # Insert data into the table
    system_name = "Proportional Representation"
    level_info = f" - {level}" if level != "All Seats" else ""
    threshold_info = f" Threshold" if threshold else ""
    for name in proportional_data.keys():
        system_concat = f"{system_name}{level_info}{threshold_info}"
        if level != "All Seats":
            system_concat += f" - {name}"
        for party in proportional_data[name].keys():
            cur.execute('''
                INSERT INTO electionresults VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            ''', (
                system_concat,
                party,
                proportional_data[name][party]['votes'],
                proportional_data[name][party]['seats'],
                proportional_data[name][party]['percentage_seats'],
                proportional_data[name][party]['percentage_votes'],
                proportional_data[name][party]['difference_in_seats_votes'],
                proportional_data[name][party]['different_from_winner']
            ))
    
    electoraldb.commit()

def calculate_lr(level=None):
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
        SELECT {column_name} AS geo_name, p.partyName AS party, SUM(cd.votes) AS total_votes
        FROM candidate cd
        JOIN party p ON cd.partyID = p.partyID
        JOIN constituency con ON cd.constituencyID = con.constituencyID
        JOIN {join_table} ON {join_condition}
        GROUP BY geo_name, party;
    ''')
    # Fetch the results
    pr_results = cur.fetchall()

    # Calculate the sum of total votes
    total_votes_sum = sum(float(result['total_votes']) for result in pr_results)

    # Calculate the Hare Quota
    hare_quota = total_votes_sum / 650

    # allocated seats = total votes per party / Hare Quota and store remainder in a dictionary
    allocated_seats = {}
    for result in pr_results:
        geo_name = result['geo_name']
        party = result['party']
        total_votes = float(result['total_votes'])
        if geo_name not in allocated_seats:
            allocated_seats[geo_name] = {}
        allocated_seats[geo_name][party] = {
            'votes': total_votes,
            'seats': int(total_votes / hare_quota),
            'remainder': total_votes % hare_quota
        }

    # Sort the allocated seats by the remainder in descending order
    for geo_name in allocated_seats:
        allocated_seats[geo_name] = dict(sorted(allocated_seats[geo_name].items(), key=lambda item: item[1]['remainder'], reverse=True))

    # remaining seats are allocated to parties with the highest remainders
    # and if you reach the bottom with seats left, allocate the seats at the top
    remaining_seats = 650 - sum(sum(allocated_seats[geo_name][party]['seats'] for party in allocated_seats[geo_name]) for geo_name in allocated_seats)
    allocated_remainder = {geo_name: {party: allocated_seats[geo_name][party]['seats'] for party in allocated_seats[geo_name]} for geo_name in allocated_seats}

    for geo_name in allocated_seats:
        for party in sorted(allocated_seats[geo_name].keys(), key=lambda x: allocated_seats[geo_name][x]['remainder'], reverse=True)[:remaining_seats]:
            allocated_remainder[geo_name][party] += 1

    data = {geo_name: {party: {
                    'votes': int(allocated_seats[geo_name][party]['votes']),
                    'seats': allocated_seats[geo_name][party]['seats'] + (allocated_remainder[geo_name][party] - allocated_seats[geo_name][party]['seats']),
                    'percentage_seats': f"{((allocated_seats[geo_name][party]['seats'] + (allocated_remainder[geo_name][party] - allocated_seats[geo_name][party]['seats'])) / 650) * 100:.2f}%",
                    'percentage_votes': f"{(allocated_seats[geo_name][party]['votes'] / total_votes_sum) * 100:.2f}%",
                    'difference_in_seats_votes': f"{((allocated_seats[geo_name][party]['seats'] + (allocated_remainder[geo_name][party] - allocated_seats[geo_name][party]['seats'])) / 650) * 100 - (allocated_seats[geo_name][party]['votes'] / total_votes_sum) * 100:.2f}%",
                    'different_from_winner': 0,  # Calculated this later
                } 
                for party in allocated_seats[geo_name]}
            for geo_name in allocated_seats}
    
    # Calculate 'different_from_winner'
    for geo_name in data:
        # Find the party with the most seats
        winner_party = max(data[geo_name], key=lambda party: data[geo_name][party]['seats'])
        for party in data[geo_name]:
            # Check if this party is different from the winner
            data[geo_name][party]['different_from_winner'] = 'Yes' if party != winner_party else 'No'

    for geo_name in data.keys():
        system_concat = f"Largest Remainder - {level} - {geo_name}"
        for party in data[geo_name].keys():
            cur.execute('''
                INSERT INTO electionresults VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            ''', (
                system_concat,
                party,
                data[geo_name][party]['votes'],
                data[geo_name][party]['seats'],
                data[geo_name][party]['percentage_seats'],
                data[geo_name][party]['percentage_votes'],
                data[geo_name][party]['difference_in_seats_votes'],
                data[geo_name][party]['different_from_winner']
            ))
    
    electoraldb.commit()




## CALL FUNCTIONS TO CALCULATE RESULTS FOR EACH SYSTEM AND STORE THEM IN THE DATABASE
levels = [['All Seats', None], ['All Seats', 5], ['County', None], ['Region', None], ['Country', None]]        

calculate_fptp()
print("Finished calculating FPTP results.")

for level in levels:
    calculate_spr(level[0], level[1])
    print(f"Finished calculating SPR results for {level[0]}{' with ' + str(level[1]) + '% threshold' if level[1] else ''}.")

for level in ['County', 'Region', 'Country']:
    calculate_lr(level)
    print(f"Finished calculating LR results for {level}.")


cur.close()
electoraldb.close()