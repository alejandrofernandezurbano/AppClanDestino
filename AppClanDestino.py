from flask import Flask, render_template, request, redirect, session
from firebase_config import db

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ================= LOGIN =================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        users = db.collection("Usuarios").where("username", "==", username).stream()
        user = None

        for u in users:
            user = u.to_dict()

        if user and user["password"] == password:
            session["user"] = username
            return redirect("/dashboard")
        else:
            return "Usuario o Clave invalidos"

    return render_template("login.html")


# ================= DASHBOARD =================

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    deportistas_docs = list(db.collection("Deportistas").stream())
    rutas_docs = list(db.collection("Rutas").stream())
    pegues_docs = list(db.collection("Pegues").stream())

    deportistas = []
    for d in deportistas_docs:
        data = d.to_dict()
        data["id"] = d.id
        deportistas.append(data)

    #utas = [r.to_dict() for r in rutas_docs]
    rutas = []
    for r in rutas_docs:
        data = r.to_dict()
        data["grado_num"] = int(data["grado"].replace("V", ""))
        rutas.append(data)

    rutas = sorted(rutas, key=lambda x: (x["sector"], x["grado_num"]))

    pegues = []
    for p in pegues_docs:
        data = p.to_dict()
        data["id"] = p.id
        pegues.append(data)

    # filtro por deportista seleccionado
    filtro = request.args.get("deportista")

    if filtro:
        pegues = [p for p in pegues if p["nombre"] == filtro]

    # ranking (sin duplicados)
    # ================= RANKING OPTIMIZADO =================

    pegues_unicos = {}

    #  Eliminar duplicados (mejor puntaje por ruta)
    for p in pegues:
        key = (p["nombre"], p["ruta"])

        if key not in pegues_unicos:
            pegues_unicos[key] = p["puntaje"]
        else:
            pegues_unicos[key] = max(pegues_unicos[key], p["puntaje"])

    #  Construir estadisticas por deportista
    estadisticas = {}

    for (nombre, ruta), puntaje in pegues_unicos.items():

        if nombre not in estadisticas:
            estadisticas[nombre] = {
                "total": 0,
                "rutas_jueceadas": 0
            }

        estadisticas[nombre]["total"] += puntaje
        estadisticas[nombre]["rutas_jueceadas"] += 1

    #  Armar ranking final
    ranking = []

    for d in deportistas:
        nombre = d["nombre"]
        data = estadisticas.get(nombre, {
            "total": 0,
            "rutas_jueceadas": 0
        })

        total = data["total"]
        rutas_jueceadas = data["rutas_jueceadas"]

        ranking.append({
            "nombre": nombre,
            "sexo": d.get("sexo", ""),
            "total": total,
            "rutas_jueceadas": rutas_jueceadas,
            "rutas_send": total // 100
        })

    #  Ordenar por total descendente
    ranking = sorted(ranking, key=lambda x: x["total"], reverse=True)

    return render_template(
        "dashboard.html",
        user=session["user"],
        deportistas=deportistas,
        rutas=rutas,
        pegues=pegues,
        resultados=ranking,
        filtro=filtro
    )


# ================= AGREGAR DEPORTISTA =================

@app.route("/add_deportista", methods=["POST"])
def add_deportista():
    nombre = request.form["nombre"]
    sexo = request.form["sexo"]

    db.collection("Deportistas").add({
        "nombre": nombre,
        "sexo": sexo
    })

    return redirect("/dashboard")


# ================= AGREGAR RUTA =================

@app.route("/add_ruta", methods=["POST"])
def add_ruta():
    grado = request.form["grado"]
    color = request.form["color"].upper()
    sector = request.form["sector"]

    db.collection("Rutas").add({
        "grado": grado,
        "color": color,
        "sector": sector
    })

    return redirect("/dashboard")


# ================= REGISTRAR PEGUE =================

@app.route("/add_pegue", methods=["POST"])
def add_pegue():
    nombre = request.form["nombre"]
    grado = request.form["grado"]
    color = request.form["color"].upper()
    sector = request.form["sector"]
    puntaje = int(request.form["puntaje"])

    ruta_concatenada = f"{grado}-{color}-{sector}"

    #  verificar si ruta existe
    rutas = db.collection("Rutas")\
        .where("grado", "==", grado)\
        .where("color", "==", color)\
        .where("sector", "==", sector)\
        .stream()

    existe = False
    for r in rutas:
        existe = True

    if not existe:
        db.collection("Rutas").add({
            "grado": grado,
            "color": color,
            "sector": sector
        })

    db.collection("Pegues").add({
        "nombre": nombre,
        "ruta": ruta_concatenada,
        "grado": grado,
        "color": color,
        "sector": sector,
        "puntaje": puntaje,
        "juez": session["user"]
    })

    return redirect("/dashboard")


# ================= LOGOUT =================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/delete_deportista/<doc_id>")
def delete_deportista(doc_id):
    db.collection("Deportistas").document(doc_id).delete()
    return redirect("/dashboard")

@app.route("/delete_pegue/<doc_id>")
def delete_pegue(doc_id):
    db.collection("Pegues").document(doc_id).delete()
    return redirect("/dashboard")
@app.route("/health")
def health():
    return "OK", 200
@app.route("/testdb")
def testdb():
    try:
        docs = db.collection("Usuarios").limit(1).stream()
        return "Conectado a Firebase"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    #app.run(debug=True)
    app.run()
    #app.run(host="0.0.0.0", port=5000)
    #app.run(host="0.0.0.0", port=5000, debug=True)
