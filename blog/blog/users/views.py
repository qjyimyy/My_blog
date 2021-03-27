from django.shortcuts import render
from django.views import View
from django.http.response import HttpResponseBadRequest
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.http import HttpResponse
from django.http.response import JsonResponse
from utils.response_code import RETCODE
import logging
from libs.yuntongxun.sms import CCP

from random import randint
logger = logging.getLogger('django')
# Create your views here.
# 注册视图
class RegisterView(View):

    def get(self, request):

        return render(request, 'register.html')

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

