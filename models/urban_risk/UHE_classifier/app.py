
from flask import Flask, Response, make_response, jsonify, request
import json
from utils import api_success_response
from flask_cors import CORS
# from gevent import pywsgi
from shelters import queryShelters
from routes import getRoute

app = Flask(__name__)
CORS(app)

@app.errorhandler(Exception)
def handle_database_error(error):
    # 捕获数据库查询错误并返回自定义的错误响应
    error_message = error.args[0]
    error_code = error.code
    response = jsonify({"error": error_message, "error_code": error_code})
    # 设置状态码为 500 服务器内部错误
    response.status_code = 500
    return response


@app.before_request
def before_request():
    requestUrl = request.url
    try:
        if request.method != "OPTIONS":
            request.environ['addd-ddd'] = 'aa'
        else:
            raise ValueError("Authorization faild.")
    except PermissionError as e:
        return Response(json.dumps({
            "status": 403,
            "code": 403
        }))

@app.get("/get-test")
def get_test():
    return  "The server started normal!"

# 查找避难所
@app.get("/query-shelters")
def get_print():
    print("***************************")
    address = request.args.get("address")
    print(address)
    try:
        
        data = queryShelters(address)

        response = api_success_response(data)
        return response
    except Exception as e:
        raise e

# 查找路径
@app.get("/query-routes")
def test():
    address = request.args.get("address")
    shelter_id = request.args.get("shelter_id")

    try:

        data = getRoute(address, int(shelter_id))

        response = api_success_response(data)
        return response
    except Exception as e:
        raise e

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print("The Server Started at 8083!")
    app.run(host='0.0.0.0', port=8083)
    
    # server = pywsgi.WSGIServer(('0.0.0.0', 8083), app)
    # server.serve_forever()
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
