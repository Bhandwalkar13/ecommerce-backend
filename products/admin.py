from django.contrib import admin
from .models import *

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'category', 'in_stock', 'stock_quantity', 'is_featured', 'is_trending', 'likes_count', 'views_count']
    list_filter = ['category', 'in_stock', 'is_featured', 'is_trending']
    search_fields = ['name', 'description']
    list_editable = ['is_featured', 'is_trending', 'in_stock']

admin.site.register(ProductVariant)
admin.site.register(CartItem)
admin.site.register(WishlistItem)
admin.site.register(Review)
admin.site.register(ProductLike)
admin.site.register(RecentlyViewed)
admin.site.register(UserProfile)
admin.site.register(Notification)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'final_amount', 'status', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['user__username', 'tracking_number']
    inlines = [OrderItemInline]
    list_editable = ['status', 'payment_status']

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'valid_from', 'valid_until', 'used_count', 'usage_limit', 'is_active']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code']
