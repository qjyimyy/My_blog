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
from django.shortcuts import redirect
import re
from random import randint
from django.urls import reverse
from django.contrib.auth import login
from django.contrib.auth import authenticate


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
        redis_conn = get_redis_connection('default')  # 连接redis
        redis_sms_code = redis_conn.get('sms:%s'%mobile)  # 获取redis中的图片验证码
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode != redis_sms_code.decode():  # 注意要解码
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
        # 添加状态保持
        login(request, user)

        # 4.返回响应跳转到指定页面
        # redirect 进行重定向，reverse获取到视图所对应的路由
        response = redirect(reverse('home:index'))

        # 设置cookie信息，用户信息展示判断，用户信息展示
        response.set_cookie('is_login', True)
        response.set_cookie('username', user.username, max_age=7*24*3600)

        return response

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

# 短信验证码视图
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

# 登录视图
class LoginView(View):


    def get(self, request):

        return render(request, 'login.html')

    def post(self, request):
        # 1.接受参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        # 2.参数的验证
        #     2.1验证手机号是否符合规则
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不正确')
        #     2.2验证密码是否符合规则
        if not re.match(r'^(?![0-9]+$)(?![a-zA-Z]+$)[0-9A-Za-z]{6,20}$', password):
            return HttpResponseBadRequest('密码不正确')
        # 3.用户认证登录
        # 采用系统自带的认证方法，如果用户名和密码正确，会返回user对象，如果不正确，会返回None
        # 默认方法用的username判断，当前使用的mobile
        # 需要到User模型中修改
        user = authenticate(mobile=mobile, password=password)
        if user is None:
            return HttpResponseBadRequest('用户名或密码错误')
        if password is None:
            return HttpResponseBadRequest('用户名或者密码错误')

        # 4.状态保持
        login(request, user)
        # 5.判断是否保持登录
        # 6.为了首页显示设置需要展示的cookie

        # 根据next参数进行页面跳转
        next_page = request.GET.get('next')
        if next_page:
            response = redirect(next_page)
        else:
            response = redirect(reverse('home:index'))

        if remember != 'on': # 没有保持登录
            # 浏览器关闭之后消失
            request.session.set_expiry(0)
            response.set_cookie('is_login', True)
            response.set_cookie('username', user.username, max_age=14*24*3600)
        else:                # 保持登录
            # 默认记住两周
            request.session.set_expiry(None)
            response.set_cookie('is_login', True, max_age=14*24*3600)
            response.set_cookie('username', user.username, max_age=14*24*3600)


        # 7.返回响应
        return response

from django.contrib.auth import logout
# 登出视图
class LoginOutView(View):

    def get(self, request):
        # 1.session数据清除
        logout(request)
        # 2.删除cookie部分数据
        response = redirect(reverse('home:index'))
        response.delete_cookie('is_login')
        # 3.跳转到首页
        return response
# 忘记密码视图
class ForgetPasswordView(View):
    def get(self, request):

        return render(request, 'forget_password.html')
    def post(self, request):
        '''
        # 1.接受数据
        # 2.验证数据
        #     2.1 判断参数是否齐全
        #     2.2 分别验证手机号是否符合规则
        #     2.3 判断密码是否符合规则
        #     2.4 判断确认密码和密码是否一致
        #     2.5 判断图片验证码是否正确
        # 3.根据手机号进行用户的信息查询
        # 4.如果手机号存在，则进行密码修改
        # 5.如果手机号不存在，则进行新用户创建
        # 6.进行页面跳转
        # 7.返回响应
        '''
        # 1.接受数据
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')
        # 2.验证数据
        #     2.1 判断参数是否齐全
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('参数不全')
        #     2.2 分别验证手机号是否符合规则
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.3 判断密码是否符合规则
        if not re.match(r'^(?![0-9]+$)(?![a-zA-Z]+$)[0-9A-Za-z]{6,20}$', password):
            return HttpResponseBadRequest('密码不符合要求,密码至少包含 数字和英文，长度6-20')
        #     2.4 判断确认密码和密码是否一致
        if password2 != password:
            return HttpResponseBadRequest('两次密码不一致')
        #     2.5 判断图片验证码是否正确
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms:%s'%mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode != redis_sms_code.decode():
            return HttpResponseBadRequest('短信验证码不正确')
        # 3.根据手机号进行用户的信息查询
        try:
            user = User.objects.get(mobile = mobile)
        except User.DoesNotExist:
            # 如果手机号不存在，则进行新用户创建
            try:
                User.objects.create_user(username=mobile,
                                         mobile=mobile,
                                         password=password)
            except Exception:
                return HttpResponseBadRequest('修改失败,请重试')

        else:
            # 如果手机号存在，则进行密码修改
            user.set_password(password)
            # 注意保存user信息
            user.save()



        # 6.进行页面跳转
        response = redirect(reverse('users:login'))
        # 7.返回响应
        return response

from django.contrib.auth.mixins import LoginRequiredMixin
# 如果用户未登录，则会进行默认跳转，默认跳转链接是account/login/?next=xxx(路由)
# 用户中心展示视图
class UserCenterView(LoginRequiredMixin, View):
    def get(self, request):
        # 获取登录用户信息
        user = request.user
        # 组织获取用户信息
        context = {
            'username':user.username,
            'mobile':user.mobile,
            'avatar':user.avatar.url if user.avatar else None,  # 判断头像是否存在，不存在就是None
            'user_desc':user.user_desc
        }
        return render(request, 'center.html', context=context)

