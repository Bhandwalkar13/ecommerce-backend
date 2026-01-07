from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
router.register(r'reviews', ReviewViewSet, basename='reviews')
router.register(r'likes', ProductLikeViewSet, basename='likes')
router.register(r'coupons', CouponViewSet)
router.register(r'recently-viewed', RecentlyViewedViewSet, basename='recently-viewed')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'payment', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
]
