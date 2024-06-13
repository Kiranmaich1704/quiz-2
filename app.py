from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import csv
app = Flask(__name__)

DATABASE = 'earthquakes.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS earthquakes (
        id TEXT PRIMARY KEY,
        time TEXT,
        latitude REAL,
        longitude REAL,
        depth REAL,
        mag REAL,
        net TEXT
    );
    ''')
    conn.commit()
    conn.close()

init_db()


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        try:
            latitude = float(request.form['latitude'])
            degrees = float(request.form['degrees'])
            min_lat = latitude - degrees
            max_lat = latitude + degrees
            
            conn = get_db_connection()
            cursor = conn.execute(
                'SELECT time, latitude, longitude, depth, mag, net, id FROM earthquakes WHERE latitude BETWEEN ? AND ?',
                (min_lat, max_lat)
            )
            entries = cursor.fetchall()
            conn.close()

            return render_template('results.html', entries=entries)
        
        except ValueError:
            error_message = "Invalid latitude or degrees. Please enter valid numeric values."
            return render_template('search.html', error_message=error_message)
    
    return render_template('search.html')


@app.route('/delete_entries', methods=['GET', 'POST'])
def delete_entries():
    if request.method == 'POST':
        net_value = request.form['net_value']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM earthquakes WHERE net = ?', (net_value,))
        count_before = cur.fetchone()[0]
        cur.execute('DELETE FROM earthquakes WHERE net = ?', (net_value,))
        conn.commit()
        cur.execute('SELECT COUNT(*) FROM earthquakes')
        count_after = cur.fetchone()[0]
        conn.close()
        return f"Deleted {count_before} entries. {count_after} entries remain."
    return render_template('delete.html')

@app.route('/create_entry', methods=['GET', 'POST'])
def create_entry():
    if request.method == 'POST':
        new_entry = {
            'id': request.form['id'],
            'time': request.form['time'],
            'latitude': request.form['latitude'],
            'longitude': request.form['longitude'],
            'depth': request.form['depth'],
            'mag': request.form['mag'],
            'net': request.form['net'],
            'id': request.form['id']
        }
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO earthquakes (id, time, latitude, longitude, depth, mag, net) VALUES (?, ?, ?, ?, ?, ?, ?)',
                tuple(new_entry.values())
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash('Error: ID already exists.')
            return redirect(url_for('create_entry'))
        conn.close()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/modify_entry', methods=['GET', 'POST'])
def modify_entry():
    if request.method == 'POST':
        net_id = request.form['net_id']
        conn = get_db_connection()
        entry = conn.execute('SELECT * FROM earthquakes WHERE id = ?', (net_id,)).fetchone()
        if entry is None:
            flash('Error: ID does not exist.')
            conn.close()
            return redirect(url_for('modify_entry'))

        updated_entry = {
            'id': request.form['id'],
            'time': request.form['time'],
            'latitude': request.form['latitude'],
            'longitude': request.form['longitude'],
            'depth': request.form['depth'],
            'mag': request.form['mag'],
            'net': request.form['net']
        }

        # Ensure the order of values in the tuple matches the order of placeholders in the SQL query
        conn.execute(
            'UPDATE earthquakes SET id = ?, time = ?, latitude = ?, longitude = ?, depth = ?, mag = ?, net = ? WHERE id = ?',
            (updated_entry['id'], updated_entry['time'], updated_entry['latitude'],
             updated_entry['longitude'], updated_entry['depth'], updated_entry['mag'],
             updated_entry['net'], net_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('update.html')

@app.route('/display_entries')
def display_entries():
    conn = get_db_connection()
    cursor = conn.execute('SELECT time, latitude, longitude, depth, mag, net, id FROM earthquakes')
    entries = cursor.fetchall()
    conn.close()
    return render_template('display.html', entries=entries)

@app.route('/uploadcsv')
def uploadcsv():
    return render_template('uploadcsv.html')

@app.route('/uploadcsvresults', methods=['POST'])
def uploadcsvresults():
    if 'csvfile' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['csvfile']

    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file.content_type != 'text/csv':
        return 'Invalid file type. Please upload a CSV file.'

    error_messages = []
    success_count = 0

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        cursor = conn.cursor()

        # Read the file as a string and then decode it
        stream = file.stream.read().decode('UTF-8').splitlines()
        reader = csv.DictReader(stream)

        for row in reader:
            try:
                cursor.execute("""
                    INSERT INTO earthquakes (id, time, latitude, longitude, depth, mag, net)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['id'], row['time'], float(row['latitude']), float(row['longitude']), float(row['depth']),
                    float(row['mag']), row['net']))
                success_count += 1
            except sqlite3.IntegrityError:
                error_messages.append(f"Error: ID {row['id']} already exists.")
            except Exception as e:
                error_messages.append(f"Error processing row {row['id']}: {str(e)}")
                
        conn.commit()

    return render_template('uploadresult.html', success_count=success_count, error_messages=error_messages)

if __name__ == '__main__':
    app.run(debug=True)
