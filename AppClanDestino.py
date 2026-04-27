from flask import Flask, render_template, request, redirect, session
from firebase_config import db
import os

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

    # ================= DEPORTISTAS =================
    deportistas = []
    for d in deportistas_docs:
        data = d.to_dict()
        data["id"] = d.id
        data["infantil"] = data.get("infantil", False)
        deportistas.append(data)

    # ================= RUTAS =================
    rutas = []
    for r in rutas_docs:
        data = r.to_dict()
        data["id"] = r.id
        data["infantil"] = data.get("infantil", False)

        grado_str = data["grado"]

        if grado_str.startswith("N"):
            data["grado_num"] = int(grado_str.replace("N", "")) - 2
        elif grado_str.startswith("V"):
            data["grado_num"] = int(grado_str.replace("V", ""))
        else:
            data["grado_num"] = 0

        rutas.append(data)

    rutas = sorted(rutas, key=lambda x: (x["sector"], x["grado_num"]))

    # ================= PEGUES =================
    pegues = []
    for p in pegues_docs:
        data = p.to_dict()
        data["id"] = p.id
        pegues.append(data)

    filtro = request.args.get("deportista")
    if filtro:
        pegues = [p for p in pegues if p["nombre"] == filtro]

    # ================= RANKING =================

    pegues_unicos = {}

    for p in pegues:
        key = (p["nombre"], p.get("ruta_id"))

        if key not in pegues_unicos:
            pegues_unicos[key] = p["puntaje"]
        else:
            pegues_unicos[key] = max(pegues_unicos[key], p["puntaje"])

    estadisticas = {}

    for (nombre, ruta), puntaje in pegues_unicos.items():

        if nombre not in estadisticas:
            estadisticas[nombre] = {
                "total": 0,
                "rutas_jueceadas": 0
            }

        estadisticas[nombre]["total"] += puntaje
        estadisticas[nombre]["rutas_jueceadas"] += 1

    ranking = []

    for d in deportistas:
        nombre = d["nombre"]

        data = estadisticas.get(nombre, {
            "total": 0,
            "rutas_jueceadas": 0
        })

        ranking.append({
            "nombre": nombre,
            "sexo": d.get("sexo", ""),
            "infantil": d.get("infantil", False),
            "total": data["total"],
            "rutas_jueceadas": data["rutas_jueceadas"],
            "rutas_send": data["total"] // 100
        })

    ranking = sorted(ranking, key=lambda x: x["total"], reverse=True)

    # 🔥 separar rankings (FIX copas)
    ranking_m = [r for r in ranking if r["sexo"] == "M" and not r["infantil"]]
    ranking_f = [r for r in ranking if r["sexo"] == "F" and not r["infantil"]]
    ranking_mi = [r for r in ranking if r["sexo"] == "M" and r["infantil"]]
    ranking_fi = [r for r in ranking if r["sexo"] == "F" and r["infantil"]]

    return render_template(
        "dashboard.html",
        user=session["user"],
        deportistas=deportistas,
        rutas=rutas,
        pegues=pegues,
        filtro=filtro,
        ranking_m=ranking_m,
        ranking_f=ranking_f,
        ranking_mi=ranking_mi,
        ranking_fi=ranking_fi
    )


# ================= AGREGAR DEPORTISTA =================

@app.route("/add_deportista", methods=["POST"])
def add_deportista():
    nombre = request.form["nombre"]
    sexo = request.form["sexo"]
    infantil = request.form.get("infantil") == "on"

    db.collection("Deportistas").add({
        "nombre": nombre,
        "sexo": sexo,
        "infantil": infantil
    })

    return redirect("/dashboard")


# ================= AGREGAR RUTA =================

@app.route("/add_ruta", methods=["POST"])
def add_ruta():
    grado = request.form["grado"]
    color = request.form["color"].upper()
    sector = request.form["sector"]
    infantil = request.form.get("infantil") == "on"

    db.collection("Rutas").add({
        "grado": grado,
        "color": color,
        "sector": sector,
        "infantil": infantil
    })

    return redirect("/dashboard")


# ================= REGISTRAR PEGUE =================

@app.route("/add_pegue", methods=["POST"])
def add_pegue():
    nombre = request.form["nombre"]
    sector = request.form["sector"]
    ruta_id = request.form["ruta_id"]
    puntaje = int(request.form["puntaje"])

    ruta_doc = db.collection("Rutas").document(ruta_id).get()
    ruta = ruta_doc.to_dict()

    db.collection("Pegues").add({
        "nombre": nombre,
        "ruta": f"{ruta['grado']}-{ruta['color']}-{ruta['sector']}",
        "ruta_id": ruta_id,
        "sector": sector,
        "puntaje": puntaje,
        "juez": session["user"]
    })

    return redirect("/dashboard")


# ================= GET RUTAS DINÁMICAS =================

@app.route("/get_rutas")
def get_rutas():
    sector = request.args.get("sector")
    nombre = request.args.get("nombre")

    deportistas = db.collection("Deportistas").where("nombre", "==", nombre).stream()
    deportista = next(deportistas).to_dict()

    infantil = deportista.get("infantil", False)

    rutas_ref = db.collection("Rutas").where("sector", "==", sector).stream()

    rutas = []
    for r in rutas_ref:
        data = r.to_dict()

        if infantil:
            if not data.get("infantil", False):
                continue
        else:
            if data.get("infantil", False):
                continue

        rutas.append({
            "id": r.id,
            "nombre": f"{data['grado']} - {data['color']}"
        })

    return {"rutas": rutas}


# ================= DELETE =================

@app.route("/delete_deportista/<doc_id>")
def delete_deportista(doc_id):
    db.collection("Deportistas").document(doc_id).delete()
    return redirect("/dashboard")


@app.route("/delete_pegue/<doc_id>")
def delete_pegue(doc_id):
    db.collection("Pegues").document(doc_id).delete()
    return redirect("/dashboard")


# ================= UTILS =================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/health")
def health():
    return "OK", 200


@app.route("/testdb")
def testdb():
    try:
        db.collection("Usuarios").limit(1).stream()
        return "Conectado a Firebase"
    except Exception as e:
        return f"Error: {str(e)}"


@app.route("/envtest")
def envtest():
    return str(bool(os.environ.get("FIREBASE_KEY")))


# ================= RUN =================

if __name__ == "__main__":
    app.run()
