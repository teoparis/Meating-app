from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os
import logging
import secrets
from datetime import date

# Configura i log
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),  # Salva i log anche su file
        logging.StreamHandler()  # Mostra i log nel terminale
    ]
)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

DATA_DIR = "data"
MENU_FILE = os.path.join(DATA_DIR, "menu.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")

def test_logging():
    logging.debug("Eseguendo il test del logging.")
    try:
        result = load_menu()
        assert isinstance(result, dict), "Il menu non è un dizionario."
        logging.info("Test del logging superato con successo.")
    except Exception as e:
        logging.error("Errore durante il test del logging: %s", e)

def ensure_keys(menu):
    if not isinstance(menu, dict):
        raise ValueError("Il menu deve essere un dizionario.")
    for date, categories in menu.items():
        if not all(key in categories for key in ["primi", "secondi", "dolci"]):
            raise ValueError(f"Chiavi mancanti nella data {date}.")
        logging.debug("Menu validato per la data %s", date)
    return menu


def load_menu():
    logging.debug("Inizio caricamento del menu...")
    try:
        if os.path.exists(MENU_FILE):
            with open(MENU_FILE, "r") as f:
                menu = json.load(f)
                logging.debug("Menu caricato correttamente.")
                return ensure_keys(menu)
        else:
            logging.warning("Menu non trovato.")
    except json.JSONDecodeError as e:
        logging.error("Errore nel parsing del file menu: %s", e)
    except Exception as e:
        logging.error("Errore sconosciuto durante il caricamento del menu: %s", e)
    return {}


def save_menu(menu):
    logging.debug("Salvataggio menu: %s", menu)
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(MENU_FILE, "w") as f:
            json.dump(menu, f, indent=4)
        logging.debug("Menu salvato con successo.")
    except Exception as e:
        logging.error("Errore durante il salvataggio del menu: %s", e)


def load_orders():
    logging.debug("Caricamento ordini...")
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r") as f:
                orders = json.load(f)
                logging.debug("Ordini caricati: %s", orders)
                return orders
        except json.JSONDecodeError as e:
            logging.error("Errore nella decodifica degli ordini: %s", e)
    logging.warning("File degli ordini non trovato. Restituisco lista vuota.")
    return []


def save_orders(orders):
    logging.debug("Salvataggio ordini: %s", orders)
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(ORDERS_FILE, "w") as f:
            json.dump(orders, f, indent=4)
        logging.debug("Ordini salvati con successo.")
    except Exception as e:
        logging.error("Errore durante il salvataggio degli ordini: %s", e)


@app.route("/")
def index():
    logging.debug("Accesso alla homepage.")
    menu_data = load_menu()
    today_date = date.today().strftime("%Y-%m-%d")
    menu = menu_data.get(today_date, {"primi": [], "secondi": [], "dolci": []})
    total_dishes = len(menu.get("primi", []) + menu.get("secondi", []) + menu.get("dolci", []))
    logging.debug("Rendering index con menu: %s", menu)
    return render_template(
        "index.html",
        menu=menu,
        quantities=[0] * total_dishes,
        notes=[""] * total_dishes,
        error_message=None,
    )

def validate_order(order):
    if "details" not in order or not isinstance(order["details"], dict):
        raise ValueError("L'ordine non ha un formato valido.")
    if "firstname" not in order or "lastname" not in order:
        raise ValueError("Nome e cognome sono obbligatori.")

@app.route("/order", methods=["POST"])
def order():
    logging.debug("Gestione ordine ricevuto.")
    try:
        menu = load_menu()
        total_dishes = sum(len(menu.get(category, [])) for category in ["primi", "secondi", "dolci"])
        logging.debug("Numero totale di piatti nel menu: %d", total_dishes)

        quantities = [int(request.form.get(f"quantities_{i}", 0) or 0) for i in range(total_dishes)]
        notes = [request.form.get(f"notes_{i}", "") for i in range(total_dishes)]
        logging.debug("Quantità ricevute: %s", quantities)
        logging.debug("Note ricevute: %s", notes)

        dishes = []
        index = 0
        for category in ["primi", "secondi", "dolci"]:
            for dish in menu.get(category, []):
                if quantities[index] > 0:
                    dishes.append({
                        "name": dish["name"],
                        "quantity": quantities[index],
                        "note": notes[index]
                    })
                index += 1

        extras = [
            {"name": "Acqua Naturale", "quantity": int(request.form.get("quantity_water_natural", 0) or 0)},
            {"name": "Acqua Frizzante", "quantity": int(request.form.get("quantity_water_sparkling", 0) or 0)},
            {"name": "Caffè", "quantity": int(request.form.get("quantity_coffee", 0) or 0)},
        ]
        extras = [extra for extra in extras if extra["quantity"] > 0]
        logging.debug("Extra ordinati: %s", extras)

        if not (dishes or extras):
            flash("Devi selezionare almeno un piatto o un extra.", "danger")
            logging.warning("Ordine non valido: nessun piatto o extra selezionato.")
            return redirect(url_for("index"))

        order_data = {
            "firstname": request.form.get("firstname", "").strip(),
            "lastname": request.form.get("lastname", "").strip(),
            "people_count": int(request.form.get("people_count", 0)),
            "timeslot": request.form.get("timeslot", "").strip(),
            "details": {
                "dishes": dishes,
                "extras": extras
            },
        }
        logging.debug("Ordine creato con successo: %s", order_data)

        orders = load_orders()
        orders.append(order_data)
        save_orders(orders)

        flash("Ordine inviato con successo!", "success")
        logging.info("Ordine salvato con successo.")
        return render_template("confirm.html", order=order_data)
    except Exception as e:
        logging.error("Errore nella gestione dell'ordine: %s", e)
        flash("Si è verificato un errore. Riprova.", "danger")
        return redirect(url_for("index"))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    logging.debug("Accesso alla pagina admin.")
    menu_data = load_menu()
    menu_date = request.args.get("menu_date", date.today().strftime("%Y-%m-%d"))
    if menu_date not in menu_data:
        menu_data[menu_date] = {"primi": [], "secondi": [], "dolci": []}
    menu = menu_data[menu_date]

    if request.method == "POST":
        action = request.form.get("action")
        category = request.form.get("category")
        dish_name = request.form.get("dish", "").strip()
        notes = request.form.get("notes", "").strip()
        try:
            if action == "add" and dish_name and category:
                menu[category].append({"name": dish_name, "notes": notes})
                menu_data[menu_date] = menu
                save_menu(menu_data)
                flash(f"Piatto '{dish_name}' aggiunto con successo!", "success")
            elif action == "delete" and dish_name and category:
                menu[category] = [dish for dish in menu[category] if dish["name"] != dish_name]
                menu_data[menu_date] = menu
                save_menu(menu_data)
                flash(f"Piatto '{dish_name}' rimosso con successo!", "success")
            else:
                flash("Azione non valida o dati incompleti.", "danger")
        except Exception as e:
            logging.error("Errore nella gestione del menu: %s", e)
            flash("Si è verificato un errore nella gestione del menu.", "danger")

    return render_template("admin.html", menu=menu, menu_date=menu_date)


@app.route("/admin/orders")
def view_orders():
    logging.debug("Accesso alla pagina degli ordini.")
    orders = load_orders()
    logging.debug("Ordini caricati: %s", orders)
    return render_template("orders.html", orders=orders)


if __name__ == "__main__":
    logging.info("Avvio dell'applicazione Flask.")
    app.run(debug=True, host="0.0.0.0", port=5000)