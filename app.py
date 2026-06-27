from flask import Flask,jsonify

app=Flask(__name__)

@app.route('/',methods=["GET"])
def home():
    return jsonify({"msg":"Hello,World Version 2"})


if __name__ == "__main__":
    app.run(debug=True, threaded=True)  