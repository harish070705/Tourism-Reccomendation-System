import pandas as pd
import sqlite3
import random

# Path to the destination dataset (Excel file)
dataset_path = r"data\canadian_tourist_destinations.xlsx"

# SQLite database connection function
def get_db_connection():
    conn = sqlite3.connect('tourism_website.db')
    conn.row_factory = sqlite3.Row
    return conn

# Load destination data from Excel file into a pandas DataFrame
def load_destination_data():
    df = pd.read_excel(dataset_path)
    return df

# Function to get search history for a user
def get_user_search_history(user_id):
    conn = get_db_connection()
    history = conn.execute('SELECT search_term FROM search_history WHERE user_id = ?', (user_id,)).fetchall()
    conn.close()
    return [h['search_term'] for h in history]

# Function to recommend destinations based on search history (or random for guests)
def recommend_destinations(user_id=None):
    # Load the destination dataset
    df = load_destination_data()

    if user_id:
        # Get user search history
        search_history = get_user_search_history(user_id)
        
        # If no search history, return random recommendations
        if not search_history:
            return get_random_recommendations(df)

        recommended = []
        
        # For each search term in history, recommend destinations whose name or description contains the search term
        for search in search_history:
            results = df[df.apply(lambda row: search.lower() in row['dest_name'].lower() or search.lower() in row['description'].lower(), axis=1)]
            recommended.extend(results.to_dict(orient='records'))
        
        # Deduplicate recommendations
        seen = set()
        unique_recommendations = []
        for rec in recommended:
            if rec['dest_name'] not in seen:
                unique_recommendations.append(rec)
                seen.add(rec['dest_name'])

        return unique_recommendations[:6]  # Return top 6 recommendations

    else:
        # For guest users, return random recommendations
        return get_random_recommendations(df)

# Function to get random recommendations for guest users
def get_random_recommendations(df, num_recommendations=6):
    random_recs = df.sample(n=num_recommendations).to_dict(orient='records')
    return random_recs
