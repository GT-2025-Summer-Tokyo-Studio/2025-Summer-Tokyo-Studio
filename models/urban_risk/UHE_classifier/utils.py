from flask import jsonify, make_response

# 接口响应通用类
class APIResponse:
    def __init__(self, data=None, message="响应成功", status_code=200):
        self.data = data
        self.message = message
        self.status_code = status_code

    def to_dict(self):
        response_dict = {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code
        }
        return response_dict

# 成功响应的返回
def api_success_response(data, code=200):
    res = APIResponse(data).to_dict()
    return make_response(jsonify(res), code)

def response_code():
    codes = {
        "SUCCESS": 200
    }
    return codes
