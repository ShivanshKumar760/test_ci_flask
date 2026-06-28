from flask import Flask,jsonify,request

app=Flask(__name__)
const_internal_db=[]

@app.route('/',methods=["GET"])
def home():
    return jsonify({"msg":"Hello,World Version 3 deployed from another os"})

@app.route('/create',methods=["POST"])
def create():
    data=request.get_json()
    new_item={
        "id":len(const_internal_db)+1,
        "name":data.get("name")
    }
    const_internal_db.append(new_item);
    return jsonify(new_item),201

if __name__ == "__main__":
    app.run(debug=True, threaded=True)  