from flask import Flask,jsonify,request

app=Flask(__name__)
users=[
    {"id":1,"name":"Alice","email":"alice@example.com"},
    {"id":2,"name":"Bob","email":"bob@example.com"}
]

# Helper : find a user by id

def find_user(user_id):
    return next((u for u in users if u["id"]==user_id),None)

@app.route('/',methods=["GET"])
def home():
    return jsonify({"msg":"Hello,World Version 3 deployed from another os"})

@app.get("/users")
def get_all_users():
    return jsonify(users),200

@app.get("/users/<int:user_id>")
def get_user(user_id):
    user = find_user(user_id)
    if not user:
        return jsonify({"error":"User not found"}),404
    return jsonify(user),200

@app.route('/users',methods=["POST"])
def create():
    data=request.get_json()
    if not data:
        return jsonify({
            "error":"Request body must be JSON"
        }),400
    if not data.get("name"):
        return jsonify({
            "error":"Name is required"
        }),400
    if not data.get("email"):
        return ({
            "error":"email is required"
        }),400
    
    new_user={
        "id" : len(users)+1,
        "name":data["name"],
        "email":data["email"],
    }

    users.append(new_user)
    return jsonify(new_user),201

if __name__ == "__main__":
    app.run(debug=True, threaded=True)  