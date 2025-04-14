from flask import Flask, request, render_template_string, redirect, url_for, session
from flask_cors import CORS
from flask_mail import Mail, Message
import json
import os
import openai
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# OpenAI API-Key einsetzen!
openai.api_key = "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"

app = Flask(__name__)
CORS(app)
app.secret_key = 'super_secret_key'

# Mail konfigurieren
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'deine_email@gmail.com'  # DEINE E-MAIL HIER
app.config['MAIL_PASSWORD'] = 'dein_passwort'          # DEIN PASSWORT HIER
mail = Mail(app)

DATA_FILE = 'data.json'
PDF_FILE = 'Angebot.pdf'

# Wenn Datei nicht existiert, erstelle sie
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as file:
        json.dump([], file)

# Template
template_base = '''
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{{ title }}</title>
<style>
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f4f4 url('hintergrundbild.jpg') no-repeat center center fixed; /* HINTERGRUNDBILD */
    background-size: cover;
    color: #333;
}
header {
    background: #4caf50;
    color: white;
    padding: 20px;
    text-align: center;
}
section {
    padding: 20px;
    max-width: 600px;
    margin: 20px auto;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}
input, button, textarea {
    width: 100%;
    padding: 10px;
    margin-top: 10px;
    border-radius: 4px;
    border: 1px solid #ddd;
}
button {
    background: #4caf50;
    color: white;
    border: none;
    cursor: pointer;
}
.lead-entry {
    margin-bottom: 20px;
}
</style>
</head>
<body>
<header>
    <h1>{{ header }}</h1>
    <p>{{ description }}</p>
</header>
<section>
    {{ body | safe }}
</section>
</body>
</html>
'''

# PDF-Erzeugung
def generate_pdf(data):
    c = canvas.Canvas(PDF_FILE, pagesize=letter)
    width, height = letter

    # Logo einfügen (du musst logo.png im Ordner haben!)
    try:
        c.drawImage("logo.png", 50, height - 100, width=120, preserveAspectRatio=True)
    except:
        pass  # Falls kein Logo gefunden, einfach weitermachen

    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 50, "Dein PV-Angebot")

    c.setFont("Helvetica", 12)
    y = height - 150
    for key, value in data.items():
        c.drawString(50, y, f"{key.capitalize()}: {value}")
        y -= 20

    c.drawString(50, y - 20, "Vielen Dank für deine Anfrage! Wir melden uns in Kürze.")
    c.save()

# Startseite
@app.route('/')
def home():
    body = '''
    <form method="POST" action="/submit">
        <input type="email" name="email" placeholder="Deine E-Mail-Adresse" required />
        <input type="text" name="address" placeholder="Adresse" required />
        <input type="number" name="area" placeholder="Dachfläche in m²" required />
        <input type="text" name="direction" placeholder="Dachausrichtung (z.B. Süd)" required />
        <input type="number" name="consumption" placeholder="Stromverbrauch / Jahr (kWh)" required />
        <button type="submit">Absenden & Angebot erhalten (PDF)</button>
    </form>
    <br>
    <form method="POST" action="/chat">
        <textarea name="question" placeholder="Frag den AI-Chatbot..."></textarea>
        <button type="submit">Fragen</button>
    </form>
    {% if answer %}
    <p><strong>AI Antwort:</strong> {{ answer }}</p>
    {% endif %}
    '''
    return render_template_string(template_base, title="PV-Konfigurator", header="Dein smarter PV-Berater",
                                  description="Individuelle Simulation & Beratung", body=body)

# Formularverarbeitung
@app.route('/submit', methods=['POST'])
def submit():
    data = {
        "email": request.form['email'],
        "address": request.form['address'],
        "area": request.form['area'],
        "direction": request.form['direction'],
        "consumption": request.form['consumption']
    }

    # Daten speichern
    with open(DATA_FILE, 'r+') as file:
        leads = json.load(file)
        leads.append(data)
        file.seek(0)
        json.dump(leads, file, indent=4)

    # PDF erzeugen
    generate_pdf(data)

    # E-Mail mit PDF senden
    try:
        # An dich
        msg_admin = Message('Neue PV-Anfrage!', sender=app.config['MAIL_USERNAME'],
                            recipients=['ziel_email@gmail.com'])  # DEINE E-MAIL HIER
        msg_admin.body = f"Neue Anfrage:\nAdresse: {data['address']}\nFläche: {data['area']} m²\nAusrichtung: {data['direction']}\nVerbrauch: {data['consumption']} kWh"
        with app.open_resource(PDF_FILE) as pdf:
            msg_admin.attach(PDF_FILE, "application/pdf", pdf.read())
        mail.send(msg_admin)

        # An Kunde
        msg_customer = Message('Dein persönliches PV-Angebot!', sender=app.config['MAIL_USERNAME'],
                               recipients=[data['email']])
        msg_customer.body = "Vielen Dank für deine Anfrage! Im Anhang findest du dein persönliches Angebot als PDF."
        with app.open_resource(PDF_FILE) as pdf:
            msg_customer.attach(PDF_FILE, "application/pdf", pdf.read())
        mail.send(msg_customer)

    except Exception as e:
        print(f"E-Mail-Fehler: {e}")

    return redirect(url_for('home'))

# AI-Chatbot
@app.route('/chat', methods=['POST'])
def chat():
    question = request.form['question']

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Du bist ein hilfsbereiter Solarenergie-Experte."},
                {"role": "user", "content": question}
            ]
        )
        answer = response['choices'][0]['message']['content'].strip()
    except Exception as e:
        answer = f"Fehler bei der AI-Anfrage: {e}"

    return render_template_string(template_base, title="PV-Konfigurator", header="Dein smarter PV-Berater",
                                  description="Individuelle Simulation & Beratung",
                                  body=f'''
    <form method="POST" action="/submit">
        <input type="email" name="email" placeholder="Deine E-Mail-Adresse" required />
        <input type="text" name="address" placeholder="Adresse" required />
        <input type="number" name="area" placeholder="Dachfläche in m²" required />
        <input type="text" name="direction" placeholder="Dachausrichtung (z.B. Süd)" required />
        <input type="number" name="consumption" placeholder="Stromverbrauch / Jahr (kWh)" required />
        <button type="submit">Absenden & Angebot erhalten (PDF)</button>
    </form>
    <br>
    <form method="POST" action="/chat">
        <textarea name="question" placeholder="Frag den AI-Chatbot..."></textarea>
        <button type="submit">Fragen</button>
    </form>
    <p><strong>AI Antwort:</strong> {answer}</p>
    ''')

# Admin-Login & Dashboard
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'adminpass':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Falsche Zugangsdaten!", 401

    body = '''
    <form method="POST">
        <input type="text" name="username" placeholder="Benutzername" required />
        <input type="password" name="password" placeholder="Passwort" required />
        <button type="submit">Login</button>
    </form>
    '''
    return render_template_string(template_base, title="Admin Login", header="Admin Bereich",
                                  description="Login zum Admin Dashboard", body=body)

@app.route('/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    with open(DATA_FILE, 'r') as file:
        leads = json.load(file)

    entries = ''.join([f"<div class='lead-entry'><p><strong>E-Mail:</strong> {lead['email']}</p><p><strong>Adresse:</strong> {lead['address']}</p><p><strong>Fläche:</strong> {lead['area']} m²</p><p><strong>Ausrichtung:</strong> {lead['direction']}</p><p><strong>Verbrauch:</strong> {lead['consumption']} kWh</p><hr/></div>" for lead in leads])

    return render_template_string(template_base, title="Dashboard", header="Admin Dashboard",
                                  description="Alle eingegangenen Leads im Überblick", body=entries)

# Start
if _name_ == '_main_':
    app.run(debug=True)