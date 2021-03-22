 # 进行users子应用的视图路由
from django.urls import path
from users.views import RegisterView
urlpatterns = [
    # 两个参数：路由，视图函数名
    path('register/', RegisterView.as_view(), name='register'),
]