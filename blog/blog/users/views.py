from django.shortcuts import render
from django.views import View
from django.http.response import HttpResponseBadRequest
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.http import HttpResponse
from django.http.response import JsonResponse
from utils.response_code import RETCODE
import logging
from django.db import DatabaseError
from users.models import User
from libs.yuntongxun.sms import CCP
import re

from random import randint
logger = logging.getLogger('django')
# Create your views here.
# 注册视图
class RegisterView(View):

    def get(self, request):

        return render(request, 'register.html')
    def post(self, request):
        '''
        1.接受数据
        2.验证数据
            2.1 参数是否齐全
            2.2 手机号的格式是否正确
            2.3 密码是否符合格式
            2.4 密码和确认密码是否一致
            2.5 短信验证码是否和redis中的一致
        3.保存注册信息
        4.返回响应跳转到指定页面
        '''
        # 1.接受数据
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')
        # 2.验证数据
        #     2.1 参数是否齐全
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('缺少必要参数')
        #     2.2 手机号的格式是否正确
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合格式')

        #     2.3 密码是否符合格式
        if not re.match(r'^(?![0-9]+$)(?![a-zA-Z]+$)[0-9A-Za-z]{6,20}$', password):
            return HttpResponseBadRequest('密码不符合要求,密码至少包含 数字和英文，长度6-20')
        #     2.4 密码和确认密码是否一致
        if password2 != password:
            return HttpResponseBadRequest('两次密码不一致')
        #     2.5 短信验证码是否和redis中的一致
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms:%s'%mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode != redis_sms_code.decode():
            return HttpResponseBadRequest('短信验证码不正确')
        # 3.保存注册信息
        # create_user 可以对密码进行加密
        try:
            user = User.objects.create_user(username=mobile,
                                            mobile=mobile,
                                            password=password)
        except DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest('注册失败')
        # 4.返回响应跳转到指定页面
        return HttpResponse('注册成功,重定向到首页')

# 定义图片验证码视图
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


class SmsCodeView(View):

    def get(self, request):
        '''
        1,接受参数
        2.参数验证
            2.1验证参数是否齐全
            2.2 图片验证码的验证
                连接redis，获取到redis中的图片验证码
                判断图片验证码是否存在
                若未过期，获取到之后就可以删除图片验证码
                比对图片验证码
        3.生成短信验证码
        4.将短信验证码保存在redis中
        5.发送短信
        6.返回响应
        '''
        # TODO 1 查询字符串
        mobile = request.GET.get('mobile')
        image_code = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        # TODO 2
            # TODO 2.1 验证参数是否齐全
        if not all([mobile, image_code, uuid]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errorMessage': '缺少必要参数'})
            # TODO 2.2 图片验证码的验证
            # 连接redis
        redis_conn = get_redis_connection('default')
        redis_image_code = redis_conn.get("img:%s"%uuid)
            # 判断验证码是否存在
        if redis_image_code == None:
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errorMassage': '图片验证码不存在'})
        #        若未过期，获取到之后就可以删除图片验证码
        try:
            redis_conn.delete('img:%s' % uuid)
        except Exception as e:
            logger.error(e)
        #         比对图片验证码,注意 大小写，redis数据是bytes类型
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errorMessage': '图片验证码不正确'})
        #3.生成短信验证码
        sms_code = '%6d'%randint(0, 999999)
        # 为了后期比对方便
        logger.info(sms_code)
        # 4.将短信验证码保存在redis中
        redis_conn.setex('sms:%s'%mobile, 300, sms_code)
        # 5.发送短信
        CCP().send_template_sms(mobile, [sms_code, 5], 1)
        # 6.返回响应
        return JsonResponse({'code': RETCODE.OK, 'errorMessage': '短信发送成功'})


        pass

