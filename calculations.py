import mysql.connector
import os

# Connect to the database
electoraldb = mysql.connector.connect(
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASS'),
        host='localhost',
        database='electoralsystem',
        auth_plugin='mysql_native_password'
    )
print("Connected to the database.")

## Create table called 'electionresults' in the database
cur = electoraldb.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS electionresults (
        systemName VARCHAR(37) NOT NULL,
        partyName VARCHAR(51) NOT NULL,
        votes INT NOT NULL,
        seats INT NOT NULL,
        percentage_seats VARCHAR(6) NOT NULL,
        percentage_votes VARCHAR(6) NOT NULL,
        difference_in_seats_votes VARCHAR(6) NOT NULL,
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

    # Calculate total constituencies
    for y in data:
        if y[1] not in constituencies:
            totalConstituencies += 1
            constituencies.append(y[1])

    # Calculate total seats
    for x in data:
        if x[0] not in partiesVotes:
            partiesVotes[x[0]] = 0

    # Calculate total votes
    for x in data:
        if x[0] not in partiesSeats:
            partiesSeats[x[0]] = 0

    # Calculate seats for each party and total votes for each party in each constituency
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

    # Calculate total votes for each party
    for x in data:
        partiesVotes[x[0]] += x[2]

    total_votes = sum(partiesVotes.values())
    most_seats = max(partiesSeats, key=partiesSeats.get)

    # Prepare data for template
    data_unsorted = {
        party: {
            'votes': partiesVotes[party], 
            'seats': partiesSeats[party], 
            'percentage_seats': "{:.2f}%".format(partiesSeats[party] / totalConstituencies * 100),  
            'percentage_votes': "{:.2f}%".format(partiesVotes[party] / total_votes * 100),
            'difference_in_seats_votes': "{:.2f}%".format(abs((partiesSeats[party] / totalConstituencies - partiesVotes[party] / total_votes) * 100)),
            'different_from_winner': 0 # Calculated this later
        } 
        for party in partiesSeats.keys()
    }

    # Calculate 'different_from_winner'
    for party in data_unsorted:
        winner_party = max(data_unsorted, key=lambda x: data_unsorted[x]['seats'])
        data_unsorted[party]['different_from_winner'] = 'No' if winner_party == 'Conservative' else 'Yes'

    ## Insert data into the table in the database
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

    electoraldb.commit() # commit changes to the database

def calculate_spr(level=None, threshold=None):
    cur = electoraldb.cursor(dictionary=True)

    # Determine the appropriate SQL query based on the specified level and threshold (if any)
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

    # Calculate the sum of total votes
    total_votes_sum = sum(float(result['total_votes']) for result in pr_results)

    if level == "All Seats":
        # Execute a SQL query to get the total number of unique constituencies
        cur.execute("SELECT COUNT(DISTINCT constituencyName) FROM constituency")
        total_seats_sum = cur.fetchone()['COUNT(DISTINCT constituencyName)']

        # Calculate seats and prepare data for template
        temp_data = {}
        for result in pr_results:
            party = result['partyName']
            total_votes = int(result['total_votes'])

            # Calculate seats for "All Seats" based on the proportional representation formula
            seats = round(total_votes * total_seats_sum / total_votes_sum)  # Simple proportional representation formula

            # If the party is not yet in the aggregate data dictionary, add it
            if party not in temp_data:
                temp_data[party] = {
                    'votes': 0,
                    'seats': 0
                }

            # Update the aggregate data for the party
            temp_data[party]['votes'] += total_votes
            temp_data[party]['seats'] += seats

        # Initialize the proportional_data dictionary
        proportional_data = {}

        # Prepare data for template and calculate the data for percentages and difference_in_seats_votes
        for party in temp_data:
            proportional_data[party] = {
                'votes': temp_data[party]['votes'],
                'seats': temp_data[party]['seats'],
                'percentage_votes': f"{(temp_data[party]['votes'] / total_votes_sum) * 100:.2f}%",
                'percentage_seats': f"{(temp_data[party]['seats'] / total_seats_sum) * 100:.2f}%",
                'difference_in_seats_votes': f"{abs((temp_data[party]['seats'] / total_seats_sum) * 100 - (temp_data[party]['votes'] / total_votes_sum) * 100):.2f}%",
                'different_from_winner': 0,  # Calculated this later
        }

    elif level in ["County", "Region", "Country"]:
        party_seats = {}
        # Iterate over the selected level and calculate seats for each party
        for result in pr_results:
            name = result[group_by_column]
            party_aggregate_data = {}
            # Execute a SQL query to get the total number of unique constituencies for the current geographical area
            cur.execute(f"""
                SELECT COUNT(DISTINCT constituencyName) 
                FROM constituency 
                JOIN candidate ON constituency.constituencyID = candidate.constituencyID
                JOIN party ON candidate.partyID = party.partyID
                WHERE {level.lower()}ID = (SELECT {level.lower()}ID FROM {level.lower()} WHERE {group_by_column} = '{name}')
            """)
            total_seats_sum = cur.fetchone()['COUNT(DISTINCT constituencyName)']

            # Calculate total votes for the current level
            total_votes_level = sum(int(result['total_votes']) for result in pr_results if result[group_by_column] == name)

            # Calculate seats for each party based on the proportional representation formula for the current level
            for result in pr_results:
                name = result[group_by_column]
                party = result['partyName']
                total_votes = int(result['total_votes'])

                seats = round(total_votes / total_votes_level * total_seats_sum)

                # If the party is not yet in the aggregate data dictionary, add it
                if party not in party_aggregate_data:
                    party_aggregate_data[party] = {
                        'votes': 0,
                        'seats': 0
                    }

                # Update the aggregate data for the party
                party_aggregate_data[party]['votes'] += total_votes
                party_aggregate_data[party]['seats'] += seats

                # Add the seats for the party in this level to the total seats for the party
                if party not in party_seats:
                    party_seats[party] = 0
                party_seats[party] += seats

        # Prepare data for template and calculate the data for percentages and difference_in_seats_votes
        proportional_data = {}
        for party in party_aggregate_data:
            proportional_data[party] = {
                'votes': party_aggregate_data[party]['votes'],
                'seats': party_aggregate_data[party]['seats'],
                'percentage_votes': f"{(party_aggregate_data[party]['votes'] / total_votes_sum) * 100:.2f}%",
                'percentage_seats': f"{(party_aggregate_data[party]['seats'] / total_seats_sum ):.2f}%",
                'difference_in_seats_votes': f"{abs((party_aggregate_data[party]['seats'] / total_seats_sum ) - (party_aggregate_data[party]['votes'] / total_votes_sum )):.2f}%",
                'different_from_winner': 0,  # Calculated this later
            }  

    # Calculate 'different_from_winner' for each party in the proportional_data dictionary
    for party in proportional_data:
        # Find the party with the most seats
        winner_party = max(proportional_data, key=lambda x: proportional_data[x]['seats'])
        proportional_data[party]['different_from_winner'] = 'No' if winner_party == 'Conservative' else 'Yes'

    # Insert data into the table database for each party in the proportional_data dictionary using the appropriate system name
    system_name = "Proportional Representation"
    level_info = f" - {level}" if level != "All Seats" else ""
    threshold_info = f" Threshold" if threshold else ""
    for party in proportional_data.keys():
        if party in proportional_data:
            system_concat = f"{system_name}{level_info}{threshold_info}"
            cur.execute('''
                INSERT INTO electionresults VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            ''', (
                system_concat,
                party,
                proportional_data[party]['votes'],
                proportional_data[party]['seats'],
                proportional_data[party]['percentage_seats'],
                proportional_data[party]['percentage_votes'],
                proportional_data[party]['difference_in_seats_votes'],
                proportional_data[party]['different_from_winner']
            ))
    
    electoraldb.commit() # commit changes to the database

def calculate_lr(level=None):
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
    pr_results = cur.fetchall()

    # Group the results by geo_name
    grouped_results = {}
    for result in pr_results:
        geo_name = result['geo_name']
        if geo_name not in grouped_results:
            grouped_results[geo_name] = []
        grouped_results[geo_name].append(result)

    # Initialize the dictionary to store total seats for each party
    party_seats = {}
    # Calculate the sum of total votes for the data set
    total_votes_sum = sum(int(result['total_votes']) for result in pr_results)
    # Calculate the sum of total seats for the data set
    cur.execute('''SELECT COUNT(DISTINCT constituencyName) FROM constituency''')
    total_seats_sum = cur.fetchone()['COUNT(DISTINCT constituencyName)']

    # Calculate the quota
    quota = total_votes_sum / total_seats_sum

    # Initialize a dictionary to store the remainders for each party
    party_remainders = {}

    # Iterate over each geo_name
    for geo_name, results in grouped_results.items():
        # Calculate the sum of total votes
        geo_total_votes_sum = sum(float(result['total_votes']) for result in results)

        # Calculate seats for each party based on the proportional representation formula for the current level
        for result in results:
            party = result['party']
            total_votes = int(result['total_votes'])

            # Calculate the initial number of seats and the remainder for each party
            seats = int(total_votes / quota)
            remainder = total_votes % quota

            # If the party is not yet in the aggregate data dictionary, add it
            if party not in party_seats:
                party_seats[party] = {
                    'votes': 0,
                    'seats': 0,
                    'remainder': 0
                }

            # Update the aggregate data for the party
            party_seats[party]['votes'] += total_votes
            party_seats[party]['seats'] += seats
            party_seats[party]['remainder'] = remainder  # Store the remainder for later

    # Calculate the remaining seats
    remaining_seats = total_seats_sum - sum(party_seats[party]['seats'] for party in party_seats)

    # Distribute the remaining seats to the parties with the largest remainders
    while remaining_seats > 0:
        party_with_largest_remainder = max(party_seats, key=lambda party: party_seats[party]['remainder'])
        party_seats[party_with_largest_remainder]['seats'] += 1
        party_seats[party_with_largest_remainder]['remainder'] = 0
        remaining_seats -= 1

    # Iterate over the aggregate data and prepare data for template
    largest_remainder_data = {}
    for party in party_seats:
        largest_remainder_data[party] = {
            'votes': party_seats[party]['votes'],
            'seats': party_seats[party]['seats'],
            'percentage_seats': f"{(party_seats[party]['seats'] / total_seats_sum) * 100:.2f}%",
            'percentage_votes': f"{(party_seats[party]['votes'] / total_votes_sum) * 100:.2f}%",
            'difference_in_seats_votes': f"{abs(((party_seats[party]['seats'] / total_seats_sum) * 100) - ((party_seats[party]['votes'] / total_votes_sum) * 100)):.2f}%" if party_seats[party]['seats'] != 0 else "0.00%",
            'different_from_winner': 0,  # Calculated this later
        }

    # Calculate 'different_from_winner' for each party in the largest_remainder_data dictionary
    for party in largest_remainder_data:
        winner_party = max(largest_remainder_data, key=lambda x: largest_remainder_data[x]['seats'])
        largest_remainder_data[party]['different_from_winner'] = 'No' if winner_party == 'Conservative' else 'Yes'

    # Insert data into the table in the database
    for party in largest_remainder_data.keys():
        if party in largest_remainder_data:
            system_concat = f"Largest Remainder - {level}"
            cur.execute('''
                INSERT INTO electionresults VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            ''', (
                system_concat,
                party,
                largest_remainder_data[party]['votes'],
                largest_remainder_data[party]['seats'],
                largest_remainder_data[party]['percentage_seats'],
                largest_remainder_data[party]['percentage_votes'],
                largest_remainder_data[party]['difference_in_seats_votes'],
                largest_remainder_data[party]['different_from_winner']
            ))

    electoraldb.commit() # commit changes to the database

def calculate_dhondt(level=None):
    cur = electoraldb.cursor(dictionary=True)

    level_map = { # Map the level to the appropriate table and column names
        "County": ("county", "countyName", "countyID"),
        "Region": ("region", "regionName", "regionID"),
        "Country": ("country", "countryName", "countryID")
    }
    table, column_name, id_column = level_map[level] # Get the table, column name and id column for the specified level

    # SQL query to get all the votes for each party by the level
    cur.execute(f'''
        SELECT {column_name} AS geo_name, p.partyName AS party, SUM(cd.votes) AS total_votes
        FROM candidate cd
        JOIN party p ON cd.partyID = p.partyID
        JOIN constituency con ON cd.constituencyID = con.constituencyID
        JOIN {table} ON {table}.{id_column} = con.{id_column}
        GROUP BY geo_name, party;
    ''')

    # Fetch the results and get the unique levels
    results = cur.fetchall()
    unique_levels = set(result['geo_name'] for result in results)

    # Initialize a dictionary to store the total seats and votes for each party
    party_total_seats = {}
    party_votes = {}

    # Get the unique parties in the current level
    for level_name in unique_levels:
        query = (f"""
            SELECT
                {table}.{column_name},
                COUNT(DISTINCT c.constituencyName) AS 'total seats'
            FROM
                constituency c
            LEFT JOIN
                {table} ON c.{id_column} = {table}.{id_column}
            WHERE
                {table}.{column_name} = %s
            GROUP BY
                {table}.{column_name}
        """, (level_name,))
        

        # Execute the query
        cur.execute(*query)
        total_seats = cur.fetchone()

        # Get the unique parties in the current level
        parties_in_level = set(row['party'] for row in results if row['geo_name'] == level_name)

        # Initialize a list to store the votes and seats for each party
        parties = []

        # Calculate the total votes for each party
        for party_name in parties_in_level:
            total_votes = sum(row['total_votes'] for row in results if row['party'] == party_name and row['geo_name'] == level_name)
            parties.append({'name': party_name, 'votes': total_votes, 'seats': 0})
            party_votes[party_name] = party_votes.get(party_name, 0) + total_votes

        # Distribute the seats to the parties based on their votes
        while sum(party['seats'] for party in parties) < total_seats['total seats']:
            for party in parties:
                party['quotient'] = party['votes'] / (party['seats'] + 1) # D'Hondt formula

            # Find the party with the largest quotient and add a seat to it
            max_quotient = max(parties, key=lambda party: party['quotient'])
            max_quotient['seats'] += 1

            # Break the loop if the total number of seats allocated equals the total number of seats available
            if sum(party['seats'] for party in parties) >= total_seats['total seats']:
                break

        # Calculate the total seats for each party
        for party in parties:
            party_total_seats[party['name']] = party_total_seats.get(party['name'], 0) + party['seats']

    # Prepare data for template
    dhont_data = {}
    for party in party_total_seats:
        dhont_data[party] = {
            'votes': party_votes[party],
            'seats': party_total_seats[party],
            'percentage_seats': f"{(party_total_seats[party] / sum(party_total_seats.values())) * 100:.2f}%",
            'percentage_votes': f"{(party_votes[party] / sum(party_votes.values())) * 100:.2f}%",
            'difference_in_seats_votes': f"{abs(((party_total_seats[party] / sum(party_total_seats.values())) * 100) - float((party_votes[party] / sum(party_votes.values())) * 100)):.2f}%",
            'different_from_winner': 0,  # Calculated this later
        }

    # Calculate 'different_from_winner' for each party in the dhont_data dictionary
    for party in dhont_data:
        winner_party = max(dhont_data, key=lambda x: dhont_data[x]['seats'])
        dhont_data[party]['different_from_winner'] = 'No' if winner_party == 'Conservative' else 'Yes'

    # Insert data into the table in database
    for party in dhont_data.keys():
        # Check if the party exists in the dhont_data dictionary
        if party in dhont_data:
            system_concat = f"D'Hondt - {level}"
            cur.execute('''
                INSERT INTO electionresults VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            ''', (
                system_concat,
                party,
                dhont_data[party]['votes'],
                dhont_data[party]['seats'],
                dhont_data[party]['percentage_seats'],
                dhont_data[party]['percentage_votes'],
                dhont_data[party]['difference_in_seats_votes'],
                dhont_data[party]['different_from_winner']
            ))

    electoraldb.commit() # commit changes to the database

def calculate_webster(level=None):
    cur = electoraldb.cursor(dictionary=True)

    level_map = { # Map the level to the appropriate table and column names
        "County": ("county", "countyName", "countyID"),
        "Region": ("region", "regionName", "regionID"),
        "Country": ("country", "countryName", "countryID")
    }
    table, column_name, id_column = level_map[level]

    # SQL query to get all the votes for each party by the specified level
    cur.execute(f'''
        SELECT {column_name} AS geo_name, p.partyName AS party, SUM(cd.votes) AS total_votes
        FROM candidate cd
        JOIN party p ON cd.partyID = p.partyID
        JOIN constituency con ON cd.constituencyID = con.constituencyID
        JOIN {table} ON {table}.{id_column} = con.{id_column}
        GROUP BY geo_name, party;
    ''')

    # Fetch the results and get the unique levels
    results = cur.fetchall()
    unique_levels = set(result['geo_name'] for result in results)

    # Initialize a dictionary to store the total seats and votes for each party
    party_total_seats = {}
    party_votes = {}

    # Get the unique parties in the current level
    for level_name in unique_levels:
        query = (f"""
            SELECT
                {table}.{column_name},
                COUNT(DISTINCT c.constituencyName) AS 'total seats'
            FROM
                constituency c
            LEFT JOIN
                {table} ON c.{id_column} = {table}.{id_column}
            WHERE
                {table}.{column_name} = %s
            GROUP BY
                {table}.{column_name}
        """, (level_name,))
        

        # Execute the query
        cur.execute(*query)
        total_seats = cur.fetchone()

        # Get the unique parties in the current level
        parties_in_level = set(row['party'] for row in results if row['geo_name'] == level_name)

        # Initialize a list to store the votes and seats for each party
        parties = []

        # Calculate the total votes for each party
        for party_name in parties_in_level:
            total_votes = sum(row['total_votes'] for row in results if row['party'] == party_name and row['geo_name'] == level_name)
            parties.append({'name': party_name, 'votes': total_votes, 'seats': 0})
            party_votes[party_name] = party_votes.get(party_name, 0) + total_votes

        # Distribute the seats to the parties based on their votes
        while sum(party['seats'] for party in parties) < total_seats['total seats']:
            for party in parties:
                party['quotient'] = party['votes'] / (2 * party['seats'] + 1) # Webster formula (same as D'Hondt but with 2 * party['seats'] + 1)

            # Find the party with the largest quotient and add a seat to it
            max_quotient = max(parties, key=lambda party: party['quotient'])
            max_quotient['seats'] += 1

            # Break the loop if the total number of seats allocated equals the total number of seats available
            if sum(party['seats'] for party in parties) >= total_seats['total seats']:
                break

        # Calculate the total seats for each party
        for party in parties:
            party_total_seats[party['name']] = party_total_seats.get(party['name'], 0) + party['seats']

    # Prepare data for template
    webster_data = {}
    for party in party_total_seats:
        webster_data[party] = {
            'votes': party_votes[party],
            'seats': party_total_seats[party],
            'percentage_seats': f"{(party_total_seats[party] / sum(party_total_seats.values())) * 100:.2f}%",
            'percentage_votes': f"{(party_votes[party] / sum(party_votes.values())) * 100:.2f}%",
            'difference_in_seats_votes': f"{abs(((party_total_seats[party] / sum(party_total_seats.values())) * 100) - float((party_votes[party] / sum(party_votes.values())) * 100)):.2f}%",
            'different_from_winner': 0,  # Calculated this later
        }

    # Calculate 'different_from_winner' for each party in the webster_data dictionary
    for party in webster_data:
        winner_party = max(webster_data, key=lambda x: webster_data[x]['seats'])
        webster_data[party]['different_from_winner'] = 'No' if winner_party == 'Conservative' else 'Yes'

    # Insert data into the table in database
    for party in webster_data.keys():
        # Check if the party exists in the dhont_data dictionary
        if party in webster_data:
            system_concat = f"Webster - {level}"
            cur.execute('''
                INSERT INTO electionresults VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            ''', (
                system_concat,
                party,
                webster_data[party]['votes'],
                webster_data[party]['seats'],
                webster_data[party]['percentage_seats'],
                webster_data[party]['percentage_votes'],
                webster_data[party]['difference_in_seats_votes'],
                webster_data[party]['different_from_winner']
            ))

    electoraldb.commit() # commit changes to the database


##              CALL FUNCTIONS TO CALCULATE RESULTS     ##
##             ALSO PROVIDES A PROGRESS INDICATOR       ##

try:
    calculate_fptp()
    print("Finished calculating FPTP results.")

    for level in [['All Seats', None], ['All Seats', 5], ['County', None], ['Region', None], ['Country', None]]:
        calculate_spr(level[0], level[1])
        print(f"Finished calculating SPR results for {level[0]}{' with ' + str(level[1]) + '% threshold' if level[1] else ''}.")

    for level in ['County', 'Region', 'Country']:
        calculate_lr(level)
        print(f"Finished calculating LR results for {level}.")

    for level in ['County', 'Region', 'Country']:
        calculate_dhondt(level)
        print(f"Finished calculating D'Hondt results for {level}.")

    for level in ['County', 'Region', 'Country']:
        calculate_webster(level)
        print(f"Finished calculating Webster results for {level}.")

except Exception as e:
    print("Error: " + str(e))
    cur = electoraldb.cursor()
    cur.execute("DROP TABLE IF EXISTS electionresults;")
    electoraldb.commit()
    cur.close()
    print("Please try again. If the error persists, please contact the developer.")
    exit(1) # Exit with error code 1 (error)
    
cur.close()
electoraldb.close()