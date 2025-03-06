from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import requests
import subprocess
import json
from bs4 import BeautifulSoup
import re
from recommendation import recommend_destinations  # Import the recommendation function

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# SQLite database connection function
def get_db_connection():
    conn = sqlite3.connect('tourism_website.db')
    conn.row_factory = sqlite3.Row
    return conn

# Create the database and tables if they don't exist
def create_tables():
    if not os.path.exists('tourism_website.db'):
        conn = get_db_connection()
        conn.execute('''CREATE TABLE IF NOT EXISTS user (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE NOT NULL,
                            email TEXT UNIQUE NOT NULL,
                            password TEXT NOT NULL
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS search_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            search_term TEXT NOT NULL,
                            FOREIGN KEY (user_id) REFERENCES user (id)
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS reviews (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            username TEXT,
                            rating INTEGER NOT NULL,
                            review_text TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES user (id)
                        )''')
        conn.commit()
        conn.close()

# Run table creation
create_tables()

def get_user_from_db(user_id):
    conn = sqlite3.connect('tourism_website.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, email, country FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {'username': user[0], 'email': user[1], 'country': user[2]}
    return None

# Home Route (Main Page)
@app.route('/')
@app.route('/index')
def index():
    user = None
    if 'loggedin' in session:
        user_id = session['user_id']
        conn = get_db_connection()
        user = conn.execute('SELECT username, email FROM user WHERE id = ?', (user_id,)).fetchone()
        conn.close()

        recommendations = recommend_destinations(user_id)
    else:
        recommendations = recommend_destinations()

    # Fetch images for each recommendation
    for destination in recommendations:
        image_url = fetch_image_urls(destination['dest_name'])
        if image_url:
            destination['image_url'] = image_url[0]

    # Fetch reviews from the database
    conn = get_db_connection()
    reviews = conn.execute('SELECT * FROM reviews').fetchall()
    conn.close()

    return render_template('index.html', user=user, recommended_destinations=recommendations, reviews=reviews)


# Function to fetch image URLs from Google Images
def fetch_image_urls(query, num_images=1):
    url = f"https://www.google.com/search?hl=en&tbm=isch&q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        img_tags = soup.find_all("img", {"src": re.compile('^https://')})
        
        img_urls = []
        for img_tag in img_tags[:num_images]:
            img_url = img_tag.get("src")
            if img_url:
                img_urls.append(img_url)
        return img_urls
    else:
        print(f"Failed to retrieve page, status code: {response.status_code}")
        return []

# Function to run geocode.py and get hotel details
def get_hotel_details(query):
    result = subprocess.run(
        ['python', 'geocode.py', query], capture_output=True, text=True
    )
    output = result.stdout
    hotels = json.loads(output)
    
    # Extract hotel name, price, and rating (assuming these fields exist in the JSON)
    hotel_details = []
    for hotel in hotels:
        name = hotel['hotel_name']
        price = hotel.get('price', 'N/A')  # If price isn't available, use 'N/A'
        rating = hotel.get('hotel_rating', 'N/A')  # If rating isn't available, use 'N/A'
        hotel_details.append({'name': name, 'price': price, 'rating': rating})
    
    return hotel_details

# Search Route (For Hotel Search and Image Fetching)
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if query:
        # Get hotel details by running geocode.py
        hotel_details = get_hotel_details(query)
        
        # Fetch images for each hotel name
        for hotel in hotel_details:
            image_url = fetch_image_urls(hotel['name'])
            if image_url:
                hotel['image_url'] = image_url[0]  # Get the first image URL for each hotel
        
        # Log user search term if logged in
        if 'loggedin' in session:
            user_id = session['user_id']
            conn = get_db_connection()
            conn.execute('INSERT INTO search_history (user_id, search_term) VALUES (?, ?)', (user_id, query))
            conn.commit()
            conn.close()

        return render_template('search.html', query=query, hotels=hotel_details)
    else:
        return render_template('search.html')

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO user (username, email, password) VALUES (?, ?, ?)', 
                         (username, email, password))
            conn.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists. Please try again.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM user WHERE username = ? AND password = ?', 
                            (username, password)).fetchone()
        conn.close()

        if user:
            session['loggedin'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('login.html')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()  # Clears session data
    return redirect(url_for('index'))

# Route to handle review submission
@app.route('/submit_review', methods=['POST'])
def submit_review():
    rating = request.form['rating']
    review_text = request.form['review_text']
    user_id = session.get('user_id', None)  # Get from session if logged in
    username = session.get('username', 'Anonymous')  # Get username from session, default to 'Anonymous'

    if user_id:  # Only allow review submission if logged in
        conn = get_db_connection()
        conn.execute('INSERT INTO reviews (user_id, username, rating, review_text) VALUES (?, ?, ?, ?)',
                     (user_id, username, rating, review_text))
        conn.commit()
        conn.close()
    else:
        flash('You need to log in to submit a review.', 'danger')

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
