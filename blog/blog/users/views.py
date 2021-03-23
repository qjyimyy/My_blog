from django.shortcuts import render
from django.views import View
from django.http.response import HttpResponseBadRequest
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.http import HttpResponse
# Create your views here.
# 注册视图
class RegisterView(View):

    def get(self, request):

        return render(request, 'register.html')

# 定义视图
class ImageCodeView(View):

    def get(self, request):
        # 1接受前端的UUID
        uuid = request.GET.get('uuid')
        # 2检查UUID是否收到
        if uuid is None:
            return HttpResponseBadRequest('uuid未被接收')
        # 通过调用captcha来生成图片验证码
        text, image = captcha.generate_captcha()
        # 4 将图片内容保存到redis中
        redis_conn = get_redis_connection('default')
        # 参数：uuid，过期秒数，text
        redis_conn.setex('img:%s'%uuid, 300, text)
        # 5返回图片二进制
        return HttpResponse(image, content_type='image/jpeg')



